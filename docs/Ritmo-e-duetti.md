# Ritmo sulla base originale e duetti

I TAG come `[Verse 1 — Male]` e `[Verse 1 — Female]` esprimono l'intenzione di
alternare i cantanti. YuE2 li riceve nel testo, ma non dispone in questa API di
un'assegnazione obbligatoria dei cantanti alle sezioni. H3 riconosce ora entrambi
i ruoli nei TAG e aggiunge allo stile istruzioni esplicite che riportano i nomi
delle rispettive sezioni. Parole, ordine e TAG originali rimangono identici;
il progetto conserva anche lo stile scritto dall'utente. Le indicazioni effettive
sono registrate nella richiesta al motore e in `vocal-roles.json`.

Si tratta di una guida alla generazione, non della verifica delle identità delle
voci. Un messaggio nello Studio spiega questo limite e segnala i conflitti più
evidenti: i CNZN installati sono orientati al baritono; Particle Male e Female
guidano una voce nell'intero brano. Non si alternano automaticamente nelle
strofe e non costituiscono un motore di duetti controllati. Per provare un duetto,
YuE2 senza LoRA evita questa ulteriore preferenza per un singolo cantante.

## Deriva progressiva

In Base originale, un allineamento a ritardo costante può superare le soglie
pur lasciando un piccolo scorrimento progressivo rispetto alla base. Per brani
con almeno 45 secondi fra la prima e l'ultima nota, se resta uno scarto mediano
superiore a 20 ms, H3 confronta anche una correzione di tempo limitata al ±3%.
La sceglie soltanto se:

- la variazione è almeno dello 0,05% e accumula almeno 120 ms nel tratto cantato;
- lo scarto mediano migliora di almeno 15 ms e almeno il 25%;
- il 90° percentile non peggiora e resta entro le soglie previste;
- il confronto conserva almeno il 98% degli abbinamenti della soluzione costante.

Per i brani già ben allineati e i tratti brevi resta il percorso precedente.
La correzione opera sulla sola nuova voce, preservandone l'intonazione;
la base originale non viene rallentata, accelerata o rigenerata. La verifica
successiva misura l'audio corretto e non può proporre una nuova correzione
per far superare il proprio controllo. Il rapporto include la misurazione
precedente in `replaced_constant_timing`.

Questa correzione può migliorare gli attacchi musicali. Non sposta singole
sillabe, non verifica le parole cantate e non garantisce un'alternanza perfetta
maschile/femminile. Un testo con accenti o sillabe incompatibili con la melodia
richiede ancora un adattamento metrico e un ascolto del risultato.

Fonti: [interfaccia e cover ufficiali YuE2](https://github.com/multimodal-art-projection/YuE/blob/main/skills/yue2-music/references/generation-and-covers.md),
[Particle v2](https://huggingface.co/ntc-ai/yue2-particle-sliders),
[CNZN](https://huggingface.co/becausereasons/yue2-cnzn-canzone-italiana).

## Rallentamenti locali

Se una correzione unica non riesce, H3 può stimare un tempo separato per ciascuna
frase affidabile. Il tentativo richiede almeno 30 abbinamenti su un tratto di
almeno 30 secondi, con copertura melodica valida in ogni frase. Il tempo globale
resta entro ±3% e il ritardo globale entro 2,5 secondi; soltanto il 20% al massimo
degli abbinamenti può appartenere a frasi con un tempo locale fuori da ±3%.
Le velocità locali e i raccordi devono rientrare nello stesso intervallo
0,85–1,18 già previsto per i raccordi fra frasi. Prima del render, lo scarto
previsto deve restare entro 150 ms al 90° percentile e 450 ms nel caso peggiore.

È una correzione della sola voce: spartito, parole, seed e accompagnamento
rimangono quelli della richiesta. La verifica finale sull'audio corretto usa
le soglie normali e non può applicare altre correzioni per superare il controllo.
Un brano già accettato segue il percorso precedente. Un canto mancante, una
melodia diversa o una variazione globale di tempo eccessiva non viene recuperato
con questo metodo. Il rapporto salva `local_tempo_scales` e gli ancoraggi usati.
