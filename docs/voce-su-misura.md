# Voce su misura per i brani generati

La conversione vocale è implementata e collaudata su CPU e GPU. Usa un campione di riferimento per cambiare il timbro della voce cantata, poi la rimixa con la base separata. Non richiede addestramento; la somiglianza va valutata all'ascolto.

## Come usarla ora

1. Prepara un file WAV, MP3 o FLAC con 10–30 secondi di una sola voce, pulita e senza musica. Metti un solo campione nella cartella `data/voci/MiaVoce/` (creala se manca).
2. Apri un brano generato nella Libreria e premi **Separa voce e base**.
3. Aspetta che il lavoro finisca, quindi apri il risultato della separazione, riconoscibile dal titolo **voce e base**.
4. Premi **Canta con una voce** e scegli **MiaVoce**. Se hai aggiunto il campione a finestra già aperta, chiudila e riaprila.
5. Quando la conversione è completata, apri il nuovo risultato: trovi player ed esportazione audio. `audio.wav` è il mix finale; `voce.wav` contiene la sola voce convertita.

Sul PC dell'autore il percorso completo del campione è `F:\H3-Music\data\voci\MiaVoce\campione.wav`. Usa **NVIDIA CUDA** per ridurre i tempi.

La conversione cambia il timbro della voce già cantata: non corregge automaticamente testo, pronuncia, accenti o melodia. Conserva la base separata del brano di partenza, con i possibili artefatti della separazione. Il pulsante attuale parte dai brani generati nella Libreria; non è un'importazione diretta di qualsiasi MP3 nella funzione di clonazione.

## 0. Stato di avanzamento

- **Fase 1 — separazione: fatta.** HTDemucs (59 MB) nel repository con revisione
  fissata e SHA-256; nuovo lavoro `sep` nell'app con pulsante «Separa voce e
  base»; l'installer scarica il modello. Verificato col motore CPU: 30 s di audio
  separati in 37 s (rtf 1,24).
- **Fase 2 — conversione: motore e app fatti.** SeedVC (2,98 GB) scaricato e
  verificato; comando `--task svc --family seed_vc --audio <voce separata>
  --voice-ref <campione parlato> --out <file>`. Verificato col motore CPU: la
  catena gira (content, style, f0, length regulator, diffusione, vocoder) e
  scrive il file. Libreria voci in `data/voci/<nome>/` e nuovo lavoro `voice`
  nell'app, con scelta della voce da una finestra.
- **Fase 3 — rimix: fatta.** La voce convertita (mono) viene unita alla base
  strumentale (batteria, basso, altro) con FFmpeg in un `audio.wav` stereo;
  verificato con la funzione dell'app.
- **Fase 4 — collaudo GPU completato su frammenti di prova** sulla RTX 5070 Ti: separazione, conversione e rimix. Vedi [CPU-GPU.md](CPU-GPU.md) per le prove e i relativi limiti.

**Attenzione ai tempi su CPU**: la conversione SeedVC è la parte pesante, circa
20-60 volte la durata dell'audio (un brano di 3 minuti richiede da una a tre ore
su CPU). La separazione invece è rapida (circa 1,2 volte). Su GPU entrambe sono
molto più veloci. Il flusso completo, quindi, è pratico sulla macchina con GPU;
su quella solo CPU conviene usarlo su frammenti brevi.

**Nota sul motore**: servono entrambe le famiglie (`htdemucs`, `seed_vc`). Il
motore CPU distribuito le include ed è quello con cui sono state fatte le prove.
Un motore CUDA compilato in precedenza con un insieme di modelli più ristretto
potrebbe non averle: in quel caso ricompila con `scripts/build_engine_cuda.ps1`.


- Il campione di riferimento è **voce parlata** (10-30 secondi, puliti).
- Il risultato è **cantato**: la voce del brano generato viene convertita.
- Modalità **zero-shot**: nessun modello da addestrare, basta il campione.
- Deve funzionare sia sul PC con GPU sia su quello solo CPU.
- Le funzioni esistenti (generazione, pianificazione, trascrizione, coda,
  avanzamento) non devono rompersi.

## 1. Cosa c'è già nel motore (nessuna ricompilazione)

Il motore audio.cpp usa già queste famiglie, incluse nel motore CPU distribuito:

| famiglia | compito | capacità | pesi (q8/f16) |
|---|---|---|---|
| YuE2 | `gen` | musica da testo e stile | già installato |
| HTDemucs | `sep` | separa voce, batteria, basso, altro | **59 MB** |
| Mel-Band-RoFormer | `sep` | separazione alternativa | 240 MB |
| SeedVC | `vc`, **`svc`** | conversione voce **cantata**, campione di riferimento | **2,98 GB** |
| MeanVC2 | `vc` | conversione voce con riferimento | 1,55 GB |
| RVC | `vc` | conversione con modello di voce addestrato (`.pth`) | 1,20 GB |
| Vevo2 | `tts`, `music`, `vc`, `svc` | musica e voce in un unico modello | 3,09 GB |

I pesi stanno tutti nel repository Hugging Face `audio-cpp/audio.cpp-gguf`
(da fissare a una revisione, come è stato fatto per YuE2).

