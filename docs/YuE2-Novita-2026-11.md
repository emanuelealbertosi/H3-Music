# YuE2: verifica del 12 novembre 2026

## Cosa cambia per H3-Music

Le novità degli altri Studio non aggiornano automaticamente i pesi YuE2.
H3-Music usa audio.cpp, con estensioni proprie per artefatti e LoRA, e lo stesso
binario gestisce anche separazione e conversione vocale. Il motore yue2.cpp di
Studio non può sostituirlo direttamente senza adattare e verificare questi percorsi.

| Componente | Riscontro | Decisione |
|---|---|---|
| YuE2 ufficiale | Il repository dei pesi 3B elenca il rilascio del 9 settembre; i successivi commit visibili riguardano documentazione e riferimenti. Il pacchetto di inferenza è 0.1.6. | Nessun nuovo checkpoint principale identificato in questa verifica. |
| Studio 3.8.4–3.8.5 | Correzioni Blackwell, gestione cache e raccordi fra chunk. Esistono anche segnalazioni di regressioni. | Portare e misurare separatamente le correzioni pertinenti. Non sostituire il motore in blocco. |
| Words follow the score | La generazione limita l'attenzione alle parole delle sezioni future, in base ai tempi ABC. | Priorità per cover lunghe; richiede sezioni affidabili nello spartito e modifiche native, non soltanto un prompt. |
| AB2 | La sintesi usa S+1 valutazioni invece di 2S per S passi. | Candidato per un'opzione facoltativa; mantenere midpoint come predefinito e confrontare l'audio. Il guadagno non riguarda tutte le fasi. |
| Hangry Labs v1.0.0 | Applicazione C++/GGML con API e distribuzione Docker, qualificata sulla RTX 5070 Ti 16 GB. | Utile come riferimento per prove e gestione del motore; non è un modello più grande o un miglioramento dimostrato dell'italiano. |
| YuE2-Turbo | Gli autori misurano la velocità su RTX 5090; configurazione Linux, circa 18 GB di VRAM già a riposo. | Non adottare la configurazione predefinita sulla scheda da 16 GB. |
| MiniMax Music 3 | Modello alternativo con componenti 8B e 0,6B; il percorso di inferenza ufficiale richiede due GPU CUDA. | Richiederebbe un'integrazione e prove dedicate con un port adatto a 16 GB; nessuna sostituzione automatica di YuE2. |

LoRA italiani opzionali, conservazione della base separata e generazione di nuovo
canto con altre parole sono già presenti in H3-Music. I benchmark citati da YuE2
usano 192 prompt in cinese e inglese: non misurano direttamente pronuncia italiana,
fedeltà alla registrazione caricata o qualità della clonazione personale.

La cache ridotta a 9216 token di Studio non va applicata indiscriminatamente:
spartito, testo e audio condividono il contesto. Un limite inferiore può accorciare
il canto di brani che già funzionano; durata massima e memoria vanno verificate
insieme, senza ridurre silenziosamente i minuti disponibili.

## Errore riprodotto e correzione locale

In una cover su base originale di 138,60 secondi, quattro tentativi con stesso
seed e LoRA hanno prodotto token semantici identici. La generazione terminava
spontaneamente a 131,12 secondi, senza raggiungere il limite massimo di token.
L'ultima frase originale (133,60–138,49 secondi, 15 note) non risultava abbinata.
Il controllo di allineamento fermava correttamente il mix: non era un crash CUDA.

Il nuovo minimo automatico della generazione su base originale deriva dall'ultima
nota vocale riconosciuta: `ceil(fine_ultima_nota * 25)` token, quando supera il
minimo del motore. Non modifica stile, testo o durata massima, non aggiunge silenzio
al file e non disattiva i controlli melodici. Un minimo impostato esplicitamente
dall'utente resta rispettato. Un massimo incompatibile viene spiegato prima della
sintesi; la generazione normale senza base originale non cambia.

Nella prova con gli stessi modello BF16, seed, LoRA e 48 passi, il canto ha raggiunto
138,64 secondi e superato il primo controllo melodico: 299 note abbinate su 322,
correzione di tempo stimata entro il 2%, errore di attacco al 90° percentile di
circa 12 ms dopo la correzione prevista. Queste misure verificano tempi e note,
non garantiscono pronuncia o qualità percepita.

La verifica completa ha poi separato il canto, applicato l'allineamento e
rimixato sulla base originale: durata finale 138,60 secondi, 302 note abbinate
su 322 nel controllo del mix, ritardo mediano misurato pari a zero e 90°
percentile dell'errore di attacco di circa 10 ms. Il risultato ha superato i
controlli già previsti, senza allentarne le soglie.

Gli errori per frasi insufficientemente riconosciute ora indicano intervallo e
numero di note abbinate, e suggeriscono di cambiare seed o LoRA. Resta attivo il
blocco del mix quando manca una frase: allungare la generazione non basta da solo
a garantire il canto corretto.

Un ulteriore tentativo storico ha invece incontrato un'asserzione di allocazione
del contesto GGML (`ctx->mem_buffer != NULL`). Il log non identifica un esaurimento
della VRAM: va distinto dai fallimenti di allineamento e dalla regressione
Blackwell descritta da Studio.

## Fonti primarie

- [Pesi e storico ufficiale YuE2](https://huggingface.co/m-a-p/YuE2-3B/commits/main)
- [Pacchetto ufficiale di inferenza](https://github.com/multimodal-art-projection/YuE/blob/main/pyproject.toml)
- [Studio 3.8.5](https://github.com/timoncool/YuE2-Studio/releases/tag/v3.8.5)
- [Segnalazione di regressioni #213](https://github.com/timoncool/YuE2-Studio/issues/213)
- [Programmazione delle sezioni del testo](https://github.com/timoncool/YuE2-Studio/blob/main/crates/music-server/src/score/schedule.rs)
- [Solver AB2](https://github.com/timoncool/yue2.cpp/blob/c8516dbf44d660cca40d3f420c67063e37ec8258/src/flow-solver.h)
- [YuE2-Turbo: requisiti e misure dichiarate](https://github.com/NoizAI/YuE2-Turbo)
- [Hangry Labs YuE2](https://github.com/hangry-labs/yue2)
- [MiniMax Music 3 ufficiale](https://github.com/MiniMax-AI/MiniMax-Music3)
- [WildSongBench: prompt e benchmark](https://huggingface.co/datasets/m-a-p/WildSongBench)
