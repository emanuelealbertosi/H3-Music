# H3-Music

Studio musicale locale per Windows, basato su **YuE2-3B Q8** e **audio.cpp**. Interfaccia in italiano, con gli stessi colori avorio e verde petrolio e i font Manrope/Cormorant delle altre app H3. In questa installazione il motore usa la **GPU CUDA**; il motore precompilato distribuito nel repository per il clone su altri PC usa la **CPU**.

## Contenuto del repository

Questo repository contiene il codice dell’app, l’interfaccia, il launcher Windows, gli script, i test e la documentazione, oltre al motore audio.cpp precompilato per CPU (`dist/h3-engine-cpu-win64.zip`) e il manifest dei pesi YuE2. I modelli pesanti, i runtime, le registrazioni, il database, le cache, i log e i backup restano esclusi da Git: un clone non è ancora un’installazione pronta all’uso, ma `install.bat` la completa scaricando i componenti mancanti (vedi sotto). Gli script di packaging e alcuni collaudi di integrazione si riferiscono all’installazione su `F:\H3-Music` descritta in questa documentazione.

## Installazione da GitHub (clone)

Su un PC Windows x64 senza GPU dedicata:

1. `git clone https://github.com/emanuelealbertosi/H3-Music.git`
2. Nella cartella del clone, esegui `install.bat` (oppure `powershell -ExecutionPolicy Bypass -File install.ps1`).

L’installatore non richiede compilatori né Visual Studio: estrae il motore audio.cpp precompilato per CPU da `dist/`, scarica Python incorporato 3.12, FFmpeg, i pesi YuE2 (circa 4,5 GB) e il runtime di trascrizione con torch CPU (SheetSage2 + MERT-v2, circa 3 GB), imposta `backend=cpu` nel database e avvia il server su `127.0.0.1:8776`. Servono circa 15 GB di spazio libero e una connessione internet; i download sono riprendibili se interrotti.

Al termine apri **H3-Music.exe** (o `Avvia-H3-Music.bat`): la finestra app si apre sull’app già attiva. La generazione funziona interamente su CPU: le sintesi richiedono più tempo che sulla GPU e il numero di thread è regolabile nelle impostazioni.

Il motore CPU precompilato richiede un processore x64 con **AVX2, FMA, F16C e BMI2** (Intel Haswell 2013 o successivi, AMD Excavator/Zen o successivi). L’installatore è ripetibile: ogni passo salta ciò che è già presente, quindi si può rilanciare `install.bat` dopo un’interruzione senza riscaricare tutto.

La generazione su CPU riserva molta memoria di sistema: il motore prealloca le arene dei grafi (circa 20 GB nel picco di una generazione completa, oltre ai pesi). Sono consigliati **32 GB di RAM**; con 16 GB conviene chiudere le altre applicazioni e lasciare il file di paging gestito da Windows. Come riferimento, su un Ryzen 5 3600 (6 core, 8 thread) la sola pianificazione di un brano richiede circa 7 minuti; la sintesi audio completa è sensibilmente più lunga.

## Avvio

Apri il collegamento **H3-Music** sul desktop oppure `F:\H3-Music\H3-Music.exe`. Il launcher apre una finestra app di Microsoft Edge e avvia il servizio esclusivamente su `127.0.0.1:8776`. Se è già attivo, riusa il servizio. Il runtime Python e FFmpeg sono inclusi nella cartella; ComfyUI non è necessario.

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

## Prima prova

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

## Limiti effettivi

La versione YuE2 di audio.cpp è sul ramo `dev`: il supporto è recente e sperimentale. La build locale è compilata per la RTX 5070 Ti, architettura CUDA 120, e usa i pesi Q8_0 con VAE F16. Il repository include anche una build CPU precompilata (`dist/h3-engine-cpu-win64.zip`) usata dall’installatore: funziona su qualsiasi PC x64, con o senza GPU.

Il modello dichiara principalmente inglese e cinese; l’italiano è sperimentale. Le impostazioni di tempo e durata nello stile sono indicazioni, non vincoli esatti. Il limite di token può troncare il risultato: H3-Music evidenzia questo stato senza presentarlo come una canzone completa.

Le modifiche producono una nuova registrazione dell’intero brano. YuE2 non offre in questa distribuzione separazione voce/strumenti, clonazione controllata di una voce, editing di un solo intervallo dell’audio o addestramento LoRA. Queste funzioni non sono simulate.

La sezione **Trascrivi** usa **SheetSage2 + MERT-v2**, installati in un runtime isolato incluso nell’app. Ricava note, accordi, battiti, tonalità e struttura da MP3/WAV/FLAC/M4A e altri formati. Non riconosce le parole cantate e non separa l’audio in registrazioni di voce/strumenti. Le trascrizioni sono stime da verificare: polifonia, voci sovrapposte, rumore e cambi di tempo possono produrre errori. Se lo spartito non è costruibile, MIDI e annotazioni restano consultabili con il relativo avviso.

L’assistente richiede un modello caricato e il server locale di LM Studio; non è necessario per generare musica con YuE2. Nessuna API a pagamento è configurata.

## Dati e cartelle

- `data/music.sqlite`: progetti, lavori e impostazioni.
- `data/outputs/<id>/`: tutti i file di una generazione, senza sovrascrivere le altre.
- `data/imports/<id>/`: originali importati e metadati SHA-256.
- `models/SheetSage2/` e `models/MERT-v2-FullSong/`: trascrittore e modello audio.
- `runtime/transcription/`: cartella reale su F: con Python 3.11 e PyTorch CUDA. Le librerie usano compressione trasparente Windows per risparmiare spazio. Non sono necessari dischi esterni.
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
