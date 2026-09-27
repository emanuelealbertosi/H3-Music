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

## Salva solo la musica

Apri **Cambia voce**, carica o seleziona la canzone e premi **Salva solo la musica** sotto il player dell’originale. Non serve caricare una voce. La base strumentale appare in **Libreria** e si può esportare in WAV, FLAC, MP3 e Ogg.

Il lavoro usa soltanto HTDemucs e il mix delle parti batteria, basso e altri strumenti: non carica SeedVC o YuE2. Il file importato resta intatto.

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

## Correzione della voce nella versione 1.4.1

La versione precedente selezionava il percorso SVC ma lasciava `f0_condition` al valore predefinito `false` del motore C++. Il checkpoint per il canto richiede il condizionamento dell’intonazione: disattivarlo può produrre suoni degradati anziché canto utilizzabile. L’app ora passa esplicitamente `f0_condition=true`, `auto_f0_adjust=false` e `semitone_shift=0`, sia nel flusso automatico sia nel precedente comando manuale. Nessuna ricompilazione o nuovo download richiesto.

Le [istruzioni ufficiali Seed-VC](https://github.com/Plachtaa/seed-vc#usage%EF%B8%8F) richiedono F0 attivo per il canto. La correzione è verificata nei comandi, nei log di estrazione RMVPE e con confronto dell’intonazione su un estratto. Il solo completamento dei test e la presenza di audio non dimostrano intelligibilità o somiglianza: resta necessaria la verifica all’ascolto. I risultati vecchi non vengono sovrascritti; per applicare la correzione bisogna creare una nuova versione.

38 test automatici superati, più prove complete GPU di sola base, cambio voce da import e generazione con cambio voce. Verificati pulsante senza campione vocale, coda, Libreria, riproduzione, esportazione MP3 e interfaccia mobile.

## Brani lunghi: correzione 1.4.2

La correzione F0 della 1.4.1 non bastava. Nel motore nativo incluso, `SeedVcWhisperContentEncoder::extract_16k_mono` limita l’ingresso a 480.000 campioni a 16 kHz (30 secondi) e l’uscita a 1.500 frame. Il regolatore di lunghezza estendeva poi quel contenuto alla durata di tutto il brano. Le note potevano seguire F0 mentre parole e articolazione risultavano degradate. I test precedenti su frammenti brevi non coprivano questo difetto.

L’app ora converte segmenti di massimo 25 secondi, con 400 ms di sovrapposizione e raccordo lineare. Ogni segmento passa al modello la propria porzione di canto. La ricomposizione conserva il numero di campioni e non allunga la voce. La correzione si applica a brani importati, generati e al percorso manuale, su CPU e GPU, senza cambiare binari o modelli. La coda mostra il segmento in lavorazione.

Riferimento: il [codice originale Seed-VC](https://github.com/Plachtaa/seed-vc/blob/main/inference.py) gestisce già separatamente il contenuto degli audio oltre 30 secondi; il motore nativo distribuito qui non implementa quel ciclo nell’encoder Whisper. La segmentazione nell’app evita quel limite. Restano possibili artefatti e variazioni di timbro alle giunzioni; intelligibilità e somiglianza vanno valutate all’ascolto.

Il riferimento resta una registrazione **parlata**: non è necessario cantare. Si trasferisce il timbro sul canto già presente nella canzone. Le parti della traccia separata praticamente silenziose (RMS sotto −60 dBFS e picco sotto −40 dBFS) vengono conservate senza sintesi, evitando errori F0 e rumori inventati nelle code strumentali; i segmenti interessati sono registrati nel manifest.

Collaudo 1.4.2: 42 test, copertura dei segmenti fino a 30 minuti, numero di campioni invariato nel raccordo, cancellazione e code quasi silenziose. Una prova GPU sul brano completo di circa 174 secondi produce 8 segmenti. Il confronto locale con riconoscimento vocale mostra il recupero di contenuto dopo i primi 30 secondi, ma è impreciso anche sull’originale e non è una certificazione di intelligibilità o somiglianza.
