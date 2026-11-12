# Parole al passo con lo spartito

Nello **Studio → Composizione e controllo**, **Parole al passo con lo spartito**
attiva un controllo facoltativo delle sezioni del testo durante la generazione.
È inizialmente selezionato e la scelta viene salvata nel progetto. Disattivalo
per mantenere il percorso precedente.

Con uno spartito ABC fornito, oppure preparato automaticamente da **Base originale**,
l'app abbina in ordine le sezioni `% verse`, `% chorus`, `% bridge` ecc. ai TAG
del testo. Per ogni sezione abbinata ricava il momento della prima nota vocale.
Il motore applica un bias di attenzione di −4 alle parole delle sezioni future,
rimuovendolo quando la generazione raggiunge il loro tempo. Stile, parole,
TAG, note ABC e seed non vengono riscritti. Non serve un LLM per questo controllo.

È un port del principio HOT-Step C6 / YuE2 Studio nel motore audio.cpp di H3-Music,
non una modifica allo Style Prompt. La lettura iniziale del contesto resta
causale e invariata; il controllo durante la generazione orienta i tempi delle
sezioni, senza garantire singole sillabe, pronuncia o perfetta fedeltà melodica.
La parte di sintesi e il decoder non cambiano.

## Quando si applica

- Serve uno spartito con sezioni riconoscibili e un tempo `Q:`.
- Devono essere riconoscibili la parte vocale e i TAG corrispondenti nel testo.
- Richiede CFG pari a 1, come il percorso iniziale di Melodia e accordi/Solo melodia.
- Una generazione diretta senza spartito fornito segue il percorso precedente.
- Il lettore gestisce durate razionali, cambi di metro e tempo, pause di più
  misure, legature e gruppi irregolari semplici del dialetto ABC YuE2. Quando
  incontra una costruzione non supportata, per esempio ripetizioni da espandere,
  registra il motivo e continua senza inventare tempi.

Il risultato nello Studio e i dettagli della sessione indicano se il controllo è
stato applicato, quante sezioni sono state agganciate e quali TAG non hanno una
sezione corrispondente. I blocchi non abbinati restano visibili al modello come
prima: non vengono eliminati o spostati. Anche i dettagli di un lavoro fallito
mostrano il rapporto preparato prima della generazione.

I dati sono in `lyric-schedule.json` e, quando attivo, `lyric-schedule.tsv` nella
cartella della generazione. Gli intervalli del testo sono byte UTF-8: accenti,
apostrofi ed emoji restano associati ai token corretti. Il motore verifica che
la tokenizzazione corrisponda alla dimensione del testo originale.

## Installazione e compatibilità

Il motore CPU Windows aggiornato è incluso in `dist/h3-engine-cpu-win64.zip`.
Una nuova installazione continua a partire su CPU. Su un'installazione NVIDIA
esistente, `install.bat` conserva il motore CUDA funzionante; per ricompilarlo
con questa estensione usa **Attiva-GPU.bat**. La build locale è verificata prima
dell'attivazione e conserva il motore precedente.

Con un vecchio motore, il controllo viene segnalato come non disponibile e la
generazione precedente resta utilizzabile. I sorgenti della patch sono comuni
alle build CPU, CUDA e Metal; le cache delle build Mac includono la nuova patch.
I pacchetti Mac pubblicati prima dell'estensione non acquisiscono la funzione
aggiornando soltanto i file Python.

## Verifiche e limiti della prova

La build CUDA sulla RTX 5070 Ti ha generato un brano con sei sezioni di testo
agganciate. I token differiscono dalla generazione senza controllo a partire
dal secondo frame, confermando che il controllo interviene nel motore.
In una prova separata, disattivandolo, i token semantici sono identici byte per
byte a quelli del motore precedente con stessi pesi, testo, seed e parametri.
Anche il pacchetto CPU è stato eseguito con Q4 e il controllo attivo, inclusa
la decodifica di due frame e la produzione dell'audio. Sono passati 238 test
automatici e i controlli dell'interfaccia su desktop e telefono.

Il testo della cover usata nella prova contiene anche TAG aggiuntivi senza una
sezione ABC corrispondente. Il controllo è quindi parziale e viene indicato come
tale. La verifica della melodia ha ancora respinto una breve frase della prova;
non viene pubblicato un mix che non supera i controlli solo perché il flag è attivo.

Per i cori e gli arrangiamenti densi, quando il riconoscimento sul mix indica una
frase mancante, viene controllata anche la voce separata prima di decidere. Le
soglie melodiche e temporali restano uguali: una frase realmente mancante o
troppo diversa continua a fermare il lavoro.

Fonti: [programmazione delle sezioni di YuE2 Studio](https://github.com/timoncool/YuE2-Studio/blob/main/crates/music-server/src/score/schedule.rs)
e [controllo dell'attenzione nel motore](https://github.com/timoncool/yue2.cpp/blob/c8516dbf44d660cca40d3f420c67063e37ec8258/src/generate.h).
