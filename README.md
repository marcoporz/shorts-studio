# shorts-studio

Pipeline **tutto gratis** per Shorts e video essay: OpenCode + DaVinci Resolve (free) + ffmpeg + Whisper locale.

L'AI ascolta il voiceover **oppure il tuo talking head** (italiano o inglese), toglie errori e pause,
progetta il montaggio, costruisce in Resolve una timeline di **segnaposto gia animati** con marker che
dicono cosa mettere in ogni slot. Se registri in video, **la tua faccia viene tagliata e montata
automaticamente** negli slot A-roll: non devi sostituirla. Tu sostituisci solo i media mancanti.

Gia fatto dallo script: **A-roll della faccia** se registri in video, **caption** statiche e
leggibili, **transizioni** automatiche sui punti di svolta, **SFX** e **BGM**. Le caption e le
transizioni stanno su tracce separate, quindi restano anche dopo la sostituzione dei segnaposto. `cross-dissolve`, animazioni di camera e mix fine restano
manuali (limiti dell'API free, spiegati in `WORKFLOW.md`).

Niente SaaS, niente abbonamenti, niente upload dei tuoi file su servizi esterni.

---

## Cosa serve

| Pezzo | Versione | Costo |
|---|---|---|
| OpenCode | V2 | gratis |
| Modello per codice/Lua | `opencode/deepseek-v4.1-flash-free` | $0 |
| Modello per guardare frame | `opencode/nemotron-3.5-super-vl-free` | $0 |
| DaVinci Resolve | free (21.x) | $0 |
| ffmpeg + ffprobe | 6.x o superiore | $0 |
| Python | 3.11–3.13 (3.13 consigliato) | $0 |
| Pillow | per i segnaposto | $0 |
| faster-whisper | installato dal setup, per la trascrizione | $0 |

> Resolve **free** supporta lo scripting solo dalla Console interna (`Workspace > Console`, linguaggio Lua).
> Python esterno, MCP e Scripts menu sono Studio-only da Resolve 21.1. Questo progetto usa solo la Console.

---

## Avvio rapido

```bash
cd ~/shorts-studio
./scripts/setup-macos.sh                  # una volta sola (su Nobara: setup-nobara.sh)
.venv/bin/python scripts/shorts.py doctor

# metti il voiceover in media/voiceover/raw/ e i materiali in media/clips|images|logos|screenshots
# se registri in video (talking head) va bene lo stesso: metti l'mp4/mov nella stessa cartella
.venv/bin/python scripts/shorts.py init fallout-3-vs-new-vegas --language auto
.venv/bin/python scripts/shorts.py scan
.venv/bin/python scripts/shorts.py transcribe fallout-3-vs-new-vegas --language auto
.venv/bin/python scripts/shorts.py roughcut fallout-3-vs-new-vegas
.venv/bin/python scripts/shorts.py render-audio fallout-3-vs-new-vegas --normalize
# se registri in video (talking head), usa questa al posto della precedente:
.venv/bin/python scripts/shorts.py render-audio fallout-3-vs-new-vegas --normalize --video
```

`--language auto` rileva la lingua; puoi forzare `it` o `en` (vale anche in `project.json` con
`"language": "it"`). Il resto della pipeline e identico per le due lingue. Se il file sorgente e un
video, `--video` produce `vo_clean.mp4` (faccia tagliata) oltre a `vo_clean.wav` per l'audio.

Poi apri OpenCode **dentro** questa cartella (così trova la skill e `AGENTS.md`):

```bash
cd ~/shorts-studio
opencode
```

e scrivi:

```text
@shorts-editor prepara il montaggio di fallout-3-vs-new-vegas
```

L'agente legge la trascrizione pulita, guarda l'indice dei media, scrive `projects/<slug>/shotlist.json`
con un suggerimento per ogni slot, valida, genera i segnaposto e lo script Lua. Se hai registrato in
video, decide anche **dove si vede la tua faccia** (`source: "face"`) e taglia quelle clip da solo.

Infine:

1. Apri Resolve, apri un progetto.
2. `Workspace > Console`, seleziona **Lua**.
3. Trascina dentro `build/<slug>/<slug>_build.lua` e premi Invio.
4. Vai in Edit: c'e la timeline con tutto.
5. Sostituisci solo i segnaposto (fase 8 di `WORKFLOW.md`). Le caption, le transizioni e le
   eventuali clip A-roll della tua faccia sono gia a posto.

Lo script non contiene percorsi assoluti: trova la cartella da `~/shorts-studio`. Se l'hai spostata,
scrivi prima in Console `SHORTS_ROOT = "/percorso/della/cartella"`.

---

## Vuoi vedere com'è fatto prima di registrare?

Ci sono due progetti di prova già pronti:

```text
projects/esempio-spacehey/     shotlist con 4 slot e soli suggerimenti "?"
projects/test-demo/            pipeline completa (voce finta, caption, 4 transizioni, SFX e BGM)
```

```bash
.venv/bin/python scripts/shorts.py validate esempio-spacehey
.venv/bin/python scripts/shorts.py placeholders esempio-spacehey
.venv/bin/python scripts/shorts.py lua esempio-spacehey
```

Genera segnaposto veri e uno script Lua valido. Serve a guardare il formato, non a essere esportato.
Per vedere caption e transizioni automatiche usa `test-demo` (`validate`, `placeholders --force`, `lua`).

---

## Script Lua pronti (`scripts/lua/`)

Oltre allo script generato per ogni progetto, ci sono tre utility da trascinare nella Console:

| File | Cosa fa |
|---|---|
| `00_check.lua` | Diagnostica: versione, progetto, timeline, tracce, marker, render formats. Non modifica nulla |
| `20_fusion_probe.lua` | Test sperimentale: verifica se la tua versione free accetta `AddFusionComp`/`ImportFusionComp` |
| `90_render_queue.lua` | Imposta 1080x1920 H.264 e aggiunge il job di render (modifica `OUT_DIR` in cima) |

Passano tutti `luac -p` e non hanno percorsi assoluti (tranne `OUT_DIR`, che è una scelta esplicita).

---

## Cartelle

```text
shorts-studio/
├── .opencode/skills/shorts-editor/   skill che insegna all'agente questo flusso
├── scripts/
│   ├── shorts.py                    CLI: scan, transcribe, roughcut, validate, placeholders, lua, qc
│   ├── lua/                         script Lua pronti per la Console di Resolve (vedi sotto)
│   ├── setup-macos.sh
│   └── setup-nobara.sh
├── media/
│   ├── clips/                       gameplay registrato da te
│   ├── images/                      foto, artwork, frame
│   ├── logos/                       loghi (canale, giochi)
│   ├── screenshots/                 screenshot di siti/app
│   ├── voiceover/raw/               il file che registri (wav/mp4)
│   ├── sfx/                         effetti con nomi fissi (vedi media/sfx/README.md)
│   └── bgm/                         musica di sottofondo
├── projects/<slug>/
│   ├── project.json
│   ├── script.md
│   ├── shotlist.json                la "regia": uno slot per ogni momento del video
│   ├── cuts.manual.json             tagli decisi da te o dall'AI
│   └── notes.md
└── build/<slug>/                    tutto quello che viene generato
    ├── transcript.json/.txt/.srt
    ├── cuts.json + review.md
    ├── vo_clean.wav + vo_clean.txt + words.json
    ├── vo_clean.mp4 (solo con --video: faccia gia tagliata)
    ├── aroll/                      clip della faccia tagliate per gli slot source=face
    ├── placeholders/                mp4/mov gia animati + card PNG
    ├── captions/                    card QTRLE alpha + captions.srt
    ├── transitions/                 overlay alpha (glitch/flash/dip/whip-pan)
    ├── audio/                       SFX con gain + bgm_mix.wav
    ├── <slug>_build.lua             script da incollare in Resolve
    └── qc/                          contact sheet per la revisione
```

---

## Comandi

```bash
.venv/bin/python scripts/shorts.py doctor                     # controlla ffmpeg, font, Pillow, Resolve
.venv/bin/python scripts/shorts.py init <slug>                # nuovo progetto
.venv/bin/python scripts/shorts.py scan                       # indicizza media/ (media/index.json)
.venv/bin/python scripts/shorts.py transcribe <slug>          # Whisper -> transcript (--language auto|it|en)
.venv/bin/python scripts/shorts.py roughcut <slug>            # silenzi/riempitivi/ripetizioni -> cuts.json
.venv/bin/python scripts/shorts.py render-audio <slug>        # taglia davvero -> vo_clean.wav + words.json (--video per la faccia)
.venv/bin/python scripts/shorts.py validate <slug>            # controlla lo shotlist
.venv/bin/python scripts/shorts.py placeholders <slug>        # segnaposto + caption + transizioni
.venv/bin/python scripts/shorts.py captions <slug>            # solo caption (overlay + SRT)
.venv/bin/python scripts/shorts.py lua <slug>                 # genera lo script per Resolve
.venv/bin/python scripts/shorts.py qc <slug> --video out.mp4  # contact sheet del video finale
```

Opzioni utili:

- `init --language it|en|auto` salva la lingua in `project.json`.
- `transcribe --language it|en|auto` forza la lingua (default: `project.json`, poi `auto`).
- `roughcut --aggressive` taglia anche "cioè", "tipo", "praticamente".
- `roughcut --keep-fillers` non tocca i riempitivi.
- `render-audio --normalize` porta la voce a -16 LUFS.
- `render-audio --video` taglia anche il video del talking head e prepara l'A-roll (1080x1920).
- `face_fit` nello shotlist: `crop` (default, riempie il verticale) o `fit` (letterbox).
- `placeholders --force` rigenera segnaposto, A-roll, caption e transizioni.
- `captions --force` rigenera solo le caption (utile se cambi `captions` nello shotlist).
- `qc --video` accetta qualsiasi export.

---

## Documenti

- **`WORKFLOW.md`** — il flusso completo, fase per fase, con i click in Resolve.
- **`SETUP.md`** — installazione macOS e Nobara Linux, Console di Resolve, font, codec.
- **`STYLE.md`** — preset visivi: anime anni 90, CRT, PS2, Frutiger Aero.
- **`AGENTS.md`** — istruzioni permanenti per OpenCode.
- **`media/sfx/README.md`** — nomi fissi degli effetti.
- **`presets/fusion/README.md`** — come creare una volta sola le animazioni da riusare dopo la sostituzione.

---

## Regola d'oro

L'AI **non scarica** clip o immagini da internet. Usa solo quello che c'e in `media/`.
Se per uno slot non hai il materiale, il suggerimento inizia con `?` e descrive cosa procurarti.
Così non prendi strike per copyright e sai sempre cosa manca.
