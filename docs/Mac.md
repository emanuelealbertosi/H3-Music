# H3-Music per Mac · anteprima

Scarica il pacchetto adatto da [GitHub Releases](https://github.com/emanuelealbertosi/H3-Music/releases/tag/v1.6.0-macos-preview.1):

- **H3-Music-Mac-arm64.zip** per Apple Silicon (M1, M2, M3 e successivi).
- **H3-Music-Mac-x86_64.zip** per Mac Intel.

Questa anteprima richiede **macOS 15 o successivo**, circa **20 GB liberi** per l'installazione e preferibilmente **32 GB di RAM** per generare musica. La generazione può occupare molta più memoria dei soli pesi; i tempi dipendono dal Mac e dal brano. I Mac con poca RAM non sono un obiettivo garantito di questa anteprima.

## Installazione

1. Installa [Homebrew](https://brew.sh) se non è già presente. È il prerequisito per Python e FFmpeg.
2. Estrai lo ZIP e sposta la cartella **H3-Music** in una posizione stabile, ad esempio nella tua cartella utente. Evita cartelle protette o sincronizzate mentre generi.
3. Apri **Installa-Mac.command**. Prepara Python e FFmpeg, i modelli musicali, la separazione, il cambio voce e la trascrizione. Il primo avvio scarica diversi GB; dopo un'interruzione puoi riaprire l'installatore.
4. Apri **Avvia-Mac.command**: lo studio appare nel browser predefinito. **Ferma-Mac.command** arresta il servizio locale.

Il pacchetto è **non firmato e non notarizzato**. Se macOS blocca l'apertura, autorizza il file appena aperto in **Impostazioni di Sistema → Privacy e sicurezza → Apri comunque**. Scarica solo dal repository indicato sopra. Non è una pubblicazione sull'App Store.

Python e FFmpeg dipendono da Homebrew sul singolo Mac: non spostare o copiare la cartella `runtime` da un altro computer. Le registrazioni, i progetti e i risultati sono nella cartella `data` accanto all'app. Puoi copiare questi dati separatamente.

## CPU, GPU e precisione

Una nuova installazione parte con **CPU e Q4**. In **Sistema → Dispositivo** puoi selezionare **GPU · Metal** e salvare; l'app controlla che il motore rilevi un dispositivo Metal. Puoi tornare alla CPU senza riscaricare i modelli. Generazione, separazione e conversione vocale usano il dispositivo selezionato; **la trascrizione sul Mac usa sempre la CPU**.

Per scaricare Q8 o BF16, apri Terminale nella cartella H3-Music ed esegui uno di questi comandi, poi scegli il modello in Sistema:

```sh
runtime/python/bin/python scripts/install_macos.py --quant q8
runtime/python/bin/python scripts/install_macos.py --quant bf16
```

I modelli hanno le stesse revisioni fisse della versione Windows. Apple Silicon usa PyTorch 2.8; Intel usa 2.2.2, l'ultima versione con pacchetti macOS Intel. La trascrizione mantiene SheetSage2 e MERT-v2 e il calcolo in FP32.

Prima di aggiornare i componenti termina i lavori e chiudi il servizio con **Ferma-Mac.command**. L'installatore conserva le preferenze esistenti.

Per aggiornare solo i modelli di trascrizione puoi aprire **Aggiorna-Trascrizione-Mac.command**: mantiene Python e la scelta CPU/Metal e conserva un backup dei file sostituiti.

## Installazione dal clone GitHub

Anche il clone è supportato: apri **Installa-Mac.command**. Scarica il motore precompilato della stessa anteprima e ne verifica il pacchetto con SHA-256; non devi compilare CUDA o installare un compilatore. La release deve essere già pubblicata perché il download funzioni.

## Verifiche e limiti dell'anteprima

Il workflow GitHub compila il motore nativo per entrambe le architetture dalla revisione `13c4192a28d6a212f075c4cbefc5e4983e6ed52a`, con le estensioni H3-Music per ABC e artefatti intermedi. Include YuE2, HTDemucs e SeedVC, CPU e Metal, con gli shader incorporati. La verifica del pacchetto esclude dipendenze dinamiche da percorsi del computer di compilazione.

I controlli automatici verificano il caricamento del motore e dei runtime Python, l'avvio del servizio, il database, il salvataggio dei progetti, FFmpeg e le preferenze CPU. **Non equivalgono a un collaudo completo di brani generati, clonazione o qualità sonora su ogni GPU Mac**. Metal va provato sul Mac dell'utilizzatore; in caso di problemi seleziona CPU e conserva il log del lavoro. Questa è perciò una prerelease sperimentale.

LM Studio e Tailscale restano facoltativi. Su Mac l'assistente usa lo stesso indirizzo locale configurabile. Per Tailscale, con il relativo comando disponibile nel PATH, puoi eseguire `runtime/python/bin/python scripts/tailscale_access.py` per attivare l'accesso e lo stesso comando seguito da `--disable` per disattivarlo; viene mantenuto l'accesso privato della tailnet.
