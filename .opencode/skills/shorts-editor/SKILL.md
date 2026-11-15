---
name: Shorts Editor
description: Use this skill when user wants to transform a voiceover or talking head (Italian or English) into a Short or video essay edited in DaVinci Resolve (free): transcription, rough cut, shotlist, animated placeholders, face A-roll, captions, transitions, timeline with markers, SFX and BGM. Activate for requests like "prepare my edit", "cut pauses", "create timeline", "add subtitles", "fix this short", "I also recorded my face".
---

# Shorts Editor

You're the editor who preps the work. Your output isn't a rendered video: it's an **editable DaVinci Resolve free timeline**, full of already-animated placeholders and markers explaining what goes where. User replaces placeholders with their clips. Everything else must already be decided. If user recorded on video, you also decide **where their face appears**: those slots get auto-cut and must not be replaced.

## Before Starting

1. Read `WORKFLOW.md`, `STYLE.md` and `references/shotlist-schema.md`.
2. Work **only** inside `~/shorts-studio`.
3. Use CLI commands. Don't rewrite `build/` manually: it's regenerable.
4. If project missing: `python scripts/shorts.py init <slug>`.

## Non-Negotiable Rules

- **Never invent paths.** Every `media/...` you write must exist in `media/index.json`. If material missing, write `"?precise description of what's needed"`.
- **Never download** clips, images, or music from internet. Not in workflow and creates copyright risk.
- **Every slot needs a `why`.** If you can't motivate the slot, don't add it.
- **Every slot must be specific.** "Fallout gameplay" isn't enough: "Vault 101 exit, door opening".
- **Full coverage.** `base` slots cover voiceover from 0 to duration, no holes or overlaps.
- **Don't touch original times.** Everything measured on `vo_clean.txt` (clean time).
- **Don't promise** MCP, external Python, or one-click automation: on Resolve free they don't exist.
- **Captions are mandatory** for Shorts: keep `captions.enabled: true` and verify `render-audio` produced `build/<slug>/words.json`. Static cards, readable, lower third; don't animate them.
- **Automatic transitions**: use `glitch`, `flash`, `dip-to-black`, `whip-pan`. They become alpha overlays on a dedicated track and **survive placeholder replacement**. `cross-dissolve` stays manual: free API doesn't create real transitions between clips.
- **Talking head**: if source is video, alternate `"source": "face"` and b-roll slots. Face slots are `layer: "base"`, `kind: "clip"`, `animation: "static"`; don't replace them because `placeholders` cuts them from `vo_clean.mp4` into `build/<slug>/aroll/`. Keep lower third free for captions. If `vo_clean.mp4` missing, don't improvise: ask for `render-audio --video`.
- If video is long, don't change visual every second: 1.5–3s is the right pace.
- Don't put a transition on every cut: pick only turning points (hook, chapters, revelation).

### Studio 21.1.1 Quality Mode (Optional)

If user has DaVinci Resolve Studio 21.1.1, you can enable quality mode in shotlist by adding these top-level fields (all optional, default to current `baked` behavior):

```json
"animation_mode": "fusion",
"native_transitions": true,
"transition_handle": 0.6,
"audio": { "voice_isolation": true, "voice_isolation_amount": 60 },
"bgm": { "duck": true, "duck_db": -9 }
```

**What changes for you (agent):**
- Set `animation_mode: "fusion"` and `native_transitions: true` for Studio 21.1.1 projects.
- `transition_handle` (default 0.6s) defines handles in placeholders for native transitions.
- `audio.voice_isolation` enables Voice Isolation on A1 (talking head).
- `bgm.duck` enables automatic BGM ducking under voice.

