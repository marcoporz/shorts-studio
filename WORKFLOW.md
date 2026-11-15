# Complete Workflow

This is the operational flow. Phases 2–7 are prepared by AI/CLI (OpenCode). Phases 8–11 you do in Resolve: replace slots, refine audio/color, export. Phase 12 (QC) goes back to AI.

```text
  voiceover or video with face + media
         |
         v
  [1] scan          media/index.json
         |
         v
  [2] transcribe    transcript.json / .txt / .srt
         |
         v
  [3] roughcut      cuts.json + review.md      (silence, fillers, repetitions)
         |
         v
  [4] render-audio  vo_clean.wav + vo_clean.txt + words.json
         |          (--video: vo_clean.mp4 with face cut)
         v
  [5] shotlist      projects/<slug>/shotlist.json    <-- the direction, slot by slot
         |
         v
  [6] validate + placeholders                        <-- placeholders + A-roll + captions + transitions
         |
         v
  [7] lua           build/<slug>/<slug>_build.lua
         |
         v
  [8] RESOLVE       timeline + markers + captions + transitions + SFX + BGM
         |
         v
  [9] you           replace only placeholders, refine, export
```

---

## Phase 1 — Materials

### Folders

| Folder | What to put | Format |
|---|---|---|
| `media/clips/<game>/` | your recorded gameplay | mp4/mov, 1080p+ |
| `media/images/` | artwork, photos, extracted frames | png/jpg |
| `media/logos/` | channel logos, game logos | png with alpha |
| `media/screenshots/` | website/app screenshots | png |
| `media/voiceover/raw/` | voice recording, also on video (talking head) | wav 48kHz (best) or mp4/mov |
| `media/sfx/` | sound effects with fixed names | wav 48kHz |
| `media/bgm/` | background music | mp3/wav |

### File Naming

The filename is information the AI uses to understand what you're providing:

```text
fallout3-vault101-exit.mp4
fallout3-downtown-dc-panoramic.mp4
newvegas-dialogue-sunny.mp4
spacehey-profile-2005.png
spacehey-music-player.png
channel-logo.png
logo-newvegas.png
```

Rule: `<project>-<content>-<detail>`. No `IMG_4821.MOV`.

### Copyright

The AI downloads nothing. You can use:

- your recorded gameplay;
- your own screenshots;
- official trailers and press kits (with judgment);
- assets with compatible license (Wikimedia, CC0), citing source.

Don't use other youtubers' clips, third-party edits, unlicensed music.
The `suggest` field in shotlist always tells you what's missing: if it starts with `?`, it's not in your library.

---

## Phase 2 — Transcription

```bash
.venv/bin/python scripts/shorts.py transcribe <slug> --language auto
```

Works with **Italian and English** voiceover. `--language auto` (default) lets Whisper detect; force with `--language it` or `--language en`, or set `"language": "it"` in `projects/<slug>/project.json` once; CLI uses that value if you don't pass `--language`. Works for both languages without separate projects.

Output:

- `build/<slug>/transcript.txt` — readable, with timecodes
- `build/<slug>/transcript.json` — words with centisecond timing
- `build/<slug>/transcript.srt` — subtitles

For noisy audio, use `--model medium`. For Italian/English `small` is good; for game names and technical terms, `medium` reduces errors.

The AI reads the `.txt`, not the full `.json`: the `.txt` is compact and sufficient to understand content.

---

## Phase 3 — Rough Cut

```bash
.venv/bin/python scripts/shorts.py roughcut <slug>
```

What it removes automatically:

- silences longer than `--max-gap` (default 0.45s), keeping `--pad` (0.10s) breathing room;
- safe fillers (`ehm`, `uhm`, `mmm`, `boh`...), only if isolated;
- immediate repetitions (`this this`, stutters).

What it **doesn't** remove automatically:

- wrong but fluent sentences;
- false starts ("I meant... no wait");
- "actually", "like", "basically" (unless `--aggressive`).

For those, manual review is needed. Output: `build/<slug>/review.md` with a table of every cut and context.

### Manual or AI Correction

`projects/<slug>/cuts.manual.json`:

```json
{
  "drop": [
    {"start": 42.10, "end": 44.80, "reason": "wrong sentence, restarts"}
  ],
  "keep": [
    {"start": 61.00, "end": 63.50, "reason": "intentional pause, don't cut"}
  ]
}
```

Then:

```bash
.venv/bin/python scripts/shorts.py roughcut <slug>
.venv/bin/python scripts/shorts.py render-audio <slug> --normalize
```

