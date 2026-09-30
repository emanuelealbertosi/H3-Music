import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import platform_runtime
import transcription
from scripts.install_macos import transcription_requirements
from scripts import launch_macos
from scripts import install_macos


class PlatformRuntimeTests(unittest.TestCase):
    def test_windows_paths_preserved(self):
        with patch.object(platform_runtime.sys, 'platform', 'win32'):
            self.assertEqual(platform_runtime.binary(Path('app'), 'ffmpeg'), Path('app/runtime/ffmpeg.exe'))
            self.assertEqual(platform_runtime.python(Path('app')), Path('app/runtime/python/python.exe'))
            self.assertEqual(platform_runtime.backends(), ['cpu', 'cuda'])

    def test_mac_paths_and_transcription_backend(self):
        with patch.object(platform_runtime.sys, 'platform', 'darwin'):
            self.assertEqual(platform_runtime.binary(Path('app'), 'audiocpp_cli', True), Path('app/runtime/engine/audiocpp_cli'))
            self.assertEqual(platform_runtime.python(Path('app'), 'transcription'), Path('app/runtime/transcription/bin/python'))
            self.assertEqual(platform_runtime.backends(), ['cpu', 'metal'])
            self.assertEqual(platform_runtime.transcription_backend('metal'), 'cpu')

    def test_mac_status_uses_venv_root_for_marker(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(platform_runtime.sys, 'platform', 'darwin'):
            state = transcription.status(Path(directory), 'metal')
            self.assertIn('runtime/transcription/installed.json', state['missing'])
            self.assertIn('runtime/transcription/bin/python', state['missing'])
            self.assertNotIn('runtime/transcription/bin/installed.json', state['missing'])

    def test_transcription_versions_match_available_architecture(self):
        self.assertIn('torch==2.8.0', transcription_requirements('arm64'))
        self.assertIn('torch==2.2.2', transcription_requirements('x86_64'))

    def test_launcher_recognizes_only_h3_health(self):
        import io
        with patch.object(launch_macos.urllib.request, 'urlopen', return_value=io.BytesIO(b'{"app":"H3-Music","status":"ok"}')):
            self.assertTrue(launch_macos.healthy())
        with patch.object(launch_macos.urllib.request, 'urlopen', return_value=io.BytesIO(b'{"status":"ok"}')):
            self.assertFalse(launch_macos.healthy())

    def test_homebrew_updates_before_installing_dependencies(self):
        with patch.dict(install_macos.os.environ, {'H3_MUSIC_BREW_UPDATED': ''}), patch.object(install_macos, 'run') as run:
            install_macos.prepare_homebrew()
        self.assertEqual(run.call_args_list[0].args, ('brew', 'update'))
        self.assertEqual(run.call_args_list[1].args, ('brew', 'install', '--skip-link', 'python@3.12', 'python@3.11', 'ffmpeg'))

    def test_homebrew_update_failure_prevents_install(self):
        import subprocess
        with patch.dict(install_macos.os.environ, {'H3_MUSIC_BREW_UPDATED': ''}), patch.object(install_macos, 'run', side_effect=subprocess.CalledProcessError(1, ['brew', 'update'])) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                install_macos.prepare_homebrew()
        self.assertEqual(run.call_count, 1)

    def test_homebrew_is_not_updated_twice_by_command_launcher(self):
        with patch.dict(install_macos.os.environ, {'H3_MUSIC_BREW_UPDATED': '1'}), patch.object(install_macos, 'run') as run:
            install_macos.prepare_homebrew()
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[1], 'install')


if __name__ == '__main__':
    unittest.main()