**What changes for user (what to say in final message):**
- **Fusion Animations**: animated placeholders are static; animation lives in a Fusion comp on timeline clip. After `Replace Selected Clip` (F11) animation **stays** and applies to real media. **Don't re-apply** zoom/pan.
- **Native Transitions**: `cross-dissolve` and `dip-to-black` are real Resolve transitions. Need handles (default 0.6s) in placeholders. `glitch`, `flash`, `whip-pan` remain V3 overlays. If handles insufficient, Lua falls back to overlay and warns.
- **BGM Ducking**: music automatically ducks under voice.
- **Voice Isolation**: enabled on A1 for talking head (reduces noise/reverb).
- **Micro-fade**: 5ms fade in/out on voice and SFX to prevent clicks.

**Validation Rules You Must Enforce:**
- `native_transitions` requires `animation_mode: "fusion"`.
- `transition_handle` between 0.2 and 1.5 seconds.
- `audio.voice_isolation_amount` between 0 and 100.
- `bgm.duck_db` negative between -24 and -3.
- `animation_mode` in `baked|fusion`.
- Existing projects without fields stay in `baked` (identical to today).
- If video is long, don't change visual every second: 1.5–3s is the right pace.
- Don't put a transition on every cut: choose only turning points (hook, chapters, revelation).

## Procedure

### 1. Check Status

```bash
python scripts/shorts.py doctor
python scripts/shorts.py scan
```

Read `media/index.json`: your only source of truth on materials. Contains duration, resolution, fps, and tags from filename.

### 2. Transcribe (if not already)

```bash
python scripts/shorts.py transcribe <slug> --model small --language auto
```

Default language is `auto` (Whisper detects). To force: `--language it` or `--language en`. You can also set it once in `projects/<slug>/project.json` with `"language": "it"` (or `en`); CLI uses that if you don't pass `--language`. Works for Italian and English: no separate project needed. If `build/<slug>/transcript.json` exists, don't redo it.

### 3. Rough Cut

```bash
python scripts/shorts.py roughcut <slug>
```

Read `build/<slug>/review.md`. Then decide if more needed:

- fluent but wrong sentences → add `drop` in `projects/<slug>/cuts.manual.json`;
- intentional pauses → add `keep`.

Rerun `roughcut` then:

```bash
python scripts/shorts.py render-audio <slug> --normalize
```

If recording is a **video** (talking head), check `media/index.json` (`has_video: true` on voice in `voiceover_raw`) and add `--video`:

```bash
python scripts/shorts.py render-audio <slug> --normalize --video
```

This produces `vo_clean.mp4` (cut face) and `vo_clean.wav` for A1. Without `--video` no face slots: write only b-roll.

### 4. Read Clean Voice

Open `build/<slug>/vo_clean.txt`. Contains segments with new times and text.
**Don't** use `transcript.txt` for shotlist: times are wrong after cuts.

If `vo_clean.txt` doesn't exist, stop and ask user to run `render-audio`.

### 5. Write Direction

Create `projects/<slug>/shotlist.json`. First read `project.json` for title and style. If user didn't specify style, pick based on content and tell them.

Minimal schema (details in `references/shotlist-schema.md`):

```json
{
  "project": "<slug>",
  "title": "...",
  "format": { "width": 1080, "height": 1920, "fps": 30 },
  "style": "ps2-crt",
  "animation_mode": "baked",
  "native_transitions": false,
  "transition_handle": 0.6,
  "audio": { "voice_isolation": false, "voice_isolation_amount": 60 },
  "voiceover": "build/<slug>/vo_clean.wav",
  "voiceover_duration": 58.4,
  "face_fit": "crop",
  "bgm": { "file": "media/bgm/...", "gain_db": -24, "duck_db": -9, "loop": true, "duck": false },
  "captions": {
    "enabled": true,
    "position": "lower",
    "max_words": 4,
    "max_chars": 32,
    "max_duration": 3.2,
    "font_size": 66,
    "uppercase": false,
    "background": 0.55
  },
  "slots": [
    {
      "id": "s01",
      "start": 0.0,
      "duration": 1.8,
      "layer": "base",
      "kind": "clip",
      "intent": "...",
      "suggest": { "primary": "media/clips/...", "alternatives": [], "why": "..." },
      "animation": "push-in-slow",
      "zoom": 1.0,
      "opacity": 100,
      "blend": "normal",
      "transition_in": { "type": "glitch", "duration": 0.4 },
      "sfx": [{ "file": "media/sfx/impact-1.wav", "at": 0.0, "gain_db": -8 }],
      "text": null
    }
  ]
}
```