`keep` wins over `drop`: if an auto-cut falls inside a `keep`, it's cancelled.

---

## Phase 4 — Clean Audio

```bash
.venv/bin/python scripts/shorts.py render-audio <slug> --normalize
```

Output:

- `vo_clean.wav` — cut voice, 48kHz stereo
- `vo_clean.txt` — same transcript but with **new times**, used for shotlist
- `words.json` — each word with new time
- `timemap.json` — original → clean time mapping

If you record on video (talking head), add `--video`:

```bash
.venv/bin/python scripts/shorts.py render-audio <slug> --normalize --video
```

With `--video` you also get:

- `vo_clean.mp4` — your face already cut, same cuts as audio (original resolution; A-roll adapted to 1080x1920);
- `vo_clean_norm.mp4` — same normalized to -16 LUFS (if `--normalize`);
- `vo_clean.wav` / `vo_clean_norm.wav` — audio for A1 track.

Slots with `"source": "face"` are cut from `vo_clean.mp4` into `build/<slug>/aroll/` and placed directly on V1: **they are not placeholders and must not be replaced**. The rest of slots remain b-roll to replace. If video is horizontal, default `face_fit: "crop"` fills vertical cropping sides; use `"fit"` for letterbox.

> From here on **all times are in clean time**, i.e., final video time. Never go back to original file times except to fix cuts.

---

## Phase 5 — The Direction (Shotlist)

Here the AI does the real work. Reads `build/<slug>/vo_clean.txt` and `media/index.json`, writes `projects/<slug>/shotlist.json`: a sequence of **slots** covering the whole voiceover.

A slot = a visual block. Not a frame, not a word: a shot.

### Editing Rules the AI Must Follow

- **Hook**: first slot 1–2s, shows your strongest material.
- **Pace**: visual change every **1.5–3s**. Never more than 4s on same image, unless intentional slow moment.
- **Coverage**: `base` slots must cover voiceover from start to end, no holes.
- **Overlay**: logos and text go on `layer: "overlay"`, inside a base slot duration.
- **Specificity**: suggestion must be specific ("Vault 101 door opening", not "Fallout gameplay").
- **Motivation**: every slot has a `why`. If you can't motivate it, the slot doesn't belong.
- **Captions**: mandatory, static, lower third, max 2 lines. Don't cover face or important game UI. No word-by-word or bouncing: user wants readable.
- **Transitions**: pick 2–4 turning points and use `glitch`, `flash`, `dip-to-black`, `whip-pan`. They become overlays on V3 and survive placeholder replacement. `cross-dissolve` is manual.
- **Talking head**: if you recorded on video, alternate face and b-roll. Use `"source": "face"` for slots where face appears (hook, conclusions, personal opinions, passages where face adds something) and leave rest as b-roll. Face slots are `layer: "base"`, `kind: "clip"`, `animation: "static"`, duration 1.5–4s. Don't put them on `overlay` and don't ask for replacement: clip is already cut from `vo_clean.mp4`. Keep lower third of face free: captions go there.

### Format

```json
{
  "project": "fallout-3-vs-new-vegas",
  "title": "Why FALLOUT 3 is HATED and NEW VEGAS LOVED?",
  "format": { "width": 1080, "height": 1920, "fps": 30 },
  "style": "ps2-crt",
  "voiceover": "build/fallout-3-vs-new-vegas/vo_clean.wav",
  "voiceover_duration": 58.4,
  "face_fit": "crop",
  "bgm": {
    "file": "media/bgm/ps2-menu.mp3",
    "gain_db": -24,
    "loop": true
  },
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
      "intent": "Fallout 3 gameplay: exiting Vault 101, door opening",
      "suggest": {
        "primary": "media/clips/fallout3/vault101-exit.mp4",
        "alternatives": ["media/screenshots/fallout3/vault101.png"],
        "why": "The phrase talks about 'where it all began': need the most recognizable moment."
      },
      "animation": "push-in-slow",
      "zoom": 1.0,
      "opacity": 100,
      "blend": "normal",
      "transition_in": { "type": "cut" },
      "sfx": [
        { "file": "media/sfx/impact-1.wav", "at": 0.0, "gain_db": -8 }
      ],
      "text": null
    }
  ]
}
```

### Fields

