"""Native Mac service/database/FFmpeg/runtime checks without multi-GB weights."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import execution
import platform_runtime

assert sys.platform == 'darwin'
execution.check_engine(platform_runtime.binary(ROOT, 'audiocpp_cli', True), 'cpu')
execution.check_torch(platform_runtime.python(ROOT, 'transcription'))
with socket.socket() as listener:
    listener.bind(('127.0.0.1', 0))
    port = listener.getsockname()[1]
url = f'http://127.0.0.1:{port}/api/'


def api(name, data=None):
    request = urllib.request.Request(url + name, data=json.dumps(data).encode() if data is not None else None,
        headers={'Content-Type': 'application/json', 'X-H3-Music': '1'})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


with tempfile.TemporaryDirectory(prefix='H3 Music Mac ') as directory:
    env = os.environ | {'H3_MUSIC_DATA': directory, 'H3_MUSIC_PORT': str(port)}
    process = subprocess.Popen([sys.executable, str(ROOT / 'app.py')], cwd=ROOT, env=env)
    try:
        for _ in range(60):
            try:
                if api('health')['app'] == 'H3-Music':
                    break
            except OSError:
                pass
            time.sleep(.2)
        else:
            raise AssertionError('Mac service failed to start')
        state = api('state')
        assert state['settings']['backend'] == 'cpu'
        assert state['runtime']['backends'] == ['cpu', 'metal']
        assert api('system')['memory']['total_gb'] > 0
        api('settings', {'paused': True})
        project = api('projects', {'title': 'Test Mac', 'abc': 'X:1\nT:Test\nM:4/4\nL:1/4\nK:C\nCDEF|'})
        assert project['id'] in [p['id'] for p in api('state')['projects']]
        wav = Path(directory) / 'test.wav'
        subprocess.run([str(platform_runtime.binary(ROOT, 'ffmpeg')), '-v', 'error', '-f', 'lavfi',
            '-i', 'sine=frequency=440:duration=1', str(wav)], check=True)
        assert wav.stat().st_size > 1000
        # Spaces in package/data paths and native FFmpeg must work.
        subprocess.run([str(platform_runtime.binary(ROOT, 'ffprobe')), '-v', 'error', '-show_entries',
            'format=duration', '-of', 'json', str(wav)], check=True)
        api('shutdown', {})
        process.wait(timeout=15)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=15)
print('Native Mac smoke checks passed')
