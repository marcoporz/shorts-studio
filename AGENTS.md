# AGENTS.md

Istruzioni permanenti per OpenCode quando lavora in questa cartella.

## Cos'è questo progetto

`shorts-studio` trasforma un voiceover o un **talking head** (**italiano o inglese**) in una
**timeline editabile in DaVinci Resolve free**: trascrizione → rough cut → shotlist → segnaposto
animati + caption + transizioni → script Lua per la Console → timeline con marker, SFX e BGM.
L'utente sostituisce i segnaposto con i suoi media; caption, transizioni e clip A-roll della faccia
restano gia montate.

Stack: OpenCode + DaVinci Resolve free + ffmpeg + Python (Pillow, Whisper opzionale).
Nessun servizio a pagamento, nessun upload, nessun download automatico di media.

## Regole ferree

1. **Non inventare percorsi.** Ogni `media/...` scritto nello shotlist deve esistere in
   `media/index.json`. Se manca, usa `"?descrizione precisa"`.
2. **Non scaricare** clip, immagini, musica o loghi. L'utente mette i file in `media/`.
3. **Non modificare i file in `media/`**: sono originali dell'utente.
4. **Tempo pulito**: usa sempre `build/<slug>/vo_clean.txt` (o `words.json`), mai i tempi di
   `transcript.txt`, dopo il rough cut.
5. **La fonte di verità della regia è `projects/<slug>/shotlist.json`.** `build/` è rigenerabile:
   non correggerlo a mano.
6. **Resolve free**: scripting solo dalla Console interna, linguaggio Lua. Non proporre Python
   esterno, MCP, menu Scripts o automazioni Studio-only.
7. **Niente promesse impossibili**: l'API non crea transizioni reali tra clip, keyframe Edit, velocità
   o nodi Fusion. Le transizioni automatiche sono overlay alpha su V3 (`glitch`, `flash`,
   `dip-to-black`, `whip-pan`); `cross-dissolve`, animazioni di camera e nodi Fusion restano manuali
   o via template. Zoom, opacity e blend mode invece sì.
8. **Caption obbligatorie** per gli Shorts: statiche, terzo inferiore, max 2 righe, generate da
   `words.json` e messe su V4. Non sono una traccia sottotitoli: sono clip alpha + `captions.srt`.
9. **Talking head**: se il sorgente e un video, usa `render-audio --video`. Gli slot con
   `"source": "face"` devono essere `layer: "base"`, `kind: "clip"`, `animation: "static"`; vengono
   tagliati in `build/<slug>/aroll/` e **non vanno sostituiti**. Non inventare `vo_clean.mp4`:
   se manca, fermati e chiedi di lanciare `render-audio --video`.
10. Parla italiano con l'utente. Identificatori, chiavi JSON e codice in inglese.

## Comandi (usa sempre il venv)

```bash
.venv/bin/python scripts/shorts.py doctor
.venv/bin/python scripts/shorts.py init <slug>
.venv/bin/python scripts/shorts.py scan
.venv/bin/python scripts/shorts.py transcribe <slug> [--model small] [--language auto|it|en]
.venv/bin/python scripts/shorts.py roughcut <slug> [--aggressive]
.venv/bin/python scripts/shorts.py render-audio <slug> [--normalize] [--video]
.venv/bin/python scripts/shorts.py validate <slug>
.venv/bin/python scripts/shorts.py placeholders <slug> [--force]
.venv/bin/python scripts/shorts.py captions <slug> [--force]
.venv/bin/python scripts/shorts.py lua <slug>
.venv/bin/python scripts/shorts.py qc <slug> [--video FILE]
```

Se `.venv` non esiste: `./scripts/setup-macos.sh` (macOS) o `./scripts/setup-nobara.sh` (Linux).

## Flusso quando l'utente chiede un nuovo video

1. `doctor` e `scan`.
2. Se non c'è `build/<slug>/transcript.json`: `transcribe`.
3. `roughcut`, leggi `build/<slug>/review.md`, aggiungi eventuali tagli in
   `projects/<slug>/cuts.manual.json`, rilancia `roughcut` + `render-audio --normalize`.
   Se il sorgente e un video (talking head), aggiungi `--video`.
4. Leggi `build/<slug>/vo_clean.txt` e `media/index.json`.
5. Scrivi `projects/<slug>/shotlist.json` secondo `.opencode/skills/shorts-editor/`:
   caption attive, transizioni automatiche solo sui punti di svolta. Se c'e il video, alterna
   slot `"source": "face"` e b-roll: la faccia va su `base`, mai su `overlay`.
6. `validate` finché non ci sono errori (l'avviso su `cross-dissolve` è voluto).
7. `placeholders` (segnaposto + caption + transizioni), poi `lua`.
8. Dai all'utente le istruzioni per la Console, il layout V1-V4/A1-A3 e l'elenco degli slot con `?`.
9. Quando esporta: `qc --video ...`, leggi la contact sheet con `read` e commenta anche le caption.

## Skill

Carica la skill `shorts-editor` per lo schema completo dello shotlist, i limiti dell'API e i cue audio:

- `.opencode/skills/shorts-editor/SKILL.md`
- `.opencode/skills/shorts-editor/references/shotlist-schema.md`
- `.opencode/skills/shorts-editor/references/resolve-lua.md`
- `.opencode/skills/shorts-editor/references/audio-cues.md`

## Documenti

- `WORKFLOW.md` — fasi operative e click in Resolve.
- `SETUP.md` — installazione macOS/Nobara.
- `STYLE.md` — palette e regole per anime90, CRT, PS2, Frutiger Aero.
- `README.md` — panoramica e comandi.

## Cosa controllare prima di consegnare

- [ ] `validate` senza errori.
- [ ] Copertura base = durata voiceover (±0.25s), nessun buco.
- [ ] Ogni slot ha `intent`, `suggest.primary`, `suggest.why`.
- [ ] Gli overlay stanno dentro uno slot base.
- [ ] Gli SFX sono sui tagli, max 1 ogni 2-3s.
- [ ] Le caption sono attive e `build/<slug>/captions/manifest.json` non è vuoto.
- [ ] Se ci sono slot faccia: `build/<slug>/aroll/` contiene le clip, i marker dicono di non
      sostituirle e `vo_clean.mp4` copre tutti i tempi.
- [ ] Le transizioni automatiche sono tra `glitch`/`flash`/`dip-to-black`/`whip-pan`.
- [ ] I `?` sono elencati nel messaggio finale.
- [ ] Lo script Lua passa `luac -p` (se disponibile) e non contiene percorsi assoluti.
- [ ] Il report Lua (o il mock) mostra V3 transizioni e V4 caption con i conteggi attesi.
