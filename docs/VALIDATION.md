# Collaudo H3-Music — 12 settembre 2026

Installazione: `F:\H3-Music`. GPU: NVIDIA GeForce RTX 5070 Ti, 16 GB. CPU: AMD Ryzen 5 3600. Build nativa CUDA 12.8 / architettura 120. Pesi: YuE2-3B Q8_0 e VAE F16, scaricati e verificati contro gli SHA-256 pubblicati dal repository dei pesi.

## Risultati

- 7 test backend superati: Unicode, validazione, snapshot immutabili, seed, annullamento, recupero dopo arresto, decodifica token ABC e limiti dell’assistente locale.
- Test API superati: riavvio e persistenza dei progetti, rifiuto di origini/host estranei, lettura HTTP Range, isolamento dei percorsi e combinazioni non valide.
- Test UI superati in Edge: salvataggio, navigazione, conservazione della bozza, visualizzazione ABC, download MIDI e layout mobile senza scorrimento orizzontale.
- Test UI con dati reali superati: spartito prodotto da YuE2, apertura come nuova bozza, rimozione degli accordi senza corrompere gli header delle voci, confronto A/B e diagnostica.
- Riproduzione audio e cambio esclusivo tra player A/B verificati nel browser. Metadati caricati correttamente.
- Export WAV 24 bit, FLAC, MP3 e Ogg verificati con ffprobe: taglio 1–8 s, stereo 48 kHz, gain −1 dB, normalizzazione e dissolvenze. Hash dell’audio originale invariato.

## Generazioni reali

| Operazione | ID | Esito |
|---|---|---|
| Solo spartito | 908948b1f77b4c5a8b035ff2b78395a3 | ABC valido, 333 token, circa 5,95 s di motore |
| Canzone da testo, melodia + accordi | 24712e7f52c94df7aa0fcde44ff17974 | 36,318667 s di audio stereo a 48 kHz; circa 12,48 s di motore |
| Cover jazz dalla melodia ABC | 7acacc56ba854341ad239041df8c45ec | 42,438667 s di audio stereo a 48 kHz |

Le due prove audio usano 8 passi NAR, seed 831001 e un limite di 3000 token semantici. Nessuna delle generazioni completate ha raggiunto il limite di token. I tempi sono delle singole prove brevi e non vanno estesi a brani lunghi o ad altre impostazioni.

Il tentativo 15451bfc250d413ba305f8a07ffdc543 è stato interrotto durante il collaudo di arresto del servizio. Il riavvio lo ha correttamente marcato come interrotto; la ripetizione ha prodotto il brano completo. Il tentativo è conservato nella cronologia.

Queste verifiche attestano il funzionamento dei flussi, la correttezza dei file e la riproduzione. Non sono una valutazione percettiva della qualità musicale o della pronuncia. Le prove audio usano testi originali in inglese; l’italiano resta sperimentale.

## Memoria GPU su Windows

Il valore WDDM di nvidia-smi appariva quasi pieno, ma CUDA riportava 14,57 GiB allocabili. Un’allocazione temporanea da 8 GiB è riuscita ed è stata subito liberata. H3-Music interroga CUDA tramite un processo breve separato per mostrare la memoria effettivamente utilizzabile. Nessun servizio estraneo è stato chiuso o scaricato dalla memoria.

## Confini del collaudo

- L’assistente LM Studio è implementato e il catalogo locale risponde, ma non sono stati caricati modelli LLM né eseguite richieste generative all’assistente.
- SheetSage2 e MERT-v2 sono installati. Il flusso MP3 → ABC/MIDI → cover YuE2 è stato verificato con audio reale; il dettaglio è riportato sotto.
- La build include una piccola estensione locale ad audio.cpp per esposizione degli artefatti e modalità solo spartito; patch e commit sono conservati in questa cartella.
- Il supporto YuE2 nel ramo dev di audio.cpp è recente. La distribuzione ufficiale Python indica Linux e 24 GB VRAM; questa installazione usa il percorso nativo GGUF Windows, provato direttamente sulla GPU del PC.

I registri e i dettagli machine-readable sono in `logs/`. Gli screenshot della UI sono in questa cartella.

## Avvio finale
Launcher H3-Music.exe e comando --stop verificati. Collegamento creato sul desktop; finestra Edge in modalita app con profilo dedicato aperta. Servizio riavviato e pronto su 127.0.0.1:8776. Nessun lavoro ancora in esecuzione.


## Trascrizione da audio — versione 1.1

