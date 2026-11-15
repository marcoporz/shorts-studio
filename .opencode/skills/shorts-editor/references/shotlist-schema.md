# Shotlist — Complete Schema

File: `projects/<slug>/shotlist.json`
Validated by: `python scripts/shorts.py validate <slug>`

---

## Structure

```json
{
  "project": "slug",
  "title": "Video Title",
  "format": { "width": 1080, "height": 1920, "fps": 30 },
  "style": "ps2-crt",
  "animation_mode": "baked",
  "native_transitions": false,
  "transition_handle": 0.6,
  "audio": {
    "voice_isolation": false,
    "voice_isolation_amount": 60
  },
  "voiceover": "build/<slug>/vo_clean.wav",
  "voiceover_duration": 58.4,
  "face_fit": "crop",
  "bgm": {
    "file": "media/bgm/ps2-menu.mp3",
    "gain_db": -24,
    "duck_db": -9,
    "loop": true,
    "duck": false
  },
  "captions": {
    "enabled": true,
    "position": "lower",
    "max_words": 4,
    "max_chars": 32,
    "max_duration": 3.2,
    "font_size": 66,
    "uppercase": false,
    "background": 0.55,
    "color": "#FFFFFF"
  },
  "slots": []
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `project` | string | yes | must match slug |
| `title` | string | no | readability only |
| `format` | object | yes | **1080x1920 @ 30** is Shorts default |
| `style` | string | yes | `anime90`, `crt`, `ps2`, `frutiger-aero`, `clean` |
| `animation_mode` | enum | no | `baked` (default) or `fusion` |
| `native_transitions` | boolean | no | `false` default; `true` requires `animation_mode: fusion` |
| `transition_handle` | number | no | seconds (0.2–1.5); default 0.6 if `native_transitions` |
| `audio` | object | no | `{ voice_isolation: bool, voice_isolation_amount: 0-100 }` |
| `voiceover` | string | yes | path to `vo_clean.wav` (or `.mp4`) |
| `voiceover_duration` | number | yes | clean voiceover duration in seconds |
| `face_fit` | string | no | `crop` (default) or `fit`: how to fit talking head to vertical |
| `face_video` | string | no | advanced override: pre-cut A-roll in sync. Default `build/<slug>/vo_clean.mp4` |
| `bgm` | object/null | no | if `null`, no music |
| `captions` | object | no | default on, lower third; see below |
| `slots` | array | yes | at least one |

> Voiceover language is not in shotlist: set in `projects/<slug>/project.json` (`"language": "auto" | "it" | "en" | ...`) or with `transcribe --language`. Works for Italian and English without pipeline changes.

### `bgm`

| Field | Type | Notes |
|---|---|---|
| `file` | string | path in `media/bgm/` |
| `gain_db` | number | negative. -24 is good starting point |
| `duck_db` | number | how much to duck under voice (indicative, for auto ducking: -3 to -24) |
| `loop` | bool | if true BGM loops to timeline duration |
| `duck` | boolean | `false` default; `true` = generate `bgm_duck.wav` with sidechaincompress |

Lua creates `build/<slug>/audio/bgm_mix.wav` (or `bgm_duck.wav` if `duck: true`): loop, exact cut to timeline duration, fade in/out and gain already baked. Single clip in timeline. With `duck: true` ducking is automatic via `sidechaincompress` (voice as sidechain, ratio ~\|duck_db\|*0.9). If filter fails, falls back to standard mix and warns. Manual ducking (Fairlight, keyframes) no longer needed.

### `captions`

For Shorts they're **mandatory**. Static cards (not word-by-word), lower third, max 2 lines, semi-transparent background. Generated from `words.json` (from `render-audio`) and placed on dedicated video track above transitions.

| Field | Default | Notes |
|---|---|---|
| `enabled` | `true` | if `false`, no captions (not recommended) |
| `position` | `lower` | `lower`, `middle`, `upper` |
| `max_words` | `4` | 3–5 is readable range |
| `max_chars` | `32` | limits card width |
| `max_duration` | `3.2` | seconds; avoids cards staying too long |
| `font_size` | `66` | at 1080x1920 already large; code reduces to fit 2 lines |
| `uppercase` | `false` | keep false for Italian |
| `background` | `0.55` | black panel alpha, 0–1 |
| `color` | `#FFFFFF` | text color |

Output: `build/<slug>/captions/c###.mov` (QTRLE alpha), `manifest.json`, `captions.srt`. Text not editable in Resolve as subtitles: captions are video clips. SRT is exportable copy for YouTube/TikTok or other editor.

---

## Slot

```json
{
  "id": "s03",
  "start": 12.4,
  "duration": 2.1,
  "layer": "base",
  "kind": "screenshot",
  "intent": "SpaceHey 2005 profile screenshot, pan left to right",
  "suggest": {
    "primary": "media/screenshots/spacehey-profile-2005.png",
    "alternatives": [
      "media/screenshots/spacehey-home.png"
    ],
    "why": "The phrase describes the customizable profile: the feature that set it apart from MySpace."
  },
  "animation": "pan-lr",
  "zoom": 1.0,
  "opacity": 100,
  "blend": "normal",
  "transition_in": { "type": "cut" },
  "sfx": [
    { "file": "media/sfx/transition-1.wav", "at": 0.0, "gain_db": -12 }
  ],
  "text": null
}
```

### Fields

