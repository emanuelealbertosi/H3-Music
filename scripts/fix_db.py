from pathlib import Path
p=Path(r'F:\H3-Music\app.py');s=p.read_text(encoding='utf-8')
s=s.replace('from pathlib import Path','from pathlib import Path\nfrom contextlib import contextmanager')
s=s.replace("def conn():\n c=sqlite3.connect(DATA/'music.sqlite',timeout=20); c.row_factory=sqlite3.Row; return c", "@contextmanager\ndef conn():\n c=sqlite3.connect(DATA/'music.sqlite',timeout=20); c.row_factory=sqlite3.Row\n try:\n  with c: yield c\n finally: c.close()")
p.write_text(s,encoding='utf-8')
p=Path(r'F:\H3-Music\tests\test_studio.py');s=p.read_text(encoding='utf-8-sig').replace("app.DATA,app.OUT,app.MODEL=self.old;self.tmp.cleanup()","assert pathlib.Path(self.tmp.name).resolve().is_relative_to((app.ROOT/'tests').resolve())\n  app.DATA,app.OUT,app.MODEL=self.old;self.tmp.cleanup()")
s=s.replace("(d/'request.json').read_text()","(d/'request.json').read_text(encoding='utf-8')")
p.write_text(s,encoding='utf-8')
