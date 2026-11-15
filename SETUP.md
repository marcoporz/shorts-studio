# Setup

Two systems: **macOS** (now) and **Nobara Linux** (later). Project uses only relative paths, so it moves between computers without changes.

---

## macOS

### 1. Tools

```bash
xcode-select --install          # if never done
brew install ffmpeg python@3.13
```

Verify:

```bash
ffmpeg -version
/opt/homebrew/opt/python@3.13/bin/python3.13 --version
```

> If your ffmpeg lacks `drawtext` filter it's not a problem: placeholders are drawn with Pillow and animated with `zoompan`, present in all builds.

> **Python 3.15 and faster-whisper don't get along**: library `av` doesn't have wheels yet and install fails. Use Python 3.13 (or 3.12/3.11). Setup script does this automatically.

### 2. Project Python Environment

```bash
cd ~/shorts-studio
/opt/homebrew/opt/python@3.13/bin/python3.13 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install pillow
.venv/bin/pip install faster-whisper "av<17"
```

> `av` 19 removed a parameter faster-whisper 1.2 still uses. With `av<17` everything works; setup script does it already.

From now on always use `.venv/bin/python` (or activate with `source .venv/bin/activate`).

Easiest way is running the setup script, which picks right Python and installs everything:

```bash
./scripts/setup-macos.sh              # includes faster-whisper
./scripts/setup-macos.sh --no-whisper # if you don't want auto transcription
```

Check:

```bash
.venv/bin/python scripts/shorts.py doctor
```

### 3. DaVinci Resolve

Download **DaVinci Resolve free** from Blackmagic site and install. On first launch create an empty project (e.g. `Shorts`). Nothing else needed: Console scripting works on free too.

### 4. How to Use Console (Important)

1. Open Resolve with a project open.
2. Menu **Workspace > Console**.
3. Bottom dropdown: select **Lua**.
4. Drag `build/<slug>/<slug>_build.lua` into Console window.
5. Press **Enter**.

Console doesn't remember between sessions: every time you reopen Resolve you must drag script again. It's fine, 5-second operation.

Quick test:

```lua
print(resolve:GetVersion())
```

If it prints version, you're good.

Captions and automatic transitions need no extra software: Pillow draws cards and ffmpeg encodes QTRLE with alpha. Captions use `build/<slug>/words.json`, so generate after `render-audio`. In Resolve they arrive as video clips on V4 (not subtitle track): `captions.srt` in same folder is exportable copy.

### 5. Diagnostic Scripts (`scripts/lua/`)

Three standalone utilities, drag into Console like any script:

| File | When to Use |
|---|---|
| `00_check.lua` | Always, first time. Prints version, project, timeline, tracks, markers, render formats. Modifies nothing |
| `20_fusion_probe.lua` | Only if you want to know if your free version accepts `AddFusionComp`/`ImportFusionComp`. Use a test timeline: create and delete a comp on first V1 clip |
| `90_render_queue.lua` | To export: sets 1080x1920 H.264 and adds job. Open file and check `OUT_DIR` before running |

If `00_check.lua` prints nothing, Console language isn't **Lua** or no project is open.

### 6. Fonts (Recommended, Free)

Install from Google Fonts those needed for chosen style (see `STYLE.md`):

- **Anton**, **Bebas Neue** — big titles
- **VT323**, **Press Start 2P**, **Share Tech Mono** — CRT / PS2
- **Jost**, **Inter** — Frutiger Aero / clean
- **Noto Sans JP** — if using kanji

On macOS: double-click `.ttf` → *Install Font*.
On Nobara: copy to `~/.local/share/fonts/` and run `fc-cache -f -v`.

---

## Nobara Linux

Nobara is pre-configured for multimedia. Base packages:

```bash
sudo dnf install -y ffmpeg ffmpeg-free python3 python3-pip python3-virtualenv
```

If Resolve won't start, usually missing these libs:

```bash
sudo dnf install -y libxcrypt-compat mesa-libGLU alsa-lib fuse-libs
```

Install **DaVinci Resolve free** with Blackmagic `.run` installer:

```bash
chmod +x DaVinci_Resolve_*_Linux.run
./DaVinci_Resolve_*_Linux.run
```

Resolve ends up in `/opt/resolve/bin/resolve`. Console is always **Workspace > Console**, Lua.

Python Environment:

```bash
cd ~/shorts-studio
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install pillow faster-whisper "av<17"
.venv/bin/python scripts/shorts.py doctor
```

Linux-specific notes:

- NVIDIA proprietary drivers mandatory for Resolve. Nobara installs them via its tool.
- If on Wayland and Resolve misbehaves, start X11 session.
- Placeholder font path already handled: script finds DejaVu/Liberation.
- Lua scripts have no absolute paths: they search in `~/shorts-studio` or current directory. If you move/rename it, write in Console first `SHORTS_ROOT = "/path/to/folder"` then run script.

---

## Whisper: Which Model

| Model | Speed on M1/M2 | Italian/English Quality | When |
|---|---|---|---|
| `tiny` | very high | low | quick tests |
| `base` | high | medium | drafts |
| `small` | medium | good | **recommended default** |
| `medium` | slow | very good | if you have time |
| `large-v3` | very slow | excellent | only if needed |

```bash
.venv/bin/python scripts/shorts.py transcribe <slug> --model small --language auto
```

Language resolves as: explicit `--language` > `"language"` in `projects/<slug>/project.json` > `auto` (Whisper detection). For Italian voiceover use `--language it`, for English `--language en`; `auto` works for both without changing project.

If recording **video** (talking head), put mp4/mov in `media/voiceover/raw/`: Whisper uses audio track and rest of pipeline works same. Then run `render-audio <slug> --video` (plus `--normalize` if you want): besides cut voice prepares `vo_clean.mp4` and A-roll clips. Only needs ffmpeg with `libx264`, which `doctor` checks.

First run downloads model (200–500 MB) to `~/.cache/huggingface`. On Nobara with NVIDIA GPU use `--device cuda --compute-type float16` for much faster speed.

---

## If You Don't Want to Install Whisper

You can still use everything else:

1. Transcribe with your preferred tool (even manually).
2. Create `build/<slug>/transcript.json` in minimal format:

```json
{
  "source": "media/voiceover/raw/voice.wav",
  "language": "it",
  "duration": 143.2,
  "segments": [
    {
      "id": 0, "start": 0.0, "end": 3.2, "text": "Hello guys",
      "words": [
        {"word": "Hello", "start": 0.0, "end": 0.35, "probability": 1.0},
        {"word": "guys", "start": 0.4, "end": 0.9, "probability": 1.0}
      ]
    }
  ]
}
```

3. From there `roughcut`, `render-audio`, `validate`, `placeholders`, `lua` work identical.

---

## Where Files End Up

No cloud, no external cache:

- Whisper models: `~/.cache/huggingface`
- Placeholders & renders: `build/<slug>/`
- Original media: `media/` (better on external drive, they're large)

Minimal backup: `projects/` + `media/` + `build/<slug>/shotlist.json`. Rest is regenerable.