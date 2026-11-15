# shorts-studio — AI Video Editing Pipeline for DaVinci Resolve

**AI-powered video editing** for Shorts & video essays: OpenCode + DaVinci Resolve (Free/Studio 21.1.1) + ffmpeg + Whisper local.

Transform voiceover or talking-head footage (Italian/English) into a **fully editable DaVinci Resolve timeline** with animated placeholders, captions, transitions, SFX, BGM — all via Lua Console script. You replace placeholders with your media; the edit stays.

![GitHub Repo stars](https://img.shields.io/github/stars/marcoporz/shorts-studio?style=social)
![GitHub license](https://img.shields.io/github/license/marcoporz/shorts-studio)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![DaVinci Resolve](https://img.shields.io/badge/DaVinci%20Resolve-Free%20%7C%20Studio%2021.1.1-orange)
![No cloud](https://img.shields.io/badge/No%20cloud-%E2%9C%85-brightgreen)

**Keywords:** AI video editing, AI editing, video automation, DaVinci Resolve scripting, Shorts creator, talking-head editor, local-first, Whisper transcription, Lua scripting

---

The AI listens to your voiceover **or your talking head** (Italian or English), removes errors and pauses, plans the edit, builds a timeline in Resolve with **animated placeholders and markers** explaining what goes in each slot. If you record on video, **your face is automatically cut and placed** in A-roll slots: you don't replace it. You only replace the missing media.

Already done by the script: **A-roll face** if you record on video, **static captions** (readable, lower third), **transitions** on key moments, **SFX** and **BGM**. Captions and transitions stay on separate tracks, so they survive placeholder replacement. `cross-dissolve`, camera animations, and fine mix remain manual (free API limits, explained in `WORKFLOW.md`).

No SaaS, no subscriptions, no uploads of your files to external services.

---

## Requirements

| Component | Version | Cost |
|---|---|---|
| OpenCode | V2 | free |
| Code/Lua model | `opencode/deepseek-v4.1-flash-free` | $0 |
| Frame viewing model | `opencode/nemotron-3.5-super-vl-free` | $0 |
| DaVinci Resolve | free (21.x) | $0 |
| ffmpeg + ffprobe | 6.x+ | $0 |
| Python | 3.11–3.13 (3.13 recommended) | $0 |
| Pillow | for placeholders | $0 |
| faster-whisper | installed by setup, for transcription | $0 |

> Resolve **free** only supports scripting from the internal Console (`Workspace > Console`, Lua language).
> External Python, MCP, and Scripts menu are Studio-only from Resolve 21.1. This project uses only the Console.

---

## Quick Start

```bash
cd ~/shorts-studio
./scripts/setup-macos.sh                  # one-time (on Nobara: setup-nobara.sh)
.venv/bin/python scripts/shorts.py doctor

# put voiceover in media/voiceover/raw/ and assets in media/clips|images|logos|screenshots
# if you record on video (talking head), put mp4/mov in the same folder
.venv/bin/python scripts/shorts.py init my-video --language auto
.venv/bin/python scripts/shorts.py scan
.venv/bin/python scripts/shorts.py transcribe my-video --language auto
.venv/bin/python scripts/shorts.py roughcut my-video
.venv/bin/python scripts/shorts.py render-audio my-video --normalize
# if recording on video (talking head), use this instead:
.venv/bin/python scripts/shorts.py render-audio my-video --normalize --video
```

`--language auto` detects language; force with `it` or `en` (also works via `project.json` with `"language": "it"`). Pipeline is identical for both languages. If source is video, `--video` produces `vo_clean.mp4` (face cut) plus `vo_clean.wav` for audio.

Then open OpenCode **inside** this folder (so it finds the skill and `AGENTS.md`):

```bash
cd ~/shorts-studio
opencode
```

And write:

```text
@shorts-editor prepare the edit for my-video
```

The agent reads the clean transcript, checks the media index, writes `projects/<slug>/shotlist.json` with a suggestion for each slot, validates, generates placeholders and the Lua script. If you recorded on video, it also decides **where your face appears** (`source: "face"`) and cuts those clips automatically.

Finally:

1. Open Resolve, open a project.
2. `Workspace > Console`, select **Lua** at bottom.
3. Drag `build/<slug>/<slug>_build.lua` into Console and press Enter.
4. In Edit page: timeline `<slug>_v1` is ready.
5. Replace only placeholders (see `WORKFLOW.md` phase 8). Captions, transitions, and A-roll face clips are already in place.

---

## Alternative: Start from an Already-Edited Video

If you already have a video file **without pauses or errors** (already cut in another editor), skip transcribe/roughcut/render-audio:

```bash
.venv/bin/python scripts/shorts.py init-from-video my-video /path/to/edited_video.mp4
```

This extracts audio (`vo_clean.wav`), copies the video (`vo_clean.mp4` for A-roll), measures duration, and creates the project ready for shotlist writing. Then continue from `scan` → `validate` → `placeholders` → `lua`.

---

## Commands

```bash
.venv/bin/python scripts/shorts.py doctor                     # check dependencies
.venv/bin/python scripts/shorts.py init <slug>                 # new project (from voiceover)
.venv/bin/python scripts/shorts.py init-from-video <slug> <video>  # new project from pre-edited video
.venv/bin/python scripts/shorts.py scan                        # index media/
.venv/bin/python scripts/shorts.py transcribe <slug>           # Whisper -> transcript (--language auto|it|en)
.venv/bin/python scripts/shorts.py roughcut <slug>             # silence/fillers/repetitions -> cuts.json
.venv/bin/python scripts/shorts.py render-audio <slug>         # apply cuts -> vo_clean.wav + words.json (--video for talking head)
.venv/bin/python scripts/shorts.py validate <slug>             # validate shotlist
.venv/bin/python scripts/shorts.py placeholders <slug>         # placeholders + captions + transitions
.venv/bin/python scripts/shorts.py captions <slug>             # captions only (overlay + SRT)
.venv/bin/python scripts/shorts.py lua <slug>                  # generate Lua script for Resolve Console
.venv/bin/python scripts/shorts.py qc <slug> [--video FILE]    # contact sheet from exported video
```

Useful options:

- `init --language it|en|auto` saves language in `project.json`.
- `transcribe --language it|en|auto` forces language (default: `project.json`, then `auto`).
- `roughcut --aggressive` also cuts "actually", "like", "basically"...
- `roughcut --keep-fillers` keeps fillers.
- `render-audio --normalize` normalizes voice to -16 LUFS.
- `render-audio --video` cuts video too (talking head) and prepares A-roll (1080x1920).
- `face_fit` in shotlist: `crop` (default, fills vertical) or `fit` (letterbox).
- `placeholders --force` regenerates placeholders, A-roll, captions, transitions.
- `captions --force` regenerates only captions (useful after changing `captions` in shotlist).
- `qc --video` accepts any export.

---

## Project Structure

```
shorts-studio/
├── .opencode/skills/shorts-editor/   # skill teaching the agent this workflow
├── scripts/
│   ├── shorts.py                     # CLI: scan, transcribe, roughcut, validate, placeholders, lua, qc
│   ├── lua/                          # Lua scripts for Resolve Console
│   ├── setup-macos.sh
│   └── setup-nobara.sh
├── media/
│   ├── clips/                        # your recorded gameplay
│   ├── images/                       # photos, artwork, frames
│   ├── logos/                        # channel logos, game logos
│   ├── screenshots/                  # website/app screenshots
│   ├── voiceover/raw/                # your recording (wav/mp4)
│   ├── sfx/                          # sound effects (fixed names, see media/sfx/README.md)
│   └── bgm/                          # background music
├── projects/<slug>/
│   ├── project.json                  # meta: slug, title, language, style
│   ├── script.md                     # your script/outline
│   ├── shotlist.json                 # the "direction": one slot per moment
│   ├── cuts.manual.json              # manual corrections to rough cut
│   └── notes.md
└── build/<slug>/                     # all generated (regenerable, don't edit manually)
    ├── transcript.json/.txt/.srt
    ├── cuts.json + review.md
    ├── vo_clean.wav + vo_clean.txt + words.json
    ├── vo_clean.mp4 (with --video: face already cut)
    ├── aroll/                        # face clips cut for source=face slots
    ├── placeholders/                 # animated mp4/mov + card PNGs
    ├── captions/                     # QTRLE alpha cards + captions.srt
    ├── transitions/                  # alpha overlays (glitch/flash/dip/whip-pan)
    ├── audio/                        # SFX with gain + bgm_mix.wav
    ├── <slug>_build.lua              # script to paste in Resolve Console
    └── qc/                           # contact sheet for review
```

---

## Studio 21.1.1 Quality Mode (Optional)

If you have **DaVinci Resolve Studio 21.1.1**, enable quality mode in shotlist:

```json
"animation_mode": "fusion",
"native_transitions": true,
"transition_handle": 0.6,
"audio": { "voice_isolation": true, "voice_isolation_amount": 60 },
"bgm": { "duck": true, "duck_db": -9 }
```

What changes:
- **Fusion Animations**: zoom/pan live in a Fusion comp on the timeline clip. After `Replace Selected Clip` (F11) the animation **stays** and applies to your real media.
- **Native Transitions**: `cross-dissolve` and `dip-to-black` become real Resolve transitions (not overlays). Need handles (default 0.6s) in placeholders.
- **BGM Ducking**: music automatically ducks under voice (`sidechaincompress`).
- **Voice Isolation**: enabled on A1 for talking head (reduces noise/reverb).
- **Micro-fade**: 5ms fade in/out on voice and SFX to prevent clicks.

Projects without these fields stay in `baked` mode (current behavior).

---

## Documentation

- **`WORKFLOW.md`** — complete operational flow, phase by phase, with Resolve clicks.
- **`SETUP.md`** — macOS and Nobara Linux installation, Resolve Console, fonts, codecs.
- **`STYLE.md`** — visual presets: 90s anime, CRT, PS2, Frutiger Aero.
- **`AGENTS.md`** — permanent instructions for OpenCode.
- **`media/sfx/README.md`** — fixed SFX names.
- **`presets/fusion/README.md`** — how to create reusable Fusion animation templates.

---

## Golden Rule

The AI **does not download** clips or images from the internet. It only uses what's in `media/`.
If you don't have the material for a slot, the suggestion starts with `?` describing what to get.
No copyright strikes, and you always know what's missing.

---

## License

MIT — free to use, modify, distribute.