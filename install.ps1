# H3-Music - installatore Windows x64 (motore CPU precompilato)
# Uso: powershell -ExecutionPolicy Bypass -File install.ps1   (oppure install.bat)
# Non richiede compilatori, Visual Studio o GPU: scarica Python incorporato,
# FFmpeg, i modelli YuE2 e il runtime di trascrizione (torch CPU), estrae il
# motore audio.cpp precompilato da dist/, imposta backend=cpu e avvia il server.

param([switch]$DryRun, [switch]$SkipGpuBuild, [switch]$LatestModels, [string]$Models = 'both')

$ErrorActionPreference = 'Stop'
# TLS 1.2 sempre; TLS 1.3 solo se il .NET Framework installato lo conosce.
$tls = [Net.SecurityProtocolType]::Tls12
if ([Enum]::GetNames([Net.SecurityProtocolType]) -contains 'Tls13') { $tls = $tls -bor [Net.SecurityProtocolType]::Tls13 }
[Net.ServicePointManager]::SecurityProtocol = $tls
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
# Python in UTF-8 a prescindere dalla codepage di sistema: evita errori di
# codifica su console non Unicode e mantiene coerenti i file scritti dagli script.
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

function Write-Step([int]$n, [string]$text) {
  Write-Host ''
  Write-Host "[$n/8] $text" -ForegroundColor Cyan
}

function Get-Text([string]$url) {
  $req = [Net.HttpWebRequest]::Create($url)
  $req.Timeout = 15000
  $req.UserAgent = 'H3-Music-Installer'
  $resp = $req.GetResponse()
  try {
    $sr = New-Object IO.StreamReader($resp.GetResponseStream())
    return $sr.ReadToEnd()
  } finally { $sr.Close(); $resp.Close() }
}

function New-ParentDir([string]$path) {
  $dir = Split-Path -Parent $path
  if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
}

function Download-File([string]$url, [string]$dest) {
  if (Test-Path -LiteralPath $dest) { Write-Host "  gia' presente: $(Split-Path -Leaf $dest)"; return }
  New-ParentDir $dest
  $tmp = "$dest.partial"
  $why = ''
  # 1) .NET HttpWebRequest (TLS 1.2/1.3 impostati sopra)
  for ($i = 0; $i -lt 3; $i++) {
    try {
      $req = [Net.HttpWebRequest]::Create($url)
      $req.Timeout = 300000
      $req.UserAgent = 'H3-Music-Installer'
      $resp = $req.GetResponse()
      try {
        $fs = [IO.File]::Open($tmp, [IO.FileMode]::Create, [IO.FileAccess]::Write)
        try {
          $buf = New-Object byte[] (1MB)
          while (($n = $resp.GetResponseStream().Read($buf, 0, $buf.Length)) -gt 0) { $fs.Write($buf, 0, $n) }
        } finally { $fs.Close() }
      } finally { $resp.Close() }
      Move-Item -LiteralPath $tmp -Destination $dest -Force
      Write-Host "  scaricato: $(Split-Path -Leaf $dest) ($([math]::Round((Get-Item -LiteralPath $dest).Length / 1MB, 1)) MB)"
      return
    } catch {
      if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue }
      $why = $_.Exception.Message
      if ($_.Exception.InnerException) { $why = "$why - $($_.Exception.InnerException.Message)" }
      Write-Host "  nuovo tentativo $($i+1)/3... ($why)" -ForegroundColor DarkYellow
      Start-Sleep -Seconds 3
    }
  }
  # 2) Ripiego su curl.exe (usa lo stack TLS di Windows): utile se .NET non
  #    riesce a negoziare TLS o mancano certificati radice aggiornati.
  $curl = Join-Path $env:SystemRoot 'System32\curl.exe'
  if (Test-Path -LiteralPath $curl) {
    Write-Host '  riprovo con curl.exe...' -ForegroundColor DarkYellow
    & $curl '--location' '--fail' '--silent' '--show-error' '--retry' '3' '--retry-delay' '3' '--output' $tmp $url
    if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $tmp)) {
      Move-Item -LiteralPath $tmp -Destination $dest -Force
      Write-Host "  scaricato con curl: $(Split-Path -Leaf $dest) ($([math]::Round((Get-Item -LiteralPath $dest).Length / 1MB, 1)) MB)"
      return
    }
    if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue }
    $why = "$why - anche curl.exe ha fallito (exit $LASTEXITCODE)"
  }
  throw "Download fallito: $url`n  motivo: $why"
}

function Expand-Zip([string]$zip, [string]$dest) {
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  New-ParentDir $dest
  if (Test-Path -LiteralPath $dest) { Remove-Item -Recurse -Force $dest }
  [IO.Compression.ZipFile]::ExtractToDirectory($zip, $dest)
}

