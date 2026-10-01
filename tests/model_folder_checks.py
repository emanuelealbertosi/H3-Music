"""Model-location checks needing only Python, on Windows and both Mac CPUs."""
from pathlib import Path
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
suite = unittest.TestSuite()
for name in ('model_store', 'macos_space', 'platform_runtime', 'transcription_update', 'windows_engine'):
    suite.addTests(unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='test_' + name + '.py'))
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
