import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import platform_runtime
import transcription
from scripts.install_macos import transcription_requirements


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


if __name__ == '__main__':
    unittest.main()
