import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import macos_space


class MacSpaceTests(unittest.TestCase):
    def test_fresh_q4_fits_below_previous_fixed_20_gib_limit(self):
        entries = list(macos_space.model_entries(ROOT, 'q4'))
        with patch.object(macos_space, 'model_entries', return_value=entries), patch.object(macos_space, 'matches', return_value=False), patch.object(macos_space.shutil, 'disk_usage', return_value=SimpleNamespace(free=20_000_000_000)):
            result = macos_space.check(ROOT, 'q4')
        self.assertGreater(result['required'], 12_000_000_000)
        self.assertLess(result['required'], 20_000_000_000)

    def test_bf16_needs_more_space_than_q4(self):
        with patch.object(macos_space, 'matches', return_value=False):
            q4 = macos_space.estimate(ROOT, 'q4')
            bf16 = macos_space.estimate(ROOT, 'bf16')
        self.assertEqual(bf16['models'] - q4['models'], 7261475392 - 2665632320)

    def test_windows_both_adds_q8_without_duplicating_shared_models(self):
        with patch.object(macos_space, 'matches', return_value=False):
            q4 = macos_space.estimate(ROOT, 'q4')
            both = macos_space.estimate(ROOT, 'both')
        self.assertEqual(both['models'] - q4['models'], 4264186432)

    def test_separate_disks_check_models_and_runtime_independently(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests', prefix='tmp-space-') as directory:
            root = Path(directory); target = root / 'external'; target.mkdir()
            with patch.object(macos_space.model_store, 'location', return_value=target), patch.object(macos_space, 'model_entries', return_value=[]), patch.object(macos_space, 'same_volume', return_value=False), patch.object(macos_space.shutil, 'disk_usage', side_effect=lambda p: SimpleNamespace(free=8_000_000_000 if Path(p) == target else 2_000_000_000)):
                with self.assertRaisesRegex(RuntimeError, 'Python e le librerie'):
                    macos_space.check(root, 'q4')

    def test_verified_existing_files_reduce_space_but_corrupt_files_do_not(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests', prefix='tmp-space-') as directory:
            root = Path(directory)
            file = root / 'weight'
            file.write_bytes(b'good')
            entry = {'size': 4, 'lfs': {'oid': hashlib.sha256(b'good').hexdigest()}}
            with patch.object(macos_space, 'model_entries', side_effect=lambda *_: [(file, entry)]):
                complete = macos_space.estimate(root, 'q4')
                file.write_bytes(b'evil')
                corrupted = macos_space.estimate(root, 'q4')
                file.write_bytes(b'go')
                partial = macos_space.estimate(root, 'q4')
            self.assertEqual(complete['models'], 0)
            self.assertEqual(corrupted['models'], 4)
            self.assertEqual(partial['models'], 4)

    def test_low_space_error_reports_actual_folder_free_and_required_gb(self):
        with patch.object(macos_space, 'estimate', return_value={'models': 1_000_000_000, 'required': 7_000_000_000, 'free': 2_000_000_000}):
            with self.assertRaisesRegex(RuntimeError, '2.0 GB liberi effettivi, circa 7.0 GB necessari'):
                macos_space.check(ROOT, 'q4')


if __name__ == '__main__':
    unittest.main()
