"""CPU-first execution and explicit, checked CUDA activation (stdlib only)."""
import json, os, re, subprocess
from pathlib import Path
import platform_runtime

REQUIRED_FAMILIES = {'yue2', 'htdemucs', 'seed_vc'}
HIDDEN = 0x08000000 if os.name == 'nt' else 0

def capture(args, timeout=60):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=timeout, creationflags=HIDDEN)
    if result.returncode:
        raise ValueError((result.stderr or result.stdout)[-1500:] or 'Componente non avviabile.')
    return result.stdout

def check_engine(executable, backend='cuda'):
    executable = Path(executable)
    if not executable.is_file():
        raise ValueError('Motore assente: esegui '+platform_runtime.setup_name()+'.')
    loaders = json.loads(capture([executable, '--list-loaders', '--json']))['loaders']
    missing = REQUIRED_FAMILIES - set(loaders)
    if missing:
        raise ValueError('Il motore non include ' + ', '.join(sorted(missing)) + ('. Esegui Attiva-GPU.bat per aggiornare la versione NVIDIA.' if backend=='cuda' else '. Esegui '+platform_runtime.setup_name()+' per aggiornare il motore CPU.'))
    devices = capture([executable, '--list-devices'])
    if backend == 'cuda' and not re.search(r'^CUDA:\d+\s', devices, re.M):
        raise ValueError('Il motore non rileva una GPU CUDA. Esegui Attiva-GPU.bat e controlla il driver NVIDIA.')
    if backend == 'cpu' and not re.search(r'^CPU:\d+\s', devices, re.M):
        raise ValueError('Il motore non include il dispositivo CPU.')
    if backend == 'metal' and not re.search(r'^Metal:\d+\s',devices,re.M|re.I):
        raise ValueError('Il motore non rileva una GPU Metal. Seleziona CPU in Sistema.')
    return {'families': sorted(loaders), 'devices': devices.strip()}

def transcription_python(root, backend):
    root = Path(root)
    separate = root/'runtime/transcription-cuda/python.exe'
    if backend == 'cuda' and separate.is_file():
        return separate
    return platform_runtime.python(root,'transcription')

def check_torch(executable, cuda=False):
    code = "import json,torch,torchaudio,transformers,numpy; print(json.dumps({'torch':torch.__version__,'torchaudio':torchaudio.__version__,'cuda':bool(torch.cuda.is_available())}))"
    result = json.loads(capture([executable, '-X', 'utf8', '-c', code], timeout=120).strip().splitlines()[-1])
    if cuda:
        if not result['cuda']:
            raise ValueError('La trascrizione non ha un runtime CUDA funzionante. Esegui Attiva-GPU.bat; il runtime CPU resta disponibile.')
        capture([executable, '-X', 'utf8', '-c', "import torch; x=torch.ones((16,16),device='cuda'); y=x@x; assert y[0,0].item()==16; torch.cuda.synchronize()"], timeout=120)
    return result

def check_cuda(root, engine=None):
    root = Path(root)
    return {'engine': check_engine(engine or root/'runtime/engine/audiocpp_cli.exe'),
            'transcription': check_torch(transcription_python(root, 'cuda'), cuda=True)}
