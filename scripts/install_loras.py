from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import loras
if __name__=='__main__':
 loras.install(Path(__file__).resolve().parents[1],lambda **r:print(r,flush=True) if r.get('status')!='downloading' or not r.get('done') or r['done']% (16*2**20)==0 else None)
 print('Quattro LoRA CNZN installati e verificati.')
