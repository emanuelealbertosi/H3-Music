# H3-Music - installatore Windows x64 (motore CPU precompilato)
# Uso: powershell -ExecutionPolicy Bypass -File install.ps1   (oppure install.bat)
# Non richiede compilatori, Visual Studio o GPU: scarica Python incorporato,
# FFmpeg, i modelli YuE2 e il runtime di trascrizione (torch CPU), estrae il
# motore audio.cpp precompilato da dist/, imposta backend=cpu e avvia il server.

param([switch]$DryRun)

$ErrorActionPreference = 'Stop'
# TLS 1.2 sempre; TLS 1.3 solo se il .NET Framework installato lo conosce.
$tls = [Net.SecurityProtocolType]::Tls12
if ([Enum]::GetNames([Net.SecurityProtocolType]) -contains 'Tls13') { $tls = $tls -bor [Net.SecurityProtocolType]::Tls13 }
[Net.ServicePointManager]::SecurityProtocol = $tls
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Write-Step([int]$n, [string]$text) {
  Write-Host ''
  Write-Host "[$n/7] $text" -ForegroundColor Cyan
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

function Get-Sha256([string]$path) {
  $h = [Security.Cryptography.SHA256]::Create()
  try { $s = [IO.File]::OpenRead($path); return ([BitConverter]::ToString($h.ComputeHash($s))).Replace('-','').ToLower() } finally { $s.Close(); $h.Dispose() }
}

function Run-Python([string]$script, [string[]]$args) {
  Write-Host "  python: $(Split-Path -Leaf $script) $($args -join ' ')"
  & "$root\runtime\python\python.exe" $script @args
  if ($LASTEXITCODE -ne 0) { throw "Script Python fallito: $script (exit code $LASTEXITCODE)" }
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
if ($drive.TotalFreeSpace -lt 15GB) { throw "Spazio insufficiente: servono almeno 15 GB liberi (disponibili $freeGB GB)." }

# ---------- 2. Python incorporato ----------
Write-Step 2 'Python incorporato 3.12.10'
$pydir = "$root\runtime\python"
if (-not (Test-Path "$pydir\python.exe")) {
  Download-File 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' "$root\runtime\python-embed.zip"
  Expand-Zip "$root\runtime\python-embed.zip" $pydir
  Remove-Item -Force "$root\runtime\python-embed.zip"
}
& "$pydir\python.exe" -c "import sys, sqlite3, ssl; print(' ', sys.version.split()[0], '- sqlite3 e ssl ok')"
if ($LASTEXITCODE -ne 0) { throw 'Il Python incorporato non si avvia correttamente. Scarica di nuovo il runtime (cancella runtime\python) e riprova.' }

# ---------- 3. FFmpeg ----------
Write-Step 3 'FFmpeg'
if (-not (Test-Path "$root\runtime\ffmpeg.exe")) {
  # URL versionato e hash bloccato: il link "latest" cambierebbe a ogni release
  # e l'hash non corrisponderebbe piu'. FFmpeg 9.0.2 essentials (2026-09-19).
  Download-File 'https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-9.0.2-essentials_build.zip' "$root\runtime\ffmpeg.zip"
  $sha = Get-Sha256 "$root\runtime\ffmpeg.zip"
  if ($sha -ne '60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba') { throw "SHA-256 FFmpeg non valido: $sha" }
  Expand-Zip "$root\runtime\ffmpeg.zip" "$root\runtime\ffmpeg-extract"
  Copy-Item "$root\runtime\ffmpeg-extract\bin\ffmpeg.exe" "$root\runtime\ffmpeg.exe" -Force
  Copy-Item "$root\runtime\ffmpeg-extract\bin\ffprobe.exe" "$root\runtime\ffprobe.exe" -Force
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
& "$eng\audiocpp_cli.exe" --version | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Motore non avviabile (exit code $LASTEXITCODE)" }

# ---------- 5. Modelli YuE2 ----------
Write-Step 5 'Modelli YuE2 (download da Hugging Face)'
Run-Python "$root\scripts\download_models.py" @()

# ---------- 6. Trascrizione ----------
Write-Step 6 'Trascrizione (SheetSage2 + MERT-v2, torch CPU)'
Run-Python "$root\scripts\install_transcription.py" @('--backend','cpu')

# torch e' codice C++: se sul PC manca il redistributable Visual C++ 2015-2022
# non riesce a caricare msvcp140.dll. Le stesse DLL sono nel motore precompilato:
# le copiamo accanto a python.exe e in torch\lib e riproviamo.
$txpy = "$root\runtime\transcription\python.exe"
if (Test-Path $txpy) {
  & $txpy -c "import torch; print('  torch', torch.__version__)"
  if ($LASTEXITCODE -ne 0) {
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
    & $txpy -c "import torch; print('  torch', torch.__version__)"
    if ($LASTEXITCODE -ne 0) { throw 'torch non si carica: installa il redistributable Microsoft Visual C++ 2015-2022 x64 e rilancia install.bat.' }
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
