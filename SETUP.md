# Setup

Due sistemi: **macOS** (oggi) e **Nobara Linux** (domani). Il progetto usa solo percorsi relativi,
quindi si sposta da un computer all'altro senza modifiche.

---

## macOS

### 1. Strumenti

```bash
xcode-select --install          # se non l'hai mai fatto
brew install ffmpeg python@3.13
```

Verifica:

```bash
ffmpeg -version
/opt/homebrew/opt/python@3.13/bin/python3.13 --version
```

> Se il tuo ffmpeg non ha il filtro `drawtext` non è un problema: i segnaposto sono disegnati con
> Pillow e animati con `zoompan`, che c'è in tutte le build.

> **Python 3.15 e faster-whisper non vanno d'accordo**: la libreria `av` non ha ancora i wheel e
> l'installazione fallisce. Usa Python 3.13 (o 3.12/3.11). Lo script di setup lo fa da solo.

### 2. Ambiente Python del progetto

```bash
cd ~/shorts-studio
/opt/homebrew/opt/python@3.13/bin/python3.13 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install pillow
.venv/bin/pip install faster-whisper "av<17"
```

> `av` 19 ha rimosso un parametro che faster-whisper 1.2 usa ancora. Con `av<17` tutto
> funziona; lo script di setup lo fa già.

Da qui in poi usa sempre `.venv/bin/python` (oppure attiva il venv con `source .venv/bin/activate`).

Il modo più semplice è lanciare lo script, che sceglie il Python giusto e installa tutto:

```bash
./scripts/setup-macos.sh              # faster-whisper incluso
./scripts/setup-macos.sh --no-whisper # se non vuoi la trascrizione automatica
```

Controllo:

```bash
.venv/bin/python scripts/shorts.py doctor
```

### 3. DaVinci Resolve

Scarica **DaVinci Resolve free** dal sito Blackmagic e installa. Al primo avvio crea un progetto vuoto
(es. `Shorts`). Non serve altro: lo scripting dalla Console funziona anche nel free.

### 4. Come si usa la Console (importante)

1. Apri Resolve con un progetto aperto.
2. Menu **Workspace > Console**.
3. In basso nella Console c'e un selettore di linguaggio: scegli **Lua**.
4. Trascina il file `build/<slug>/<slug>_build.lua` dentro la finestra della Console.
5. Premi **Invio**.

La Console non ricorda niente tra una sessione e l'altra: ogni volta che riapri Resolve devi
ritrascinare lo script. Va bene, e una operazione da 5 secondi.

Per un test rapido:

```lua
print(resolve:GetVersion())
```

Se stampa la versione, sei a posto.

Caption e transizioni automatiche non richiedono altro software: Pillow disegna le card e ffmpeg
le codifica in QTRLE con alpha. Le caption usano `build/<slug>/words.json`, quindi vanno generate
dopo `render-audio`. In Resolve arrivano come clip video su V4 (non come traccia sottotitoli):
il file `captions.srt` nella stessa cartella e la copia esportabile.

### 5. Script di diagnostica (`scripts/lua/`)

Tre utility indipendenti dai progetti, da trascinare nella Console come qualsiasi altro script:

| File | Quando usarlo |
|---|---|
| `00_check.lua` | Sempre, la prima volta. Stampa versione, progetto, timeline, tracce, marker e formati render. Non modifica nulla |
| `20_fusion_probe.lua` | Solo se vuoi capire se la tua versione free accetta `AddFusionComp`/`ImportFusionComp`. Usa una timeline di prova: crea e cancella una comp sul primo clip di V1 |
| `90_render_queue.lua` | Per esportare: imposta 1080x1920 H.264 e aggiunge il job. Apri il file e controlla `OUT_DIR` prima di lanciarlo |

Se `00_check.lua` non stampa niente, il linguaggio della Console non è **Lua** o non c'è un progetto aperto.

### 6. Font (consigliati, gratuiti)

Installa da Google Fonts quelli che ti servono per lo stile scelto (vedi `STYLE.md`):

- **Anton**, **Bebas Neue** — titoli grossi
- **VT323**, **Press Start 2P**, **Share Tech Mono** — CRT / PS2
- **Jost**, **Inter** — Frutiger Aero / pulito
- **Noto Sans JP** — se usi kanji

