"""Isolated browser test runner: never touches installed models or preferences."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def serve(root):
    import app
    app.ROOT = root
    app.DATA = root / 'data'; app.OUT = app.DATA / 'outputs'
    app.MODEL = root / 'models/yue2'; app.TOOLS = root / 'models/tools'
    app.VOCI = app.DATA / 'voci'
    app.MUSIC_MODELS = dict(app.MUSIC_MODELS) | {'q4': ('yue2-3b-q4_0.gguf', 5, 'Q4')}
    app.init(); app.save_settings(app.DEFAULTS | {'backend': 'cpu', 'model': 'q4'})
    server = app.http.server.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
    app.PORT = server.server_port
    (root / 'server.json').write_text(json.dumps({'port': app.PORT}))
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main():
    if '--serve' in sys.argv:
        serve(Path(sys.argv[-1])); return
    with tempfile.TemporaryDirectory(dir=ROOT / 'tests', prefix='tmp-model-ui-') as directory:
        base = Path(directory); root = base / 'app'; root.mkdir()
        shutil.copytree(ROOT / 'static', root / 'static')
        for name, data in {'models/yue2/yue2-3b-q4_0.gguf': b'music',
                           'models/yue2/sidecars/test.json': b'{}',
                           'models/tools/HTDemucs-GGUF/sep.gguf': b'sep',
                           'models/tools/SeedVC-MLX-GGUF/voice.gguf': b'voice',
                           'models/manifest.json': b'[]', 'models/tools-manifest.json': b'{}'}.items():
            p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
        (root / 'models/installed-models.json').write_text(json.dumps({'files': {
            'yue2-3b-q4_0.gguf': {'size': 5}, 'sidecars/test.json': {'size': 2}}}))
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--serve', str(root)],
                                   creationflags=0x08000000 if os.name == 'nt' else 0)
        url = None
        try:
            for _ in range(100):
                if (root / 'server.json').exists():
                    url = 'http://127.0.0.1:' + str(json.loads((root / 'server.json').read_text())['port']); break
                if process.poll() is not None: raise RuntimeError('Fixture server stopped')
                time.sleep(.1)
            if not url: raise RuntimeError('Fixture server timed out')
            env = dict(os.environ, H3_TEST_URL=url, H3_MODEL_DESTINATION=str(base / 'Modelli è musica'))
            for script in ('ui_execution.cjs', 'ui_model_location.cjs', 'ui_studio_result.cjs', 'ui_library_cleanup.cjs'):
                subprocess.run([shutil.which('node'), str(ROOT / 'tests' / script)], env=env, check=True)
        finally:
            if url:
                try:
                    request = urllib.request.Request(url + '/api/shutdown', data=b'{}', headers={'X-H3-Music': '1'})
                    urllib.request.urlopen(request, timeout=5).close()
                except OSError: pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate(); process.wait()


if __name__ == '__main__':
    main()
