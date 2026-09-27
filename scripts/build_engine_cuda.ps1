# Build H3's three native model families with CUDA. CPU remains the default
# until this explicit command has verified both the engine and transcription.
param(
  [string]$Arch = '', [switch]$ConfigureOnly, [switch]$BuildOnly,
  [switch]$Serial, [switch]$Revert, [string]$SourceDir = '',
  [string]$BuildDir = '', [string]$VsRoot = '', [string]$CudaRoot = ''
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$src = if ($SourceDir) { [IO.Path]::GetFullPath($SourceDir) } else { Join-Path $root 'vendor\audio.cpp' }
$build = if ($BuildDir) { [IO.Path]::GetFullPath($BuildDir) } else { Join-Path $root 'vendor\audio.cpp\build\cuda-h3' }
$py = Join-Path $root 'runtime\python\python.exe'
$commit = '13c4192a28d6a212f075c4cbefc5e4983e6ed52a'
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'
function Native([string]$exe, [string[]]$argv) {
  $prior=$ErrorActionPreference; $ErrorActionPreference='Continue'
  try { & $exe @argv; $code=$LASTEXITCODE } finally { $ErrorActionPreference=$prior }
  if ($code -ne 0) { throw "Comando fallito (exit $code): $exe" }
}
if (-not (Test-Path -LiteralPath $py)) { throw 'Esegui prima install.bat.' }
if ($Revert) {
  Native $py @((Join-Path $root 'scripts\set_backend.py'),'cpu')
  Write-Host 'CPU attiva. Il motore GPU rimane disponibile.'; exit 0
}
foreach ($path in @($src,$build)) {
  if (-not $path.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Sorgenti e build devono restare dentro la cartella H3-Music.' }
}
Write-Host '[1/6] GPU e strumenti di compilazione' -ForegroundColor Cyan
$gpu = & nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader
if ($LASTEXITCODE -ne 0 -or -not $gpu) { throw 'Serve una GPU NVIDIA con driver installato.' }
Write-Host ($gpu -join "`n")
if (-not $Arch) { if ($gpu[0] -match ',\s*(\d+)\.(\d+)\s*$') { $Arch=$Matches[1]+$Matches[2] } elseif ([string]$gpu -match ',\s*(\d+)\.(\d+)\s*$') { $Arch=$Matches[1]+$Matches[2] } else { $Arch='native' } }
if ($Arch -notmatch '^(native|[0-9]+[a-z]?)$') { throw 'Architettura CUDA non valida.' }
if (-not $VsRoot) {
  $vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
  if (Test-Path -LiteralPath $vswhere) {
    $vsCandidates=@(& $vswhere -all -version '[17.0,18.0)' -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath)
    $compatible=@($vsCandidates | Where-Object { Test-Path (Join-Path $_ 'VC\Tools\MSVC\14.38*') })
    $VsRoot=if ($compatible.Count) { $compatible[0] } else { $vsCandidates | Select-Object -First 1 }
  }
}
if (-not $VsRoot -or -not (Test-Path (Join-Path $VsRoot 'VC\Auxiliary\Build\vcvarsall.bat'))) { throw 'Installa Visual Studio 2022 Build Tools con strumenti C++ e CMake.' }
if (-not $CudaRoot) { $CudaRoot='C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8' }
$nvcc=Join-Path $CudaRoot 'bin\nvcc.exe'
if (-not (Test-Path -LiteralPath $nvcc)) { throw 'Installa CUDA Toolkit 12.8, oppure indica il percorso con -CudaRoot.' }
Native $nvcc @('--version')
$cmake=Join-Path $VsRoot 'Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
$ninja=Join-Path $VsRoot 'Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe'
if (-not (Test-Path -LiteralPath $cmake) -or -not (Test-Path -LiteralPath $ninja)) { throw 'Aggiungi C++ CMake tools for Windows ai Build Tools. Non serve integrazione CUDA per MSBuild.' }
Write-Host "Visual Studio: $VsRoot"
$vcvars=Join-Path $VsRoot 'VC\Auxiliary\Build\vcvarsall.bat'
# Use the CUDA 12.8-compatible toolset when it is installed alongside newer MSVC.
$toolset=if (Test-Path (Join-Path $VsRoot 'VC\Tools\MSVC\14.38*')) { ' -vcvars_ver=14.38' } else { '' }
$envText=cmd /c "`"$vcvars`" x64$toolset && set"
if ($LASTEXITCODE -ne 0) { throw 'Ambiente C++ non inizializzato.' }
foreach ($line in $envText) { if ($line -match '^([^=]+)=(.*)$') { Set-Item "env:$($Matches[1])" $Matches[2] } }

Write-Host '[2/6] Sorgenti alla revisione collaudata' -ForegroundColor Cyan
if (-not (Test-Path (Join-Path $src 'CMakeLists.txt'))) {
  if (Test-Path -LiteralPath $src) { throw 'La cartella dei sorgenti esiste ma e incompleta: scegli -SourceDir dentro H3-Music.' }
  New-Item -ItemType Directory -Force (Split-Path -Parent $src) | Out-Null
  Native 'git' @('clone','https://github.com/0xShug0/audio.cpp.git',$src)
  Native 'git' @('-C',$src,'checkout','--detach',$commit)
}
$head=& git -C $src rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $head -ne $commit) { throw "Revisione dei sorgenti inattesa: richiesta $commit. I sorgenti locali non sono stati sovrascritti." }
Native $py @((Join-Path $root 'scripts\patch_engine.py'),'--source',$src)

# CMake embeds compiler paths in generated source; use forward slashes.
$nvccCmake=$nvcc.Replace('\','/'); $cudaCmake=$CudaRoot.Replace('\','/'); $ninjaCmake=$ninja.Replace('\','/')
$hostCmake=(Get-Command cl.exe -ErrorAction Stop).Source.Replace('\','/')
Write-Host '[3/6] Configurazione CUDA: YuE2, HTDemucs, SeedVC' -ForegroundColor Cyan
Native $cmake @('-S',$src,'-B',$build,'-G','Ninja',"-DCMAKE_MAKE_PROGRAM=$ninjaCmake",'-DCMAKE_BUILD_TYPE=Release',
 '-DCMAKE_C_FLAGS=/DWIN32 /D_WINDOWS /utf-8','-DCMAKE_CXX_FLAGS=/DWIN32 /D_WINDOWS /EHsc /utf-8',
 "-DCMAKE_CUDA_COMPILER=$nvccCmake","-DCMAKE_CUDA_HOST_COMPILER=$hostCmake","-DCUDAToolkit_ROOT=$cudaCmake",
 '-DCMAKE_CUDA_FLAGS=-Xcompiler=/utf-8',"-DCMAKE_CUDA_ARCHITECTURES=$Arch",
 '-DAUDIOCPP_DEPLOYMENT_BUILD=ON','-DAUDIOCPP_MODEL_SET=custom','-DAUDIOCPP_MODELS=yue2,demucs,seed_vc',
 '-DENGINE_ENABLE_CUDA=ON','-DENGINE_ENABLE_CUDA_GRAPHS=ON','-DENGINE_ENABLE_NATIVE_CPU=OFF',
 '-DENGINE_ENABLE_LLAMAFILE=ON','-DENGINE_ENABLE_OPENMP=ON')
if ($ConfigureOnly) { Write-Host 'Configurazione completata. Nessun motore sostituito.'; exit 0 }
Write-Host '[4/6] Compilazione (la prima build puo richiedere 20-60 minuti)' -ForegroundColor Cyan
$parallel=if ($Serial) { '1' } else { '2' }
Native $cmake @('--build',$build,'--target','audiocpp_cli','--parallel',$parallel)

Write-Host '[5/6] Pacchetto e verifica del motore' -ForegroundColor Cyan
$stage=Join-Path $build ('stage-'+[guid]::NewGuid().ToString('N'))
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::ExtractToDirectory((Join-Path $root 'dist\h3-engine-cpu-win64.zip'),$stage)
Copy-Item -LiteralPath (Join-Path $build 'bin\audiocpp_cli.exe') -Destination $stage -Force
foreach ($pattern in @('cudart64_*.dll','cublas64_*.dll','cublasLt64_*.dll')) {
  $files=@(Get-ChildItem -LiteralPath (Join-Path $CudaRoot 'bin') -Filter $pattern -File)
  if (-not $files.Count) { throw "DLL mancante: $pattern" }
  foreach ($file in $files) { Copy-Item -LiteralPath $file.FullName -Destination $stage -Force }
}
Native $py @((Join-Path $root 'scripts\verify_engine.py'),'--engine',(Join-Path $stage 'audiocpp_cli.exe'),'--backend','cuda')
[IO.File]::WriteAllText((Join-Path $build 'last-stage.txt'),$stage)
if ($BuildOnly) { Write-Host "Build verificata: $stage. Nessuna attivazione richiesta."; exit 0 }

Write-Host '[6/6] Runtime di trascrizione GPU e attivazione' -ForegroundColor Cyan
Native $py @((Join-Path $root 'scripts\install_transcription.py'),'--backend','cuda','--runtime-only')
Native $py @((Join-Path $root 'scripts\activate_engine.py'),'--candidate',$stage,'--backend','cuda')
Write-Host 'GPU attiva. Generazione, separazione, voce e trascrizione verificate come disponibili.' -ForegroundColor Green
Write-Host 'Puoi tornare alla CPU dalle Preferenze o con Attiva-CPU.bat.'
