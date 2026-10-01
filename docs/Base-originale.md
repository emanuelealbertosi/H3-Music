# Nuovo canto sulla base originale

Disponibile da H3-Music 1.7. Nello Studio attiva **Base originale**, carica o scegli il brano, scrivi le parole e premi **Genera il brano**. Se vuoi usare il tuo timbro, attiva anche **Clona · usa la mia voce** e seleziona un campione. Lo stile è facoltativo: descrive il canto, mentre melodia e tempo vengono ricavati dalla canzone. Le opzioni ABC manuali sono disabilitate in questo percorso. Le preferenze CPU/GPU e di precisione continuano a valere.

Per un brano fino a 4 minuti (240 secondi) puoi lasciare inizio e fine a zero. Per sostituire solo una parte, apri **Cambia solo un tratto del canto** e inserisci i tempi in secondi. Per brani più lunghi scegli un tratto di massimo 4 minuti (240 secondi). Il risultato conserva tutta la base, e fuori dal tratto selezionato mantiene anche il canto originale. Ogni tentativo crea una sessione nuova; il file caricato e le versioni precedenti restano disponibili.

L'app separa voce e strumenti con HTDemucs, trascrive il tratto con SheetSage2, genera una registrazione con YuE2 usando quello spartito e il nuovo testo, e scarta la musica generata dal risultato finale. Un secondo riconoscimento delle note controlla il nuovo canto. Se la melodia corrisponde e lo scostamento temporale è stabile, viene corretto il ritardo della sola voce. Le frasi non vengono stirate e le tracce strumentali originali mantengono i propri tempi. Se la melodia o il ritmo si discostano troppo, la sessione segnala un errore e non pubblica un mix fuori tempo.

Il controllo delle note usa stime del trascrittore e non garantisce la chiarezza delle parole. Un testo con sillabe e accenti molto diversi dall'originale può richiedere più tentativi o una riscrittura. Separazione, sintesi e clonazione possono introdurre artefatti. **Cambia voce** conserva invece parole e pronuncia del canto esistente e ne cambia soprattutto il timbro: resta una funzione distinta.

In Libreria puoi ascoltare ed esportare il risultato, aprire la sessione, confrontare original.wav e voce.wav e regolare voce e musica senza ripetere la generazione. alignment.json riporta le note riconosciute e il ritardo stimato. Il mix può attenuare uniformemente il volume finale per evitare picchi.

## Collaudo

Il 1 ottobre 2026 il percorso completo su CUDA/BF16 è stato provato su una strofa di 24,94 secondi di un brano già importato dall'utente. La seconda trascrizione ha associato 53 note su 54 originali, con uno scarto massimo degli attacchi corrispondenti di circa 0,01 secondi. Il risultato completo dura circa 119,095 secondi e conserva il canto fuori dalla strofa. Il file sorgente ha mantenuto lo stesso SHA-256. Questi numeri descrivono quel campione, non una garanzia per ogni canzone. I test automatici coprono anche CPU, clonazione facoltativa, interruzione, metrica incompatibile, troncamento, progetti precedenti e conservazione della musica.
