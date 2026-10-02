"""Download and start the optional official runtime, with no heavy model download."""
import argparse,json,sqlite3,sys,tempfile,shutil
from contextlib import closing
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import install_assistant
import platform_runtime
with tempfile.TemporaryDirectory(dir=ROOT/'tests',prefix='tmp-assistant-install-') as folder:
 root=Path(folder);(root/'scripts').mkdir();(root/'data').mkdir()
 shutil.copy2(ROOT/'scripts/assistant-runtime.json',root/'scripts/assistant-runtime.json')
 # The executable --version probe does not load weights.
 model=root/'Existing model.gguf';model.write_bytes(b'GGUF')
 settings={'backend':'cpu','model':'q4','threads':6,'llm_provider':'lmstudio'}
 with closing(sqlite3.connect(root/'data/music.sqlite')) as db, db:
  db.execute('CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)')
  db.execute('CREATE TABLE jobs(status TEXT)')
  db.execute('INSERT INTO settings VALUES (?,?)',('main',json.dumps(settings)))
 install_assistant.ROOT=root
 install_assistant.install(argparse.Namespace(gpu=False,model=str(model),local_engine=None,optimized_mtp=False,library_path=None))
 marker=json.loads((root/'runtime/assistant/installed.json').read_text())
 assert marker['backends']==(['cpu','metal'] if platform_runtime.macos() else ['cpu'])
 assert not marker['optimized_mtp']
 with closing(sqlite3.connect(root/'data/music.sqlite')) as db:after=json.loads(db.execute("SELECT value FROM settings WHERE key='main'").fetchone()[0])
 assert all(after[k]==settings[k] for k in ('backend','model','threads'))
 assert after['llm_provider']=='internal' and after['llm_device']=='cpu'
 print('PASS: optional official runtime checksum/extraction/startup, independent CPU defaults and preserved music settings')
