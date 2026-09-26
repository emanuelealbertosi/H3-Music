# H3-Music - build del motore audio.cpp con CUDA su questa macchina.
#
# Non serve se ti accontenti della CPU: il repository include gia' il motore CPU
# precompilato. Serve per generare con una scheda NVIDIA.
#
# Requisiti:
#   - GPU NVIDIA con driver aggiornato
#   - Visual Studio 2022 Build Tools con "Desktop development with C++"
#   - NVIDIA CUDA Toolkit 12.x  (https://developer.nvidia.com/cuda-downloads)
#   - git (oppure connessione internet: il sorgente viene scaricato come zip)
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts\build_engine_cuda.ps1
#
# Opzioni:
#   -Arch 86           architettura CUDA (default: rilevata dalla GPU)
#   -ConfigureOnly     solo configurazione CMake, nessuna compilazione
#   -Serial            compilazione a un processo (piu' lenta, meno memoria)
#   -Revert            ripristina il motore CPU salvato in runtime\engine-cpu
#
# Al termine il motore CUDA sostituisce quello CPU in runtime\engine (il motore
# CPU viene conservato in runtime\engine-cpu) e il backend passa a cuda.

param(
  [string]$Arch = '',
  [switch]$ConfigureOnly,
  [switch]$Serial,
  [switch]$Revert,
  [string]$SourceDir = '',
  [string]$BuildDir = ''
)

# I comandi nativi (git, cmake, msbuild, nvcc) scrivono messaggi su stderr: con
# ErrorActionPreference='Stop' PowerShell li tratterebbe come errori fatali.
# Qui ogni comando nativo viene controllato esplicitamente con $LASTEXITCODE.
$ErrorActionPreference = 'Continue'

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$src = if ($SourceDir) { $SourceDir } else { Join-Path $root 'vendor\audio.cpp' }
$build = if ($BuildDir) { $BuildDir } else { Join-Path $root 'vendor\audio.cpp\build\cuda-release' }
$eng = Join-Path $root 'runtime\engine'
$backup = Join-Path $root 'runtime\engine-cpu'
$py = Join-Path $root 'runtime\python\python.exe'
$commit = '13c4192a28d6a212f075c4cbefc5e4983e6ed52a'
$repo = 'https://github.com/0xShug0/audio.cpp.git'

function Fail([string]$msg) { throw "ERRORE: $msg" }

# ---------------------------------------------------------------- ripristino
if ($Revert) {
  if (-not (Test-Path $backup)) { Fail "nessun motore CPU salvato in $backup" }
  if (Test-Path $eng) { Remove-Item -Recurse -Force $eng }
  Move-Item $backup $eng
  & $py (Join-Path $root 'scripts\set_backend.py') cpu
  Write-Host 'Motore CPU ripristinato: backend = cpu' -ForegroundColor Green
  exit 0
}

# ------------------------------------------------------------------ 1. GPU
Write-Host ''
Write-Host '[1/6] Scheda NVIDIA' -ForegroundColor Cyan
$smi = (Get-Command nvidia-smi -ErrorAction SilentlyContinue).Source
if (-not $smi) { Fail 'nvidia-smi non trovato: serve una GPU NVIDIA con il driver installato.' }
$gpuLine = (& $smi --query-gpu=name,compute_cap --format=csv,noheader 2>$null | Select-Object -First 1)
if (-not $gpuLine) { $gpuLine = (& $smi --query-gpu=name --format=csv,noheader 2>$null | Select-Object -First 1) }
if (-not $gpuLine) { Fail 'nessuna GPU NVIDIA rilevata da nvidia-smi.' }
$driver = (& $smi --query-gpu=driver_version --format=csv,noheader 2>$null | Select-Object -First 1)
Write-Host "  $gpuLine   driver $driver"

if (-not $Arch) {
  $cap = ''
  if ($gpuLine -match ',\s*(\d+\.\d+)\s*$') { $cap = $Matches[1] }
  if ($cap) { $Arch = $cap -replace '\.', '' } else { $Arch = 'native' }
}
Write-Host "  architettura CUDA: $Arch"

# --------------------------------------------------------- 2. Visual Studio
Write-Host ''
Write-Host '[2/6] Visual Studio (strumenti C++)' -ForegroundColor Cyan
$vsRoot = ''
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (Test-Path $vswhere) {
  $vsRoot = (& $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>$null | Select-Object -First 1)
}
if (-not $vsRoot -or -not (Test-Path (Join-Path $vsRoot 'VC\Auxiliary\Build\vcvarsall.bat'))) {
  $candidates = @()
  foreach ($base in @(${env:ProgramFiles(x86)}, ${env:ProgramFiles})) {
    foreach ($edition in @('BuildTools', 'Community', 'Professional', 'Enterprise')) {
      $candidates += Join-Path $base "Microsoft Visual Studio\2022\$edition"
    }
  }
  $vsRoot = $candidates | Where-Object { Test-Path (Join-Path $_ 'VC\Auxiliary\Build\vcvarsall.bat') } | Select-Object -First 1
}
if (-not $vsRoot) {
  Fail 'Visual Studio 2022 con "Desktop development with C++" non trovato. Scaricalo da https://visualstudio.microsoft.com/downloads/ (va bene la versione Build Tools).'
}
Write-Host "  $vsRoot"