# Esegue un programma esterno e restituisce il suo exit code.
# Serve perche' con ErrorActionPreference='Stop' qualunque messaggio su stderr
# (pip, python, git, il motore) verrebbe trattato come errore fatale: qui lo
# stderr viene mostrato ma non interrompe l'installazione.
function Invoke-Native([string]$exe, [string[]]$arguments) {
  $prev = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  $code = 0
  try {
    & $exe @arguments 2>&1 | ForEach-Object {
      if ($_ -is [System.Management.Automation.ErrorRecord]) { Write-Host "  $($_.Exception.Message)" }
      else { Write-Host "  $_" }
    }
    $code = $LASTEXITCODE
  } finally { $ErrorActionPreference = $prev }
  if ($null -eq $code) { $code = 0 }
  return $code
}

function Get-Sha256([string]$path) {
  $h = [Security.Cryptography.SHA256]::Create()
  try { $s = [IO.File]::OpenRead($path); return ([BitConverter]::ToString($h.ComputeHash($s))).Replace('-','').ToLower() } finally { $s.Close(); $h.Dispose() }
}

function Run-Python([string]$script, [string[]]$args) {
  Write-Host "  python: $(Split-Path -Leaf $script) $($args -join ' ')"
  $code = Invoke-Native "$root\runtime\python\python.exe" (@($script) + $args)
  if ($code -ne 0) { throw "Script Python fallito: $script (exit code $code)" }
}

# ---------- 1. Prerequisiti ----------
Write-Step 1 'Verifica prerequisiti'
if (-not [Environment]::Is64BitOperatingSystem) { throw 'H3-Music richiede Windows x64.' }
$drive = New-Object IO.DriveInfo([IO.Path]::GetPathRoot((Resolve-Path $root).Path))
$freeGB = [math]::Round($drive.TotalFreeSpace / 1GB, 1)
Write-Host "  Spazio libero su disco: ${freeGB} GB"
try {
  $ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem -ErrorAction Stop).TotalPhysicalMemory / 1GB, 1)
  Write-Host "  Memoria fisica: ${ramGB} GB"
  if ($ramGB -lt 24) {
    Write-Host '  Nota: la generazione su CPU riserva molta memoria (circa 20 GB nel picco).' -ForegroundColor Yellow
    Write-Host '  Con meno di 24 GB conviene chiudere le altre applicazioni o aumentare il file di paging.' -ForegroundColor Yellow
  }
} catch { Write-Host '  Memoria fisica: non rilevata' }
if ($DryRun) { Write-Host 'DRY RUN - nessun download eseguito.'; exit 0 }
if ($drive.TotalFreeSpace -lt 20GB) { throw "Spazio insufficiente: servono almeno 20 GB liberi (disponibili $freeGB GB)." }

# ---------- 2. Python incorporato ----------
Write-Step 2 'Python incorporato 3.12.10'
$pydir = "$root\runtime\python"
if (-not (Test-Path "$pydir\python.exe")) {
  Download-File 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' "$root\runtime\python-embed.zip"
  Expand-Zip "$root\runtime\python-embed.zip" $pydir
  Remove-Item -Force "$root\runtime\python-embed.zip"
}
$code = Invoke-Native "$pydir\python.exe" @('-c', "import sys, sqlite3, ssl; print(' ', sys.version.split()[0], '- sqlite3 e ssl ok')")
if ($code -ne 0) { throw 'Il Python incorporato non si avvia correttamente. Controlla che runtime\python contenga python.exe e riprova.' }

# ---------- 3. FFmpeg ----------
Write-Step 3 'FFmpeg'
if (-not (Test-Path "$root\runtime\ffmpeg.exe")) {
  # URL versionato e hash bloccato: il link "latest" cambierebbe a ogni release
  # e l'hash non corrisponderebbe piu'. FFmpeg 9.0.2 essentials (2026-09-19).
  Download-File 'https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-9.0.2-essentials_build.zip' "$root\runtime\ffmpeg.zip"
  $sha = Get-Sha256 "$root\runtime\ffmpeg.zip"
  if ($sha -ne '60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba') { throw "SHA-256 FFmpeg non valido: $sha" }
  Expand-Zip "$root\runtime\ffmpeg.zip" "$root\runtime\ffmpeg-extract"
  # Lo zip di gyan.dev contiene una cartella di primo livello
  # (ffmpeg-<versione>-essentials_build\bin\...): cerchiamo gli eseguibili
  # ovunque invece di dare per scontata la struttura.
  $ff = Get-ChildItem "$root\runtime\ffmpeg-extract" -Recurse -Filter 'ffmpeg.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
  $fp = Get-ChildItem "$root\runtime\ffmpeg-extract" -Recurse -Filter 'ffprobe.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $ff -or -not $fp) { throw 'Nello zip di FFmpeg non trovo ffmpeg.exe e ffprobe.exe.' }
  Copy-Item $ff.FullName "$root\runtime\ffmpeg.exe" -Force
  Copy-Item $fp.FullName "$root\runtime\ffprobe.exe" -Force
  Remove-Item -Recurse -Force "$root\runtime\ffmpeg-extract"
  Remove-Item -Force "$root\runtime\ffmpeg.zip"
}

