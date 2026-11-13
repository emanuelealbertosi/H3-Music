# Particle v2 in H3-Music

In Studio, **Voce e stile · LoRA facoltativo** contiene le 16 versioni standard
distillate rank-8 v2 di [ntc-ai](https://huggingface.co/ntc-ai/yue2-particle-sliders).
Sono approssimazioni degli slider originali, che usano un adattatore non lineare
e richiedono un caricatore diverso. H3 non presenta queste LoRA come gli slider
originali. Non sono un aggiornamento dei pesi YuE2.

Da **Sistema → Particle v2** puoi scaricare un adattatore o tutti e 16.
Il download completo è di 206 MB; originali e file convertiti occupano circa
412 MB nella cartella modelli scelta. Installazione e riparazione verificano
dimensione e SHA-256. Si possono riprendere dopo un'interruzione senza
riscaricare gli adattatori già verificati. Aspetta la fine dei lavori audio
prima di installare o riparare.

Seleziona **Particle · Voce maschile**, **Voce femminile**, oppure un genere.
L'intensità varia da **0** (spento, nessuna LoRA caricata) a **1** (effetto pieno);
**0,5** è intermedio. Il valore viene salvato con la bozza e con ogni generazione.
Il valore predefinito è 1. Se scegli YuE2 normale o una CNZN, questa intensità
non cambia il comportamento precedente. Nessuna Particle si attiva da sola.

H3 usa un solo adattatore alla volta: Particle sostituisce la selezione CNZN,
non la somma a Coro o Notte. Non serve una trigger word aggiunta al testo.
Il prompt e le parole vengono conservati. Le LoRA guidano la parte AR;
la sintesi NAR rimane quella del modello base. Possono cambiare fraseggio,
struttura e resa della voce; maschile/femminile non sono clonazioni di persone.
Non sono state dimostrate correzioni della pronuncia italiana o della fedeltà
parola per parola. In Base originale restano attivi i controlli melodici e temporali.

Per confrontare due versioni, mantieni spartito, testo, stile, seed, durata,
passi e scelta Words follow uguali; cambia soltanto l'adattatore o la sua forza.
Il solo seed uguale non rende equivalenti le versioni con Coro e con Particle.

## Provenienza tecnica

`particle-catalog.json` fissa la revisione
`31649319eee53e6da999cc4aff3e081d213f7911`, i file native standard distillati,
le dimensioni e gli hash pubblicati su Hugging Face. La conversione rinomina
tutte le 112 coppie di matrici di attenzione AR e conserva i byte F32 originali.
Alpha/rank deve essere esattamente 8/8: un formato diverso viene rifiutato.
Gli slider non lineari originali non vengono accettati né troncati per adattarli
al caricatore. Il motore applica poi le proprie normali regole di precisione
al merge LoRA, come per gli altri adattatori.

Serve il motore H3 con supporto AR/NAR LoRA; non è richiesta una nuova
compilazione per chi lo ha già. CPU e CUDA usano gli stessi file convertiti.
La licenza dell'autore è **CC BY-NC 4.0**, uso non commerciale.
