# CPU predefinita e CUDA facoltativa — H3-Music 1.2

Aggiornamento e collaudi del 26–27 settembre 2026. Il report `report-sessione.md` descrive la sessione precedente: il blocco CUDA indicato lì riguardava un eseguibile compilato soltanto con YuE2 e un problema con gli strumenti di compilazione.

## Uso dopo clone o pull

- **Nuovo PC:** clone, `install.bat`, poi `H3-Music.exe`. La scelta iniziale è CPU anche su un PC dotato di NVIDIA. Python è installato dentro l'app; non serve un Python di sistema.
- **Aggiornamento:** termina la coda, esegui `Ferma-H3-Music.bat`, `git pull` e `install.bat`. Le preferenze esistenti sono conservate. Il pacchetto CPU viene aggiornato quando cambia; un motore CUDA completo e funzionante viene conservato. Se il vecchio motore CUDA è incompleto o non rileva più una GPU, viene conservato in backup e sostituito dal motore CPU completo, così tutte le funzioni sono disponibili subito.
- **GPU:** esegui `Attiva-GPU.bat`. Per aggiornare il vecchio motore CUDA è necessario eseguire questo comando una volta dopo il pull.
- **Ritorno a CPU:** scegli CPU in Sistema e salva, oppure esegui `Attiva-CPU.bat`. I componenti GPU restano disponibili.

La CPU richiede Windows x64 e istruzioni AVX2/FMA/F16C/BMI2. La generazione richiede molta RAM ed è sensibilmente più lenta rispetto a CUDA; per i requisiti completi vedi il README.

## Preparazione NVIDIA

Occorrono driver NVIDIA compatibili, CUDA Toolkit 12.8 e Visual Studio 2022 Build Tools con C++ e CMake. Lo script usa Ninja, quindi non richiede l'integrazione CUDA di MSBuild. Se il toolset installato è troppo recente per CUDA 12.8, aggiungi MSVC v143 14.38 dai componenti individuali di Visual Studio Installer: lo script lo seleziona se presente.

Il comando rileva l'architettura della GPU del PC e compila la revisione `13c4192a28d6a212f075c4cbefc5e4983e6ed52a` di audio.cpp, con le patch H3. Include YuE2 (musica), HTDemucs (separazione) e SeedVC (voce). I contratti dei modelli sono incorporati negli eseguibili CPU e CUDA: il motore distribuito non dipende dalla cartella dei sorgenti.

La trascrizione viene verificata separatamente con PyTorch 2.8.0+cu128. Un runtime CUDA già funzionante viene riutilizzato; altrimenti viene installato in `runtime/transcription-cuda`, lasciando quello CPU in `runtime/transcription`. Il motore e il backend vengono sostituiti soltanto dopo le verifiche e con la coda vuota. La versione precedente resta in `runtime/engine-backup-*`; un errore durante la sostituzione ne provoca il ripristino.

Per percorsi non standard:

```powershell
.\Attiva-GPU.bat -VsRoot "F:\visualstudiobuild" -CudaRoot "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8"
```

Per compilare e verificare senza attivare: `Attiva-GPU.bat -BuildOnly`. Il percorso del pacchetto candidato viene scritto in `vendor/audio.cpp/build/cuda-h3/last-stage.txt` (o nella directory passata con `-BuildDir`).

## Verifiche della versione

I collaudi audio usano database e cartelle separati dalla libreria dell'utente. La fixture MP3 contiene musica originale generata per i test. La prova di conversione usa una voce sintetica, con una breve traccia separata come riferimento.

- 23 test automatici Python: studio e trascrizione esistenti, CPU iniziale, conservazione delle preferenze, selezione dei runtime, rifiuto di un motore incompleto, migrazione dal vecchio CUDA alla CPU completa, conservazione di CUDA compatibile, coda occupata e ripristino dopo un errore simulato nella sostituzione.
- Interfaccia in Edge: salvataggio progetto, navigazione, bozza, CPU predefinita, scelta CUDA, preferenze, rendering ABC, esportazione MIDI e layout mobile. Nessun errore JavaScript rilevato.
- GPU NVIDIA RTX 5070 Ti: generazione Q4 e Q8 di circa 20 secondi, separazione in quattro tracce, conversione della voce e remix stereo, trascrizione MP3 con ABC e MIDI validi. La prova usa limiti di token deliberatamente bassi: l'app segnala correttamente che il risultato è troncato. Non è una valutazione della qualità musicale né della somiglianza vocale.

- Installazione isolata senza Python: download del Python incorporato 3.12.10 e installazione reale da zero di PyTorch 2.8.0+cpu; installer completo concluso con server pronto e backend CPU. I pesi dei modelli e FFmpeg sono stati riutilizzati dalla copia locale per evitare download duplicati. La cartella di prova non contiene i sorgenti audio.cpp.
- Aggiornamento sull'installazione CUDA esistente: installer standard completato, mantenuti motore GPU e preferenze precedenti (Q8, 8 thread, stato della coda).
- Configurazione CUDA da una directory di build nuova: riuscita con rilevamento automatico della GPU e di Visual Studio. La prova ha individuato e corretto sia la scelta del toolset compatibile tra più installazioni sia i separatori nei percorsi passati a CMake.

Pacchetto CPU: `dist/h3-engine-cpu-win64.zip`, 9.436.007 byte. SHA-256: `6e18ddc07e3ff321721623dbf50b98abe60d28ea634a7b548e904fcf662827a2`.

## Ripetere i controlli

```powershell
runtime\python\python.exe -X utf8 -m unittest discover -s tests -p "test_*.py"
runtime\python\python.exe -X utf8 tests\hardware_regression.py --engine runtime\engine\audiocpp_cli.exe --backend cpu --transcribe
runtime\python\python.exe -X utf8 tests\hardware_regression.py --engine runtime\engine\audiocpp_cli.exe --backend cuda --model q8 --transcribe
```

I test hardware richiedono i modelli scaricati e creano i risultati sotto `logs/hardware-*`. La durata varia con CPU, GPU, RAM e carico del PC. Il collaudo dell'interfaccia `tests/ui_execution.cjs` richiede Playwright/Edge e un server di prova separato; `H3_TEST_URL` vale `http://127.0.0.1:8777` se non specificato.