How to build the sequence:

1. Split voiceover into **sense units**: a sentence or half-sentence, not a word.
2. For each unit pick **what must be seen**. If sentence is abstract ("and that's when everything changes"), choose image that makes it concrete.
3. If you have talking head, decide **where face returns**: hook, conclusions, personal opinions, passages where face adds something. One face block every 20–40s is enough; rest use b-roll. Face slots written like:

```json
{
  "id": "s02",
  "start": 12.4,
  "duration": 2.2,
  "layer": "base",
  "source": "face",
  "kind": "clip",
  "intent": "Talking head: I explain the key point looking at camera",
  "suggest": {
    "primary": "?your face, already cut from video",
    "alternatives": [],
    "why": "Passage is personal: face holds contact better than gameplay."
  },
  "animation": "static",
  "zoom": 1.0,
  "transition_in": { "type": "cut" },
  "sfx": [],
  "text": null
}
```

`source` absent = `broll`. Face slots must be `base` and `animation: "static"`.

4. Check index: got that material? If yes, use path. If no, `?description`.
5. Pick animation by style and media type:
   - moving gameplay → `static` or `push-in-slow`
   - screenshot → `pan-lr` / `pan-rl`
   - logo → `push-in-fast`
   - single image → `drift-up` or `push-in-slow`
6. Add SFX only on important cuts: hook, revelation, chapter change. Max 1 every 2–3s.
7. Transitions: pick 2–4 turning points. `glitch` for chapter change, `flash` for revelation, `dip-to-black` to close section, `whip-pan` for fast change. Don't use `cut` everywhere and don't use `cross-dissolve` if you want it automatic.
8. Captions: mandatory. Leave defaults (lower third, max 2 lines, static). Don't cover face or game UI: if slot is close-up, consider `position: "middle"` only for that project. No `uppercase` for Italian Shorts. On face slots, frame face in upper half and leave lower third free.
9. Overlay: logos and text on `layer: "overlay"`, always inside a base slot. Blend better with `opacity` (e.g. 85) and `blend` (`screen` for scanlines/glare, `add` for particles, `multiply` for shadows/textures).

### 6. Validate

```bash
python scripts/shorts.py validate <slug>
```

Repeat until no errors. Read warnings: holes, misplaced overlays, coverage different from voiceover duration.

### 7. Generate Placeholders

```bash
python scripts/shorts.py placeholders <slug>
```

Generates captions (`build/<slug>/captions/`, QTRLE alpha + `captions.srt`) and automatic transitions (`build/<slug>/transitions/`, alpha overlays). `source: "face"` slots become real A-roll clips in `build/<slug>/aroll/`, already cut from `vo_clean.mp4`: no card, no replacement. Captions need `words.json` from `render-audio`: if missing, `placeholders` warns and skips. If you changed shotlist after generating, use `--force`. Captions only: `python scripts/shorts.py captions <slug> --force`.

### 8. Generate Lua Script

```bash
python scripts/shorts.py lua <slug>
```

Then give user **exactly** this message, customized:

