import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import app,vocal_roles


class VocalRoleTests(unittest.TestCase):
 def test_no_change_for_normal_songs_and_single_voice(self):
  for lyrics in ('[Verse]\nCanto', '[Verse — Female]\nCanto', 'A male and a female sing\n[Verse]\nCanto'):
   self.assertEqual(vocal_roles.guidance('Italian pop',lyrics),('Italian pop',None))
 def test_duet_labels_are_explicit_in_style_without_modifying_lyrics(self):
  lyrics='[Verse 1 — Male]\nUno\n[Verse 1 — Female]\nDue\n[Chorus]\nTre'
  style,report=vocal_roles.guidance('Italian pop duet',lyrics)
  self.assertTrue(style.startswith('Italian pop duet\n'))
  self.assertIn('Male voice sings the sections labelled [Verse 1 — Male]',style)
  self.assertIn('Female voice sings the sections labelled [Verse 1 — Female]',style)
  self.assertEqual(report['roles']['male'],['Verse 1 — Male'])
  self.assertFalse(report['enforced'])
  self.assertEqual(vocal_roles.sections('[Strofa — femminile]\nDue\n[Strofa — maschile]\nUno'),{'male':['Strofa — maschile'],'female':['Strofa — femminile']})
 def test_engine_request_preserves_text_and_request_snapshot(self):
  req=app.validate({'style':'Italian duet','lyrics':'[Verse — Male]\nUno\n[Verse — Female]\nDue'})
  with tempfile.TemporaryDirectory(dir=ROOT/'tests',prefix='tmp-vocal-roles-') as temp:
   folder=Path(temp)
   with patch.object(app,'settings',return_value={'backend':'cpu','threads':2}),patch.object(app,'main_model_file',return_value='model.gguf'),patch.object(app,'memory_profile',return_value={}):
    app.command_for({'kind':'generate','request':req},folder)
   engine=json.loads((folder/'engine-request.json').read_text(encoding='utf-8'))[0]
   self.assertEqual(engine['text'],req['lyrics'])
   self.assertIn('Female voice sings',engine['options']['style'])
   self.assertEqual(json.loads((folder/'request.json').read_text(encoding='utf-8')),req)
   self.assertFalse(json.loads((folder/'vocal-roles.json').read_text())['enforced'])


if __name__=='__main__':unittest.main()
