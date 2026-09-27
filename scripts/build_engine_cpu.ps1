# H3-Music - build del motore audio.cpp per CPU (Windows x64, MSVC)
#
# Produce dist/h3-engine-cpu-win64.zip, l'engine precompilato che l'installatore
# estrae in runtime/engine. Serve solo sulla macchina di build: il PC di
# destinazione non compila nulla.
#
# Uso:  powershell -ExecutionPolicy Bypass -File scripts\build_engine_cpu.ps1
#
# Note:
#  - /utf-8 e' obbligatorio: diversi sorgenti di audio.cpp contengono letterali
#    non ASCII e senza il flag MSVC li interpreta con la codepage di sistema.
#  - Il motore viene costruito dal checkout vendor/audio.cpp con la patch H3 gia'
#    applicata (scripts/patch_engine.py) e senza CUDA.
#  - TrackFileAccess=false evita il file tracker di MSBuild (TRK0002 in ambienti
#    con restrizioni sui processi figli); /m:1 evita i nodi MSBuild paralleli.

param(
  [string]$VsRoot = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools',
  [string]$BuildDir = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not $BuildDir) { $BuildDir = Join-Path $root 'vendor\audio.cpp\build\cpu-vs' }

# --- ambiente MSVC ---
$vcvars = Join-Path $VsRoot 'VC\Auxiliary\Build\vcvarsall.bat'
if (-not (Test-Path $vcvars)) { throw "vcvarsall.bat non trovato in $VsRoot" }
$envText = cmd /c "`"$vcvars`" x64 && set"
foreach ($line in $envText) { if ($line -match '^([^=]+)=(.*)$') { Set-Item "env:$($matches[1])" $matches[2] } }

# --- configurazione ---
Write-Host 'Configurazione CMake (Visual Studio 17 2022, x64, CPU)...'
cmake -S "$root\vendor\audio.cpp" -B $BuildDir -G 'Visual Studio 17 2022' -A x64 `
  '-DCMAKE_C_FLAGS=/DWIN32 /D_WINDOWS /utf-8' `
  '-DCMAKE_CXX_FLAGS=/DWIN32 /D_WINDOWS /EHsc /utf-8' `
  -DAUDIOCPP_DEPLOYMENT_BUILD=ON -DENGINE_ENABLE_CUDA=OFF -DENGINE_ENABLE_NATIVE_CPU=OFF `
  -DENGINE_ENABLE_LLAMAFILE=ON -DENGINE_ENABLE_OPENMP=ON
if ($LASTEXITCODE -ne 0) { throw 'Configurazione CMake fallita.' }

# --- compilazione ---
Write-Host 'Compilazione (MSBuild, Release)...'
$msbuild = Join-Path $VsRoot 'MSBuild\Current\Bin\MSBuild.exe'
& $msbuild "$BuildDir\AudioCpp.sln" /p:Configuration=Release /p:Platform=x64 `
  /m:1 /p:TrackFileAccess=false /v:m
if ($LASTEXITCODE -ne 0) { throw 'Compilazione fallita.' }

# --- pacchettizzazione ---
Write-Host 'Pacchettizzazione in dist/h3-engine-cpu-win64.zip...'
& "$root\runtime\python\python.exe" "$root\scripts\package_engine_cpu.py"
if ($LASTEXITCODE -ne 0) { throw 'Pacchettizzazione fallita.' }