```text
Done. Edit prepared.

In DaVinci Resolve:
1. open a project (even empty)
2. Workspace > Console
3. select Lua at bottom
4. drag in build/<slug>/<slug>_build.lua
5. press Enter

At the end you'll find timeline <slug>_v1 in Edit page.
Each clip is an animated placeholder: click marker to read what to put.
To replace: select placeholder in Media Pool > right-click > Clip Operations >
Replace Selected Clip (or F11), choose your file.
A-ROLL/FACE slots are already cut and mounted: DO NOT replace them.

Tracks: V1 B-ROLL + A-roll, V2 OVERLAY, V3 TRANSITIONS, V4 CAPTIONS | A1 VOICE, A2 SFX, A3 BGM.
Captions already positioned and readable, with captions.srt as copy.
Transitions are overlays on V3: they stay after replacement.

Slots: N | A-roll: N | Duration: MM:SS | SFX: N | Captions: N | Transitions: N | "?" placeholders (to get): N
```

List also the 3–5 most important slots and what's missing.

### 9. Review

When user exports:

```bash
python scripts/shorts.py qc <slug> --video <file.mp4>
```

Read contact sheet with `read` tool (and image) and comment: framing, text, style consistency, empty or repetitive slots.

## What to Tell User, Always

- What you decided and why (3 lines, not an essay).
- Which slots lack material (`?`).
- That placeholder camera animations are a preview: after replacement they must be reapplied with Fusion templates (`presets/fusion/README.md`); static zoom/opacity/blend stay instead. Face A-roll slots are already real clips and static: any push-in applied manually.
- That automatic transitions are on V3 and **don't** need redoing after replacement; `cross-dissolve` and real clip transitions stay manual in Edit.
- That captions are alpha clips on V4 (not subtitle track): already readable and positioned, with `captions.srt` as exportable copy. To fix a word, regenerate from `words.json`, don't edit card manually.
- That SFX/BGM gain is already baked in `build/<slug>/audio/` files (single BGM clip, already looped and cut); ducking and fine balance remain manual in Fairlight.

## Reference Files

- `references/shotlist-schema.md` — complete schema, examples, common errors
- `references/resolve-lua.md` — what Lua script does, free API limits, debug
- `references/audio-cues.md` — SFX names, volumes, ducking
- `../../WORKFLOW.md` — complete operational flow
- `../../STYLE.md` — palettes, fonts, animations by style

## Common Mistakes to Avoid

| Mistake | Why Serious |
|---|---|
| Using `transcript.txt` times | after cuts everything shifts |
| Filling `suggest.primary` with invented file | Resolve imports non-existent file and script stops |
| 40 slots of 0.8s in a 60s video | frantic pace, user can't replace them |
| Generic `why` | user doesn't know why you picked that clip |
| Transition on every cut | video feels like template, loses pace |
| Using `cross-dissolve` thinking it's automatic | stays manual: free API doesn't create real transitions |
| Forgetting captions | for Shorts they're mandatory: lose half audience |
| Animating captions word-by-word | user wants static, readable, non-invasive |
| Face slot on `overlay` | face is a base: must cover voiceover on V1 |
| Asking to replace A-roll | already cut from `vo_clean.mp4`: replacing breaks edit |
| Writing face slot without `vo_clean.mp4` | `placeholders` stops: first `render-audio --video` |
| Promising "I do it all" | media replacement is manual by choice |

## Pre-Delivery Checklist

- [ ] `validate` with no errors.
- [ ] `base` slots cover voiceover 0 to end, no holes or overlaps.
- [ ] Every slot has `intent`, `suggest.primary`, `suggest.why` specific.
- [ ] Overlays inside a base slot; `opacity`/`blend` only if really needed.
- [ ] SFX on important cuts, max 1 every 2–3 seconds.
- [ ] `captions.enabled` and `words.json` present: captions generated.
- [ ] If talking head: face slots are `base`/`static`, `aroll/` has clips, `vo_clean.mp4` covers all times.
- [ ] Automatic transitions are among `glitch`/`flash`/`dip-to-black`/`whip-pan`; `cross-dissolve` only as manual note.
- [ ] Voiceover language correct (`project.json` or `--language`).
- [ ] `?` listed in final message.
- [ ] Lua script passes `luac -p` and no absolute paths.
- [ ] Mock or Lua report shows V3 transitions and V4 captions with expected counts.