from pathlib import Path
p=Path(r'F:\H3-Music\app.py');s=p.read_text(encoding='utf-8')
s=s.replace("g=run_capture(['nvidia-smi','--query-gpu=name,memory.total,memory.free,utilization.gpu','--format=csv,noheader,nounits'],10)","g=run_capture(['nvidia-smi','--query-gpu=name','--format=csv,noheader'],10)\n    cuda=json.loads(run_capture([str(ROOT/'runtime/python/python.exe'),str(ROOT/'scripts/gpu_info.py')],15).stdout or '{}')")
s=s.replace("ready()|{'gpu':g.stdout.strip(),","ready()|{'gpu':g.stdout.strip(),'cuda':cuda,")
p.write_text(s,encoding='utf-8')
p=Path(r'F:\H3-Music\static\app.js');s=p.read_text(encoding='utf-8')
s=s.replace("info('GPU / VRAM totale, libera / uso',r.gpu||'Non rilevata')", "info('GPU',r.gpu||'Non rilevata')+info('VRAM libera / totale (CUDA)',r.cuda?.free_gb!==undefined?r.cuda.free_gb+' / '+r.cuda.total_gb+' GB':'Da verificare a motore installato')")
p.write_text(s,encoding='utf-8')