# ------------------------------------------------------------------ 3. CUDA
Write-Host ''
Write-Host '[3/6] CUDA Toolkit' -ForegroundColor Cyan
$cudaRoot = ''
if ($env:CUDA_PATH -and (Test-Path (Join-Path $env:CUDA_PATH 'bin\nvcc.exe'))) { $cudaRoot = $env:CUDA_PATH.TrimEnd('\') }
if (-not $cudaRoot) {
  $base = 'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA'
  $cudaRoot = (Get-ChildItem $base -Directory -ErrorAction SilentlyContinue |
    Where-Object { (Test-Path (Join-Path $_.FullName 'bin\nvcc.exe')) -and $_.Name -like 'v12*' } |
    Sort-Object Name | Select-Object -Last 1).FullName
}
if (-not $cudaRoot) { Fail 'CUDA Toolkit 12.x non trovato: installalo da https://developer.nvidia.com/cuda-downloads' }
Write-Host "  $cudaRoot"
$nvcc = Join-Path $cudaRoot 'bin\nvcc.exe'
(& $nvcc --version 2>$null | Select-String 'release') | ForEach-Object { Write-Host "  $($_.Line.Trim())" }

# ----------------------------------------------------------------- 4. CMake
Write-Host ''
Write-Host '[4/6] CMake e sorgente' -ForegroundColor Cyan
$cmake = (Get-Command cmake -ErrorAction SilentlyContinue).Source
if (-not $cmake) { $cmake = Join-Path $vsRoot 'Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe' }
if (-not (Test-Path $cmake)) { Fail 'cmake non trovato (di solito arriva con Visual Studio).' }
Write-Host "  $cmake"

# Generatore: con l'integrazione CUDA per Visual Studio si usa MSBuild, altrimenti
# Ninja (incluso in Visual Studio). Ninja e' anche il generatore della build di
# riferimento di audio.cpp.
$ninja = Join-Path $vsRoot 'Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe'
$vsCuda = Get-ChildItem (Join-Path $vsRoot 'MSBuild\Microsoft\VC') -Recurse -Filter 'CUDA*.props' -ErrorAction SilentlyContinue | Select-Object -First 1
$generator = ''
if ($vsCuda) { $generator = 'Visual Studio 17 2022'; Write-Host '  generatore: Visual Studio (integrazione CUDA presente)' }
elseif (Test-Path $ninja) { $generator = 'Ninja'; Write-Host '  generatore: Ninja (integrazione CUDA per VS assente)' }
else { Fail 'serve Ninja oppure l integrazione CUDA per Visual Studio.' }

if (-not (Test-Path (Join-Path $src 'CMakeLists.txt'))) {
  Write-Host '  sorgente assente: lo scarico'
  New-Item -ItemType Directory -Force (Split-Path -Parent $src) | Out-Null
  $git = (Get-Command git -ErrorAction SilentlyContinue).Source
  if ($git) {
    Write-Host '  git clone di audio.cpp (circa 300 MB)...'
    & $git clone --progress $repo $src
    if ($LASTEXITCODE -ne 0) { Fail 'git clone di audio.cpp non riuscito.' }
    & $git -C $src checkout --quiet $commit
    if ($LASTEXITCODE -ne 0) { Fail "checkout del commit $commit non riuscito." }
  } else {
    $zip = Join-Path $env:TEMP 'audio-cpp-h3.zip'
    $tmp = Join-Path $env:TEMP ('audio-cpp-h3-' + [Guid]::NewGuid().ToString('N'))
    Write-Host '  git assente: scarico lo zip da GitHub'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    (New-Object Net.WebClient).DownloadFile("https://codeload.github.com/0xShug0/audio.cpp/zip/$commit", $zip)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::ExtractToDirectory($zip, $tmp)
    Move-Item (Join-Path $tmp "audio.cpp-$commit") $src
    Remove-Item -Recurse -Force $tmp, $zip -ErrorAction SilentlyContinue
  }
} else {
  Write-Host "  sorgente presente: $src"
  if (Test-Path (Join-Path $src '.git')) {
    $git = (Get-Command git -ErrorAction SilentlyContinue).Source
    if ($git) {
      & $git -C $src checkout --quiet $commit
      $head = (& $git -C $src rev-parse HEAD 2>$null | Select-Object -First 1)
      Write-Host "  commit: $head"
    }
  }
}

# applica la patch H3 (idempotente)
if (-not (Test-Path $py)) { Fail 'runtime\python non trovato: esegui prima install.bat' }
& $py (Join-Path $root 'scripts\patch_engine.py')
if ($LASTEXITCODE -ne 0) { Fail 'applicazione della patch H3 non riuscita.' }

# ambiente MSVC
$vcvars = Join-Path $vsRoot 'VC\Auxiliary\Build\vcvarsall.bat'
$envText = cmd /c "`"$vcvars`" x64 && set"
foreach ($line in $envText) { if ($line -match '^([^=]+)=(.*)$') { Set-Item "env:$($Matches[1])" $Matches[2] } }

# ---------------------------------------------------------- 5. Configurazione
Write-Host ''
Write-Host '[5/6] Configurazione CMake (CUDA)' -ForegroundColor Cyan
$cmakeArgs = @(
  '-S', $src, '-B', $build, '-G', $generator,
  '-DCMAKE_C_FLAGS=/DWIN32 /D_WINDOWS /utf-8',
  '-DCMAKE_CXX_FLAGS=/DWIN32 /D_WINDOWS /EHsc /utf-8',
  "-DCMAKE_CUDA_ARCHITECTURES=$Arch",
  "-DCMAKE_CUDA_COMPILER=$nvcc",
  "-DCUDAToolkit_ROOT=$cudaRoot",
  '-DENGINE_ENABLE_CUDA=ON', '-DENGINE_ENABLE_CUDA_GRAPHS=ON',
  '-DENGINE_ENABLE_NATIVE_CPU=OFF', '-DENGINE_ENABLE_LLAMAFILE=ON', '-DENGINE_ENABLE_OPENMP=ON'
)
if ($generator -eq 'Visual Studio 17 2022') { $cmakeArgs += @('-A', 'x64') } else { $cmakeArgs += @('-DCMAKE_BUILD_TYPE=Release', "-DCMAKE_MAKE_PROGRAM=$ninja") }
& $cmake @cmakeArgs
if ($LASTEXITCODE -ne 0) { Fail 'configurazione CMake non riuscita.' }
if ($ConfigureOnly) { Write-Host 'Configurazione completata (-ConfigureOnly): nessuna compilazione.' -ForegroundColor Green; exit 0 }

# ----------------------------------------------------------- 6. Compilazione
Write-Host ''
Write-Host '[6/6] Compilazione (puo durare da 20 a 60 minuti)' -ForegroundColor Cyan
if ($generator -eq 'Visual Studio 17 2022') {
  $msbuild = Join-Path $vsRoot 'MSBuild\Current\Bin\MSBuild.exe'
  $par = if ($Serial) { '/m:1' } else { '/m' }
  & $msbuild (Join-Path $build 'AudioCpp.sln') /p:Configuration=Release /p:Platform=x64 $par /p:TrackFileAccess=false /v:m
} else {
  $par = if ($Serial) { '1' } else { [string][Environment]::ProcessorCount }
  & $cmake --build $build --parallel $par
}
if ($LASTEXITCODE -ne 0) { Fail 'compilazione non riuscita.' }

# ------------------------------------------------------------ installazione
$candidates = @(
  (Join-Path $build 'bin\audiocpp_cli.exe'),
  (Join-Path $build 'bin\Release\audiocpp_cli.exe')
)
$exe = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $exe) { Fail "motore non trovato in $build\bin" }

$stage = Join-Path $build 'stage'
if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory -Force $stage | Out-Null
Copy-Item $exe $stage

foreach ($pattern in @('cudart64_*.dll', 'cublas64_*.dll', 'cublasLt64_*.dll')) {
  $found = Get-ChildItem (Join-Path $cudaRoot 'bin') -Filter $pattern -ErrorAction SilentlyContinue
  if (-not $found) { Fail "DLL CUDA non trovata in $cudaRoot\bin ($pattern)" }
  $found | ForEach-Object { Copy-Item $_.FullName $stage -Force }
}
$redistBase = Join-Path $vsRoot 'VC\Redist\MSVC'
$redist = (Get-ChildItem $redistBase -Directory -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -like '14.*' } | Sort-Object Name | Select-Object -Last 1).FullName
if ($redist) {
  foreach ($folder in @('Microsoft.VC143.CRT', 'Microsoft.VC143.OpenMP')) {
    Get-ChildItem (Join-Path $redist "x64\$folder") -Filter '*.dll' -ErrorAction SilentlyContinue |
      ForEach-Object { Copy-Item $_.FullName $stage -Force }
  }
}

$ver = & (Join-Path $stage 'audiocpp_cli.exe') --version 2>&1
$dev = & (Join-Path $stage 'audiocpp_cli.exe') --list-devices 2>&1
$ver | ForEach-Object { Write-Host "  $_" }
$dev | ForEach-Object { Write-Host "  $_" }
if (($dev -join "`n") -notmatch 'CUDA') {
  Fail 'il motore compilato non elenca dispositivi CUDA: di solito significa che il driver NVIDIA e piu vecchio del CUDA Toolkit. Aggiorna il driver e riprova.'
}

if (Test-Path $eng) {
  Remove-Item -Recurse -Force $backup -ErrorAction SilentlyContinue
  Move-Item $eng $backup
}
New-Item -ItemType Directory -Force $eng | Out-Null
Copy-Item (Join-Path $stage '*') $eng -Force
& $py (Join-Path $root 'scripts\set_backend.py') cuda

Write-Host ''
Write-Host 'MOTORE CUDA PRONTO' -ForegroundColor Green
Write-Host "  motore: $eng"
Write-Host "  motore CPU precedente: $backup (ripristino: -Revert)"
Write-Host '  backend impostato su cuda: ricarica la finestra dell app.'
