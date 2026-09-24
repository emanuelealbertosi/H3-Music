import sys,pathlib
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
import app
app.init();app.save_settings(app.settings()|{'paused':True})
p=root/'tests/api_test.py';s=p.read_text(encoding='utf-8-sig').replace('except urllib.error.URLError:break','except (urllib.error.URLError,ConnectionResetError):break').replace('except urllib.error.URLError:pass','except (urllib.error.URLError,ConnectionResetError):pass');p.write_text(s,encoding='utf-8')
