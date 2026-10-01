# Collaudo 1.8

La suite comprende 152 test Python e sette verifiche dell'interfaccia.
Copre anche creazione normale, CPU/GPU, cartella dei modelli, libreria,
risultati nello Studio, base originale e intervalli ai due lati dei 150 secondi.

La trascrizione reale di Dragon Ball GT, circa 217 secondi, produce ora
122 battute ABC con 460 note vocali e 100 note strumentali. I MIDI e le
annotazioni precedenti sono conservati. Il problema era un'ultima
annotazione di accordo di circa 15 millisecondi, più breve di una cella
della griglia ABC. Il test completo sul modello pinned e la prova
dell'interfaccia verificano codice ABC, spartito e apertura nello Studio.

Per il nuovo motore, la prova **senza LoRA** confronta vecchio e nuovo
binario a parità di spartito, testo, seed e parametri:

| Dispositivo | Pesi | Campione | Esito |
| --- | --- | --- | --- |
| NVIDIA CUDA | BF16 | 24 secondi, 8 passi | Token, latenti e WAV identici byte per byte |
| CPU | Q4 | 8 secondi, 1 passo | Token, latenti e WAV identici byte per byte |

I limiti token ridotti sono intenzionali per queste prove riproducibili;
non sono valutazioni della qualità musicale o test di completamento
di un intero brano. La gestione dei brani lunghi conserva le verifiche
dell'allineamento della versione precedente.

Per tutti i quattro checkpoint CNZN sono verificati SHA-256, struttura,
dimensioni e **tutti i valori BF16** dei tensori convertiti, in entrambe
le parti AR/NAR e in tutti i 28 livelli. La separazione delle proiezioni
fuse conserva l'intera matrice A e suddivide le righe B, anche quando
i ranghi sono condivisi. Ogni LoRA ha prodotto audio sul motore CUDA
con i valori consigliati dall'autore; i log confermano entrambe le parti.

L'adattamento metrico è verificato con risposte simulate, anche errate,
e con un LLM reale da 12B in LM Studio **su CPU**. La prova traduce
una frase inglese in «Vedo l'alba sorgere», conservando spartito e stile;
tempo circa 44 secondi. Il controllo delle elisioni è stato ricontrollato
dopo la prova. Questo campione non certifica la qualità di un testo intero,
né pronuncia, accenti tonici o allineamento finale del canto.

I controlli dell'interfaccia verificano che la proposta non sostituisca
il testo prima di **Applica**, che l'applicazione cambi soltanto le parole,
che pause, legature e ripetizioni entrino nella lettura della melodia e
che le nuove scelte siano utilizzabili anche su uno schermo piccolo.
