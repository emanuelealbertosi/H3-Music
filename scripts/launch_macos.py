"""Start the local service on macOS and open its browser window."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
URL = 'http://127.0.0.1:' + os.environ.get('H3_MUSIC_PORT', '8776')


def healthy():
    try:
        with urllib.request.urlopen(URL + '/api/health', timeout=2) as response:
            state = json.load(response)
            return state.get('app') == 'H3-Music' and state.get('status') == 'ok'
    except (OSError, ValueError, urllib.error.URLError):
        return False


def main():
    if '--stop' in sys.argv:
        if healthy():
            request = urllib.request.Request(URL + '/api/shutdown', data=b'{}',
                headers={'Content-Type': 'application/json', 'X-H3-Music': '1'})
            with urllib.request.urlopen(request, timeout=10):
                pass
        return
    if not healthy():
        logs = ROOT / 'logs'
        logs.mkdir(exist_ok=True)
        with (logs / 'server-mac.log').open('ab') as log:
            process = subprocess.Popen([sys.executable, str(ROOT / 'app.py')], cwd=ROOT,
                stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        for _ in range(40):
            if healthy():
                break
            if process.poll() is not None:
                raise RuntimeError('Avvio fallito: consulta logs/server-mac.log.')
            time.sleep(.5)
        else:
            raise RuntimeError('Il servizio non risponde: consulta logs/server-mac.log.')
    subprocess.run(['open', URL], check=True)


if __name__ == '__main__':
    main()
