import ctypes as c
rt=c.WinDLL(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8\bin\cudart64_12.dll')
free=c.c_size_t();total=c.c_size_t()
print('context',rt.cudaFree(c.c_void_p()),flush=True)
print('mem',rt.cudaMemGetInfo(c.byref(free),c.byref(total)),round(free.value/2**30,2),round(total.value/2**30,2),flush=True)
p=c.c_void_p()
rc=rt.cudaMalloc(c.byref(p),c.c_size_t(8*1024**3));print('allocate_8GiB',rc,flush=True)
if rc==0: print('free',rt.cudaFree(p),flush=True)