| Field | Required | Notes |
|---|---|---|
| `id` | yes | `s01`, `s02`... unique |
| `start` / `duration` | yes | seconds, clean time |
| `layer` | yes | `base` (V1) or `overlay` (V2) |
| `source` | no | `broll` (default) or `face` (talking head already cut) |
| `kind` | yes | `clip`, `image`, `logo`, `screenshot`, `text`, `ui` |
| `intent` | yes | ≥ 8 chars, specific |
| `suggest.primary` | yes | existing path **or** `?description` |
| `suggest.alternatives` | array | no | same rule |
| `suggest.why` | yes | ≥ 15 chars, explains choice |
| `animation` | enum | yes | see below |
| `zoom` | number | no | 1.0 = none. Static transform (`ZoomX`/`ZoomY`) |
| `opacity` | number | no | 0–100, default 100. Useful for overlay |
| `blend` | enum | no | `normal`, `add`, `multiply`, `screen`, `overlay` |
| `transition_in` | object | no | `{ "type": "...", "duration": 0.3 }` |
| `sfx` | array | no | `file`, `at`, `gain_db` |
| `text` | string/null | only `kind: text` | text to display |

### Enumerations

**layer**

- `base` → V1, covers voiceover
- `overlay` → V2, over a base, with alpha

**source**

- `broll` (default) → normal placeholder to replace
- `face` → talking head already recorded: `placeholders` cuts `build/<slug>/vo_clean.mp4` into `build/<slug>/aroll/<id>_face.mp4` and puts on V1. Requires `layer: "base"`, `kind: "clip"` and `animation: "static"`; clip must not be replaced. `suggest` still required for documentation, but suggested file isn't used: write `"?your face, already cut from video"` and explain in `why` why face appears here.

**face_fit** (top-level, talking head only)

| value | effect | when |
|---|---|---|
| `crop` | fills 1080x1920 cropping sides | default; horizontal video with centered face |
| `fit` | letterbox, no cropping | face or text you can't crop, already vertical with margins |

If face isn't centered, use `crop` and reposition in Resolve with Transform: A-roll file is still generated at 1080x1920.

Tracks V3 `TRANSITIONS` and V4 `CAPTIONS` are added by Lua script only if there are automatic transitions or captions. They are not slots: don't put them in shotlist.

**kind**

| value | color | meaning |
|---|---|---|
| `clip` | blue | moving video |
| `image` | green | static image |
| `logo` | orange | logo with alpha |
| `screenshot` | purple | website, app, UI |
| `text` | yellow | title card |
| `ui` | pink | graphic element/HUD |

**animation**

| value | effect | when |
|---|---|---|
| `static` | still | gameplay already dynamic |
| `push-in-slow` | zoom 1.0 → 1.16 | images, important moments |
| `pull-out-slow` | zoom 1.16 → 1.0 | closing a concept |
| `push-in-fast` | fast zoom at slot start | logo, reveal |
| `pan-lr` | pan left → right | wide screenshots |
| `pan-rl` | pan right → left | screenshots, alternative |
| `drift-up` | slight upward movement | vertical images |

**blend**

| value | effect | use |
|---|---|---|
| `normal` | normal | default |
| `screen` | lightens | scanlines, light leaks, light logos |
| `add` | adds | glows, particles |
| `multiply` | multiplies | shadows, dark textures |
| `overlay` | contrast | grain, textures |

Applied as `CompositeMode` on clip. If blend not needed, leave `normal`.

**transition_in.type**

`cut`, `cross-dissolve`, `dip-to-black`, `glitch`, `whip-pan`, `flash`

| type | automatic | native* | effect |
|---|---|---|---|
| `cut` | yes | no | hard cut |
| `glitch` | yes | no | RGB/scanline bands for 0.2–0.8s on cut |
| `flash` | yes | no | white flash |
| `dip-to-black` | yes | **yes** | fade to black and back (native if `native_transitions: true`) |
| `whip-pan` | yes | no | horizontal motion streaks |
| `cross-dissolve` | **no** | **yes** | real dissolve between clips (native if `native_transitions: true`) |

* `native` = real Resolve transition (not overlay). Requires `native_transitions: true` + `animation_mode: fusion` + handles in placeholders (`transition_handle`). If handles insufficient, falls back to overlay with warning.

**sfx**

```json
{ "file": "media/sfx/whoosh-2.wav", "at": 0.4, "gain_db": -10 }
```

- `at` is relative to slot start (seconds)
- must be within slot duration
- `gain_db` optional, default 0

---

## Example Talking Head (2 slots)

