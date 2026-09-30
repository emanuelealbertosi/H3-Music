"""Build a Mac ZIP from tracked public files plus the native patched engine."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', type=Path, required=True)
    args = parser.parse_args()
    architecture = platform.machine()
    if platform.system() != 'Darwin' or architecture not in ('arm64', 'x86_64'):
        parser.error('Run on a native macOS build runner.')
    dependencies = subprocess.check_output(['otool', '-L', str(args.engine)], text=True)
    for line in dependencies.splitlines()[1:]:
        dependency = line.strip().split(' (')[0]
        if not dependency.startswith(('/usr/lib/', '/System/Library/')):
            raise RuntimeError('Non-system dependency must be bundled: ' + dependency)
    output = ROOT / 'release-output'
    output.mkdir(exist_ok=True)
    name = f'H3-Music-Mac-{architecture}.zip'
    files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    with zipfile.ZipFile(output / name, 'w', zipfile.ZIP_DEFLATED) as package:
        for relative in files:
            if not relative or relative.startswith(('dist/', '.github/', 'tests/')) or relative.endswith(('.exe', '.bat', '.ps1', '.cs')):
                continue
            info = zipfile.ZipInfo('H3-Music/' + relative)
            info.create_system = 3
            info.external_attr = (0o100755 if relative.endswith('.command') else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            package.writestr(info, (ROOT / relative).read_bytes())
        info = zipfile.ZipInfo('H3-Music/runtime/engine/audiocpp_cli')
        info.create_system = 3
        info.external_attr = 0o100755 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        package.writestr(info, args.engine.read_bytes())
        package.writestr('H3-Music/runtime/engine/mac-build.json', json.dumps({
            'source': '13c4192a28d6a212f075c4cbefc5e4983e6ed52a',
            'h3_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'architecture': architecture, 'backends': ['cpu', 'metal'],
            'min_macos': '15', 'h3_artifacts': True}, indent=2))
    with (output / name).open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    (output / (name + '.sha256')).write_text(digest + '  ' + name + '\n')
    print(output / name)


if __name__ == '__main__':
    main()
