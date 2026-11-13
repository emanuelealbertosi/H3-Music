# Coro e piccoli frammenti melodici

In **Studio → Base originale**, **Accetta piccole variazioni del canto** permette
di completare il brano con un avviso quando il confronto fallisce soltanto su un
breve passaggio parzialmente riconosciuto accanto a una frase affidabile. La scelta è salvata
nel progetto ed è inizialmente attiva. Disattivandola si conserva il controllo
severo precedente.

Non viene modificato il LoRA: Coro mantiene i valori originali di composizione
e sintesi, come gli altri adattatori. Non cambiano pesi, testo, ABC, seed o base
strumentale. I risultati che superavano già il confronto seguono lo stesso
percorso di prima.

## Limiti dell'accettazione

Un frammento può essere valutato insieme alla frase vicina solo se:

- comprende da 3 a 8 note e dura al massimo 3 secondi;
- almeno metà delle note è riconosciuta, con al massimo tre note non abbinate;
- resta valida anche la precedente eccezione per una cadenza di 3–4 note entro
  0,9 secondi, con almeno una nota riconosciuta e al massimo due non abbinate;
- una frase vicina di almeno 5 note è riconosciuta almeno al 70%;
- la pausa fra i due gruppi non supera 1,5 secondi;
- contando **tutte** le note dei due gruppi, la copertura resta almeno al 70%.

Un frammento interamente mancante resta un errore. Non vengono accettati con
questa regola passaggi lunghi, gruppi isolati o derive di tempo oltre i limiti
già previsti. Il conteggio non elimina note dall'originale e i confronti di
intonazione mantengono le stesse regole.

Quando un frammento viene accettato, il controllo finale viene sempre eseguito
sulla **nuova voce isolata dopo l'allineamento**. La base originale non può quindi
far superare il controllo a una voce mancante. Restano i limiti di ritardo globale e quelli sulla precisione del 90% degli
attacchi. In modalità tollerante il singolo attacco peggiore può avere uno
scarto riconosciuto fino a 0,75 secondi (0,65 dopo la stima del cambio di tempo),
con avviso e verifica sulla voce isolata. Il controllo severo conserva i limiti
precedenti di 0,65 e 0,45 secondi. Non viene aumentato il ritardo globale
consentito sul canto finale.

Lo Studio e i dettagli mostrano l'avviso **Piccole variazioni del canto accettate**,
con i punti da ascoltare nella canzone finale. Per un tratto selezionato gli
orari comprendono il suo inizio nella registrazione completa. I dettagli del
confronto sono conservati in `alignment.json` e nel risultato della sessione.
L'avviso segnala una differenza o un'incertezza del riconoscimento; non promette
una copia perfetta delle note né della pronuncia.

## Verifica sul caso che falliva

Il frammento che fermava Coro era a 123,905–124,675 secondi: 1 nota abbinata su 3,
vicino a una frase ben riconosciuta. Dopo l'allineamento, il confronto sulla nuova
voce isolata ha abbinato 300 note su 322 dell'originale. Il ritardo mediano
misurato era circa −16 ms, l'errore di attacco mediano circa 14 ms e il 90°
percentile circa 26 ms. Il mix completo conserva la durata di 138,60 secondi.

La prova ha riutilizzato esattamente l'audio generato dal tentativo fallito con
Coro pieno: la correzione riguarda la classificazione del breve frammento, non
una rigenerazione fortunata o un cambiamento del suono del LoRA. Sono stati
ricalcolati l'allineamento, i controlli sull'audio corretto e il rimix finale.

In modalità tollerante, se la verifica finale sulla voce isolata fallisce, sono
compatibili differenze locali di esattamente un’ottava entro 0,65 secondi
dall’attacco previsto. Devono riguardare al massimo il 10% delle note riconosciute.
Una nota già riconosciuta esattamente nelle vicinanze ha sempre la precedenza.
La verifica di melodia, copertura e tempi viene ripetuta sul confronto corretto;
i passaggi interessati sono segnalati nell’avviso. L’audio non viene trasposto.
Una voce assente, una trasposizione globale o note di altra classe non vengono
accettate da questa regola. In modalità severa questo recupero non è attivo.