```json
{
  "project": "my-face",
  "title": "I Tried This for 30 Days...",
  "format": { "width": 1080, "height": 1920, "fps": 30 },
  "style": "clean",
  "voiceover": "build/my-face/vo_clean.wav",
  "voiceover_duration": 4.8,
  "face_fit": "crop",
  "bgm": null,
  "captions": { "enabled": true, "position": "lower" },
  "slots": [
    {
      "id": "s01",
      "start": 0.0,
      "duration": 2.6,
      "layer": "base",
      "source": "face",
      "kind": "clip",
      "intent": "Talking head: hook, looking at camera stating video promise",
      "suggest": {
        "primary": "?your face, already cut from video",
        "alternatives": [],
        "why": "Personal hook works if viewer sees face and hears tone."
      },
      "animation": "static",
      "zoom": 1.0,
      "transition_in": { "type": "cut" },
      "sfx": [],
      "text": null
    },
    {
      "id": "s02",
      "start": 2.6,
      "duration": 2.2,
      "layer": "base",
      "kind": "clip",
      "intent": "B-roll: the result I'm talking about, from my footage",
      "suggest": {
        "primary": "?your clip of the result",
        "alternatives": [],
        "why": "When the concrete data arrives, leave face and show proof."
      },
      "animation": "static",
      "zoom": 1.05,
      "transition_in": { "type": "dip-to-black", "duration": 0.4 },
      "sfx": [],
      "text": null
    }
  ]
}
```

Before this shotlist, you need `render-audio --video` and `vo_clean.mp4`. `placeholders` creates `build/my-face/aroll/s01_face.mp4`; slot s02 remains a placeholder to replace.

---

## Phase 6 — Validation and Placeholders

```bash
.venv/bin/python scripts/shorts.py validate <slug>
```

Checks: missing fields, missing files, overlaps, holes, invalid animations, SFX outside slots, voiceover coverage, caption config, transition types. For talking head also checks `source`, `face_fit`, that face slots are `base`, and that `build/<slug>/vo_clean.mp4` exists and covers all times. If errors **don't** generate placeholders. Warning on `cross-dissolve` is intentional: that transition stays manual.

```bash
.venv/bin/python scripts/shorts.py placeholders <slug>
```

Generates for each slot:

- a 1350x2400 card PNG with ID, type, intent, suggestion, reason, animation, SFX;
- a 1080x1920 MP4 with animation baked in (zoom/pan);
- for overlays a MOV with alpha (ProRes 4444).

For `source: "face"` slots no card: cuts `build/<slug>/vo_clean.mp4` into `build/<slug>/aroll/<id>_face.mp4` at 1080x1920, puts in manifest as base. These clips **must not be replaced**. If `vo_clean.mp4` missing, `placeholders` stops and tells you to run `render-audio --video`.

Also generates:

- `build/<slug>/captions/` — QTRLE alpha cards (`c001.mov`...), `manifest.json`, `captions.srt`;
- `build/<slug>/transitions/` — alpha overlays for `glitch`, `flash`, `dip-to-black`, `whip-pan`.

Captions require `build/<slug>/words.json`: if missing, `placeholders` warns and skips. Regenerate captions only with `shorts.py captions <slug> --force`. Only captions: `python scripts/shorts.py captions <slug> --force`.

Placeholders last **exactly** the slot duration. This matters for replacement.

---

## Phase 7 — Build Timeline in Resolve

```bash
.venv/bin/python scripts/shorts.py lua <slug>
```

Generates `build/<slug>/<slug>_build.lua`.

In Resolve:

1. Open a project (even empty).
2. **Workspace > Console**.
3. Select **Lua** in bottom dropdown.
4. Drag the `.lua` file into Console.
5. Press Enter.

Script:

- sets 1080x1920 and frame rate;
- creates bin `SHORTS_<slug>` and imports placeholders, voiceover, SFX, BGM;
- creates timeline `<slug>_v1` (if exists, renames to `_old_HHMMSS` and creates new);
- adds tracks and names them:
  - V1 `B-ROLL` (placeholders + A-roll face clips)
  - V2 `OVERLAY`
  - V3 `TRANSITIONS` (only if automatic transitions exist)
  - V4 `CAPTIONS` (only if captions exist)
  - A1 `VOICE`
  - A2 `SFX`
  - A3 `BGM`
- appends clips with `AppendToTimeline({ mediaPoolItem, trackIndex, recordFrame })`;
  for face slots also adds `startFrame = 0` and `endFrame = frames` (exclusive bound),
  so A-roll duration is exact to the frame
