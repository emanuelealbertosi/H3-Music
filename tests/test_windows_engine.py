import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import windows_engine

MANIFEST = b'''<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
<trustInfo xmlns="urn:schemas-microsoft-com:asm.v3"><security><requestedPrivileges>
<requestedExecutionLevel level="asInvoker" uiAccess="false" />
</requestedPrivileges></security></trustInfo></assembly>'''


class WindowsEngineTests(unittest.TestCase):
    def test_utf8_manifest_preserves_privileges_and_is_idempotent(self):
        first = windows_engine.with_utf8(MANIFEST)
        tree = ET.fromstring(first)
        self.assertEqual(tree.find('.//{%s}requestedExecutionLevel' % windows_engine.APPLICATION).attrib,
                         {'level': 'asInvoker', 'uiAccess': 'false'})
        self.assertEqual(tree.find('.//{%s}activeCodePage' % windows_engine.SETTINGS).text, 'UTF-8')
        self.assertEqual(windows_engine.with_utf8(first), first)

    @unittest.skipUnless(os.name == 'nt', 'Windows resource APIs')
    def test_bundled_engine_resource_update_needs_no_compiler(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests', prefix='tmp-utf8-') as directory:
            path = Path(directory) / 'engine.exe'
            with zipfile.ZipFile(ROOT / 'dist/h3-engine-cpu-win64.zip') as archive:
                path.write_bytes(archive.read('audiocpp_cli.exe'))
            before, languages = windows_engine.resources(path)
            was_utf8 = any(n.text == 'UTF-8' for n in ET.fromstring(before).iter('{%s}activeCodePage' % windows_engine.SETTINGS))
            self.assertEqual(windows_engine.enable_utf8(path), not was_utf8)
            after, after_languages = windows_engine.resources(path)
            self.assertEqual(languages, after_languages)
            self.assertTrue(any(n.text == 'UTF-8' for n in ET.fromstring(after).iter('{%s}activeCodePage' % windows_engine.SETTINGS)))
            self.assertIn(b'asInvoker', after)
            self.assertFalse(windows_engine.enable_utf8(path))

    @unittest.skipUnless(os.name == 'nt', 'Windows engine repair')
    def test_failed_execution_check_keeps_installed_engine(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tests', prefix='tmp-utf8-') as directory:
            root = Path(directory); exe = root / 'runtime/engine/audiocpp_cli.exe'
            exe.parent.mkdir(parents=True); exe.write_bytes(b'MZ original')
            with patch.object(windows_engine, 'resources', return_value=(MANIFEST, [1033])), patch.object(windows_engine, 'enable_utf8'), patch('execution.check_engine', side_effect=ValueError('invalid engine')):
                with self.assertRaises(ValueError): windows_engine.prepare(root)
            self.assertEqual(exe.read_bytes(), b'MZ original')
            self.assertEqual(list(exe.parent.glob('unicode-ready-*.exe')), [])


if __name__ == '__main__':
    unittest.main()
