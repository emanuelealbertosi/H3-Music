import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app
import model_store
import transcription
from scripts import download_models, download_tools, install_transcription, macos_space


class ModelStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / 'tests', prefix='tmp-store-')
        self.base = Path(self.tmp.name)
        self.root = self.base / 'app'
        self.source = self.root / 'models'
        self.source.mkdir(parents=True)
        self.target = self.base / 'Modelli è musica'
        self.contents = {'yue2/model.gguf': b'music', 'yue2/sidecars/config.json': b'{}',
                         'tools/SeedVC-MLX-GGUF/voice.gguf': b'voice', 'tools/HTDemucs-GGUF/sep.gguf': b'sep',
                         'SheetSage2/model.safetensors': b'sheet', 'MERT-v2-FullSong/model.safetensors': b'mert',
                         'installed-models.json': b'{"files":{}}', 'tools-installed.json': b'{}',
                         'transcription-manifest.json': b'{"sheet_revision":"test"}',
                         'yue2/download.partial': b'partial'}
        for relative, content in self.contents.items():
            p = self.source / relative
            p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(content)
        for name in model_store.METADATA:
            (self.source / name).write_bytes(b'metadata')

    def tearDown(self):
        self.tmp.cleanup()

    def move(self, **kwargs):
        with model_store.exclusive(self.root):
            return model_store.relocate(self.root, str(self.target), **kwargs)

    def test_move_preserves_all_modules_records_partials_and_repository_metadata(self):
        progress = []
        result = self.move(progress=lambda **p: progress.append(p))
        self.assertEqual(result['path'], str(self.target.resolve()))
        for relative, content in self.contents.items():
            self.assertEqual((self.target / relative).read_bytes(), content)
            self.assertFalse((self.source / relative).exists())
        for name in model_store.METADATA:
            self.assertEqual((self.source / name).read_bytes(), b'metadata')
        self.assertEqual(model_store.location(self.root), self.target.resolve())
        self.assertEqual(transcription.installed_revision(self.root), 'test')
        self.assertEqual(progress[-1]['status'], 'cleaning')
        self.assertEqual(progress[-1]['done'], sum(map(len, self.contents.values())))

    def test_failed_verification_keeps_old_location_and_every_source_file(self):
        with patch.object(model_store, 'digest', return_value='corrupted'):
            with self.assertRaisesRegex(ValueError, 'Verifica'):
                self.move()
        self.assertEqual(model_store.location(self.root), self.source)
        self.assertFalse(any(self.target.iterdir()))
        for relative, content in self.contents.items():
            self.assertEqual((self.source / relative).read_bytes(), content)

    def test_failed_configuration_commit_rolls_back_published_files(self):
        with patch.object(model_store, 'save_location', side_effect=OSError('disk error')):
            with self.assertRaises(OSError):
                self.move()
        self.assertFalse(any(self.target.rglob('*.*')))
        for relative, content in self.contents.items():
            self.assertEqual((self.source / relative).read_bytes(), content)

    def test_nonempty_destination_is_never_overwritten(self):
        self.target.mkdir(); (self.target / 'important.txt').write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError, 'vuota'):
            self.move()
        self.assertEqual((self.target / 'important.txt').read_bytes(), b'keep')
        self.assertEqual(model_store.location(self.root), self.source)

    def test_existing_store_selection_does_not_delete_old_models(self):
        (self.target / 'yue2').mkdir(parents=True)
        (self.target / 'yue2/new.gguf').write_bytes(b'new')
        self.move(transfer=False)
        self.assertEqual(model_store.location(self.root), self.target)
        self.assertTrue((self.source / 'yue2/model.gguf').exists())

    def test_rejects_relative_nested_and_app_paths(self):
        for value in ('relative', str(self.source / 'nested'), str(self.base), str(self.root), str(self.root / 'data')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                model_store.validate_destination(self.root, self.source, value, True)

    def test_low_disk_space_changes_nothing(self):
        from types import SimpleNamespace
        with patch.object(model_store.shutil, 'disk_usage', return_value=SimpleNamespace(free=1)):
            with self.assertRaisesRegex(ValueError, 'Spazio insufficiente'):
                self.move()
        self.assertFalse(self.target.exists())
        self.assertEqual(model_store.location(self.root), self.source)

    def test_lock_prevents_concurrent_downloads_and_is_released_after_failure(self):
        with self.assertRaises(RuntimeError):
            with model_store.exclusive(self.root):
                with self.assertRaises(ValueError):
                    with model_store.exclusive(self.root):
                        self.fail('Second writer acquired the model lock')
                raise RuntimeError()
        with model_store.exclusive(self.root):
            pass

    def test_downloaders_reuse_files_in_external_store_without_network(self):
        self.move()
        weight = {'path': 'model.gguf', 'size': 5, 'lfs': None}
        with patch.object(download_models.urllib.request, 'urlopen', side_effect=AssertionError('network')):
            self.assertEqual(download_models.download(self.root, weight, 'revision', {'size': 5, 'sha256': 'known'}), 'known')
        tool = {'directory': 'HTDemucs-GGUF', 'file': 'sep.gguf', 'size': 3}
        with patch.object(download_tools.urllib.request, 'urlopen', side_effect=AssertionError('network')):
            self.assertEqual(download_tools.download(self.root, {}, tool, {'sha256': 'known'}), 'known')

    def test_transcription_updates_and_manifest_use_external_store(self):
        self.move()
        (self.target / 'MERT-v2-FullSong/modeling_mert2.py').write_bytes(b'model code')
        (self.target / 'MERT-v2-FullSong/configuration_mert2.py').write_bytes(b'config code')
        (self.target / 'SheetSage2/modeling_sheetsage2.py').write_bytes(b'sheet code')
        with patch.object(install_transcription, 'r', self.root):
            install_transcription.manifest()
        manifest = json.loads((self.target / 'transcription-manifest.json').read_text())
        for relative, sha in manifest['sha256'].items():
            self.assertEqual(model_store.digest(self.target / relative.removeprefix('models/')), sha)

    def test_offline_configured_store_does_not_switch_to_empty_destination(self):
        model_store.save_location(self.root, self.base / 'missing disk')
        with self.assertRaisesRegex(ValueError, 'non è disponibile'):
            self.move()
        self.assertEqual(model_store.location(self.root), self.base / 'missing disk')


class AppModelStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / 'tests', prefix='tmp-location-api-')
        self.base = Path(self.tmp.name); self.root = self.base / 'app'; self.root.mkdir()
        self.stack = []
        for name, value in [('ROOT', self.root), ('DATA', self.root / 'data'), ('OUT', self.root / 'data/outputs'),
                            ('MODEL', self.root / 'models/yue2'), ('TOOLS', self.root / 'models/tools'),
                            ('MODEL_OPERATION', {'status': 'idle'})]:
            p = patch.object(app, name, value); p.start(); self.stack.append(p)
        app.init(); app.save_settings(app.DEFAULTS | {'backend': 'cuda', 'model': 'bf16', 'threads': 6})
        self.target = self.base / 'external'
        (app.MODEL / 'sidecars').mkdir(parents=True)
        (app.MODEL / 'main.gguf').write_bytes(b'music')
        (app.TOOLS / 'HTDemucs-GGUF').mkdir(parents=True)
        (app.TOOLS / 'HTDemucs-GGUF/sep.gguf').write_bytes(b'sep')
        (app.TOOLS / 'SeedVC-MLX-GGUF').mkdir()
        (app.TOOLS / 'SeedVC-MLX-GGUF/voice.gguf').write_bytes(b'voice')

    def tearDown(self):
        for p in reversed(self.stack): p.stop()
        self.tmp.cleanup()

    def wait(self):
        deadline = time.monotonic() + 10
        while app.model_location_status()['operation']['status'] not in ('completed', 'failed'):
            if time.monotonic() > deadline: self.fail('transfer timed out')
            time.sleep(.02)
        # Wait until the thread also releases the model lock.
        with app.LOCK: pass

    def test_background_change_updates_all_app_paths_and_keeps_preferences(self):
        before = app.settings()
        app.change_model_location({'path': str(self.target), 'transfer': True}); self.wait()
        self.assertEqual(app.model_location_status()['operation']['status'], 'completed')
        self.assertEqual(app.MODEL, self.target / 'yue2')
        self.assertEqual(app.separation_model(), self.target / 'tools/HTDemucs-GGUF')
        self.assertEqual(app.voice_model(), self.target / 'tools/SeedVC-MLX-GGUF')
        self.assertEqual(app.settings(), before)

    def test_queued_running_and_cancelling_jobs_block_relocation(self):
        for status in ('queued', 'running', 'cancelling'):
            app.db('DELETE FROM jobs')
            app.db('INSERT INTO jobs(id,status) VALUES(?,?)', ('test', status))
            with self.subTest(status=status), self.assertRaisesRegex(ValueError, 'lavori in coda'):
                app.change_model_location({'path': str(self.target)})
        app.db('DELETE FROM jobs')
        with model_store.exclusive(self.root): pass

    def test_jobs_cannot_be_enqueued_during_transfer(self):
        copying = threading.Event(); release = threading.Event()
        original = model_store.digest
        def verify(path):
            copying.set(); release.wait(5); return original(path)
        with patch.object(model_store, 'digest', side_effect=verify):
            app.change_model_location({'path': str(self.target)})
            self.assertTrue(copying.wait(5))
            try:
                with self.assertRaisesRegex(ValueError, 'in uso'):
                    app.enqueue({})
            finally:
                release.set(); self.wait()


if __name__ == '__main__':
    unittest.main()
