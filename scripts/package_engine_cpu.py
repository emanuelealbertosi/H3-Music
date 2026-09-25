"""Package the precompiled CPU engine into dist/h3-engine-cpu-win64.zip.

Runs on the build machine after the audio.cpp CPU build (Visual Studio generator,
`vendor/audio.cpp/build/cpu-vs`, Release). The zip contains audiocpp_cli.exe plus
the MSVC runtime DLLs so a target PC needs no Visual Studio redistributable.
"""
import pathlib, shutil, subprocess, zipfile

root = pathlib.Path(__file__).resolve().parents[1]
candidates = [
    root/'vendor/audio.cpp/build/cpu-vs/bin/Release/audiocpp_cli.exe',
    root/'vendor/audio.cpp/build/cpu-release/bin/audiocpp_cli.exe',
    root/'vendor/audio.cpp/build/cpu-vs/bin/audiocpp_cli.exe',
]
exe = next((p for p in candidates if p.exists()), None)
if exe is None:
    raise SystemExit('Engine CPU non compilato. Cercato in:\n  ' + '\n  '.join(str(p) for p in candidates))
print('Engine:', exe)

staging = root/'dist/engine-cpu-staging'
if staging.exists(): shutil.rmtree(staging)
staging.mkdir(parents=True)
shutil.copy2(exe, staging/exe.name)

redist_root = pathlib.Path(r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Redist\MSVC')
versions = sorted(redist_root.glob('14.*')) if redist_root.exists() else []
if not versions: raise SystemExit('Redist MSVC non trovato in ' + str(redist_root))
redist = versions[-1]/'x64'
# Tutte le DLL del runtime C++ e di OpenMP: il PC di destinazione non deve
# installare alcun redistributable di Visual Studio.
for folder in ['Microsoft.VC143.CRT', 'Microsoft.VC143.OpenMP']:
    src_dir = redist/folder
    if not src_dir.exists(): raise SystemExit('Cartella redist mancante: ' + str(src_dir))
    for dll in sorted(src_dir.glob('*.dll')):
        shutil.copy2(dll, staging/dll.name)

r = subprocess.run([str(staging/'audiocpp_cli.exe'), '--version'], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(r.stdout.strip())
if r.returncode: raise SystemExit('Engine non avviabile (--version): ' + str(r.returncode))
r2 = subprocess.run([str(staging/'audiocpp_cli.exe'), '--list-devices'], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(r2.stdout.strip())

zip_path = root/'dist/h3-engine-cpu-win64.zip'
if zip_path.exists(): zip_path.unlink()
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(staging.iterdir()):
        z.write(p, p.name)
shutil.rmtree(staging)
print('ZIP READY', zip_path.stat().st_size)
