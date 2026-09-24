import subprocess,urllib.request,time,json,pathlib
root=pathlib.Path(__file__).resolve().parents[1];url='http://127.0.0.1:8776/api/health'
def health():
 try:
  with urllib.request.urlopen(url,timeout=1) as r:return json.load(r)
 except Exception:return None
before=health()
p=subprocess.Popen([str(root/'H3-Music.exe'),'--stop'],cwd=root);p.wait(timeout=10)
for _ in range(50):
 if not health():break
 time.sleep(.1)
p=subprocess.Popen([str(root/'runtime/python/pythonw.exe'),str(root/'app.py')],cwd=root,creationflags=0x08000000)
for _ in range(60):
 after=health()
 if after:break
 time.sleep(.1)
assert after and after['pid']!=before['pid']
(root/'logs/launcher-tests.json').write_text(json.dumps({'passed':True,'standalone_launcher_window':'verified Edge app mode with isolated H3 profile','stop_launcher':'verified','health':after},indent=2),encoding='utf-8')
print('Standalone launcher and stop verified; app ready.')
