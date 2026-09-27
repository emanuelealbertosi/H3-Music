"""Install/update the bundled CPU engine without overwriting an existing CUDA engine."""
import json,pathlib,subprocess,sys,tempfile,zipfile,hashlib
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root));sys.path.insert(0,str(root/'scripts'))
import execution
from activate_engine import activate

def main():
 engine=root/'runtime/engine';archive=root/'dist/h3-engine-cpu-win64.zip'
 if (engine/'audiocpp_cli.exe').is_file() and any(engine.glob('cudart64*.dll')):
  try:
   execution.check_engine(engine/'audiocpp_cli.exe','cuda')
  except (ValueError,OSError,subprocess.SubprocessError) as exc:
   print('OLD OR UNAVAILABLE CUDA ENGINE:',str(exc))
   print('Installing the complete CPU engine; previous engine is backed up. Use Attiva-GPU.bat to restore CUDA.')
  else:
   print('EXISTING COMPLETE CUDA ENGINE PRESERVED. Use Attiva-GPU.bat to update it.');return
 digest=hashlib.sha256(archive.read_bytes()).hexdigest();marker=engine/'cpu-package.sha256'
 if marker.is_file() and marker.read_text().strip()==digest:
  execution.check_engine(engine/'audiocpp_cli.exe','cpu');print('CPU ENGINE ALREADY VERIFIED');return
 subprocess.run([sys.executable,str(root/'scripts/seed_settings.py')],check=True)
 with tempfile.TemporaryDirectory(prefix='cpu-install-',dir=root/'runtime') as folder:
  candidate=pathlib.Path(folder)
  with zipfile.ZipFile(archive) as z:z.extractall(candidate)
  (candidate/'cpu-package.sha256').write_text(digest,encoding='ascii')
  result=activate(root,candidate,backend='cpu')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
