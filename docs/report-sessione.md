# Report della sessione di lavoro

> Aggiornamento successivo: il blocco CUDA descritto al §6 è stato risolto. Per il percorso CPU/GPU corrente e i collaudi, vedi [CPU-GPU.md](CPU-GPU.md).

Documento di riepilogo di tutto il lavoro svolto in questa sessione su H3-Music.
Raccoglie cosa è stato consegnato, i difetti trovati e corretti, le verifiche
eseguite con i numeri misurati, quello che resta da fare e le note pratiche
d'uso. Serve come memoria del lavoro e come elenco delle cose aperte.

---

## 1. Punto di partenza

Richiesta iniziale: capire perché il clone del repository su un secondo PC
(Windows x64, **solo CPU**, 16 GB di RAM) non funzionava, con l'errore del
launcher «Runtime Python non trovato nella cartella H3-Music», e rendere il
repository installabile da un semplice `git clone`.

Causa: `.gitignore` escludeva `runtime/`, `models/` e `vendor/`. Un clone
conteneva quindi solo i sorgenti: nessun runtime Python, nessun modello, nessun
motore. Non c'era niente da installare e nessuno script per farlo.

Obiettivo concordato: installazione da clone su PC x64 anche senza GPU e senza
compilatori, con motore precompilato distribuito nel repository (nessuna
compilazione sulla macchina di destinazione).

---

## 2. Cosa è stato consegnato

### Installazione da clone

| file | contenuto |
|---|---|
| `dist/h3-engine-cpu-win64.zip` | motore audio.cpp precompilato per CPU, **9.372.050 byte**, con le DLL del runtime C++ e OpenMP: nessun compilatore, nessun Visual Studio e nessun redistributable richiesto sul PC di destinazione |
| `install.bat` / `install.ps1` | installatore in 8 passi: prerequisiti, Python incorporato 3.12.10, FFmpeg 9.0.2, motore CPU, pesi YuE2, runtime di trascrizione (torch CPU), impostazioni e avvio del server, verifica GPU facoltativa |
| `scripts/seed_settings.py` | crea `data/music.sqlite` con lo schema dell'app e `backend=cpu` |
| `scripts/install_transcription.py` | runtime di trascrizione: Python 3.11 incorporato, `get-pip`, ruota torch CPU, SheetSage2 e MERT-v2 da revisioni fisse, con ripresa e verifica di dimensione e SHA-256 |
| `scripts/download_models.py` | pesi YuE2, con revisione fissa, ripresa dei download e registro di ciò che è installato |
| `scripts/download_tools.py` | modelli ausiliari (separazione e conversione vocale) |
| `scripts/build_engine_cpu.ps1` | build riproducibile del motore CPU (generatore Visual Studio, `/utf-8`) |
| `scripts/package_engine_cpu.py` | pacchettizzazione del motore nello zip distribuito |
| `scripts/build_engine_cuda.ps1` | build del motore CUDA **sulla macchina di destinazione**, con architettura rilevata dalla scheda e ripristino del motore CPU precedente |
| `scripts/set_backend.py` | passa da `cpu` a `cuda` senza toccare le altre impostazioni |
| `.gitignore` / `.gitattributes` | manifest dei modelli tracciati; zip, exe e dll mai normalizzati da `autocrlf` |
| `docs/voce-su-misura.md` | piano e stato della funzione «voce su misura» |

### Funzione «voce su misura» (sperimentale)

1. **Separazione voce/base** con HTDemucs (59 MB): nuovo tipo di lavoro `sep`,
   pulsante «Separa voce e base» nel dettaglio di un brano completato, quattro
   stem (`vocals`, `drums`, `bass`, `other`).
2. **Conversione zero-shot della voce cantata** con SeedVC (2,98 GB): libreria
   delle voci in `data/voci/<nome>/` con un campione **parlato**, finestra
   «Canta con una voce», tipo di lavoro `voice`.
3. **Rimix** con FFmpeg: la voce convertita (mono) viene unita alla base
   strumentale in un `audio.wav` 48 kHz stereo.
4. Collaudo su CPU completato; collaudo su GPU non eseguibile in questo
   ambiente (vedi §6).

### Correzioni d'uso nell'app

- **Barra di avanzamento** per generazione, separazione e conversione, con fase,
  percentuale stimata e tempo trascorso, nella striscia «In corso», nella coda e
  nel dettaglio; aggiornamento automatico ogni 3,5 secondi.
- **Profilo di memoria adattivo**: le arene del motore vengono ridotte quando la
  memoria disponibile è poca, per non far fallire la generazione sui PC con
  poca RAM o file di paging piccolo.
- **Messaggi d'errore utili**: memoria di sistema esaurita, memoria video (VRAM)
  esaurita, motore che non include un modello richiesto.
- Pagina Sistema: mostra memoria fisica e limite di commit; non fallisce più sui
  PC senza `nvidia-smi`; la nota del motore segue il backend (CPU o CUDA).
