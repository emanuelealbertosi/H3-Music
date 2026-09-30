"""Test the actual .command launcher with simulated Homebrew processes."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which('bash') if os.name != 'nt' else 'C:/Program Files/Git/bin/bash.exe'


class InstallerShellTests(unittest.TestCase):
    def run_installer(self, failure='', version='27.0'):
        with tempfile.TemporaryDirectory(prefix='tmp-mac-shell-', dir=ROOT / 'tests') as directory:
            root = Path(directory)
            launcher = root / 'Installa-Mac.command'
            launcher.write_bytes((ROOT / 'Installa-Mac.command').read_bytes().replace(b'\r\n', b'\n'))
            prefix = root / 'python'
            (prefix / 'bin').mkdir(parents=True)
            python = prefix / 'bin/python3.12'
            python.write_text('#!/bin/bash\necho runtime >> "$H3_TEST_LOG"\n', encoding='utf-8')
            python.chmod(0o755)
            fixture = root / 'fixture.sh'
            fixture.write_text('''sw_vers() { echo "$H3_TEST_VERSION"; }
brew() {
  echo "$1" >> "$H3_TEST_LOG"
  if [ "$1" = "$H3_TEST_FAILURE" ]; then
    echo "Error: unknown or unsupported macOS version: :dunno" >&2
    return 9
  fi
  if [ "$1" = "--prefix" ]; then echo "$H3_TEST_PREFIX"; fi
  return 0
}
''', encoding='utf-8')
            log = root / 'commands.log'
            env = os.environ | {'BASH_ENV': fixture.as_posix(), 'H3_TEST_LOG': log.as_posix(),
                'H3_TEST_PREFIX': prefix.as_posix(), 'H3_TEST_FAILURE': failure, 'H3_TEST_VERSION': version}
            result = subprocess.run([BASH, str(launcher)], cwd=root, env=env, input='\n',
                capture_output=True, encoding='utf-8', timeout=20)
            return result, log.read_text().splitlines() if log.exists() else []

    def test_update_precedes_install_and_success_means_runtime_finished(self):
        result, commands = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(commands, ['update', 'install', '--prefix', 'runtime'])
        self.assertIn('Installazione completata', result.stdout + result.stderr)

    def test_failed_update_does_not_start_install_or_report_success(self):
        result, commands = self.run_installer(failure='update')
        self.assertEqual(result.returncode, 9)
        self.assertEqual(commands, ['update'])
        self.assertIn('Installazione NON completata', result.stdout)
        self.assertNotIn('Installazione completata', result.stdout)

    def test_failed_install_does_not_start_runtime_or_report_success(self):
        result, commands = self.run_installer(failure='install')
        self.assertEqual(result.returncode, 9)
        self.assertEqual(commands, ['update', 'install'])
        self.assertIn('Installazione NON completata', result.stdout)
        self.assertNotIn('Installazione completata', result.stdout)

    def test_unsupported_macos_is_rejected_before_changing_homebrew(self):
        result, commands = self.run_installer(version='14.7')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(commands, [])
        self.assertIn('richiede macOS 15', result.stdout)


if __name__ == '__main__':
    unittest.main()
