# Usa la tua voce

## Nuovo brano: basta una spunta

1. Nello **Studio** scrivi stile e testo.
2. Attiva **Clona · usa la mia voce**.
3. Premi **Carica un campione di voce** oppure scegli un campione già salvato.
4. Premi **Genera il brano**. Un solo lavoro in coda genera, separa, converte la voce e rimixa.
5. Apri il risultato in **Libreria** per ascoltarlo o esportarlo.

## Canzone esistente: conserva la musica

1. Apri **Cambia voce** dal menu, oppure dal collegamento nello Studio.
2. Carica la canzone originale (MP3, WAV, FLAC, M4A; massimo 256 MB e 30 minuti), o scegli un audio già caricato.
3. Carica o scegli il campione della tua voce.
4. Premi **Cambia la voce · mantieni la base**.
5. Segui le fasi in **Coda**; il risultato completo è in **Libreria**.

Questo percorso **non usa YuE2 e non ricompone la musica**: HTDemucs separa voce, batteria, basso e altri strumenti; SeedVC converte il canto; FFmpeg lo unisce alle tre parti strumentali. Non richiede trascrizione o spartito.

La registrazione caricata resta intatta. La separazione può lasciare residui della voce originale e alterare alcuni dettagli della base: non equivale ad avere le tracce originali dello studio di registrazione.

## Il campione

Usa 10–30 secondi di una sola voce, senza musica o rumori; l’app accetta campioni da 1 a 60 secondi. Può essere parlato o cantato. Il caricamento lo salva localmente e lo rende riutilizzabile nelle due pagine. Non devi creare cartelle o addestrare un modello. I formati compressi vengono convertiti in WAV prima di passarli al motore.

La conversione modifica soprattutto il **timbro**. Melodia, parole, tempi, accenti e pronuncia derivano dalla voce del brano di partenza: un campione migliore non corregge automaticamente parole sbagliate. La somiglianza va valutata all’ascolto e non è garantita dalle prove tecniche.

## Risultati, coda e compatibilità

- `audio.wav`: mix finale stereo a 48 kHz, riproducibile ed esportabile dall’app.
- `original.wav`: copia WAV del brano prima del cambio voce; per un audio importato rimane anche il file caricato, senza modifiche, in `data/imports/`.
- `voce.wav`: voce convertita. Lo ZIP della sessione contiene anche le parti separate nella cartella `stems/`, il riferimento usato e i manifest di integrità.
- Annulla interrompe il processo corrente e impedisce le fasi successive. Riprova accoda una nuova esecuzione dall’inizio, incluso il brano generato se era un lavoro Studio.
- Il percorso manuale precedente **Separa voce e base → Canta con una voce** e i campioni già presenti in `data/voci/<nome>/` restano disponibili.

Servono HTDemucs e SeedVC, inclusi nell’installazione. Il nuovo flusso usa la preferenza **CPU / NVIDIA CUDA** già impostata. I nuovi PC mantengono CPU come impostazione iniziale; `Attiva-GPU.bat` prepara la GPU opzionale. Sulla CPU la conversione può essere molto lenta: vedi [CPU-GPU.md](CPU-GPU.md).

## Collaudo della versione 1.4

35 test automatici, prova dell’interfaccia desktop e mobile e due prove complete sulla RTX 5070 Ti: cambio voce su un import di 6 secondi e generazione di circa 20 secondi seguita dal cambio voce. Verificati integrità dell’import, output stereo a 48 kHz, campione M4A, manifest del mix finale, coda, annullamento e ripetizione. I campioni sono sintetici; queste prove verificano il funzionamento, non la somiglianza con una voce umana né la qualità di un intero album.
