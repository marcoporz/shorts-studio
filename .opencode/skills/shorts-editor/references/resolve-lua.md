# Resolve Free + Lua: What Actually Works

Reference to understand what the generated script does, and what the API doesn't allow.

---

## Context

From **Resolve 21.1**, external Python scripting, `Workspace > Scripts` menu, and official MCP server are **Studio-only**. Free version keeps scripting **inside the Console** (`Workspace > Console`), accepting Lua and Python.

We use only Lua in Console. In free, `resolve`, `bmd`, `fusion` are already globals: no need for `Resolve()`.

```lua
print(resolve:GetVersion())
```

---

## What `build/<slug>/<slug>_build.lua` Does

1. `project:SetSetting` for frame rate and resolution (1080x1920)
2. Creates bin `SHORTS_<slug>`
3. Imports placeholders, voiceover, SFX, BGM
4. Creates timeline `<slug>_v1` (if exists, renames to `_old_HHMMSS`)
5. Adds tracks and names them:
   - V1 `B-ROLL` (placeholders + A-roll face clips)
   - V2 `OVERLAY`
   - V3 `TRANSITIONS` (only if automatic transitions exist)
   - V4 `CAPTIONS` (only if captions exist)
   - A1 `VOICE`
   - A2 `SFX`
   - A3 `BGM`
6. Appends clips with `AppendToTimeline({ mediaPoolItem, trackIndex, recordFrame })`;
   for face slots also adds `startFrame = 0` and `endFrame = frames` (exclusive bound),
   so A-roll duration is exact to the frame
7. Colors clips (`SetClipColor`) by `kind` (A-roll = `Cyan`)
8. Applies static `zoom` (`SetProperty("ZoomX"/"ZoomY", ...)`)
9. Applies `opacity` (`SetProperty("Opacity", ...)`) and `blend` (`SetProperty("CompositeMode", ...)`)
10. Puts transition overlays on V3 (straddling cut) and caption cards on V4
11. Places prepared audio files from `build/<slug>/audio/` (SFX with baked gain, BGM looped/cut with fade)
12. Adds a marker per slot with multiline notes
13. Verifies and prints report

> Clip volume **is not** exposed by API: gain is applied via ffmpeg before import. Don't look for `SetProperty("Volume", ...)`: it doesn't exist.

---

## `recordFrame`: The Key Function

```lua
timeline:AppendToTimeline({
  { mediaPoolItem = item, trackIndex = 2, recordFrame = 150 }
})
```

`recordFrame` is the timeline frame where clip starts. Without it, everything appends.

Available in recent versions (21.x). If clips all end at 0, your version is old: update Resolve. Final report (`V2: N clip`) helps diagnose.

For face slots we also pass `startFrame`/`endFrame`: in Resolve API **`endFrame` is exclusive**, so `endFrame = frames` gives duration of `frames` frames (not `frames - 1`).

---

## What You CAN'T Do via API (Resolve Free)

| Thing | Status | Workaround |
|---|---|---|
| Create real transition between two clips | not exposed | alpha overlay on V3 (glitch/flash/dip/whip-pan), done; `cross-dissolve` manual |
| Edit keyframes for Transform/Opacity | not exposed | Fusion template, or manual |
| Create Fusion nodes via script | undocumented | `.setting` template + `ImportFusionComp` |
| Create subtitle track / import SRT | not exposed in free | QTRLE caption cards on V4 + `captions.srt` |
| `CreateSubtitlesFromAudio` | Studio/AI-only | captions already baked by `shorts.py` |
| Change clip speed | not exposed | manual |
| Clip audio volume/pan | not exposed | gain via ffmpeg (already done) + Fairlight |
| Precise text via API | not exposed | Text+ / template |
| Reliable auto render | partial | Deliver page / `90_render_queue.lua` |