# ---------- 4. Motore audio.cpp (CPU, precompilato) ----------
Write-Step 4 'Motore audio.cpp (CPU, precompilato)'
$zip = "$root\dist\h3-engine-cpu-win64.zip"
if (-not (Test-Path $zip)) { throw "Zip del motore non trovata: dist/h3-engine-cpu-win64.zip" }
$eng = "$root\runtime\engine"
if (-not (Test-Path "$eng\audiocpp_cli.exe")) {
  if (Test-Path $eng) { Remove-Item -Recurse -Force $eng }
  Expand-Zip $zip $eng
}
$code = Invoke-Native "$eng\audiocpp_cli.exe" @('--version')
if ($code -ne 0) { throw "Motore non avviabile (exit code $code)" }

# ---------- 5. Modelli YuE2 ----------
Write-Step 5 'Modelli YuE2 (download da Hugging Face)'
$modelArgs = @()
if ($LatestModels) {
  Write-Host '  modalita -LatestModels: prendo l ultima revisione del repository' -ForegroundColor DarkYellow
  $modelArgs += '--latest'
}
if ($Models -notin @('both', 'q8', 'q4')) { throw "Valore non valido per -Models: $Models (usa both, q8 o q4)." }
if ($Models -eq 'both') {
  Write-Host '  scarico entrambi i modelli: Q8 (4,0 GB, qualita massima) e Q4 (2,5 GB, piu veloce su CPU).' -ForegroundColor DarkYellow
  Write-Host '  Si sceglie poi dall app, in Preferenze: non serve riscaricare nulla.' -ForegroundColor DarkYellow
} else {
  Write-Host "  scarico solo il modello $Models." -ForegroundColor DarkYellow
  $modelArgs += @('--quant', $Models)
}
Run-Python "$root\scripts\download_models.py" $modelArgs

# ---------- 6. Trascrizione ----------
Write-Step 6 'Trascrizione (SheetSage2 + MERT-v2, torch CPU)'
Run-Python "$root\scripts\install_transcription.py" @('--backend','cpu')

# torch e' codice C++: se sul PC manca il redistributable Visual C++ 2015-2022
# non riesce a caricare msvcp140.dll. Le stesse DLL sono nel motore precompilato:
# le copiamo accanto a python.exe e in torch\lib e riproviamo.
$txpy = "$root\runtime\transcription\python.exe"
if (Test-Path $txpy) {
  $code = Invoke-Native $txpy @('-c', "import torch; print('  torch', torch.__version__)")
  if ($code -ne 0) {
    Write-Host '  torch non si carica: copio il runtime C++ dal motore precompilato' -ForegroundColor DarkYellow
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $arc = [IO.Compression.ZipFile]::OpenRead($zip)
    try {
      foreach ($dir in @("$root\runtime\transcription", "$root\runtime\transcription\Lib\site-packages\torch\lib")) {
        if (-not (Test-Path $dir)) { continue }
        foreach ($e in $arc.Entries) {
          if ($e.Name -like '*140*.dll') { [IO.Compression.ZipFileExtensions]::ExtractToFile($e, (Join-Path $dir $e.Name), $true) }
        }
        Write-Host "  runtime C++ copiato in $dir"
      }
    } finally { $arc.Dispose() }
    $code = Invoke-Native $txpy @('-c', "import torch; print('  torch', torch.__version__)")
    if ($code -ne 0) { throw 'torch non si carica: installa il redistributable Microsoft Visual C++ 2015-2022 x64 e rilancia install.bat.' }
  }
}

# ---------- 7. Impostazioni e avvio del server ----------
Write-Step 7 'Impostazioni e avvio del server'
Run-Python "$root\scripts\seed_settings.py" @()

try {
  Get-Text 'http://127.0.0.1:8776/api/shutdown' | Out-Null
  for ($i = 0; $i -lt 20; $i++) { Start-Sleep -Milliseconds 500; try { Get-Text 'http://127.0.0.1:8776/api/health'; continue } catch { break } }
} catch {}

