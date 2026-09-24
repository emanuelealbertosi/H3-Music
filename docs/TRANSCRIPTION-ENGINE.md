# Motore di trascrizione H3-Music

SheetSage2: https://huggingface.co/m-a-p/SheetSage2
Revisione: eab522a8168e8b8b8c4856bf8609cd86198f01fe
MERT-v2: d8ba1c745e733b3908ce6ad16ebeb17ac7600a42
PyTorch: 2.8.0 + CUDA 12.8 (architettura RTX 5070 Ti).
Python embedded: 3.11.9. Dipendenze bloccate come richiesto dal modello.

Il server usa ancora il suo Python 3.12 senza dipendenze esterne. La trascrizione vive in runtime/transcription, con un processo separato per ogni lavoro. Modelli e cache sono locali; HF_HUB_OFFLINE, TRANSFORMERS_OFFLINE e local_files_only impediscono download durante l’uso. Il parent MERT viene verificato e gli adattatori vengono uniti in memoria, senza duplicare i pesi su disco.

Il wrapper usa FFmpeg incluso per decodificare il tratto scelto in mono a 24 kHz e passa il waveform al modello. Questo evita la dipendenza dalle librerie condivise FFmpeg di torchaudio su Windows. L’algoritmo ufficiale, i pesi, le finestre sovrapposte e il campionamento restano invariati. Parametri: preset default, CUDA bf16 autocast; CPU fp32 disponibile nelle impostazioni dell’app.

L’anteprima al pianoforte usa ABCJS e i campioni distribuiti nel render_assets ufficiale, verificati con il relativo manifest SHA-256. Il mapping di note e tempi deriva dal renderer di riferimento. La sintesi gira nel browser con campioni locali; l’anteprima è limitata a 120 secondi, i MIDI conservano l’intera trascrizione. Le correzioni di visualizzazione expandRests e fixSystemKeys del renderer ufficiale non modificano l’ABC salvato.

Il server, l’interfaccia, i modelli, le sessioni e il runtime Python/CUDA sono tutti in F:/H3-Music. runtime/transcription è una cartella reale sul disco F:, senza dipendenze da dischi esterni e senza dipendenze dai runtime di altre app. Le licenze restano nelle cartelle dei componenti.
