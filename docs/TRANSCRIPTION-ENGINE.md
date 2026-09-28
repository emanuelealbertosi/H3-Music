# Motore di trascrizione H3-Music

SheetSage2: https://huggingface.co/m-a-p/SheetSage2
Revisione: 4f89269db831bdc1880124164a00d4f9385cd129
MERT-v2: d8ba1c745e733b3908ce6ad16ebeb17ac7600a42
PyTorch: 2.8.0 + CUDA 12.8 (architettura RTX 5070 Ti).
Python embedded: 3.11.9. Dipendenze bloccate come richiesto dal modello.

## Aggiornamento 1.5.2

Questa revisione include le correzioni ufficiali del 21 e 24 settembre e corregge la scrittura enarmonica di tonalità e accordi rispetto alla tonalità locale (per esempio Do invece di Si diesis). I pesi SheetSage2/MERT, il riconoscimento delle note e i tempi non cambiano. Rimangono le modalità Solo melodia e Melodia e accordi.

Su una nuova installazione `install.bat` scarica direttamente questa revisione. Dopo un `git pull`, esegui **Aggiorna-Trascrizione.bat** per aggiornare un'installazione esistente. Il comando aggiorna soltanto i file dei modelli: non reinstalla Python o PyTorch e non cambia CPU/GPU, BF16, progetti o risultati precedenti. Attendi che le trascrizioni in coda siano terminate. I nuovi file vengono verificati prima della sostituzione e i precedenti conservati in `backups/transcription-*`. I pesi già validi vengono riutilizzati senza download.

L'installatore ordinario riconosce anche le revisioni precedenti e le aggiorna. Il manifest di ogni nuova trascrizione registra la revisione realmente usata. Il caricatore prepara esplicitamente la dipendenza del tokenizer aggiunta dall'aggiornamento, necessaria anche con una cache Transformers preesistente.

Collaudo 1.5.2: 57 test automatici, inclusi verifica hash, riuso dei pesi, download incompleti e ripristino in caso di errore durante la sostituzione. Due trascrizioni CUDA del medesimo tratto di 12 secondi producono ABC e MIDI validi, 9 note melodiche con altezze, attacchi e durate identiche fra Solo melodia e Melodia e accordi, senza avvisi del trascrittore. Verificate anche le nuove grafie Do/Si diesis, Si bemolle/La diesis e Mi bemolle/Re diesis nelle tonalità previste. Un secondo aggiornamento riutilizza tutti i file senza richieste di download. Queste verifiche attestano il funzionamento dell'aggiornamento, non un aumento dell'accuratezza di riconoscimento delle note.

Il server usa ancora il suo Python 3.12 senza dipendenze esterne. La trascrizione vive in runtime/transcription, con un processo separato per ogni lavoro. Modelli e cache sono locali; HF_HUB_OFFLINE, TRANSFORMERS_OFFLINE e local_files_only impediscono download durante l’uso. Il parent MERT viene verificato e gli adattatori vengono uniti in memoria, senza duplicare i pesi su disco.

Il wrapper usa FFmpeg incluso per decodificare il tratto scelto in mono a 24 kHz e passa il waveform al modello. Questo evita la dipendenza dalle librerie condivise FFmpeg di torchaudio su Windows. L’algoritmo ufficiale, i pesi, le finestre sovrapposte e il campionamento restano invariati. Parametri: preset default, CUDA bf16 autocast; CPU fp32 disponibile nelle impostazioni dell’app.

L’anteprima al pianoforte usa ABCJS e i campioni distribuiti nel render_assets ufficiale, verificati con il relativo manifest SHA-256. Il mapping di note e tempi deriva dal renderer di riferimento. La sintesi gira nel browser con campioni locali; l’anteprima è limitata a 120 secondi, i MIDI conservano l’intera trascrizione. Le correzioni di visualizzazione expandRests e fixSystemKeys del renderer ufficiale non modificano l’ABC salvato.

Il server, l’interfaccia, i modelli, le sessioni e il runtime Python/CUDA sono tutti in F:/H3-Music. runtime/transcription è una cartella reale sul disco F:, senza dipendenze da dischi esterni e senza dipendenze dai runtime di altre app. Le licenze restano nelle cartelle dei componenti.
