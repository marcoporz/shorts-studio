# AGENTS.md

Permanent instructions for OpenCode when working in this folder.

## What This Project Is

`shorts-studio` transforms a voiceover or a **talking head** (**Italian or English**) into an **editable DaVinci Resolve timeline**: transcription → rough cut → shotlist → animated placeholders + captions + transitions → Lua script for Console → timeline with markers, SFX, and BGM. User replaces placeholders with their media; captions, transitions, and A-roll face clips stay already edited.

Stack: OpenCode + DaVinci Resolve free + ffmpeg + Python (Pillow, Whisper optional).
No paid services, no uploads, no automatic media downloads.

## Hard Rules

1. **Don't invent paths.** Every `media/...` in shotlist must exist in `media/index.json`. If missing, use `"?precise description"`.
2. **Don't download** clips, images, music, or logos. User puts files in `media/`.
3. **Don't modify files in `media/`**: they're user originals.
4. **Clean time**: always use `build/<slug>/vo_clean.txt` (or `words.json`), never `transcript.txt` times after rough cut.
5. **The direction source of truth is `projects/<slug>/shotlist.json`.** `build/` is regenerable: don't edit it manually.
6. **Resolve free**: scripting only from internal Console, Lua language. Don't propose external Python, MCP, Scripts menu, or Studio-only automations.
7. **No impossible promises**: API doesn't create real transitions between clips, Edit keyframes, speed, or Fusion nodes. Automatic transitions are alpha overlays on V3 (`glitch`, `flash`, `dip-to-black`, `whip-pan`); `cross-dissolve`, camera animations, and Fusion nodes remain manual or via template. Zoom, opacity, and blend mode work though.
   With `animation_mode: fusion`, Fusion nodes are supported via `AddFusionComp` on timeline clip.
   With `native_transitions: true`, `cross-dissolve` and `dip-to-black` become native transitions.
8. **Captions mandatory** for Shorts: static, lower third, max 2 lines, generated from `words.json` on V4. Not a subtitle track: they're alpha clips + `captions.srt`.
9. **Talking head**: if source is video, use `render-audio --video`. Slots with `"source": "face"` must be `layer: "base"`, `kind: "clip"`, `animation: "static"`; they're cut in `build/<slug>/aroll/` and **must not be replaced**. Don't invent `vo_clean.mp4`: if missing, stop and ask to run `render-audio --video`.
   With `animation_mode: fusion`, face slots remain static; face animations go applied after as Fusion comp (templates in `presets/fusion/`).
10. Speak Italian with the user. Identifiers, JSON keys, and code in English.

## Commands (always use venv)

```bash
.venv/bin/python scripts/shorts.py doctor
.venv/bin/python scripts/shorts.py init <slug>
.venv/bin/python scripts/shorts.py init-from-video <slug> <video>
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

If `.venv` doesn't exist: `./scripts/setup-macos.sh` (macOS) or `./scripts/setup-nobara.sh` (Linux).

## Flow When User Asks for New Video

1. `doctor` and `scan`.
2. If no `build/<slug>/transcript.json`: `transcribe`.
3. `roughcut`, read `build/<slug>/review.md`, add manual cuts in `projects/<slug>/cuts.manual.json`, rerun `roughcut` + `render-audio --normalize`. If source is video (talking head), add `--video`.
4. Read `build/<slug>/vo_clean.txt` and `media/index.json`.
5. Write `projects/<slug>/shotlist.json` per `.opencode/skills/shorts-editor/`: captions active, automatic transitions only on turning points. If video exists, alternate `"source": "face"` and b-roll: face goes on `base`, never on `overlay`.
6. `validate` until no errors (warning on `cross-dissolve` is intentional).
7. `placeholders` (placeholders + captions + transitions), then `lua`.
8. Give user Console instructions, V1–V4/A1–A3 layout, and slot list with `?`.
9. When exporting: `qc --video ...`, read contact sheet with `read` and comment on captions too.

## Skill

Load `shorts-editor` skill for complete shotlist schema, API limits, and audio cues:

- `.opencode/skills/shorts-editor/SKILL.md`
- `.opencode/skills/shorts-editor/references/shotlist-schema.md`
- `.opencode/skills/shorts-editor/references/resolve-lua.md`
- `.opencode/skills/shorts-editor/references/audio-cues.md`

## Documents

- `WORKFLOW.md` — operational phases and Resolve clicks.
- `SETUP.md` — macOS/Nobara installation.
- `STYLE.md` — palettes and rules for anime90, CRT, PS2, Frutiger Aero.
- `README.md` — overview and commands.

## Pre-Delivery Checklist

- [ ] `validate` with no errors.
- [ ] Base coverage = voiceover duration (±0.25s), no holes.
- [ ] Every slot has `intent`, `suggest.primary`, `suggest.why`.
- [ ] Overlays stay inside a base slot.
- [ ] SFX on cuts, max 1 every 2–3s.
- [ ] Captions active and `build/<slug>/captions/manifest.json` not empty.
- [ ] If face slots: `build/<slug>/aroll/` has clips, markers say don't replace, `vo_clean.mp4` covers all times.
- [ ] Automatic transitions are among `glitch`/`flash`/`dip-to-black`/`whip-pan`.
- [ ] If `native_transitions: true`: `cross-dissolve` and `dip-to-black` are native (require handles).
- [ ] If `animation_mode: fusion`: animated placeholders are static, Fusion comp on V1 base clips.
- [ ] `?` listed in final message.
- [ ] Lua script passes `luac -p` (if available) and no absolute paths.
- [ ] Lua report (or mock) shows V3 transitions and V4 captions with expected counts.