**Punto importante**: il motore sa già fare separazione e conversione cantata,
quindi non serve ricompilare nulla e non serve che l'utente installi strumenti di
sviluppo. Il lavoro è tutto nell'app.

## 2. La catena proposta

```
YuE2  →  brano (voce + strumenti)
  ↓  HTDemucs  (--task sep)
voce.wav  +  strumentale.wav
  ↓  SeedVC    (--task svc, con campione di riferimento)
voce-convertita.wav
  ↓  FFmpeg (già incluso) — mix voce + strumentale
brano-finale.wav
```

La conversione avviene **dopo** la generazione, come lavoro separato: così non
si somma al picco di memoria della generazione (i due modelli non restano caricati insieme) e si può rifare la voce senza rigenerare la musica.

## 3. Costi

- **Download**: 59 MB per la separazione, 2,98 GB per SeedVC (totale ~3,1 GB).
- **Spazio su disco**: ~3,3 GB in più.
- **Memoria**: i modelli di separazione e conversione sono molto più piccoli di
  YuE2; il lavoro separato non dovrebbe avvicinarsi al limite di commit attuale.
- **Tempo di calcolo**: da misurare in fase 1 e 2. La separazione è un modello
  da 59 MB (attesa: molto meno della generazione); la conversione SeedVC è a
  diffusione (30 passi) e va misurata su CPU. Su GPU sono entrambe rapide.
- **Licenze**: i pesi sono CC BY-NC 4.0 (uso non commerciale), come YuE2.

## 4. Lavoro nell'app, per fasi

### Fase 1 — Separazione (59 MB) — utile da sola
- aggiungere HTDemucs al manifest dei modelli e all'installer;
- nuovo tipo di lavoro `sep`: prende l'audio di un lavoro completato (o un file
  importato) e produce `voce.wav` e `strumentale.wav`;
- coda, avanzamento (riusa il meccanismo appena aggiunto), player ed export.
- Utile subito: base strumentale, karaoke, controllo della voce generata.
- Stima: mezza giornata di lavoro.

### Fase 2 — Conversione cantata (SeedVC) — il cuore della funzione
- libreria di voci di riferimento: `data/voci/<nome>/campione.wav`
  (10-30 secondi di voce cantata, pulita, senza musica);
- nuovo tipo di lavoro `voce`: sorgente (un brano generato o un file) + voce di
  riferimento scelta → audio convertito, salvato come nuova versione del lavoro;
- misurazione dei tempi su CPU e taratura dei parametri (passi, similarità).
- Stima: 1-1,5 giornate.

### Fase 3 — Rimix e rifiniture
- mix voce convertita + strumentale con FFmpeg (già incluso), con bilanciamento
  e normalizzazione;
- export nei formati già supportati, README e guida.
- Stima: mezza giornata.

### Fase 4 — Collaudo
- prova completa su CPU con i vincoli del PC da 16 GB, ascolto e verifica della
  qualità, eventuale confronto con RVC.
- Stima: mezza giornata.

**Totale: circa 2,5-3,5 giornate di lavoro**, con più cicli di prova reali.

## 5. Rischi e limiti da mettere in conto

1. **Qualità**: convertire una voce *sintetica* (quella di YuE2) può lasciare
   artefatti. Il campione di riferimento deve essere pulito e cantato; la
   conversione non "inventa" un timbro perfetto.
2. **Somiglianza**: con SeedVC (zero-shot) serve solo un campione; con RVC la
   somiglianza può essere maggiore ma serve un modello di voce addestrato
   (`.pth`), che non forniamo noi.
3. **Tempi su CPU**: da misurare; il PC da 16 GB è già lento sulla generazione,
   la conversione si aggiunge.
4. **Revisione dei pesi**: il repository `audio.cpp-gguf` è su `main` e cambia;
   va fissato a una revisione, come è stato necessario per YuE2.
5. **Comandi esatti**: la sintassi precisa di `sep` e `svc` va verificata
   sull'output di utilizzo del motore (il motore stampa l'esempio per ogni
   compito supportato). È il primo controllo della fase 1.

## 6. Opzioni

- **A (consigliata)** — Fase 1 subito (59 MB, mezzo giorno): separazione
  disponibile e verificabile, poi Fase 2 e 3.
- **B** — RVC invece di SeedVC: pesi più leggeri (1,2 GB) e somiglianza
  potenzialmente migliore, ma serve procurarsi o addestrare un modello di voce.
- **C** — Vevo2 (3,1 GB) come modello unico per musica e voce: da sperimentare,
  qualità non nota, affiancherebbe o sostituirebbe YuE2.

## 7. Domande per decidere

1. Su quale PC useresti la funzione? (determina i tempi di calcolo)
2. Hai un campione di voce di riferimento (10-30 s cantati, puliti)? Di chi?
3. Ti basta la Fase 1 per iniziare, o vuoi il pacchetto completo?
4. Preferisci la via zero-shot (SeedVC, solo un campione) o la massima
   somiglianza (RVC, con modello addestrato)?