**In Studio 21.1.1** (with `animation_mode: fusion` + `native_transitions: true`):
- `tlItem:AddFusionComp()` → creates Fusion comp on timeline clip (animations persist after replacement)
- `timelineItem:AddTransition({type="Cross Dissolve", ...})` → native cross-dissolve
- `timelineItem:AddTransition({type="Dip To Color Dissolve", ...})` → native dip-to-black
- `timeline:SetVoiceIsolationState(1, {isEnabled=true, amount=60})` → Voice Isolation on A1
- `sidechaincompress` in ffmpeg for automatic BGM ducking

We do use and they work: `ZoomX`/`ZoomY`, `Opacity`, `CompositeMode` (blend mode).

---

## Markers

```lua
timeline:AddMarker(frame, "Blue", "s03 SCREENSHOT", note, duration)
```

- color follows `kind` (A-roll = `Cyan`)
- `note` contains: what to put, suggested, why, animation, transition; for face slots first line is `A-ROLL/FACE: already cut, don't replace`
- clicking marker in Edit shows everything

Markers are the edit documentation: don't delete them until you're done.

---

## Replacement and What Survives

- **V1/V2 (default `baked` mode)**: `Replace Selected Clip` (or F11) replaces placeholder. Zoom/opacity/blend static stay; camera moves baked in placeholder don't (re-apply Fusion template).
- **V1/V2 (`animation_mode: fusion`)**: `Replace Selected Clip` (or F11) replaces placeholder. Fusion comp on timeline clip **stays** with all keyframes and applies to new media. Zoom/opacity/blend static stay. **Don't re-apply** animations.
- **V1 A-roll**: `source: "face"` clips are already real media, cut from `vo_clean.mp4`. Don't replace: no card, marker says so. Any push-in applies manually (Fusion template in `presets/fusion/`).
- **V3 (`baked` mode)**: transitions are separate clips (overlays). Untouched when replacing V1/V2, so glitch/flash/dip/whip-pan stay in place.
- **V3 (`native_transitions: true`)**: `cross-dissolve` and `dip-to-black` are native Resolve transitions (separate track items). Untouched. glitch/flash/whip-pan remain V3 overlays and stay.
- **V4**: captions are video clips, not subtitle track. Stay above edit and don't need redoing. If you change a word, regenerate from `words.json` with `shorts.py captions <slug> --force` and rerun Lua (caption is baked in image, not editable text in Resolve).

---

## Import and Paths

Script has no absolute paths. On startup it finds project root in:

1. `SHORTS_ROOT`, if user set it in Console;
2. `~/shorts-studio`;
3. current directory.

Checks `build/<slug>/placeholders/manifest.json` exists, then builds media paths as `DATA.root .. "/" .. relative path`. If folder is elsewhere just:

```lua
SHORTS_ROOT = "/path/to/folder"
```

before running script. No regeneration needed.

---

## Debug from Console

Common errors:

```text
attempt to index a nil value (global 'resolve')
```
Running script from terminal. Drag into Resolve Console.

```text
CreateEmptyTimeline → nil
```
No project open.

```text
!! file missing: /.../s07_ovl.mov
```
Missing placeholder: `placeholders --force`.

```text
A2 sfx: 0
```
`recordFrame` ignored or audio files not imported. Check version and rerun `scan`.

```text
V3 transitions: 0
V4 caption: 0
```
No assets generated: run `placeholders --force` (captions need `words.json` from `render-audio`). If shotlist has no auto transitions or captions, tracks aren't created: normal.

```text
[warn] captions skipped: missing build/<slug>/words.json
```
Ran `placeholders` before `render-audio`. Run `render-audio`, then `placeholders --force`.

```text
missing face clips: build/<slug>/vo_clean.mp4 not found
```
Have `source: "face"` slots but didn't cut video. Run `render-audio <slug> --video` (with `--normalize` if wanted) then `placeholders --force`.

For manual inspection:

```lua
local p = resolve:GetProjectManager():GetCurrentProject()
print(p:GetName())
print(p:GetTimelineCount())
local tl = p:GetCurrentTimeline()
```

---

## Free Limits to Remember

- no Magic Mask, Voice Isolation, speech-to-text native
- no external Python / MCP
- no some AI presets
- rest (edit, Fusion, Fairlight, color, 1080p render) is there

For a 1080x1920 Short, free is more than enough.