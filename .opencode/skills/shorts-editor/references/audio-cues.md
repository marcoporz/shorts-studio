# Audio: Names, Cues, Volumes

---

## Fixed Effect Names

Put files in `media/sfx/` with these names (lowercase, hyphen, progressive number).
You can add more: just keep names stable and descriptive.

### Transitions

| File | Use |
|---|---|
| `transizione-1.wav` | scene change / cut |
| `transizione-2.wav` | shorter variant |
| `transizione-3.wav` | aggressive variant |
| `whoosh-1.wav` | fast pass |
| `whoosh-2.wav` | soft pass |

### Impact

| File | Use |
|---|---|
| `impatto-1.wav` | dry hit, hook |
| `impatto-2.wav` | deeper hit |
| `sub-drop-1.wav` | bass drop, revelation |
| `stab-1.wav` | dramatic accent |
| `riser-1.wav` | rising tension before reveal |

### UI / Digital

| File | Use |
|---|---|
| `ui-click-1.wav` | click, selection |
| `pop-1.wav` | element appearance |
| `typing-1.wav` | text appearing |
| `glitch-1.wav` | digital error, CRT |
| `crt-on.wav` | monitor power on |
| `crt-off.wav` | monitor power off |
| `ps2-boot.wav` | console startup |

### Other

| File | Use |
|---|---|
| `bubble-1.wav` | Frutiger Aero |
| `risata-1.wav` | comedic moment |
| `record-scratch-1.wav` | stop, "wait" |

---

## Placement Rules

- One SFX goes **on the cut**, not mid-clip.
- Effect peak must hit the first frame of the new clip.
- Max **1 SFX every 2–3 seconds**. More turns video into audio library demo.
- Don't put SFX under full voice: pick pauses or first syllables.
- Same SFX repeated 10 times gets tiring: alternate variants.

In shotlist:

```json
"sfx": [
  { "file": "media/sfx/whoosh-2.wav", "at": 0.0, "gain_db": -12 }
]
```

`at` is seconds from slot start.

---

## Starting Volumes

| Track | Peak | Notes |
|---|---|---|
| Voice (A1) | -6 / -3 dB | normalized to -16 LUFS |
| SFX (A2) | -15 / -10 dB | under voice, above BGM |
| BGM (A3) | -25 / -20 dB | must "be there", not compete |

If you use `gain_db` in shotlist, script creates a copy with gain baked
(`build/<slug>/audio/`) and puts that in timeline: originals in `media/` untouched.
Resolve API doesn't expose clip volume, so this is the only automatic way.

BGM also gets looped, cut to duration, fade in/out in same pass.
Then fine-tune by ear: numbers are starting point, not law.

---

## BGM Ducking

Goal: music drops 6–9 dB when you speak.

Quick Fairlight way:

1. Select BGM track.
2. Enable volume automation (key `A` or button in track head).
3. Place keyframe before each phrase and after, at -6/-9 dB.
4. Fade in at start (1–2s) and fade out at end (2s).

Alternative: sidechain not simply available in free, so keyframe it.
For a 60s Short: 10–15 keyframes = 2 minutes work.

**With Studio 21.1.1 + `bgm.duck: true`**: automatic via `sidechaincompress` in ffmpeg (voice as sidechain, ratio ~\|duck_db\|*0.9). If filter fails, falls back to standard mix and warns.

---

## Loudness

- YouTube normalizes to ~**-14 LUFS integrated**.
- If master too high, video gets lowered and loses impact.
- If too low, gets raised and noise rises.

Check: Fairlight > Loudness Meter, or:

```bash
ffmpeg -i export.mp4 -af loudnorm=print_format=summary -f null -
```

Target **-14 LUFS** with true peak **-1 dB**.

---

## BGM: Where to Find Free

- YouTube Audio Library (inside YouTube Studio)
- Free Music Archive (check license)
- ccMixter
- your own productions

Avoid anything without clear license: fastest way to lose a video.