"""Query CUDA-allocatable VRAM; WDDM nvidia-smi figures may include reclaimable memory."""
import ctypes as c,json,pathlib
try:
 root=pathlib.Path(__file__).resolve().parents[1]
 lib=next((root/'runtime/engine').glob('cudart64*.dll'))
 rt=c.WinDLL(str(lib))
 code=rt.cudaFree(c.c_void_p())
 if code:raise RuntimeError('CUDA initialization error '+str(code))
 free=c.c_size_t();total=c.c_size_t()
 code=rt.cudaMemGetInfo(c.byref(free),c.byref(total))
 if code:raise RuntimeError('CUDA memory query error '+str(code))
 print(json.dumps({'free_gb':round(free.value/2**30,2),'total_gb':round(total.value/2**30,2)}))
 rt.cudaDeviceReset()
except Exception as e:print(json.dumps({'error':str(e)}))
