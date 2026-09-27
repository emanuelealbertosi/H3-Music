# BF16, pronuncia italiana e fedeltà delle cover — versione 1.3

BF16 è disponibile come terzo modello musicale, insieme a Q4 e Q8. Q8 resta predefinito nelle nuove installazioni; CPU resta il dispositivo iniziale. Dopo il download con `Installa-BF16.bat`, scegli **Sistema → Modello musicale → BF16 → Salva preferenze**. I tre modelli restano sul disco; non serve ricompilare il motore.

Il download BF16 usa la stessa revisione dei modelli già collaudati, `f7cb0712b9c2e5e9dcadc8b3ab23a591756c131b`, e controlla dimensione (7.261.475.392 byte) e SHA-256 (`18fe0cda4687a565fc6f2045759f446a67f0d775ea479b87da45de90e7ddc9bc`). Se BF16 è assente o incompleto, l'app lo segnala: non lo sostituisce silenziosamente con Q8.

## Prova sulla RTX 5070 Ti 16 GB

Test del 27 settembre 2026, testo italiano originale, stesso stile e seed, 32 passi, limite audio 1500 token. Libreria di prova isolata. La scelta del modello può cambiare anche la composizione: non sono due registrazioni identiche elaborate diversamente.

| Modello | Audio prodotto | Tempo del lavoro | Picco memoria GPU totale osservato |
|---|---:|---:|---:|
| Q8 | 44,96 s | 19,06 s | 6.138 MiB (6,0 GiB) |
| BF16 | 60,00 s | 28,11 s | 9.321 MiB (9,1 GiB) |

Entrambi producono audio stereo 48 kHz, finito e non silenzioso. Lo spartito è completo in entrambi i casi; BF16 raggiunge il limite dei token audio e l'app lo segnala come troncato, mentre Q8 termina senza quel limite. I tempi non sono un benchmark comparabile a parità di durata. La memoria è campionata con `nvidia-smi` ogni secondo e include desktop e altri processi; non è un limite massimo garantito per tutti i brani.

BF16 conserva maggiore precisione dei pesi rispetto a Q8/Q4. Non sono stati misurati tassi di errore di pronuncia o accento: occorre ascoltare e confrontare più campioni. L'italiano resta sperimentale per YuE2; più bit non sostituiscono dati di addestramento linguistici.

## Perché nella cover cambiano gli strumenti

La trascrizione usa **SheetSage2 + MERT-v2-FullSong** completi, senza quantizzazione Q4/Q8. L'app usa BF16 in inferenza GPU (anche i benchmark ufficiali sono in BF16) e FP32 su CPU, tutti i prompt del modello e il profilo standard con finestre sovrapposte. Non abbiamo cambiato questo profilo senza una prova che migliori la fedeltà.

SheetSage2 produce soprattutto una partitura sintetica: melodia vocale e strumentale, accordi, battiti, tonalità e struttura. Non conserva integralmente ogni parte del mix, né il suono originale degli strumenti. In particolare un simbolo di accordo non codifica necessariamente l'arpeggio, il voicing e ogni nota dell'accompagnamento originale.

Quando premi **Crea una cover**, YuE2 usa lo spartito insieme a stile e testo per generare una nuova registrazione. Gli strumenti e parte dell'accompagnamento vengono quindi ricomposti. Aumentare la precisione numerica del trascrittore non trasforma questo percorso in una copia del mix originale. L'anteprima pianoforte serve a controllare le note riconosciute prima della generazione.

Per cambiare il timbro di una voce conservando la base del brano generato, usa [Voce su misura](voce-su-misura.md): separazione, conversione della voce e remix. Anche questo percorso può introdurre artefatti, ma non rigenera tutta la musica con YuE2.

Fonti: [SheetSage2, documentazione e benchmark](https://huggingface.co/m-a-p/SheetSage2), [modelli YuE2 GGUF](https://huggingface.co/audio-cpp/Yue2-3B-GGUF).

## Verifiche

28 test automatici passati; prove Q8/BF16 sulla GPU; selezione e salvataggio BF16 dall'interfaccia; nessun errore JavaScript nei percorsi verificati. Controllato anche il player del risultato della conversione vocale. Per ripetere i campioni italiani: `runtime\python\python.exe -X utf8 tests\italian_model_generation.py --model bf16` (oppure `q8`). I risultati e le misure restano in `logs/` e non vengono pubblicati su GitHub.