- La precisione mostrata nello Studio segue il modello scelto (Q8 o Q4).
- Preset di stile con la voce esplicita (femminile, maschile, duetto).

---

## 3. Difetti trovati e corretti

Tutti i punti seguenti sono difetti reali, emersi usando l'installazione sul
secondo PC o collaudando in una copia isolata. Molti erano «funzionava sul mio
PC»: il caso della cartella `runtime/` inesistente, per esempio, non si vedeva
qui perché l'installazione locale la conteneva già.

| # | difetto | effetto | correzione |
|---|---|---|---|
| 1 | il launcher non trovava il runtime Python | clone inutilizzabile | installatore completo + motore precompilato nel repository |
| 2 | download in `runtime\` inesistente | 4 tentativi falliti al passo 2 | creazione della cartella di destinazione prima di scrivere |
| 3 | errori di download senza motivo | diagnosi impossibile | messaggio dell'eccezione a ogni tentativo |
| 4 | TLS di .NET non negozia | download fermo | ripiego su `curl.exe` (stack TLS di Windows) |
| 5 | zip FFmpeg con cartella di primo livello | `ffmpeg.exe` non trovato al passo 3 | ricerca ricorsiva degli eseguibili |
| 6 | `stderr` dei programmi esterni considerato fatale | installazione interrotta (pip, python, git) | esecutore nativo dedicato che riporta l'exit code |
| 7 | trattino lungo in `seed_settings.py` | `UnicodeEncodeError` su console non Unicode | script ASCII puri e UTF-8 esplicito sui file |
| 8 | **trattino lungo negli script PowerShell** | lo script non compilava affatto su codepage ANSI | `install.ps1`, `install.bat`, `build_engine_cuda.ps1` in ASCII puro |
| 9 | `$args` come nome di parametro in `Run-Python` | gli script partivano senza opzioni: passo 6 fallito | parametro rinominato; verificato con uno script di prova |
| 10 | `requirements.txt` installato mentre l'altro thread lo scaricava | installazione interrotta a metà (race) | il runtime scarica una propria copia del file |
| 11 | `models/tools-manifest.json` escluso da `.gitignore` | installazione interrotta sul passo nuovo | eccezione aggiunta a `.gitignore` |
| 12 | Hugging Face ha cambiato i pesi a monte | `size mismatch` sul modello principale | revisione fissata (`f7cb0712`) e registro dei modelli installati |
| 13 | `lfs` del manifest confrontato come stringa invece che come oggetto | ogni file con hash risultava «hash mismatch» | lettura corretta del campo `oid` |
| 14 | `yue2.model_gguf` passato nella richiesta | il motore ignorava la scelta e cercava sempre Q8 | passaggio come opzione di sessione (`--session-option`) |
| 15 | `nvidia-smi` assente sui PC senza NVIDIA | la pagina Sistema mostrava `[WinError 2]` | interrogazioni protette |
| 16 | arene di default del motore (circa 20 GB) | generazione fallita su PC da 16 GB | profilo di memoria adattivo |
| 17 | **campionamento a 48 kHz contro i 44,1 kHz dei modelli** | separazione sempre fallita sui brani generati | ricampionamento con FFmpeg prima della separazione |
| 18 | precisione «Q8» scritta fissa nell'interfaccia | dato sbagliato con il modello Q4 | segue l'impostazione |

---

## 4. Verifiche eseguite e numeri misurati

**Motore CPU** (Ryzen 5 3600, 8 thread; è lo stesso binario distribuito nello zip):

- pianificazione di un brano: **6,8 minuti** con Q8, **5,8 minuti** con Q4, con
  artefatti H3 scritti e nessun troncamento;
- separazione: **30 secondi di audio separati in 36-37 secondi** (rtf 1,24),
  con i quattro stem prodotti;
- conversione vocale: catena completa eseguita (content, style, f0, length
  regulator, diffusione, vocoder) e file scritto; costo **20-60 volte la durata
  dell'audio** su CPU (20 secondi in circa 7 minuti, 3 secondi con rtf 62,6);
- rimix: voce mono + tre stem → `audio.wav` **48 kHz stereo**.

**Catena completa attraverso l'app** (istanza di prova isolata, motore CPU):
separazione di un frammento → conversione verso un campione di riferimento →
rimix, tutti completati con successo; coda, avanzamento e file finali corretti.

**Installazione**: funzioni dell'installatore provate davvero (scaricamento di
124 MB da un server locale, verifica SHA-256, estrazione, idempotenza); URL e
hash di tutti i download verificati uno per uno (python.org, FFmpeg con hash
bloccato, indice PyTorch con `torchaudio 2.8.0+cpu` e tutte le dipendenze di
torch, MERT-v2 e SheetSage2 a revisione fissa, pesi YuE2).

**Clone**: il repository è stato clonato in una cartella pulita più volte; lo zip
del motore arriva **byte-identico** (SHA-256 `74f1e59e…`) e gli script si
compilano anche decodificati come ANSI.

**Dimensioni dei pesi**: YuE2 Q8 4,26 GB e Q4 2,67 GB; VAE 265 MB; SheetSage2
228 MB; MERT-v2 2,53 GB; ruota torch CPU 619 MB; HTDemucs 59 MB; SeedVC 2,98 GB.

---

## 5. Scelte tecniche rilevanti

- **Motore precompilato, non compilato a destinazione**: la build CPU è stata
  prodotta qui con il generatore Visual Studio (non Ninja, che in questo
  ambiente si blocca) con `/utf-8`, indispensabile perché diversi sorgenti di
  audio.cpp contengono letterali non ASCII.
- **Revisioni fissate** per tutti i pesi: il repository a monte è stato
  modificato durante la sessione e i file dell'app devono restare quelli
  collaudati. Il registro `models/installed-models.json` permette all'app di
  accettare anche altre versioni (per esempio con `--latest`).
- **Nessuna modifica al database**: i nuovi tipi di lavoro (`sep`, `voice`)
  usano le tabelle esistenti; le funzioni preesistenti non sono state toccate,
  solo affiancate.
- **Nessuna ricompilazione del motore per le nuove funzioni**: audio.cpp
  supporta già separazione (`sep`) e conversione cantata (`svc`).

---

## 6. Cosa resta aperto

**Collaudo su GPU: bloccato.** Il motore CUDA di questa macchina, compilato a
settembre con un insieme di modelli più ristretto, non contiene le famiglie
`htdemucs` e `seed_vc` (errore «unsupported model family hint»). Ricompilarlo
qui non è possibile: il generatore Visual Studio richiede l'integrazione CUDA
per VS (non installata, e si installerebbe solo scrivendo dentro
`C:\Program Files (x86)\Microsoft Visual Studio\…`, fuori dallo spazio di lavoro
disponibile), mentre il generatore Ninja è bloccato dall'ambiente.

Serve la macchina dell'utente, con una delle due strade:

- `powershell -ExecutionPolicy Bypass -File scripts\build_engine_cuda.ps1`
  (circa 45 minuti; sostituisce il motore e conserva il precedente in
  `runtime/engine-cpu`), poi il collaudo GPU completo;
- oppure il PC solo CPU, dove il motore distribuito include già entrambe le
  famiglie.

**Da valutare con l'utente**: se la conversione vocale vada resa più comoda su
CPU (per esempio convertire solo una finestra di secondi scelta, invece
dell'intero brano), visto il costo di 20-60 volte la durata.

**Non verificato**: la qualità percettiva della conversione (somiglianza al
campione) — richiede un ascolto, quindi la valutazione spetta all'utente.

---

## 7. Note pratiche d'uso

- Requisiti del motore CPU: processore x64 con AVX2, FMA, F16C e BMI2.
- Spazio: circa 20 GB liberi con entrambi i modelli YuE2.
- Memoria: la generazione riserva molta memoria di sistema; con 16 GB conviene
  lasciare il file di paging gestito da Windows, e l'app riduce da sola le
  prenotazioni quando serve.
- Tempi su CPU: pianificazione di un brano alcuni minuti; sintesi completa molto
  più lunga (una prova ha superato i 45 minuti senza finire, su macchina
  occupata). Con Q4 è più rapida.
- Voce: YuE2 non accetta una voce di riferimento; il timbro si indirizza con il
  testo di stile e con il seed. Per una voce specifica serve la catena
  separazione → conversione → rimix descritta sopra.
- L'installatore è ripetibile: rilanciarlo salta ciò che è già presente.

---

## 8. Metodo: cosa ha insegnato questa sessione

Tre abitudini hanno ripagato, e conviene mantenerle:

1. **Provare l'artefatto vero, non una copia.** Lo zip FFmpeg costruito a mano
   non aveva la cartella di primo livello di quello reale: il test passava e
   l'installazione no.
2. **Provare il comando esatto che usa l'app.** La conversione è stata data per
   funzionante due volte prima di scoprire che serviva `--out` e non `--out-dir`.
3. **Collaudare in una copia isolata.** L'istanza di prova con il motore CPU ha
   permesso di verificare la catena completa senza toccare l'installazione in
   uso, e senza ricompilare nulla.

---

## 9. Stato del repository

Tutto il lavoro è pubblicato sul ramo `main` di
`https://github.com/emanuelealbertosi/H3-Music`. Le modifiche della sessione
sono distribuite in una quindicina di commit, fra cui: installatore e motore CPU
precompilato, correzioni dell'installazione sul secondo PC, revisione fissa dei
modelli e scelta Q8/Q4, profilo di memoria e barra di avanzamento, rimozione
dell'errore su `nvidia-smi`, fasi 1-3 della voce su misura, ricampionamento a
44,1 kHz, istruzioni nel `README.md` e piano in `docs/voce-su-misura.md`.
