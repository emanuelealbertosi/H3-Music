"""macOS installer: local venvs, pinned models and a precompiled native engine."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import platform_runtime
import execution
import model_store
from scripts import macos_space

RELEASE = 'v1.6.1-macos-preview.1'
DOWNLOAD = 'https://github.com/emanuelealbertosi/H3-Music/releases/download/' + RELEASE


def run(*args):
    subprocess.run([str(x) for x in args], check=True, cwd=ROOT)


def check_idle():
    database = ROOT / 'data/music.sqlite'
    if database.exists():
        with sqlite3.connect(database) as connection:
            if connection.execute("SELECT 1 FROM jobs WHERE status IN ('queued','running','cancelling') LIMIT 1").fetchone():
                raise RuntimeError('Attendi o annulla i lavori in coda prima di installare o aggiornare.')
    url = 'http://127.0.0.1:' + os.environ.get('H3_MUSIC_PORT', '8776') + '/api/health'
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            active = json.load(response).get('app') == 'H3-Music'
    except (OSError, ValueError):
        active = False
    if active:
        raise RuntimeError('Chiudi il servizio con Ferma-Mac.command prima di installare o aggiornare.')


def brew_path(formula, name):
    prefix = subprocess.check_output(['brew', '--prefix', formula], text=True).strip()
    return Path(prefix) / 'bin' / name


def prepare_homebrew():
    os.environ['HOMEBREW_NO_AUTO_UPDATE'] = '1'
    # Formulae use macOS names added in newer Homebrew versions. Update brew
    # itself first, including on macOS 27; don't upgrade unrelated packages.
    if os.environ.get('H3_MUSIC_BREW_UPDATED') != '1':
        print('Aggiornamento di Homebrew…', flush=True)
        run('brew', 'update')
    # Use each formula's own prefix. Do not overwrite a Python already
    # installed by the user (or the Python.org tools on CI Intel runners).
    run('brew', 'install', '--skip-link', 'python@3.12', 'python@3.11', 'ffmpeg')


def install_engine():
    engine = platform_runtime.binary(ROOT, 'audiocpp_cli', engine=True)
    if engine.is_file():
        execution.check_engine(engine, 'cpu')
        return
    architecture = platform.machine()
    if architecture not in ('arm64', 'x86_64'):
        raise RuntimeError('Architettura Mac non supportata: ' + architecture)
    name = f'H3-Music-Mac-{architecture}.zip'
    print('Scarico il motore Mac precompilato…', flush=True)
    temp = ROOT / 'runtime/install-temp'
    temp.mkdir(parents=True, exist_ok=True)
    archive = temp / name
    with urllib.request.urlopen(DOWNLOAD + '/SHA256SUMS.txt', timeout=60) as response:
        sums = dict((line.split()[1], line.split()[0]) for line in response.read().decode().splitlines())
    with urllib.request.urlopen(DOWNLOAD + '/' + name, timeout=120) as response, archive.open('wb') as output:
        shutil.copyfileobj(response, output)
    with archive.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != sums[name]:
            raise RuntimeError('Pacchetto Mac non integro: riprova l’installazione.')
    with zipfile.ZipFile(archive) as package:
        content = package.read('H3-Music/runtime/engine/audiocpp_cli')
    engine.parent.mkdir(parents=True, exist_ok=True)
    staged = engine.with_suffix('.tmp')
    staged.write_bytes(content)
    staged.chmod(0o755)
    execution.check_engine(staged, 'cpu')
    staged.replace(engine)
    archive.unlink()


def transcription_requirements(architecture):
    # PyTorch stopped shipping Intel macOS wheels after 2.2.2. Keep the same
    # model revisions and SDPA inference; use the last supported Intel runtime.
    version = '2.8.0' if architecture == 'arm64' else '2.2.2'
    return [f'torch=={version}', f'torchaudio=={version}',
            'transformers==4.45.2', 'huggingface-hub==0.36.0',
            'safetensors==0.5.3', 'numpy==1.24.3', 'scipy==1.13.1',
            'mir_eval==0.8.2', 'pretty_midi==0.2.10', 'mido==1.3.3',
            'setuptools==78.1.1']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-models', action='store_true', help='Prepare runtimes only (CI).')
    parser.add_argument('--quant', choices=('q4', 'q8', 'bf16'), default='q4')
    parser.add_argument('--models-dir', help='Cartella dedicata ai modelli; trasferisce quelli già installati.')
    args = parser.parse_args()
    if not platform_runtime.macos():
        parser.error('Questo installatore è riservato a macOS.')
    if int(platform.mac_ver()[0].split('.')[0]) < 15:
        parser.error('Questa anteprima richiede macOS 15 o successivo.')
    check_idle()
    if args.models_dir:
        with model_store.exclusive(ROOT):
            model_store.check_idle(ROOT)
            model_store.relocate(ROOT, args.models_dir)
    if not shutil.which('brew'):
        raise RuntimeError('Installa prima Homebrew da https://brew.sh, poi riapri Installa-Mac.command.')
    if not args.no_models:
        macos_space.check(ROOT, args.quant)
    prepare_homebrew()
    runtime = ROOT / 'runtime'
    runtime.mkdir(exist_ok=True)
    for component, formula, executable in [('python', 'python@3.12', 'python3.12'),
                                           ('transcription', 'python@3.11', 'python3.11')]:
        destination = runtime / component
        interpreter = platform_runtime.python(ROOT, component)
        if not interpreter.is_file():
            run(brew_path(formula, executable), '-m', 'venv', destination)
    for name in ('ffmpeg', 'ffprobe'):
        target = runtime / name
        if target.is_symlink():
            target.unlink()
        if not target.exists():
            target.symlink_to(brew_path('ffmpeg', name))
    install_engine()
    py = platform_runtime.python(ROOT, 'transcription')
    marker = runtime / 'transcription/installed.json'
    expected = transcription_requirements(platform.machine())
    try:
        reusable = json.loads(marker.read_text())['requirements'] == expected
        if reusable:
            execution.check_torch(py)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        reusable = False
    if not reusable:
        run(py, '-m', 'pip', 'install', '--no-cache-dir', *expected)
        execution.check_torch(py)
        marker.write_text(json.dumps({'requirements': expected, 'platform': platform.machine()}))
    main_py = platform_runtime.python(ROOT)
    if not args.no_models:
        run(main_py, 'scripts/download_models.py', '--quant', args.quant)
        run(main_py, 'scripts/download_tools.py', '--tool', 'all')
        run(main_py, 'scripts/install_transcription.py', '--backend', 'cpu', '--models-only')
    # Preserve all preferences during a repair/update. CPU is set only once.
    import app
    app.init()
    if not app.db('SELECT value FROM settings WHERE key=?', ('main',), True):
        app.save_settings(app.DEFAULTS | {'backend': 'cpu', 'model': args.quant})
    print('H3-Music pronto. Apri Avvia-Mac.command.', flush=True)


if __name__ == '__main__':
    main()
