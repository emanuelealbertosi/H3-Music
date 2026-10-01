# Italiano e testo sulla melodia · 1.8

## Quattro LoRA opzionali

In **Sistema → LoRA italiani → Installa / ripara i quattro LoRA** vengono
scaricati Teatro, Notte, Coro e Sussurro, seconda generazione CNZN.
Servono circa 470 MB di download e 1 GB nella cartella modelli configurata.
Ogni file viene controllato con SHA-256 e convertito senza perdere le
modifiche dei pesi condivisi tra le proiezioni.

Nello **Studio → Voce italiana** scegli un LoRA. La scelta viene salvata
nel progetto e applicata alla prossima generazione, anche con **Base originale**.
**YuE2 normale** rimane predefinito. I brani già prodotti non vengono modificati.

| LoRA | Intensità composizione (AR) | Intensità sintesi (NAR) |
| --- | --- | --- |
| Teatro | 1 | 1 |
| Notte | 0,5 | 1 |
| Coro | 1 | 1 |
| Sussurro | 1 | 1 |

Sono i valori consigliati dall'autore per l'uso generale; Teatro e Coro
possono avere indicazioni diverse per generi specifici nella scheda originale.
Il richiamo `cnzn, Italian` viene aggiunto allo stile usato dal motore.
Per Sussurro scrivi sezioni **[Spoken]** nel testo.
Il LoRA modifica composizione e sintesi: non clona la tua voce e non garantisce
pronuncia, accenti o metrica perfetti.

Una vecchia versione del motore non può applicare i LoRA. Dopo il pull,
aggiorna la CPU con **install.bat**, oppure ricompila il motore NVIDIA con
**Attiva-GPU.bat**. L'installatore conserva un motore CUDA funzionante:
in quel caso serve Attiva-GPU.bat anche se install.bat è già stato eseguito.
Su Mac usa **Installa-Mac.command** dopo il pull oppure con il nuovo
pacchetto della release. Anche un vecchio motore CPU già funzionante viene
aggiornato se manca il supporto LoRA, conservando il binario precedente.
L'app segnala i motori incompatibili prima di accodare il lavoro.

Provenienza: [CNZN LoRA by becausereasons](https://huggingface.co/becausereasons/yue2-cnzn-canzone-italiana),
revisione `89508af770d21ea26215603fdd777f182ba4ecee`, licenza CC BY-NC 4.0.
Il supporto nel motore è un'aggiunta isolata da audio.cpp, con licenza
Apache-2.0 e provenienza in `scripts/engine-lora/README.md`.

## Adatta alla melodia

Nella scheda **Le parole del brano**, premi **Adatta alla melodia**.
Puoi migliorare il testo attuale, tradurre un testo straniero in italiano
oppure creare parole nuove seguendo le tue indicazioni.

Serve uno spartito ABC nella bozza. Con **Base originale**, l'app cerca
la trascrizione già completata dello stesso file e dello stesso tratto,
oppure lo spartito originale di una precedente generazione su quella base.
Se manca, trascrivi prima quel tratto nella pagina **Trascrivi**.
Non viene inventata una trascrizione dal solo titolo del brano.

L'assistente legge la linea vocale, note legate, pause, durate, tempi forti
e ripetizioni. Lavora per gruppi di frasi, controlla una stima delle sillabe
e può chiedere al modello una correzione. Mostra il testo e il controllo
delle frasi prima di applicare **soltanto le parole** alla bozza.
Il testo precedente rimane fino alla tua scelta; spartito, stile, base,
LoRA e impostazioni non cambiano.

Richiede **LM Studio** con un modello istruito e il server locale attivo,
configurati in Sistema. Non richiede un servizio a pagamento.
Per lasciare libera la GPU musicale, carica l'LLM sulla CPU. Se lo carichi
sulla GPU, scaricalo da LM Studio prima di avviare YuE2.
Senza un modello selezionato, viene usata una delle istanze già caricate,
conservandone la scelta CPU/GPU. L'adattamento non carica automaticamente
il primo modello disponibile. Nei modelli che espongono il controllo del
ragionamento, viene disattivato per questa richiesta. Negli altri casi
viene richiesta una risposta JSON strutturata e controllata prima dell'uso.

Le sillabe sono una stima: sinalefi, iati e melismi dipendono dal canto.
Le frasi fuori dall'intervallo sono segnalate anche dopo il tentativo di
correzione. Il controllo non certifica gli accenti tonici di ogni parola;
resta necessario ascoltare il risultato.

## Spartito dopo la trascrizione

Il risultato mostra **spartito**, **Codice ABC** e **Apri in Studio** quando
l'ABC è disponibile. Se una breve annotazione cade interamente tra due
punti della griglia dello spartito, viene omessa dalla sola notazione;
le note MIDI e le annotazioni originali sono conservate.
Altri errori non vengono nascosti: in quel caso rimangono disponibili
note e MIDI con un messaggio esplicito sull'ABC mancante.