| Field | Type | Required | Constraints |
|---|---|---|---|
| `id` | string | yes | unique, `s01`... |
| `start` | number | yes | >= 0, seconds in clean time |
| `duration` | number | yes | > 0 |
| `layer` | enum | yes | `base` or `overlay` |
| `source` | enum | no | `broll` (default) or `face` (talking head already cut) |
| `kind` | enum | yes | `clip`, `image`, `logo`, `screenshot`, `text`, `ui` |
| `intent` | string | yes | >= 8 chars, specific |
| `suggest.primary` | string | yes | existing path **or** `?description` |
| `suggest.alternatives` | array | no | same rule |
| `suggest.why` | string | yes | >= 15 chars, explains choice |
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

## Talking Head Example (2 slots)

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

Before this shotlist you need `render-audio --video` and `vo_clean.mp4`. `placeholders` creates `build/my-face/aroll/s01_face.mp4`; slot s02 remains a placeholder to replace.

---

## Complete Example (4 slots)

```json
{
  "project": "example-spacehey",
  "title": "What Are These Social Networks NOBODY Knows?",
  "format": { "width": 1080, "height": 1920, "fps": 30 },
  "style": "frutiger-aero",
  "voiceover": "build/example-spacehey/vo_clean.wav",
  "voiceover_duration": 9.0,
  "bgm": { "file": "media/bgm/y2k-loop.mp3", "gain_db": -26, "loop": true },
  "captions": {
    "enabled": true,
    "position": "lower",
    "max_words": 4,
    "max_chars": 32,
    "font_size": 66,
    "uppercase": false
  },
  "slots": [
    {
      "id": "s01",
      "start": 0.0,
      "duration": 2.0,
      "layer": "base",
      "kind": "screenshot",
      "intent": "SpaceHey home in 2005, blue bg and customizable profile",
      "suggest": {
        "primary": "media/screenshots/spacehey-home-2005.png",
        "alternatives": ["media/screenshots/spacehey-profile.png"],
        "why": "Hook is the question: must show immediately the thing nobody talks about."
      },
      "animation": "push-in-slow",
      "zoom": 1.0,
      "transition_in": { "type": "cut" },
      "sfx": [{ "file": "media/sfx/whoosh-2.wav", "at": 0.0, "gain_db": -12 }],
      "text": null
    },
    {
      "id": "s02",
      "start": 2.0,
      "duration": 3.0,
      "layer": "base",
      "kind": "clip",
      "intent": "Screen recording: profile scroll, music starts from player",
      "suggest": {
        "primary": "media/clips/spacehey/scroll-profile.mp4",
        "alternatives": ["?your scroll recording"],
        "why": "SpaceHey is understood by using it: movement shows features better than photo."
      },
      "animation": "static",
      "zoom": 1.0,
      "transition_in": { "type": "glitch", "duration": 0.4 },
      "sfx": [{ "file": "media/sfx/ui-click-1.wav", "at": 0.2, "gain_db": -14 }],
      "text": null
    },
    {
      "id": "s03",
      "start": 5.0,
      "duration": 2.5,
      "layer": "base",
      "kind": "logo",
      "intent": "SpaceHey logo on sky background, reveal with zoom",
      "suggest": {
        "primary": "?SpaceHey logo (screenshot from site, cropped by you)",
        "alternatives": [],
        "why": "You name the platform: logo closes first block and fixes the name."
      },
      "animation": "push-in-fast",
      "zoom": 1.0,
      "transition_in": { "type": "flash", "duration": 0.35 },
      "sfx": [{ "file": "media/sfx/pop-1.wav", "at": 0.05, "gain_db": -10 }],
      "text": null
    },
    {
      "id": "s04",
      "start": 7.5,
      "duration": 1.5,
      "layer": "overlay",
      "kind": "text",
      "intent": "Title card: 'exists since 2003'",
      "suggest": {
        "primary": "?animated text, create in Resolve",
        "alternatives": [],
        "why": "Key fact must be read, not heard in passing."
      },
      "animation": "static",
      "zoom": 1.0,
      "transition_in": { "type": "cut" },
      "sfx": [],
      "text": "exists since 2003"
    }
  ]
}
```

---

## Common Validation Errors

| Message | Fix |
|---|---|
| `file not in index` | file not in `media/`. Change path or use `?` |
| `hole in base layer` | two slots don't touch: fix `start`/`duration` |
| `slots cover X but voiceover lasts Y` | sum of durations must = Y (0.25s tolerance) |
| `overlay outside any base slot` | overlay must be inside a base |
| `suggest.why missing` | write why you chose that material |
| `invalid animation` | use one of 7 values |
| `sfx at X outside slot` | `at` must be < duration |
| `invalid transition_in.type` | use `cut`, `cross-dissolve`, `dip-to-black`, `glitch`, `whip-pan`, `flash` |
| `cross-dissolve stays manual` | warning: no auto overlay for dissolve |
| `invalid captions.position` | use `lower`, `middle`, or `upper` |
| `captions.X not numeric` | check caption config numbers |
| `source 'X' invalid` | use `broll` or `face` |
| `source=face requires layer=base` | face is a base, not overlay |
| `missing build/<slug>/vo_clean.mp4` | record video and run `render-audio --video` |
| `face slot up to X but video lasts Y` | times exceed video: recheck `vo_clean.txt` |

---

## Direction Tips

- **Hook**: first slot 1–2s, strongest material you have. Don't start with a logo.
- **Pattern**: alternate wide and detail. Three screenshots in a row bore.
- **Numbers**: when you say a number, put it on screen (`kind: text`).
- **Names**: when you name a game/site, show logo or title.
- **End**: last slot can be longer (3–4s) and close with question or logo.
- **Face**: if you have talking head, don't keep it all video. Return to face every 20–40s, at start and end; middle uses b-roll to show what you're saying.
- **`?` slots**: if more than 5, video isn't ready. Tell user before generating.