- colors clips (`SetClipColor`) by `kind` (A-roll = `Cyan`)
- applies static `zoom` (`SetProperty("ZoomX"/"ZoomY", ...)`)
- applies `opacity` (`SetProperty("Opacity", ...)`) and `blend` (`SetProperty("CompositeMode", ...)`)
- puts transition overlays on V3 (straddling cut) and caption cards on V4
- puts prepared audio files in timeline from `build/<slug>/audio/` (SFX with gain baked, BGM looped/cut with fade)
- adds a marker per slot with multiline notes
- prints report and verifies clips at correct positions

At the end you're in **Edit**: timeline is ready.

> If Console shows `!! file mancante`, missing placeholder: rerun `placeholders`.
> If `A2 sfx: 0`, `recordFrame` unsupported by your version: update Resolve 21.x.
> If `V4 caption: 0`, missing `words.json`: run `render-audio` then `placeholders --force`.
> If `cross-dissolve` doesn't appear, free API doesn't create real transitions: do manually in Edit, or use an automatic type.

---

## Phase 8 — Replace Placeholders

Each placeholder is a unique file (`s01_base.mp4`), used once. This makes replacement safe.

> **Talking head**: `source: "face"` slots are not placeholders. They are real clips in `build/<slug>/aroll/`, already cut and placed on V1. Don't replace them: move to next placeholder. Marker reminds you.

### Recommended Method — Replace Selected Clip

1. Import your clip into a bin (drag into Media Pool).
2. In Media Pool select the **placeholder** (`s01_base`), not your clip.
3. Right-click → **Clip Operations > Replace Selected Clip...**
4. Choose your file.

What happens: the file behind the Media Pool item changes, timeline untouched.
So **position, duration, transform, zoom, effects, grade, markers, Fusion comp** all stay.

> This method replaces the file in *all* its occurrences. Placeholder is used once,
> so it's equivalent to replacing one slot. If you duplicate a placeholder across slots, use F11 instead.

### Alternative Method — F11 (Replace Edit)

1. Double-click your clip in Media Pool (opens in Source Viewer).
2. Put playhead at correct source point.
3. Put timeline playhead over placeholder.
4. Press **F11**.

Resolve fits new clip duration to slot. Effects and grade stay.

### What Survives and What Doesn't

| Element | After replacement |
|---|---|
| position, duration, markers | stays |
| transform, static zoom, crop | stays |
| Edit effects, grade | stays |
| Fusion composition on clip | stays |
| **animation baked in placeholder** | **gone** (was in file) |
| automatic transitions on V3 | **stay** (separate clips, not in placeholder) |
| captions on V4 | **stay** (separate clips, already positioned) |
| A-roll face clips | already real media: **don't replace** |
| `cross-dissolve` | manual: create in Edit between clips |

Placeholder animation is a **preview** of how the slot should move. After replacement, re-apply it on the real clip using phase 9 methods. Automatic transitions and captions don't need redoing: they're on separate tracks.

---

## Phase 9 — Animations on Real Media

A-roll face slots are born **static**: auto-cut doesn't bake zoom/pan. If you want a push-in on face, apply it here with a Fusion template or manually. For b-rol, three paths from fastest to most powerful.

### A. Static Zoom (Already Done)

If shotlist has `"zoom": 1.05`, script applies to clip (`ZoomX`/`ZoomY`): static transform, survives replacement. Good for "punch-in" without movement. Same for `opacity` and `blend`.

### B. Fusion Template (Recommended)

In `presets/fusion/README.md` recipe to create **once** 5 animations
(zoom-in, zoom-out, pan L→R, pan R→L, drift up) as Fusion Effect. Then:

1. replace clip;
2. drag template from Effects Library onto clip;
3. done.

One template applies to multiple selected clips.

### C. Automatic (Studio 21.1.1 Quality Mode)

If shotlist has `"animation_mode": "fusion"`, script creates Fusion comp on timeline clip with keyframes. Animation **survives** `Replace Selected Clip`. See Studio 21.1.1 section in README.

---

## Phase 10 — Audio

Script already placed:

- voice on A1 (normalized to -16 LUFS if `render-audio --normalize`);
- SFX on A2 at calculated frames, with gain baked;
- BGM on A3 as **single clip**, already looped, cut to exact timeline duration, with fade in/out.

