# Italiano e testo sulla melodia · 1.9

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
Se manca, **Adatta alla melodia** accoda automaticamente la trascrizione
del tratto scelto e attende il risultato prima di interrogare il modello del testo.
Non viene inventata una trascrizione dal solo titolo del brano.

L'assistente legge la linea vocale, note legate, pause, durate, tempi forti
e ripetizioni. Lavora per gruppi di frasi, controlla una stima delle sillabe
e può chiedere al modello una correzione. Mostra il testo e il controllo
delle frasi prima di applicare **soltanto le parole** alla bozza.
Il testo precedente rimane fino alla tua scelta; spartito, stile, base,
LoRA e impostazioni non cambiano.

Puoi scegliere **Assistente integrato**, **LM Studio esterno** oppure **API online** in Sistema.
L’assistente integrato carica il modello solo durante la richiesta e lo scarica
anche in caso di errore. I lavori audio accodati attendono che abbia liberato
la memoria. Se un lavoro audio è già avviato, l’app chiede di attendere la sua conclusione.
La scelta CPU/GPU dell’assistente è indipendente da quella musicale.

Per installarlo su Windows esegui **Installa-Assistente.bat**; su Mac esegui
**Installa-Assistente-Mac.command**. È facoltativo: scarica llama.cpp e
Qwen3 4B Q4 (circa 2,5 GB), senza pacchetti Python globali. Su Windows
parte su CPU; per il motore CUDA usa `Installa-Assistente.bat --gpu`.
Il motore Mac include CPU e Metal. Durante l’installazione completa puoi
aggiungere `-Assistant` su Windows oppure `--assistant` su Mac.

In **Sistema → Assistente integrato → Sfoglia…** puoi scegliere un altro
modello istruito GGUF già presente. Premi **Salva preferenze**: viene usato
dalla sua posizione, senza copiarlo. Il selettore si apre dentro l’app e mostra le cartelle e i dischi del computer
che esegue H3-Music, anche tramite Tailscale. Include ricerca, cartella
superiore e annullamento; mostra soltanto cartelle e file GGUF. Lascia il
campo vuoto per usare il Qwen installato nella cartella modelli dell’app.
Il supporto dipende dall’architettura riconosciuta dal motore llama.cpp.
La cartella modelli include anche il Qwen predefinito durante un trasferimento;
un modello esterno scelto manualmente mantiene il proprio percorso.

I TAG già presenti, compresi quelli numerati o ripetuti e le sezioni vuote,
sono conservati nello stesso ordine. L’assistente prepara una struttura
per l’intero brano prima di lavorare sulle singole frasi; una proposta che
rimuove o cambia i TAG viene corretta oppure rifiutata senza modificare la bozza.

Per usare **LM Studio**, carica un modello istruito e attiva il server locale,
configurato in Sistema. Non richiede un servizio a pagamento.
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

## Assistente tramite API online

In **Sistema → Assistente musicale → Motore del testo** scegli **API online**.
Seleziona OpenAI, DeepSeek, OpenRouter oppure **Personalizzato · compatibile
OpenAI**, inserisci l’indirizzo base del servizio e la tua chiave. Premi
**Leggi modelli**, scegli un modello per testo/chat e poi **Salva preferenze**.
Se il servizio non espone la lista, inserisci manualmente il suo identificativo.
La lettura della lista non genera testo; assistente e adattamento possono
consumare credito secondo il servizio e il modello scelti.

La stessa selezione viene usata dall’**Assistente musicale** e da **Adatta alla
melodia**. Testo, stile, indicazioni e spartito necessari alla richiesta vengono
inviati al servizio; i file audio e i campioni vocali non vengono inviati.
La trascrizione che prepara l’ABC rimane locale. Le API non occupano la VRAM
con un modello del testo: la musica continua a essere generata da YuE2 sul PC.
La proposta deve sempre essere letta e applicata esplicitamente alla bozza.

La chiave viene conservata nel database locale dell’app, in una voce separata
dalle preferenze pubbliche, e non viene restituita al browser né esportata nei
progetti. Il database è escluso da Git; non è un archivio cifrato. Una chiave è
associata al suo indirizzo API completo: cambiando servizio non viene inviata
al nuovo indirizzo. Il campo vuoto conserva la chiave; per eliminarla seleziona
**Rimuovi la chiave salvata quando salvi** e salva. I servizi remoti richiedono
HTTPS; HTTP è ammesso solo per un server sullo stesso computer.

**Compatibilità della risposta → Automatico** usa JSON strutturato quando
supportato e passa a JSON semplice o istruzioni testuali soltanto se il servizio
rifiuta esplicitamente il formato. Puoi scegliere manualmente le altre due
modalità. I controlli di TAG, ordine delle frasi e sillabe restano attivi. Non
vengono ripetute automaticamente richieste con errore di rete, quota o chiave.
Sono supportate le API **Chat Completions** compatibili OpenAI, non protocolli
nativi differenti. Disponibilità e qualità dipendono dal modello scelto.

Riferimenti: [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create),
[DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode/),
[OpenRouter Structured Outputs](https://openrouter.ai/docs/guides/features/structured-outputs).

## Spartito dopo la trascrizione

Il risultato mostra **spartito**, **Codice ABC** e **Apri in Studio** quando
l'ABC è disponibile. Se una breve annotazione cade interamente tra due
punti della griglia dello spartito, viene omessa dalla sola notazione;
le note MIDI e le annotazioni originali sono conservate.
Altri errori non vengono nascosti: in quel caso rimangono disponibili
note e MIDI con un messaggio esplicito sull'ABC mancante.

## Componenti dell’assistente

Il componente facoltativo usa [llama.cpp](https://github.com/ggml-org/llama.cpp)
(MIT) e [Qwen3-4B-GGUF](https://huggingface.co/Qwen/Qwen3-4B-GGUF)
(Apache-2.0). Le revisioni e gli hash verificati sono in
`scripts/assistant-runtime.json`. Queste licenze sono distinte da quelle
dei modelli musicali. Un altro GGUF mantiene la licenza del proprio autore.
