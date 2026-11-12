import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
import lyric_schedule as ls

SCORE='''X:1
M:4/4
L:1/16
Q:1/4=120
V: Vocal clef=treble name="Vocal Melody"
V: Ins clef=treble
K:C
% intro
V: Vocal
z16|z16|
V: Ins
C16|C16|
% verse
V: Vocal
z8C8|D16|
V: Ins
Z2|
% chorus
V: Vocal
E16|F16|
V: Ins
Z2|
'''
LYRICS='[Intro]\n\n[Verse 1]\nÈ già l’ora\nLa luce verrà\n\n[Chorus]\nCanta con me 🎵\n'


class ScheduleTests(unittest.TestCase):
 def test_score_clock_uses_first_sung_note_and_ignores_other_voice(self):
  self.assertEqual(ls.score_sections(SCORE),[{'label':'verse','start':5.0},{'label':'chorus','start':8.0}])
 def test_unicode_offsets_are_exact_utf8_bytes_and_preserve_text(self):
  report=ls.schedule(SCORE,LYRICS);data=LYRICS.encode('utf-8')
  self.assertEqual(report['status'],'enabled');self.assertEqual(report['bias'],-4)
  self.assertEqual([data[s['byte_start']:s['byte_end']].decode('utf-8') for s in report['sections']],
                   ['[Verse 1]\nÈ già l’ora\nLa luce verrà','[Chorus]\nCanta con me 🎵'])
  self.assertEqual(report['unmatched_blocks'],0)
 def test_repeated_sections_remain_ordered(self):
  score=SCORE+'% verse\nV: Vocal\nG16|\nV: Ins\nZ|\n% chorus\nV: Vocal\nA16|\nV: Ins\nZ|'
  lyrics='[Verse 1]\nUno\n[Chorus]\nDue\n[Verse 2]\nTre\n[Chorus]\nQuattro'
  r=ls.schedule(score,lyrics)
  self.assertEqual([s['start'] for s in r['sections']],[5,8,12,14])
  self.assertEqual([s['label'] for s in r['sections']],['Verse 1','Chorus','Verse 2','Chorus'])
 def test_meter_changes_multibar_rests_and_tempo_are_timed(self):
  score='X:1\nM:3/4\nL:1/8\nQ:1/4=60\nK:C\n% verse\nz2 C4|\nM:5/8\nZ2|\nQ:1/4=120\n% chorus\nz2 D3|'
  self.assertEqual(ls.score_sections(score),[{'label':'verse','start':1},{'label':'chorus','start':8.5}])
 def test_tuplets_ties_and_grace_notes_do_not_shift_section_clock(self):
  score='X:1\nM:4/4\nL:1/8\nQ:1/4=120\nK:C\n% verse\n{c}(3CDE F2-F2 z2|\n% chorus\nG2|'
  self.assertEqual(ls.score_sections(score),[{'label':'verse','start':0},{'label':'chorus','start':2}])
 def test_unsupported_repeats_and_missing_tempo_fail_open_with_reason(self):
  for score in (SCORE.replace('z16|z16|','|:z16|z16:|'),SCORE.replace('Q:1/4=120\n','')):
   report=ls.schedule(score,LYRICS)
   self.assertEqual(report['status'],'unsupported_score');self.assertTrue(report['reason']);self.assertEqual(report['sections'],[])
 def test_sections_beyond_native_time_limit_are_not_sent_to_engine(self):
  score='X:1\nM:4/4\nL:1/8\nQ:1/4=1\nK:C\nZ9|\n% chorus\nC8|'
  self.assertEqual(ls.schedule(score,'[Chorus]\nLe parole')['status'],'unsupported_score')
 def test_tempo_change_in_instrument_part_applies_to_vocal_clock(self):
  score=SCORE+'Q:1/4=60\n% verse\nV: Vocal\nz8 G8|\nV: Ins\nZ|'
  self.assertEqual(ls.score_sections(score)[-1],{'label':'verse','start':14})
 def test_untagged_or_unmatched_text_is_not_rewritten(self):
  self.assertEqual(ls.schedule(SCORE,'Le parole senza TAG')['status'],'missing_sections')
  lyrics='[Verse]\nUna strofa\n[Bridge]\nUn ponte\n[Chorus]\nIl ritornello'
  r=ls.schedule(SCORE,lyrics);self.assertEqual(r['unmatched_labels'],['Bridge'])
  self.assertEqual([s['label'] for s in r['sections']],['Verse','Chorus'])
 def test_crlf_and_blank_lines_preserve_byte_ranges(self):
  lyrics=LYRICS.replace('\n','\r\n');r=ls.schedule(SCORE,lyrics)
  self.assertEqual(len(r['sections']),2)
  self.assertTrue(lyrics.encode()[r['sections'][1]['byte_start']:r['sections'][1]['byte_end']].startswith(b'[Chorus]\r\n'))
 def test_flag_defaults_on_and_rejects_non_booleans(self):
  self.assertTrue(app.validate({})['words_follow_score'])
  self.assertFalse(app.validate({'words_follow_score':False})['words_follow_score'])
  for value in ('true',1,None,[]):
   with self.subTest(value=value),self.assertRaisesRegex(ValueError,'sincronizzazione'):
    app.validate({'words_follow_score':value})
 def test_request_preparation_never_injects_words_into_prompts(self):
  with tempfile.TemporaryDirectory(prefix='tmp-schedule-',dir=app.ROOT/'tests') as temp:
   dest=Path(temp);engine=dest/'engine.exe';engine.write_bytes(b'h3_lyric_schedule_file')
   req=app.validate({'style':'Italian pop','lyrics':LYRICS,'abc':SCORE});before=json.dumps(req)
   with patch.object(app,'ENGINE',engine):opts=ls.prepare(app,req,dest)
   self.assertEqual(json.dumps(req),before)
   rows=(dest/'lyric-schedule.tsv').read_text().splitlines();self.assertEqual(len(rows),2)
   self.assertEqual(float(rows[0].split()[0]),5)
   self.assertEqual(opts,{'h3_lyric_schedule_file':str(dest/'lyric-schedule.tsv')})
 def test_old_engines_disabled_scoreless_and_cfg_keep_old_path(self):
  with tempfile.TemporaryDirectory(prefix='tmp-schedule-',dir=app.ROOT/'tests') as temp:
   dest=Path(temp);engine=dest/'engine.exe';engine.write_bytes(b'legacy')
   req=app.validate({'lyrics':LYRICS,'abc':SCORE})
   for updates,status in (({},'unsupported_engine'),({'words_follow_score':False},'disabled'),
                          ({'abc':''},'no_score'),({'options':{'cfg_scale':1.2}},'cfg_not_one')):
    with self.subTest(status=status),patch.object(app,'ENGINE',engine):
     self.assertEqual(ls.prepare(app,req|updates,dest),{})
     self.assertEqual(json.loads((dest/'lyric-schedule.json').read_text())['status'],status)
 def test_capability_cache_changes_when_engine_is_updated(self):
  with tempfile.TemporaryDirectory(prefix='tmp-schedule-',dir=app.ROOT/'tests') as temp:
   p=Path(temp)/'engine';p.write_bytes(b'old');self.assertFalse(ls.supported(p))
   p.write_bytes(b'h3_lyric_schedule_file');self.assertTrue(ls.supported(p))
 def test_failed_job_details_explain_actual_schedule_status(self):
  with tempfile.TemporaryDirectory(prefix='tmp-schedule-',dir=app.ROOT/'tests') as temp:
   data=Path(temp)
   with patch.multiple(app,DATA=data,OUT=data/'outputs'):
    app.init()
    project=app.project_save({'request':{'style':'pop','lyrics':LYRICS}})
    with patch.object(app,'ready',return_value={'ready':True}):
     ident=app.enqueue({'project_id':project['id'],'request':project['request']})['ids'][0]
    app.db("UPDATE jobs SET status='failed',error='melodia' WHERE id=?",(ident,))
    report={'status':'enabled','sections':[{'label':'Verse'}],'unmatched_labels':['Bridge'],'unmatched_blocks':1}
    app.write_json(app.OUT/ident/'generated/lyric-schedule.json',report)
    self.assertEqual(app.get_job(ident,True)['result']['words_follow_score'],report)
    self.assertEqual(app.get_job(ident)['result'],{})


if __name__=='__main__':unittest.main()