How gain works: Resolve API **doesn't expose clip volume**. When running `lua`, `shorts.py` creates in `build/<slug>/audio/` a copy of each SFX with shotlist `gain_db` (`impact-1_g-8.wav`) and a `bgm_mix.wav` with gain, loop, cut, fade. Timeline gets those files: your originals in `media/` untouched.

Manual steps:

1. **Levels**: listen. Voice at -6/-3 dB peak, SFX -15/-10, BGM -25/-20. If SFX too loud, change `gain_db` in shotlist and rerun `lua` (5 seconds, no timeline rebuild).
2. **Ducking**: BGM must drop 6–9 dB under voice. In Fairlight: keyframe volume on A3, or clip volume + automation. GUI does it in 20s for a Short.
3. **Silence**: if a cut breathes badly, add 2–3 frames of room tone instead of absolute silence.
4. **Final loudness**: YouTube target ~**-14 LUFS integrated**. If voice at -16, raise master 1–2 dB in Fairlight.

SFX names are fixed: see `media/sfx/README.md`. If you rename a file, redo `scan` and `lua`.
If you change timeline duration (cuts, slots), rerun `lua`: BGM recut to new duration.

---

## Phase 11 — Export

Shorts settings:

| Parameter | Value |
|---|---|
| Format | MP4 |
| Codec | H.264 |
| Resolution | 1080x1920 |
| Frame rate | 30 (or 60 if project is 60) |
| Quality | 20–24 Mbps (or "High") |
| Audio | AAC 320 kbps, 48 kHz |
| Color | Rec.709 / sRGB |

In Deliver: select timeline, set, add to queue. Or use `scripts/lua/90_render_queue.lua` (sets format, codec, folder, adds job).

---

## Phase 12 — QC and Iteration

```bash
.venv/bin/python scripts/shorts.py qc <slug> --video build/<slug>/export/<slug>.mp4
```

Extracts one frame at center of each slot, makes contact sheet with slot numbers.
Open `build/<slug>/qc/sheet_01.jpg` or attach to OpenCode: agent reads it and comments on framing, text, style consistency, caption readability (position, size, coverage).

If you need to change the edit:

1. edit `projects/<slug>/shotlist.json`;
2. `validate` → `placeholders --force` → `lua`;
3. in Resolve rerun script: renames old timeline and creates new one.

Don't waste time tweaking timeline manually if the issue is in the direction: go back to shotlist.

---

## Work Division

| Task | Who |
|---|---|
| transcribe, remove pauses/errors | AI + script |
| decide what's seen and why | AI, you approve |
| choose which clips to actually use | you |
| build timeline, markers, SFX, BGM, captions | Lua script |
| automatic transitions (glitch/flash/dip/whip-pan) | Lua script, on V3 |
| fill slots | you |
| camera animations & cross-dissolve | you (Fusion template / Edit) |
| extra text/graphics | you |
| color, audio mix, export | you |

AI saves 70–80% of mechanical time. The remaining 20% is what makes the video yours.

---

## Troubleshooting

| Problem | Cause | Solution |
|---|---|---|
| `resolve == nil` in Console | script run from terminal | drag into Resolve Console |
| `CreateEmptyTimeline` returns nil | no project open | open/create project |
| all clips end at 0 | `recordFrame` unsupported | update Resolve 21.x |
| `!! file missing` | wrong placeholder path | rerun `placeholders`, then `lua` |
| no audio | file not imported | check `vo_clean.wav` exists |
| placeholders black | unsupported codec | rerun with `--force` (H.264 + ProRes) |
| Resolve free rejects script | Scripts menu = Studio | use Console only |
| Whisper won't start | wrong venv | use `.venv/bin/python` |
| times don't match | using original file times | use `vo_clean.txt` |
| `captions skipped: missing words.json` | `placeholders` before `render-audio` | `render-audio`, then `placeholders --force` |
| no captions in timeline | V4 not created or empty manifest | check `captions.enabled` and `build/<slug>/captions/manifest.json` |
| `cross-dissolve` missing | free API doesn't create real transitions | do manually in Edit, or use automatic type |

---

## Alternative: Start from Pre-Edited Video

If you already have a video **without pauses/errors** (cut elsewhere), skip transcribe/roughcut/render-audio:

```bash
.venv/bin/python scripts/shorts.py init-from-video my-video /path/to/edited_video.mp4
```

Extracts audio (`vo_clean.wav`), copies video (`vo_clean.mp4` for A-roll), measures duration, creates project ready for shotlist. Then continue from `scan` → `validate` → `placeholders` → `lua`.