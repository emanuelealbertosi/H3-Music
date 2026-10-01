# H3-Music

**Mac:** disponibile una [anteprima scaricabile da GitHub](https://github.com/emanuelealbertosi/H3-Music/releases/tag/v1.7.3-macos-preview.1) per Apple Silicon e Intel. Richiede macOS 15+ e Homebrew; CPU predefinita, Metal facoltativo. [Installazione e limiti della versione Mac](docs/Mac.md).

Studio musicale locale per Windows, basato su **YuE2-3B (Q4, Q8 e BF16)** e **audio.cpp**. Interfaccia in italiano, con gli stessi colori avorio e verde petrolio e i font Manrope/Cormorant delle altre app H3. In questa installazione il motore usa la **GPU CUDA**; il motore precompilato distribuito nel repository per il clone su altri PC usa la **CPU**.

**Base originale 1.7:** nello **Studio** attiva il flag **Base originale**, carica la canzone o scegli un audio già importato e scrivi il nuovo testo nei campi abituali. Premi **Genera il brano**: l'app trascrive la melodia, genera il canto con YuE2, verifica i tempi, estrae la nuova voce e la rimixa con la base separata dalla registrazione originale. La musica non viene rigenerata nel risultato. Lo stile è facoltativo e descrive la voce desiderata; **Clona · usa la mia voce** applica anche il timbro del tuo campione. Senza una qualità esplicita vengono usati 48 passaggi di sintesi. Risultati e nuove versioni restano nello Studio e nella Libreria.

Puoi cambiare fino a **4 minuti (240 secondi) di canto per volta**: apri **Cambia solo un tratto del canto** per scegliere inizio e fine. Il file risultante contiene tutta la canzone, con il canto originale fuori dal tratto scelto. Scrivi un testo con una metrica simile: se il riconoscimento delle note indica una melodia o un ritmo troppo diversi, il mix viene fermato e l'originale resta disponibile. L'allineamento corregge il ritardo della voce e, quando serve, riallinea automaticamente le frasi con raccordi delicati che mantengono l'intonazione. Un ulteriore controllo sul risultato ferma il mix se la correzione non basta; la musica mantiene i propri tempi. La trascrizione non garantisce da sola pronuncia o intelligibilità. Sono possibili residui della separazione. Il percorso usa il backend scelto in Sistema (CPU, CUDA o Metal; su Mac la trascrizione usa CPU). Tutti i modelli sono quelli già previsti dall'installazione, senza servizi a pagamento.

## Contenuto del repository

Questo repository contiene il codice dell’app, l’interfaccia, il launcher Windows, gli script, i test e la documentazione, oltre al motore audio.cpp precompilato per CPU (`dist/h3-engine-cpu-win64.zip`) e il manifest dei pesi YuE2. I modelli pesanti, i runtime, le registrazioni, il database, le cache, i log e i backup restano esclusi da Git: un clone non è ancora un’installazione pronta all’uso, ma `install.bat` la completa scaricando i componenti mancanti (vedi sotto). Gli script di packaging e alcuni collaudi di integrazione si riferiscono all’installazione su `F:\H3-Music` descritta in questa documentazione.

## Installazione da GitHub (clone)

**Cartella dei modelli 1.6.1:** in **Sistema → Cartella dei modelli** scegli una cartella dedicata, anche su un altro disco. **Trasferisci i modelli attuali** copia tutti i modelli (musica, trascrizione, separazione e cambio voce), controlla i file e poi rimuove gli originali, senza riscaricarli. Scegli una cartella vuota e termina o annulla i lavori in coda; il trasferimento richiede spazio per una copia completa nella destinazione. Se li hai già spostati manualmente, scegli **Usa i modelli già presenti** e indica la cartella che contiene `yue2`, `tools`, `SheetSage2` e `MERT-v2-FullSong`. I nuovi download usano la posizione scelta. Brani, campioni vocali, runtime e preferenze CPU/GPU restano nell’app. La scelta è salvata solo su questo PC in `data/model-location.json`, esclusa da Git.

Puoi scegliere la posizione anche durante la prima installazione: su Windows `install.bat -Models q4 -ModelDirectory "F:\Modelli\H3-Music"`; su Mac esegui `bash Installa-Mac.command --models-dir "/Volumes/NomeDisco/Modelli/H3-Music"`. Questi comandi trasferiscono eventuali modelli già installati prima dei download. Su Mac viene verificato separatamente lo spazio per i modelli e per Python quando si trovano su dischi diversi. Il disco dei modelli deve restare disponibile mentre usi l’app.

**Pulizia Libreria 1.5.6:** ogni risultato ha un cestino. Per eliminare più sessioni, spunta i brani oppure usa **Seleziona tutti i risultati visibili**, poi **Elimina selezionati**. La conferma elenca tutti i titoli scelti, anche quelli selezionati prima di cambiare filtro. L’eliminazione è definitiva e rimuove i file delle sessioni per liberare spazio; conserva progetti, audio importati e campioni vocali. I risultati necessari a lavori in corso o a cambi voce che condividono le tracce vengono protetti.

**Accesso remoto privato:** con Tailscale installato e connesso, esegui **Attiva-Accesso-Remoto.bat**. Mostra l’indirizzo HTTPS da aprire sul telefono o su un altro PC nella tua rete Tailscale. Il PC deve restare acceso e H3-Music avviata; i modelli continuano a usare la CPU/GPU del PC. L’attivazione usa una porta dedicata (8776) e conserva gli altri servizi Serve. **Disattiva-Accesso-Remoto.bat** rimuove solo questo accesso. La configurazione è locale in `data/remote-access.json`, esclusa da Git: chi clona il repository mantiene l’accesso solo locale finché non lo abilita. Non viene attivato Funnel pubblico. L’accesso alla rete e al servizio è regolato dalle autorizzazioni Tailscale; H3-Music non aggiunge un secondo login. [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve).

**Studio 1.5.4:** al termine della generazione il risultato resta nella pagina di creazione, con player e selettore delle versioni del progetto. Modifica testo e stile nei campi, oppure scegli **Usa lo spartito del brano** per caricare l’ABC generato, poi **Genera nuova versione**. Le versioni precedenti restano disponibili; gli aggiornamenti della barra non interrompono il player e non sovrascrivono la bozza. Dopo `git pull`, riapri l’app o aggiorna la pagina.

**Aggiornamento trascrizione 1.5.2:** se l'app è già installata, dopo `git pull` esegui **Aggiorna-Trascrizione.bat**. Installa le correzioni ufficiali SheetSage2 alla scrittura di accordi e tonalità, riutilizzando i pesi e conservando runtime e preferenze CPU/GPU. Su questo PC l'aggiornamento è già applicato. Le nuove installazioni ricevono direttamente la revisione aggiornata. [Dettagli](docs/TRANSCRIPTION-ENGINE.md).

Su un PC Windows x64 senza GPU dedicata:

1. `git clone https://github.com/emanuelealbertosi/H3-Music.git`
2. Nella cartella del clone, esegui `install.bat` (oppure `powershell -ExecutionPolicy Bypass -File install.ps1`).

L’installatore non richiede compilatori né Visual Studio: estrae il motore audio.cpp precompilato per CPU da `dist/`, scarica Python incorporato 3.12, FFmpeg, i pesi YuE2 (Q8 e Q4, circa 7 GB) i modelli di separazione e conversione vocale (circa 3 GB) e il runtime di trascrizione con torch CPU (SheetSage2 + MERT-v2, circa 3 GB), imposta `backend=cpu` nel database e avvia il server su `127.0.0.1:8776`. Servono circa 20 GB di spazio libero e una connessione internet; i download sono riprendibili se interrotti. Per scaricare un solo modello: `install.bat -Models q4` (oppure `q8`).

In **Sistema → Modello musicale** puoi scegliere **Q4**, **Q8** oppure **BF16**. Q4 usa circa 2,5 GiB di pesi, Q8 circa 4,0 GiB; BF16 conserva i pesi a 16 bit e usa circa 6,8 GiB. Q8 resta la scelta iniziale. Il modello non cambia la precisione della trascrizione SheetSage2.

BF16 è facoltativo: esegui **`Installa-BF16.bat`**, poi selezionalo in Sistema e salva le preferenze. Il download aggiuntivo è di 7,26 GB e non elimina Q4/Q8. Per installare tutto: `install.bat -Models all`; per il solo modello principale BF16: `install.bat -Models bf16`. La memoria richiesta durante la generazione supera la dimensione dei pesi. Sulla RTX 5070 Ti 16 GB è riuscita una prova italiana di circa un minuto, con 9,1 GiB di memoria GPU totale osservata. Pronuncia e accenti vanno confrontati all'ascolto: la maggiore precisione dei pesi non garantisce la correttezza linguistica. Vedi [BF16 e fedeltà delle cover](docs/BF16-e-cover.md).

Al termine apri **H3-Music.exe** (o `Avvia-H3-Music.bat`): la finestra app si apre sull’app già attiva. La generazione funziona interamente su CPU: le sintesi richiedono più tempo che sulla GPU e il numero di thread è regolabile nelle impostazioni.

Il motore CPU precompilato richiede un processore x64 con **AVX2, FMA, F16C e BMI2** (Intel Haswell 2013 o successivi, AMD Excavator/Zen o successivi). L’installatore è ripetibile: ogni passo salta ciò che è già presente, quindi si può rilanciare `install.bat` dopo un’interruzione senza riscaricare tutto.

I pesi YuE2 vengono presi da una **revisione fissa** del repository Hugging Face, quella con cui l’app è collaudata: a monte i file cambiano (il 26/09/2026 il modello Q8 è stato sostituito con uno di dimensione diversa) e un’installazione deve restare riproducibile. L’installatore registra dimensioni e SHA-256 di ciò che ha scaricato in `models/installed-models.json`, ed è quel registro che l’app consulta per stabilire se i modelli sono pronti. Per prendere invece l’ultima revisione disponibile: `install.bat -LatestModels` (in tal caso dimensioni e hash attesi vengono letti dall’API di Hugging Face e scritti nello stesso registro).

La generazione su CPU riserva molta memoria di sistema: il motore prealloca le arene dei grafi (circa 20 GB nel picco di una generazione completa, oltre ai pesi). Sono consigliati **32 GB di RAM**; con 16 GB conviene chiudere le altre applicazioni e lasciare il file di paging gestito da Windows. Come riferimento, su un Ryzen 5 3600 (6 core, 8 thread) la sola pianificazione di un brano richiede circa 7 minuti; la sintesi audio completa è sensibilmente più lunga.

### CPU predefinita e GPU facoltativa

Una nuova installazione parte sempre su **CPU**, anche quando rileva una scheda NVIDIA. `install.bat` non compila e non attiva CUDA automaticamente. Su un'installazione esistente conserva le preferenze e un runtime di trascrizione già funzionante.

Per usare NVIDIA CUDA, esegui **`Attiva-GPU.bat`**. Servono un driver NVIDIA compatibile, **CUDA Toolkit 12.8** e **Visual Studio 2022 Build Tools** con gli strumenti C++ e CMake. Il comando usa Ninja, incluso negli strumenti CMake: non richiede l'integrazione CUDA per MSBuild. La prima compilazione può richiedere 20–60 minuti e rileva l'architettura della scheda del PC. Se il compilatore MSVC è troppo nuovo per il Toolkit, installa anche il toolset v143 14.38 dai componenti individuali di Build Tools; lo script lo seleziona quando disponibile.

Il motore GPU comprende **YuE2, HTDemucs e SeedVC**, con i contratti dei modelli inclusi nel binario. Lo script prepara anche la trascrizione CUDA: riusa un runtime CUDA già funzionante oppure ne installa uno separato in `runtime/transcription-cuda`, conservando il runtime CPU. Solo dopo le verifiche attiva CUDA. Per un'installazione iniziale con questa scelta esplicita è disponibile anche `install.bat -EnableGpu`.

Per tornare alla CPU, scegli **Sistema → Dispositivo → CPU → Salva preferenze**, oppure esegui **`Attiva-CPU.bat`**. Non servono nuovi download. `build_engine_cuda.ps1 -Revert` ora seleziona CPU conservando il motore GPU: non cancella né sostituisce cartelle.

La sostituzione del motore richiede una coda vuota. Una verifica fallita mantiene attivi il motore e il backend precedenti; il motore sostituito è conservato in una cartella univoca `runtime/engine-backup-*`. I brani, le voci di riferimento e le altre preferenze sono conservati.

### Aggiornamento dopo un pull

1. Termina i lavori e ferma il servizio con `Ferma-H3-Music.bat`.
2. Esegui `git pull` nella cartella dell'app.
3. Esegui `install.bat` per aggiornare il motore CPU e predisporre gli eventuali componenti mancanti. Un motore CUDA completo e funzionante viene conservato; quello vecchio che manca di separazione/voce viene salvato in backup e sostituito dal motore CPU completo.
4. Se desideri la GPU, oppure hai il vecchio motore CUDA che riconosce soltanto YuE2, esegui `Attiva-GPU.bat`.
5. Apri `H3-Music.exe`.

Le verifiche di questa versione sono descritte in [docs/CPU-GPU.md](docs/CPU-GPU.md).

## Avvio

Apri il collegamento **H3-Music** sul desktop oppure `F:\H3-Music\H3-Music.exe`. Il launcher apre una finestra app di Microsoft Edge e avvia il servizio esclusivamente su `127.0.0.1:8776`. Se è già attivo, riusa il servizio. Dopo `install.bat`, il runtime Python e FFmpeg sono nella cartella; ComfyUI non è necessario.

Per fermare il servizio usa `Ferma-H3-Music.bat`. Chiudere la finestra mantiene le generazioni in esecuzione. L’arresto del servizio ferma il lavoro attivo; i lavori in attesa restano salvati. Un lavoro interrotto può essere ripetuto dalla coda.

## Funzioni installate

- Generazione di canzoni da stile e testo, con voci e accompagnamento stereo a 48 kHz.
- Modalità diretta, pianificazione della sola melodia, pianificazione di melodia e accordi.
- Composizione del solo spartito prima della sintesi audio.
- Importazione, modifica, visualizzazione ed esportazione ABC; esportazione MIDI tramite abcjs.
- Cover e nuovi arrangiamenti condizionati da uno spartito; rimozione degli accordi dalla bozza per la modalità melodia.
- Tutti i controlli di campionamento musicali esposti dal motore: seed, CFG, passi NAR, temperatura, top P, top K, penalità e limiti di token separati per spartito e audio.
- Da una a otto varianti, con seed successivi e una richiesta GPU per volta.
- Progetti SQLite, bozze locali, importazione/esportazione JSON, cronologia di generazioni con richieste immutabili.
- Coda persistente, pausa degli avvii, annullamento del singolo processo, ripetizione con nuova versione e recupero dopo arresti inattesi.
- Libreria ricercabile, preferiti, confronto A/B, player audio, forma d’onda, registri e cartelle dei risultati.
- Export WAV 24 bit, FLAC, MP3 320 kbps e Ogg Vorbis; taglio, gain, normalizzazione e dissolvenze senza sovrascrivere l’originale.
- Sessioni ZIP con audio, spartito, impostazioni, token, latenti e manifest di integrità.
- Assistente musicale facoltativo via LM Studio locale: propone testi, stile e modifiche allo spartito, da applicare dopo averle lette.
- Diagnostica GPU, memoria, modelli, runtime e spazio disco.

## Voce su misura (sperimentale)

**Nuovo brano:** nello Studio attiva **Clona · usa la mia voce**, carica un campione pulito di 10–30 secondi e premi **Genera il brano**. L’app esegue automaticamente generazione, separazione, conversione e rimix.

**Qualità vocale (1.5.1):** sotto il campione scegli **Minima (30 passaggi)**, **Media (50)** o **Alta (100)**. La scelta viene salvata e vale anche per Cambia voce, CPU/GPU e tutti i segmenti dei brani lunghi. Minima mantiene il comportamento precedente; più passaggi richiedono più tempo e non garantiscono una voce priva di artefatti.

**Canzone esistente:** apri **Cambia voce**, carica canzone e campione, poi premi **Cambia la voce · mantieni la base**. La base viene separata dall’originale e non viene rigenerata con YuE2. Il file caricato resta intatto; sono possibili artefatti della separazione.

**Solo base:** nella pagina **Cambia voce**, dopo aver caricato la canzone, premi **Salva solo la musica**. Non serve un campione vocale; ascolta ed esporta il risultato dalla Libreria.

Il campione può essere **parlato**: serve come riferimento del timbro, mentre canto e parole provengono dalla canzone. I brani lunghi vengono convertiti automaticamente a segmenti mantenendo la sincronizzazione con la base.

I campioni restano disponibili nell’app. Il risultato completo si trova in **Libreria**, con player ed esportazione. La conversione cambia soprattutto il timbro, non corregge automaticamente parole e accenti. [Guida completa](docs/voce-su-misura.md).

**Mix voce e musica (1.5):** il cambio voce bilancia automaticamente il volume del canto convertito rispetto al canto originale, applica una compressione leggera e protegge il mix dai picchi. Studio e Cambia voce offrono il cursore **Più musica / Più voce** e un ambiente regolabile (inizialmente spento). Per un brano già convertito: **Libreria → Apri sessione → Regola voce e musica → Salva un nuovo mix**. Usa le tracce esistenti, senza nuova generazione o conversione; conserva la versione precedente e permette di ascoltarla nella nuova sessione. Il mix funziona su CPU con FFmpeg già incluso, anche se i modelli sono stati eseguiti su GPU. Non richiede nuovi download.

Servono due modelli ausiliari: **HTDemucs** (59 MB, separazione) e **SeedVC** (2,98 GB, conversione zero-shot). Li scarica l’installatore; a mano: `runtime\python\python.exe scripts\download_tools.py --tool sep` e `--tool voice`.

Tempi misurati su CPU (Ryzen 5 3600, 8 thread): la **separazione** costa circa 1,2 volte la durata del brano (3 minuti → ~4 minuti); la **conversione** è la parte pesante, 20-60 volte la durata (3 minuti → da una a tre ore), quindi il flusso completo è pratico sulla macchina con GPU o su frammenti brevi. Dettagli, stato e limiti in `docs/voce-su-misura.md`.

Nota: servono entrambe le famiglie nel motore installato. Il motore CPU distribuito le include; un motore CUDA compilato in precedenza con un insieme di modelli più ristretto potrebbe non averle (in quel caso ricompila con `scripts\build_engine_cuda.ps1`).


1. Scrivi il titolo e scegli un preset di stile.
2. Inserisci parole originali in sezioni `[Verse]` e `[Chorus]`.
3. Scegli **Bozza · 8 passi** per una prova rapida; **Qualità · 32 passi** per la sintesi più completa.
4. Premi **Genera il brano** e segui la coda.
5. Apri la versione in Libreria. Puoi ascoltarla, esportarla o scegliere **Modifica nello Studio** per creare un’altra versione.

Il progetto di collaudo «Prima luce» usa un breve testo originale in inglese. Le prove di generazione sono separate dalla bozza salvata dal collaudo dell’interfaccia.

## Da MP3 a spartito e cover

1. Apri **Trascrivi** e importa o trascina un audio (massimo 256 MB e 30 minuti).
2. Ascolta l’originale, assegna un titolo e scegli tutto il brano oppure un tratto in secondi.
3. Scegli **Melodia e accordi** oppure **Solo melodia**. Premi **Trascrivi la registrazione**.
4. Apri la sessione per visualizzare lo spartito e ascoltare le note al pianoforte (anteprima fino a 2 minuti). Puoi selezionare le singole parti ed esportare l’anteprima WAV.
5. Scarica ABC, MIDI completo, tracce MIDI vocali/strumentali/accordi, JSON e annotazioni LAB, oppure l’intera sessione ZIP.
6. Premi **Crea una cover nello Studio**, controlla le note, descrivi il nuovo stile e inserisci il testo da cantare. Quindi genera una nuova interpretazione.

La trascrizione e YuE2 condividono la coda: viene eseguito un solo modello alla volta, con rilascio della GPU alla fine di ciascun processo. Tutto il riconoscimento funziona offline dopo l’installazione. I tempi delle annotazioni partono dall’inizio del tratto scelto. I brani lunghi sono analizzati in finestre sovrapposte; per una cover è consigliabile partire da una strofa o un ritornello, entro il contesto musicale di YuE2.

Una cover YuE2 usa lo spartito come guida e crea un nuovo arrangiamento. SheetSage2 ricava melodia vocale/strumentale, accordi e annotazioni, non una trascrizione completa di ogni strumento: timbri, arpeggi, voicing e dettagli della base possono cambiare. Per cambiare solo il timbro vocale di un brano generato, usa invece **Separa voce e base → Canta con una voce**, che rimixa la voce convertita con le tracce strumentali separate.

## Limiti effettivi

La versione YuE2 di audio.cpp è sul ramo `dev`: il supporto è recente e sperimentale. La build locale è compilata per la RTX 5070 Ti, architettura CUDA 120, e usa i pesi Q8_0 con VAE F16. Il repository include anche una build CPU precompilata (`dist/h3-engine-cpu-win64.zip`) usata dall’installatore: richiede Windows x64 con AVX2, FMA, F16C e BMI2, con o senza GPU.

Il modello dichiara principalmente inglese e cinese; l’italiano è sperimentale. Le impostazioni di tempo e durata nello stile sono indicazioni, non vincoli esatti. Il limite di token può troncare il risultato: H3-Music evidenzia questo stato senza presentarlo come una canzone completa.

Le modifiche in YuE2 producono una nuova registrazione del brano. Separazione e conversione vocale sono operazioni successive, affidate a HTDemucs e SeedVC; non sono funzioni native di YuE2. Editing locale dell’audio e addestramento LoRA non sono implementati. La somiglianza della voce convertita va verificata ascoltando il risultato.

La sezione **Trascrivi** usa **SheetSage2 + MERT-v2**, installati in un runtime isolato incluso nell’app. Ricava note, accordi, battiti, tonalità e struttura da MP3/WAV/FLAC/M4A e altri formati. Non riconosce le parole cantate e non separa l’audio in registrazioni di voce/strumenti. Le trascrizioni sono stime da verificare: polifonia, voci sovrapposte, rumore e cambi di tempo possono produrre errori. Se lo spartito non è costruibile, MIDI e annotazioni restano consultabili con il relativo avviso.

L’assistente richiede un modello caricato e il server locale di LM Studio; non è necessario per generare musica con YuE2. Nessuna API a pagamento è configurata.

## Dati e cartelle

- `data/music.sqlite`: progetti, lavori e impostazioni.
- `data/outputs/<id>/`: tutti i file di una generazione, senza sovrascrivere le altre.
- `data/imports/<id>/`: originali importati e metadati SHA-256.
- `models/SheetSage2/` e `models/MERT-v2-FullSong/`: trascrittore e modello audio.
- `runtime/transcription/`: Python 3.11 e PyTorch per la trascrizione, CPU sulle nuove installazioni.
- `runtime/transcription-cuda/`: runtime facoltativo separato per la trascrizione GPU; non serve se il runtime principale supporta già CUDA.
- `data/window-profile/`: profilo della finestra Edge, incluse bozze locali.
- `models/yue2/`: pesi GGUF e tokenizer.
- `runtime/`: Python embedded, motore e DLL CUDA, FFmpeg.
- `static/`: interfaccia e font locali.
- `vendor/audio.cpp/`: sorgenti del motore e dipendenze.
- `scripts/`: sorgente del launcher, patch, download e packaging.
- `tests/` e `logs/`: verifiche e registri.

Per una copia di sicurezza conserva almeno `data/` e `models/`. Tutti i componenti dell’app sono nella cartella `F:\H3-Music`, senza collegamenti a dischi esterni. La base di dati va copiata a servizio fermo. Un archivio sessione ZIP riguarda una singola generazione; il JSON di progetto contiene la composizione e le impostazioni.

## Sorgenti e licenze

- YuE2: https://github.com/multimodal-art-projection/YuE
- Pesi: https://huggingface.co/audio-cpp/Yue2-3B-GGUF
- Motore: https://github.com/0xShug0/audio.cpp/tree/dev
- Trascrizione SheetSage2: https://huggingface.co/m-a-p/SheetSage2
- abcjs: https://github.com/paulrosen/abcjs

I pesi YuE2, SheetSage2 e MERT-v2 sono **CC BY-NC 4.0** (uso non commerciale). Le licenze dei componenti sono in `licenses/` e nei rispettivi sorgenti. Il codice audio.cpp è modificato localmente per salvare token ABC/semantici, latenti e indicatori di troncamento e per fermarsi dopo la composizione. Non sono stati cambiati pesi o algoritmi di campionamento.

## Verifiche ripetibili

`runtime\python\python.exe tests\test_studio.py`

`runtime\python\python.exe tests\test_transcription.py`

Il test UI `tests/ui.cjs` usa Playwright dall’ambiente di sviluppo disponibile su questo PC. Non è una dipendenza dell’app.

I dettagli del collaudo finale sono in `docs/VALIDATION.md`.