Modelli locali SheetSage2 (`eab522a8168e8b8b8c4856bf8609cd86198f01fe`) e MERT-v2-FullSong (`d8ba1c745e733b3908ce6ad16ebeb17ac7600a42`), con pesi e codice verificati SHA-256. Runtime isolato Python 3.11.9, PyTorch 2.8.0+cu128; CUDA e calcolo sulla RTX 5070 Ti verificati direttamente.

- 6 test backend di trascrizione superati: importazione e hash MP3, HTTP Range, rifiuto dei formati falsi e pulizia dopo errore, protezione Origin, intervalli e snapshot, annullamento/ripetizione e archivio ZIP con originale e annotazioni.
- Test UI superati: importazione reale, ascolto continuo durante il polling, conservazione della bozza e layout mobile.
- Anteprima di pianoforte verificata con campioni locali: audio stereo valido e non silenzioso, riproduzione nel browser e nessuna richiesta esterna.
- Flusso completo verificato: spartito riconosciuto e visualizzato, MIDI con intestazione valida, ascolto delle note, trasferimento nello Studio, rimozione accordi, generazione YuE2 e filtro Trascrizioni nella Libreria.
- I 7 test backend preesistenti e le verifiche UI audio sono stati ripetuti senza regressioni.

| Operazione | ID | Risultato |
|---|---|---|
| Trascrizione MP3, melodia e accordi | b61d2d8a56de4b36ba83cb0fdb278f7d | 36,319 s analizzati, 44 note vocali, 16 battute ABC, MIDI e annotazioni |
| Cover jazz dalla trascrizione MP3 | 394a2a95ff084fde991d3589a8b41f8b | 37,959 s, stereo 48 kHz, nessun troncamento ABC/audio |
| Solo melodia, intervallo 5–17 s | c8b04138be4c40219cfd6521bfde0868 | 12 s analizzati, 9 note vocali, 6 battute ABC, nessuna traccia accordi |

La prima analisi completa ha richiesto 44,5 s di elaborazione, escluso il caricamento iniziale del modello; l'intervallo breve ha richiesto 2,25 s dopo il primo utilizzo della GPU. La memoria massima allocata dal modello era circa 3370 MiB. I tempi di caricamento e analisi vanno distinti e questi esempi brevi non attestano le prestazioni su registrazioni di 30 minuti. La prova completa segnala due riempimenti per battute iniziali/finali parziali, visibili nella diagnostica; non presenta errori ABC.

La trascrizione ricava note e struttura musicale: non riconosce le parole e non produce tracce audio isolate. Non è una verifica della fedeltà percettiva delle note riconosciute. Le parti MIDI e il pianoforte sono ricostruzioni sintetiche. Per l'anteprima si usano fino a 120 secondi; i file MIDI conservano il risultato completo.

Registri: `transcription-tests.log`, `transcription-ui-tests.json`, `piano-tests.json`, `transcription-smoke.json`, `transcription-e2e.json`, `transcription-melody.json`. Schermate: `transcription.png`, `transcription-mobile.png`, `transcription-result.png`.

## Installazione finale interamente su F:

Il runtime `F:/H3-Music/runtime/transcription` è una cartella reale. La copia è stata verificata su 19.760 file con hash SHA-256 dei pacchetti e confrontando i file principali di Python. Il collegamento al disco esterno e le due cartelle temporanee create su quel disco sono stati rimossi; gli avviatori Python sono stati rigenerati con il percorso F:. Anche le cache del trascrittore sono configurate dentro `F:/H3-Music/data`.

La compressione trasparente Windows LZX di 65 file delle librerie PyTorch ha recuperato 3.85 GB, conservando i file completi. Spazio libero dopo il collaudo: circa 6.92 GB. Sono stati rimossi soltanto temporanei e copie di questa installazione, senza eliminare dati personali o altri programmi.

Dopo la rimozione delle copie esterne sono stati verificati import Python/PyTorch/torchaudio/NumPy da F:, calcolo CUDA, una nuova trascrizione reale di 12 secondi (`3e7ced47f8904d40a8fbc6586628b889`), ABC di 6 battute e MIDI valido. L'analisi ha richiesto 6.69 s, escluso il caricamento. Sono passati anche i 6 test backend e il controllo UI finale dello spartito e dello stato del runtime. La coda è stata ripristinata attiva.

Registri conclusivi: `runtime-copy-verification.json`, `external-runtime-removed.json`, `transcription-compact.json`, `transcription-F-only.json`, `transcription-tests-final.log`, `transcription-final-ui.json`. Screenshot finale: `transcription-F-result.png`.