$proc = Start-Process -FilePath "$pydir\pythonw.exe" -ArgumentList "app.py" -WorkingDirectory $root -PassThru
$ready = $false
for ($i = 0; $i -lt 90; $i++) {
  Start-Sleep -Milliseconds 500
  try {
    if ((Get-Text 'http://127.0.0.1:8776/api/state') -match '"ready":\s*true') { $ready = $true; break }
  } catch {}
}
if (-not $ready) {
  try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
  throw 'Server non pronto dopo l''avvio. Controlla logs/server.log.'
}

Write-Host ''
Write-Host 'INSTALLAZIONE COMPLETATA' -ForegroundColor Green
Write-Host '  Server attivo: http://127.0.0.1:8776'
Write-Host '  Per aprire l''app: H3-Music.exe (o Avvia-H3-Music.bat)'

# ---------- 8. Motore GPU (facoltativo) ----------
Write-Step 8 'Motore GPU (facoltativo)'
$gpuName = ''
try { $gpuName = (& nvidia-smi --query-gpu=name --format=csv,noheader 2>$null | Select-Object -First 1) } catch {}
$cudaRoot = $env:CUDA_PATH
if (-not $cudaRoot -or -not (Test-Path (Join-Path $cudaRoot 'bin\nvcc.exe'))) {
  $cudaBase = 'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA'
  $cudaRoot = (Get-ChildItem $cudaBase -Directory -ErrorAction SilentlyContinue |
    Where-Object { Test-Path (Join-Path $_.FullName 'bin\nvcc.exe') } |
    Sort-Object Name | Select-Object -Last 1).FullName
}
$vsFound = ''
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (Test-Path $vswhere) {
  $vsFound = (& $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>$null | Select-Object -First 1)
}
if (-not $vsFound) {
  foreach ($base in @(${env:ProgramFiles(x86)}, ${env:ProgramFiles})) {
    foreach ($edition in @('BuildTools', 'Community', 'Professional', 'Enterprise')) {
      $p = Join-Path $base "Microsoft Visual Studio\2022\$edition"
      if (-not $vsFound -and (Test-Path (Join-Path $p 'VC\Auxiliary\Build\vcvarsall.bat'))) { $vsFound = $p }
    }
  }
}

if ($gpuName) { Write-Host "  GPU NVIDIA: $gpuName" } else { Write-Host '  GPU NVIDIA: non rilevata' }
if ($cudaRoot) { Write-Host "  CUDA Toolkit: $cudaRoot" } else { Write-Host '  CUDA Toolkit: assente' }
if ($vsFound) { Write-Host "  Visual Studio C++: $vsFound" } else { Write-Host '  Visual Studio C++: assente' }

$gpuScript = "$root\scripts\build_engine_cuda.ps1"
if ($SkipGpuBuild) {
  Write-Host '  Build GPU saltata (-SkipGpuBuild).'
} elseif ($gpuName -and $cudaRoot -and $vsFound) {
  Write-Host ''
  Write-Host '  Tutti gli strumenti ci sono: compilo il motore CUDA per questa scheda.' -ForegroundColor Green
  Write-Host '  La compilazione puo durare da 20 a 60 minuti e usa la CPU; puoi interromperla con Ctrl+C.' -ForegroundColor DarkYellow
  Write-Host '  L app intanto e gia funzionante con il motore CPU.' -ForegroundColor DarkYellow
  Write-Host ''
  $code = Invoke-Native 'powershell' @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $gpuScript)
  if ($code -ne 0) {
    Write-Host ''
    Write-Host '  Build GPU non riuscita: l app resta pienamente funzionante su CPU.' -ForegroundColor Yellow
    Write-Host '  Puoi riprovare quando vuoi con: powershell -ExecutionPolicy Bypass -File scripts\build_engine_cuda.ps1' -ForegroundColor Yellow
  }
} else {
  Write-Host ''
  Write-Host '  Il motore CPU e attivo e l app funziona: la GPU e solo un miglioramento.' -ForegroundColor DarkYellow
  Write-Host '  Per generare con la scheda NVIDIA servono:' -ForegroundColor DarkYellow
  if (-not $gpuName) { Write-Host '    - una GPU NVIDIA con driver aggiornato' -ForegroundColor DarkYellow }
  if (-not $vsFound) { Write-Host '    - Visual Studio 2022 Build Tools con "Desktop development with C++"' -ForegroundColor DarkYellow }
  if (-not $cudaRoot) { Write-Host '    - NVIDIA CUDA Toolkit 12.x: https://developer.nvidia.com/cuda-downloads' -ForegroundColor DarkYellow }
  Write-Host '  Quando ci sono, da questa cartella lancia:' -ForegroundColor DarkYellow
  Write-Host '    powershell -ExecutionPolicy Bypass -File scripts\build_engine_cuda.ps1' -ForegroundColor White
  Write-Host '  Non serve reinstallare nulla: lo script compila e passa da solo al backend cuda.' -ForegroundColor DarkYellow
}