Su macOS: doppio click sul `.ttf` → *Installa carattere*.
Su Nobara: copia in `~/.local/share/fonts/` e lancia `fc-cache -f -v`.

---

## Nobara Linux

Nobara e gia predisposta per il multimedia. I pacchetti base:

```bash
sudo dnf install -y ffmpeg ffmpeg-free python3 python3-pip python3-virtualenv
```

Se Resolve non parte, mancano quasi sempre queste librerie:

```bash
sudo dnf install -y libxcrypt-compat mesa-libGLU alsa-lib fuse-libs
```

Installa **DaVinci Resolve free** con l'installer `.run` di Blackmagic:

```bash
chmod +x DaVinci_Resolve_*_Linux.run
./DaVinci_Resolve_*_Linux.run
```

Resolve finisce in `/opt/resolve/bin/resolve`. La Console e sempre **Workspace > Console**, Lua.

Ambiente Python:

```bash
cd ~/shorts-studio
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install pillow faster-whisper "av<17"
.venv/bin/python scripts/shorts.py doctor
```

Note specifiche Linux:

- I driver NVIDIA proprietari sono obbligatori per Resolve. Nobara li installa dal suo tool.
- Se usi Wayland e Resolve si comporta male, avvia la sessione X11.
- Il percorso dei font per i segnaposto è già gestito: lo script cerca DejaVu/Liberation.
- Gli script Lua non contengono percorsi assoluti: cercano la cartella in `~/shorts-studio` o nella
  directory corrente. Se la sposti altrove (o la chiami diversamente), scrivi prima in Console
  `SHORTS_ROOT = "/percorso/della/cartella"` e poi lancia lo script.

---

## Whisper: quale modello

| Modello | Velocita su M1/M2 | Qualita italiano/inglese | Quando |
|---|---|---|---|
| `tiny` | altissima | bassa | test veloci |
| `base` | alta | media | bozze |
| `small` | media | buona | **default consigliato** |
| `medium` | lenta | molto buona | se hai tempo |
| `large-v3` | molto lenta | ottima | solo se serve |

```bash
.venv/bin/python scripts/shorts.py transcribe <slug> --model small --language auto
```

La lingua si risolve cosi: `--language` esplicito > `"language"` in `projects/<slug>/project.json` >
`auto` (rilevamento Whisper). Per un voiceover italiano puoi usare `--language it`, per uno inglese
`--language en`; con `auto` funzionano entrambi senza cambiare progetto.

Se registri in **video** (talking head), metti l'mp4/mov in `media/voiceover/raw/`: Whisper usa la
traccia audio e il resto della pipeline funziona uguale. In quel caso lancia
`render-audio <slug> --video` (oltre a `--normalize` se vuoi): oltre alla voce tagliata prepara
`vo_clean.mp4` e le clip A-roll. Serve solo ffmpeg con `libx264`, che `doctor` controlla.

La prima esecuzione scarica il modello (200-500 MB) in `~/.cache/huggingface`.
Su Nobara con GPU NVIDIA puoi usare `--device cuda --compute-type float16` per andare molto piu veloce.

---

## Se non vuoi installare Whisper

Puoi comunque usare tutto il resto:

1. Trascrivi con lo strumento che preferisci (anche a mano).
2. Crea `build/<slug>/transcript.json` nel formato minimo:

```json
{
  "source": "media/voiceover/raw/voce.wav",
  "language": "it",
  "duration": 143.2,
  "segments": [
    {
      "id": 0, "start": 0.0, "end": 3.2, "text": "Ciao ragazzi",
      "words": [
        {"word": "Ciao", "start": 0.0, "end": 0.35, "probability": 1.0},
        {"word": "ragazzi", "start": 0.4, "end": 0.9, "probability": 1.0}
      ]
    }
  ]
}
```

3. Da li in poi `roughcut`, `render-audio`, `validate`, `placeholders`, `lua` funzionano identici.

---

## Dove finiscono i file

Niente cloud, niente cache esterna:

- modelli Whisper: `~/.cache/huggingface`
- segnaposto e render: `build/<slug>/`
- media originali: `media/` (meglio se su un disco esterno, sono grossi)

Backup minimo: `projects/` + `media/` + `build/<slug>/shotlist.json`. Il resto e rigenerabile.
