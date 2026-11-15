# Studio Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aggiungere qualità Studio 21.1.1 al pipeline: Fusion comp per animazioni, transizioni native (cross-dissolve, dip-to-black), BGM ducking automatico, Voice Isolation, micro-fade voce/SFX — mantenendo retrocompatibilità totale con progetti free/Lua esistenti.

**Architecture:** Modifiche puntuali a `scripts/shorts.py` (CLI, placeholders, validate, lua) + aggiornamento documentazione/skill. Nessun nuovo file Python; lo script Lua generato incorpora la logica Fusion/transition/audio. Mock Resolve esteso per regressioni.

**Tech Stack:** Python 3.13, ffmpeg, Pillow, DaVinci Resolve Studio 21.1.1 (Lua 5.5), luac per static check.

**Spec:** `docs/superpowers/specs/2026-11-15-studio-quality-design.md`

## Global Constraints

- Resolve Studio 21.1.1 target; degradazione graziosa su 21.0.x e free.
- Prodotto = script Lua Console. Python esterno solo harness test.
- Segnaposto da ffmpeg; media veri dall'utente.
- Slot faccia statici, non sostituibili.
- Default: `animation_mode: "baked"`, `native_transitions: false`, `bgm.duck: false`, micro-fade sempre attivi.
- Nessun percorso assoluto negli script generati.
- `luac -p` deve passare su tutti gli script generati.
- Backup rollback: `~/shorts-studio-backups/shorts-studio-20261115-100056.tar.gz`.

## Review Focus

1. **Progetto esistente senza campi nuovi** → genera script identico a oggi (baked, overlay transitions, niente ducking/isolation).
2. **Shotlist con `native_transitions: true` ma `animation_mode: "baked"`** → validate blocca con errore chiaro.
3. **Handle insufficienti dopo sostituzione manuale** → fallback overlay con avviso, non crash.
4. **`Dip To Color Dissolve` colore non garantito** → documentato; se serve nero garantito, fallback overlay.
5. **Ducking BGM eccessivo** → `duck: false` disattiva; ratio limitato 2..12.

---

### Task 1: Shotlist schema — nuovi campi top-level

**Files:**
- Modify: `scripts/shorts.py` (sezione costanti + `cmd_validate`)
- Test: `projects/test-demo/shotlist.json` (aggiunta campi per test)

**Interfaces:**
- Consumes: costanti `ANIMATIONS`, `TRANSITIONS`, `AUTO_TRANSITIONS`
- Produce: validazione campi `animation_mode`, `native_transitions`, `transition_handle`, `audio`, `bgm.duck`/`duck_db`

- [ ] **Step 1: Aggiungi costanti per valori ammessi**

```python
ANIMATION_MODES = ("baked", "fusion")
```

In `scripts/shorts.py` intorno a linea 53 (dopo `ANIMATIONS`).

- [ ] **Step 2: Estendi `cmd_validate` con controlli nuovi campi**

Aggiungi in `cmd_validate` (dopo validazione `captions`, prima di `voiceover_duration`):

```python
# animation_mode
anim_mode = shotlist.get("animation_mode", "baked")
if anim_mode not in ANIMATION_MODES:
    errors.append(f"animation_mode '{anim_mode}' non valido ({', '.join(ANIMATION_MODES)})")

# native_transitions
native_tr = shotlist.get("native_transitions", False)
if native_tr and anim_mode != "fusion":
    errors.append("native_transitions richiede animation_mode: fusion")

# transition_handle
handle = shotlist.get("transition_handle")
if handle is not None:
    try:
        h = float(handle)
        if h < 0.2 or h > 1.5:
            errors.append("transition_handle fuori da 0.2-1.5s")
    except Exception:
        errors.append("transition_handle non numerico")

# audio.voice_isolation
audio = shotlist.get("audio") or {}
if audio.get("voice_isolation"):
    amt = audio.get("voice_isolation_amount", 60)
    try:
        a = int(amt)
        if a < 0 or a > 100:
            errors.append("audio.voice_isolation_amount fuori da 0-100")
    except Exception:
        errors.append("audio.voice_isolation_amount non numerico")

# bgm.duck
bgm = shotlist.get("bgm") or {}
duck = bgm.get("duck", False)
duck_db = bgm.get("duck_db")
if duck and duck_db is not None:
    try:
        d = float(duck_db)
        if d > -3 or d < -24:
            warnings.append("bgm.duck_db fuori da -24..-3 (verra limitato)")
    except Exception:
        errors.append("bgm.duck_db non numerico")
```

- [ ] **Step 3: Verifica `validate` su test-demo (deve passare invariato)**

Run:
```bash
.venv/bin/python scripts/shorts.py validate test-demo
```
Expected: OK (nessun errore, campi opzionali assenti → default baked).

- [ ] **Step 4: Aggiungi campi a `projects/test-demo/shotlist.json` per test fusion+native**

```json
"animation_mode": "fusion",
"native_transitions": true,
"transition_handle": 0.6,
"audio": {
  "voice_isolation": true,
  "voice_isolation_amount": 60
},
"bgm": {
  "file": "media/bgm/test-loop.wav",
  "gain_db": -26,
  "duck_db": -9,
  "loop": true,
  "duck": true
}
```

- [ ] **Step 5: Verifica `validate` su test-demo con campi nuovi**

Run:
```bash
.venv/bin/python scripts/shorts.py validate test-demo
```
Expected: OK (zero errori, warning su cross-dissolve s05 come prima).

- [ ] **Step 6: Commit**

```bash
git add scripts/shorts.py projects/test-demo/shotlist.json
git commit -m "feat: shotlist schema per Studio quality (animation_mode, native_transitions, audio, bgm.duck)"
```

---

### Task 2: Placeholders — generazione statica + handle + fingerprint

**Files:**
- Modify: `scripts/shorts.py` (`cmd_placeholders`, `encode_base`, `build_transitions`)
- Test: `build/test-demo/placeholders/manifest.json` (controllo handle_frames)

**Interfaces:**
- Consumes: `shotlist` con nuovi campi, `fps`, `slot_frames`
- Produce: segnaposto statici per animati, handle extra, `manifest.json` con `animation_mode`, `handle_frames`, `settings_fingerprint.json`

- [ ] **Step 1: Calcola fingerprint impostazioni in `cmd_placeholders`**

All'inizio di `cmd_placeholders`, dopo caricamento shotlist:

```python
import hashlib, json
settings_fp = hashlib.md5(json.dumps({
    "animation_mode": shotlist.get("animation_mode", "baked"),
    "native_transitions": shotlist.get("native_transitions", False),
    "transition_handle": shotlist.get("transition_handle", 0.6),
    "fps": fps,
    "width": int(fmt.get("width") or 1080),
    "height": int(fmt.get("height") or 1920),
    "generator_version": 2  # incrementa se cambia logica generazione
}, sort_keys=True).encode()).hexdigest()[:12]
```

- [ ] **Step 2: Leggi fingerprint esistente; se diverso, forza rigenerazione**

```python
fp_path = pdir / "settings_fingerprint.json"
force_regen = args.force
if fp_path.exists():
    try:
        old = read_json(fp_path).get("fingerprint")
        if old != settings_fp:
            force_regen = True
            log("  [info] fingerprint cambiato ({} -> {}): rigenero segnaposto".format(old, settings_fp))
    except Exception:
        force_regen = True
else:
    force_regen = True

if force_regen:
    # cancella vecchi segnaposto base/overlay
    for f in pdir.glob("*_base.mp4"):
        f.unlink()
    for f in pdir.glob("*_ovl.mov"):
        f.unlink()
    for f in pdir.glob("*.png"):
        f.unlink()
```

- [ ] **Step 3: Salva fingerprint nuovo**

Alla fine di `cmd_placeholders` (prima di `build_transitions`):

```python
write_json(fp_path, {"fingerprint": settings_fp, "animation_mode": shotlist.get("animation_mode", "baked")})
```

- [ ] **Step 4: Modifica `encode_base` — se `animation_mode: fusion` e animazione non statica, genera statico**

In `cmd_placeholders` loop slot base (intorno linea 2011):

```python
anim_mode = shotlist.get("animation_mode", "baked")
is_animated = slot.get("animation", "static") != "static"
if anim_mode == "fusion" and is_animated and slot.get("layer") == "base":
    # genera statico per fusion: niente zoompan
    vf = "format=yuv420p"
else:
    vf = zoompan_filter(slot.get("animation", "static"), frames, fps) + ",format=yuv420p"
```

- [ ] **Step 5: Aggiungi handle_frames ai segnaposto base se `native_transitions`**

Calcola `handle_frames` prima del loop slot:

```python
handle_frames = 0
if shotlist.get("native_transitions"):
    handle_sec = float(shotlist.get("transition_handle", 0.6))
    handle_frames = max(1, math.ceil(handle_sec * fps))
```

Nel loop slot base, se `native_transitions` e `layer == "base"`:

```python
total_frames = frames + 2 * handle_frames
start_frame_src = 30  # handle sinistro fisso 1s sorgente
end_frame_src = start_frame_src + total_frames
# encode_base riceve total_frames; start/end sorgente passati via ffmpeg -ss/-t
```

Modifica `encode_base` per accettare `source_start`, `source_end` (opzionali) e `total_frames` esplicito.

- [ ] **Step 6: Aggiorna `build_transitions` per `native_transitions`**

Se `native_transitions`:
- NON genera overlay per `cross-dissolve` e `dip-to-black` (solo manifest con tipo, durata, slot)
- Genera overlay solo per `glitch`, `flash`, `whip-pan` (come oggi)
- Manifest include `native: true` per quelle native

- [ ] **Step 7: Manifest segnaposto include `animation_mode` e `handle_frames`**

In `cmd_placeholders` manifest per slot base:

```python
manifest[sid] = {
    "base": rel(out),
    "animation_mode": anim_mode,
    "handle_frames": handle_frames if slot.get("layer") == "base" else 0,
    "animation": slot.get("animation", "static"),
}
```

- [ ] **Step 8: Verifica `placeholders` su test-demo (fusion+native)**

Run:
```bash
.venv/bin/python scripts/shorts.py placeholders test-demo --force
```
Expected: segnaposto statici per s01-s04, s06 (animati); handle_frames > 0; nessun overlay per cross-dissolve/dip-to-black; manifest con fingerprint.

- [ ] **Step 9: Verifica idempotenza (seconda run senza --force non rigenera)**

Run:
```bash
.venv/bin/python scripts/shorts.py placeholders test-demo
```
Expected: "fingerprint invariato: salto rigenerazione" (o simile), file esistenti non toccati.

- [ ] **Step 10: Commit**

```bash
git add scripts/shorts.py
git commit -m "feat: placeholders fusion mode + native transitions handle + fingerprint rigenerazione"
```

---

### Task 3: Lua generation — Fusion comp, transizioni native, audio

**Files:**
- Modify: `scripts/shorts.py` (`cmd_lua`, `LUA_BODY`)
- Test: `build/test-demo/test-demo_build.lua` (controllo `luac -p`, conteggi V3/V4)

**Interfaces:**
- Consumes: `manifest` (con `animation_mode`, `handle_frames`), `shotlist` (nuovi campi), `sfx_durations`, `bgm_durations`
- Produce: script Lua con Fusion comp, transizioni native, Voice Isolation, BGM ducking file

- [ ] **Step 1: Prepara file BGM ducking in `cmd_lua` se `bgm.duck`**

Dopo preparazione `bgm_mix.wav` (intorno linea 2537), aggiungi:

```python
bgm_duck = None
if bgm and bgm.get("duck"):
    duck_db = float(bgm.get("duck_db", -9))
    ratio = max(2.0, min(12.0, abs(duck_db) * 0.9))  # -9 -> ~8
    bgm_duck_path = adir / "bgm_duck.wav"
    # sidechaincompress: voice come sidechain
    run(["ffmpeg", "-y",
         "-i", str(ROOT / bgm["file"]),  # sorgente BGM
         "-i", str(ROOT / vo),           # voice come sidechain
         "-filter_complex",
         f"[0:a]volume={bgm.get('gain_db',0)}dB,aloop=loop=-1:size=2e9,atrim=0:{total}[bgm];"
         f"[1:a]aresample=48000,apad=whole_dur={total},atrim=0:{total}[voice];"
         f"[bgm][voice]sidechaincompress=threshold=0.05:ratio={ratio}:attack=20:release=350:makeup=1[out]",
         "-map", "[out]", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(bgm_duck_path)])
    bgm_duck = rel(bgm_duck_path)
```

Se fallisce, log warning e usa `bgm_mix.wav` (comportamento attuale).

- [ ] **Step 2: Micro-fade 5ms su voce in `render-audio` (Task 6, ma anticipo qui)**

In `cmd_lua`, `vo` punta a `vo_clean_norm.wav` se esiste; il file ha già fade (vedi Task 6).

- [ ] **Step 3: Micro-fade 5ms su SFX in `prep_sfx`**

Modifica `prep_sfx` (intorno linea 2417) per aggiungere `afade=t=in:st=0:d=0.005,afade=t=out:st=D-0.005:d=0.005` dove D è durata SFX.

- [ ] **Step 4: Estendi `LUA_BODY` — Fusion comp per slot base animati**

Nella sezione `placeSlot` / dopo posizionamento V1 base (intorno linea 2289), aggiungi:

```lua
-- Fusion comp per slot con animation != "static" e layer == "base"
local function addFusionAnim(tlItem, animName, frames)
  if animName == "static" then return end
  local comp = tlItem:AddFusionComp()
  if not comp then
    p("!! Fusion comp fallito per " .. tlItem:GetName() .. " (API non disponibile)")
    return
  end
  comp:StartUndo()
  local mi = comp:FindTool("MediaIn1")
  local mo = comp:FindTool("MediaOut1")
  if not mi or not mo then
    p("!! MediaIn/MediaOut non trovati nel comp")
    comp:EndUndo(false)
    return
  end
  local t = comp:AddTool("Transform")
  if not t then
    p("!! Transform tool non disponibile")
    comp:EndUndo(false)
    return
  end
  local ok1 = t:ConnectInput("Input", mi)
  local ok2 = mo:ConnectInput("Input", t)
  if not ok1 or not ok2 then
    p("!! Wiring Transform fallito")
    comp:EndUndo(false)
    return
  end
  -- Keyframe mapping
  local keyframes = {}
  if animName == "push-in-slow" then
    keyframes = { {input="Size", [0]=1.0, [frames-1]=1.16} }
  elseif animName == "push-in-fast" then
    local f35 = math.floor(frames * 0.35)
    keyframes = { {input="Size", [0]=1.0, [f35]=1.14} }
  elseif animName == "pull-out-slow" then
    keyframes = { {input="Size", [0]=1.16, [frames-1]=1.0} }
  elseif animName == "pan-lr" then
    keyframes = {
      {input="Size", [0]=1.18, [frames-1]=1.18},
      {input="Center", [0]={0.41, 0.5}, [frames-1]={0.59, 0.5}}
    }
  elseif animName == "pan-rl" then
    keyframes = {
      {input="Size", [0]=1.18, [frames-1]=1.18},
      {input="Center", [0]={0.59, 0.5}, [frames-1]={0.41, 0.5}}
    }
  elseif animName == "drift-up" then
    keyframes = {
      {input="Size", [0]=1.14, [frames-1]=1.14},
      {input="Center", [0]={0.5, 0.43}, [frames-1]={0.5, 0.57}}
    }
  end
  for _, kf in ipairs(keyframes) do
    local inp = kf.input
    t:AddModifier(inp, "BezierSpline")
    for frame, val in pairs(kf) do
      if type(frame) == "number" then
        t[inp][frame] = val
      end
    end
    -- Verifica lettura indietro
    local check = t:GetInput(inp, frames-1)
    if check == nil then
      p("!! Keyframe " .. inp .. " non scritto")
    end
  end
  comp:EndUndo(true)
end
```

Chiama per ogni slot V1 base dopo `placeSlot`:

```lua
if slot.layer == "base" and slot.animation and slot.animation ~= "static" then
  local tlItem = placed_by_id[slot.id]  -- serve mappa id -> tlItem
  if tlItem then
    addFusionAnim(tlItem, slot.animation, slot.frames or math.floor(slot.duration * fps + 0.5))
  end
end
```

- [ ] **Step 5: Transizioni native nel Lua**

Dopo posizionamento tutti i clip V1 (intorno linea 2308), sostituisci sezione transizioni:

```lua
local nativeCount, overlayCount, failedCount = 0, 0, 0
if DATA.native_transitions and DATA.transitions then
  for _, tr in ipairs(DATA.transitions) do
    if tr.native and (tr.type == "cross-dissolve" or tr.type == "dip-to-black") then
      local incoming = placed_by_id[tr.slot]
      if incoming then
        local durFrames = math.floor((tr.duration or 0.4) * fps + 0.5)
        local leftHandle = incoming:GetLeftOffset() or 0
        local rightHandle = 0
        -- trova outgoing clip (quello prima sullo stesso track)
        local items = timeline:GetItemListInTrack("video", 1) or {}
        for i, it in ipairs(items) do
          if it:GetType() == "video" and it:GetEnd() == incoming:GetStart() then
            rightHandle = it:GetRightOffset() or 0
            break
          end
        end
        if leftHandle >= durFrames/2 and rightHandle >= durFrames/2 then
          local trType = (tr.type == "cross-dissolve") and "Cross Dissolve" or "Dip To Color Dissolve"
          local trans = incoming:AddTransition({
            type = trType,
            category = "simple",
            position = "start",
            alignment = "center",
            duration = durFrames
          })
          if trans and trans:GetDuration() >= durFrames * 0.5 then
            p("Native transition: " .. trType .. " " .. trans:GetDuration() .. "f su " .. tr.slot)
            nativeCount = nativeCount + 1
          else
            if trans then
              timeline:DeleteClips({trans}, false)
            end
            p("!! Native transition fallita/insufficiente: fallback overlay su " .. tr.slot)
            failedCount = failedCount + 1
            -- genera overlay (vedi sotto)
          end
        else
          p("!! Handle insufficienti per native transition su " .. tr.slot .. " (L=" .. leftHandle .. " R=" .. rightHandle .. " need=" .. math.ceil(durFrames/2) .. ")")
          failedCount = failedCount + 1
        end
      end
    end
  end
end
```

Overlay fallback per `glitch`/`flash`/`whip-pan` + native fallite: logica attuale su V3.

- [ ] **Step 6: Voice Isolation su A1**

Dopo posizionamento voiceover (intorno linea 2322):

```lua
if DATA.audio and DATA.audio.voice_isolation then
  local amt = DATA.audio.voice_isolation_amount or 60
  local ok = false
  if timeline.SetVoiceIsolationState then
    ok = timeline:SetVoiceIsolationState(1, {isEnabled=true, amount=amt})
    p("Voice Isolation A1: " .. (ok and ("enabled amount=" .. amt) or "fallito (API)"))
  else
    p("!! Voice Isolation non disponibile in questa versione")
  end
end
```

- [ ] **Step 7: Usa `bgm_duck.wav` se generato, altrimenti `bgm_mix.wav`**

In sezione A3 BGM, usa `DATA.bgm_duck` se presente.

- [ ] **Step 8: Aggiorna conteggi verifica per includere transizioni native**

Le transizioni native sono item separati in track; `verify` deve filtrare `GetType() == "transition"`.

- [ ] **Step 9: Verifica `lua` su test-demo + `luac -p`**

Run:
```bash
.venv/bin/python scripts/shorts.py lua test-demo
luac -p build/test-demo/test-demo_build.lua
```
Expected: script generato, `luac -p` OK (nessun errore sintassi), conteggi V1/V2/V3/V4/A1/A2/A3 stampati.

- [ ] **Step 10: Commit**

```bash
git add scripts/shorts.py
git commit -m "feat: lua Fusion comp + native transitions + Voice Isolation + BGM ducking + micro-fade"
```

---

### Task 4: Render-audio — micro-fade 5ms su voce

**Files:**
- Modify: `scripts/shorts.py` (`cmd_render_audio`)
- Test: `build/test-demo/vo_clean.wav` / `vo_clean_norm.wav` (verifica fade con ffmpeg)

**Interfaces:**
- Consumes: `segments`, `src` (audio/video)
- Produce: `vo_clean.wav` e `vo_clean_norm.wav` con fade in/out 5ms

- [ ] **Step 1: Aggiungi fade 5ms al filter_complex audio in `cmd_render_audio`**

Nel branch `with_video` e `else`, aggiungi `afade=t=in:st=0:d=0.005,afade=t=out:st=D-0.005:d=0.005` dove D è durata totale pulita.

```python
# calcola durata totale pulita
clean_dur = cuts["stats"]["cleaned"]
fade_filter = f"afade=t=in:st=0:d=0.005,afade=t=out:st={clean_dur-0.005}:d=0.005"
# inserisci nel filter_complex dopo concat
```

- [ ] **Step 2: Stesso fade su normalizzazione (già separato, aggiungi lì)**

- [ ] **Step 3: Verifica con `volumedetect` su primi/ultimi campioni**

Run:
```bash
.venv/bin/python scripts/shorts.py render-audio test-demo --normalize
ffmpeg -hide_banner -i build/test-demo/vo_clean_norm.wav -af "atrim=0:0.1,volumedetect" -f null - 2>&1 | grep mean_volume
ffmpeg -hide_banner -i build/test-demo/vo_clean_norm.wav -af "atrim=8.2:8.34,volumedetect" -f null - 2>&1 | grep mean_volume
```
Expected: volume molto basso (≈ -inf o <-80dB) ai bordi.

- [ ] **Step 4: Commit**

```bash
git add scripts/shorts.py
git commit -m "feat: micro-fade 5ms su voce in render-audio"
```

---

### Task 5: Mock Resolve esteso per regressioni

**Files:**
- Create: `scripts/lua/mock_resolve.lua`
- Modify: `scripts/shorts.py` (eventuale hook per test mock)

**Interfaces:**
- Consumes: script Lua generato
- Produce: esecuzione mock che verifica chiamate API, conteggi, fallback

- [ ] **Step 1: Crea `scripts/lua/mock_resolve.lua` con API minime**

```lua
-- Mock Resolve per test regressione script generati
local mock = {
  resolve = {
    GetProjectManager = function() return mock.pm end,
    OpenPage = function() return true end,
  },
  pm = {
    GetCurrentProject = function() return mock.project end,
    GetMediaPool = function() return mock.mp end,
  },
  project = {
    GetName = function() return "test" end,
    GetSetting = function(k) return mock.settings[k] end,
    SetSetting = function(k, v) mock.settings[k] = v; return true end,
    GetMediaPool = function() return mock.mp end,
    GetCurrentTimeline = function() return mock.timeline end,
    SetVoiceIsolationState = function(track, state) mock.voice_isolation = state; return true end,
    GetVoiceIsolationState = function(track) return mock.voice_isolation or {isEnabled=false, amount=0} end,
  },
  mp = {
    GetRootFolder = function() return mock.folder end,
    AddSubFolder = function() return mock.folder end,
    SetCurrentFolder = function() return true end,
    ImportMedia = function(paths)
      local items = {}
      for _, p in ipairs(paths) do
        table.insert(items, {GetName=function() return p:match("([^/]+)$") end})
      end
      return items
    end,
    CreateEmptyTimeline = function(name) return mock.timeline end,
    AppendToTimeline = function(infos)
      local items = {}
      for _, info in ipairs(infos) do
        local item = {
          GetName = function() return info.mediaPoolItem.GetName() end,
          GetType = function() return "video" end,
          GetStart = function() return info.recordFrame end,
          GetEnd = function() return info.recordFrame + (info.endFrame - info.startFrame) end,
          GetDuration = function() return info.endFrame - info.startFrame end,
          GetLeftOffset = function() return info.startFrame end,
          GetRightOffset = function() return 0 end,  -- override per incoming
          GetFusionCompCount = function() return 0 end,
          AddFusionComp = function()
            mock.comp_count = mock.comp_count + 1
            return mock.fusion_comp
          end,
          GetFusionCompByIndex = function() return mock.fusion_comp end,
          GetFusionCompNameList = function() return {"Composition 1"} end,
          SetClipColor = function() return true end,
          SetProperty = function() return true end,
        }
        table.insert(items, item)
      end
      return items
    end,
  },
  folder = {
    GetName = function() return "root" end,
    GetSubFolderList = function() return {} end,
    GetClipList = function() return {} end,
  },
  timeline = {
    GetName = function() return "test_tl" end,
    GetTrackCount = function(t) return mock.track_counts[t] or 0 end,
    AddTrack = function(t) mock.track_counts[t] = (mock.track_counts[t] or 0) + 1; return true end,
    SetTrackName = function(t, i, n) return true end,
    GetItemListInTrack = function(t, i) return mock.track_items[t][i] or {} end,
    AppendToTimeline = function(infos) return mock.mp.AppendToTimeline(infos) end,
    AddTransition = function(opts)
      if not mock.transition_allowed then return nil end
      local item = {
        GetType = function() return "transition" end,
        GetName = function() return opts.type end,
        GetStart = function() return mock.transition_start end,
        GetEnd = function() return mock.transition_start + (opts.duration or 0) end,
        GetDuration = function() return opts.duration or 0 end,
      }
      mock.transition_created = item
      return item
    end,
    DeleteClips = function(items, ripple) return true end,
    AddMarker = function(f, c, title, note, dur) return true end,
    SetCurrentTimecode = function(tc) return true end,
    SetVoiceIsolationState = function(track, state) return mock.project.SetVoiceIsolationState(track, state) end,
  },
  fusion_comp = {
    GetToolList = function() return {MediaIn1={ID="MediaIn"}, MediaOut1={ID="MediaOut"}} end,
    FindTool = function(name) return mock.tools[name] end,
    AddTool = function(type)
      if type == "Transform" then
        local t = {
          ConnectInput = function(inp, src) return true end,
          AddModifier = function(inp, kind) return true end,
          GetInput = function(inp, frame) return mock.keyframes[inp] and mock.keyframes[inp][frame] end,
        }
        mock.tools.Transform1 = t
        return t
      end
      return {ConnectInput=function() return true end}
    end,
    StartUndo = function() end,
    EndUndo = function(commit) end,
    SetAttrs = function(t) end,
    Render = function(opts) return true end,
  },
  settings = {},
  track_counts = {video=2, audio=3},
  track_items = {video={[1]={}, [2]={}}, audio={[1]={}, [2]={}, [3]={}}},
  comp_count = 0,
  transition_allowed = true,
  transition_start = 100,
  transition_created = nil,
  voice_isolation = nil,
  keyframes = {},
  tools = {MediaIn1={ID="MediaIn"}, MediaOut1={ID="MediaOut"}},
}
return mock
```

- [ ] **Step 2: Test manuale — carica script generato nel mock**

Creare uno script di test `scripts/lua/test_mock.lua` che:
1. Carica `mock_resolve.lua`
2. Imposta `resolve = mock.resolve`
3. Carica lo script generato (`dofile("build/test-demo/test-demo_build.lua")`)
4. Verifica: `mock.comp_count == 4` (s01-s04, s06 animati), `mock.voice_isolation.enabled == true`, `mock.transition_created` per cross-dissolve/dip-to-black, conteggi track.

- [ ] **Step 3: Verifica `luac -p` su mock**

Run:
```bash
luac -p scripts/lua/mock_resolve.lua
luac -p scripts/lua/test_mock.lua
```

- [ ] **Step 4: Commit**

```bash
git add scripts/lua/mock_resolve.lua scripts/lua/test_mock.lua
git commit -m "feat: mock Resolve esteso per regressioni Studio quality"
```

---

### Task 6: Documentazione e skill — aggiornamenti

**Files:**
- Modify: `README.md`, `WORKFLOW.md`, `STYLE.md`, `AGENTS.md`
- Modify: `.opencode/skills/shorts-editor/SKILL.md`
- Modify: `.opencode/skills/shorts-editor/references/shotlist-schema.md`
- Modify: `.opencode/skills/shorts-editor/references/resolve-lua.md`

**Interfaces:**
- Consumes: design doc decisioni
- Produce: docs aggiornate per utente e agente

- [ ] **Step 1: `README.md` — sezione "Studio 21.1.1: qualità"**

Dopo sezione "Script Lua pronti", aggiungi:

```markdown
## Studio 21.1.1: qualità (opzionale)

Se hai DaVinci Resolve Studio 21.1.1, puoi attivare la modalità qualità nello shotlist:

```json
"animation_mode": "fusion",
"native_transitions": true,
"transition_handle": 0.6,
"audio": { "voice_isolation": true, "voice_isolation_amount": 60 },
"bgm": { "duck": true, "duck_db": -9 }
```

Cosa cambia:
- **Animazioni Fusion**: zoom/pan vivono in un Fusion comp attaccato al clip timeline. Dopo `Replace Selected Clip` (F11) l'animazione **resta** e si applica al tuo media.
- **Transizioni native**: `cross-dissolve` e `dip-to-black` diventano transizioni vere di Resolve (non overlay). Servono handle (default 0.6s) nei segnaposto.
- **BGM ducking**: la musica si abbassa automaticamente sotto la voce (`sidechaincompress`).
- **Voice Isolation**: attiva su A1 per talking head (riduce rumore/riverbero).
- **Micro-fade**: 5ms fade in/out su voce e SFX per evitare click.

Progetti esistenti senza questi campi restano in modalità `baked` (comportamento attuale).
```

- [ ] **Step 2: `WORKFLOW.md` — dettagli fase 7 (placeholders) e 8 (sostituzione)**

Aggiungi nota: con `fusion` i segnaposto animati sono statici; l'animazione è nel Fusion comp. Dopo sostituzione, **non riapplicare** zoom/pan.

Aggiungi nota transizioni native: `cross-dissolve` e `dip-to-black` non vanno toccate; `glitch`/`flash`/`whip-pan` restano overlay V3.

- [ ] **Step 3: `STYLE.md` — cosa cambia per volto/transizioni**

Nessun cambiamento visivo; solo nota che animazioni ora persistono.

- [ ] **Step 4: `AGENTS.md` — regole e checklist**

Aggiungi in "Regole ferree":
- Con `animation_mode: fusion` i segnaposto animati sono statici; l'animazione è in Fusion comp.
- `native_transitions` richiede `animation_mode: fusion` e handle ≥ 0.2s.
- `bgm.duck` default false; l'agente lo imposta true per talking head.

Aggiorna checklist finale con voci Studio quality.

- [ ] **Step 5: `SKILL.md` — quando usare fusion/native_transitions**

Aggiungi sezione "Studio 21.1.1 Quality Mode" con decision tree.

- [ ] **Step 6: `references/shotlist-schema.md` — nuovi campi**

Documenta `animation_mode`, `native_transitions`, `transition_handle`, `audio`, `bgm.duck`/`duck_db` con tabelle e regole.

- [ ] **Step 7: `references/resolve-lua.md` — nuovo flusso**

Documenta: posizionamento clip con handle, Fusion comp post-place, transizioni native con lettura durata + fallback, Voice Isolation, BGM duck file.

- [ ] **Step 8: Commit**

```bash
git add README.md WORKFLOW.md STYLE.md AGENTS.md .opencode/skills/shorts-editor/
git commit -m "docs: aggiornamento Studio 21.1.1 quality in docs e skill"
```

---

### Task 7: Regressione end-to-end su test-demo

**Files:**
- Test: `build/test-demo/test-demo_build.lua`, `build/test-demo/placeholders/manifest.json`

**Interfaces:**
- Consumes: tutto il pipeline
- Produce: verifica completa

- [ ] **Step 1: Pulizia build test-demo**

```bash
rm -rf build/test-demo
```

- [ ] **Step 2: Pipeline completo (con shotlist fusion+native)**

```bash
.venv/bin/python scripts/shorts.py validate test-demo
.venv/bin/python scripts/shorts.py placeholders test-demo --force
.venv/bin/python scripts/shorts.py captions test-demo --force
.venv/bin/python scripts/shorts.py lua test-demo
luac -p build/test-demo/test-demo_build.lua
```

- [ ] **Step 3: Verifica output attesi**

- `validate`: 0 errori, 1 warning (cross-dissolve s05 manuale)
- `placeholders`: 7 segnaposto (6 base + 1 overlay), handle_frames > 0, fingerprint salvato
- `captions`: manifest non vuoto
- `lua`: `luac -p` OK, script contiene Fusion comp, transizioni native, Voice Isolation, BGM duck
- Mock test: `lua scripts/lua/test_mock.lua` passa

- [ ] **Step 4: Verifica retrocompatibilità — test-demo originale (baked)**

Ripristina shotlist originale (senza campi nuovi), rigenera, verifica output identico a prima (stessi file, stessi conteggi).

- [ ] **Step 5: Commit**

```bash
git commit -m "test: regressione end-to-end Studio quality su test-demo"
```

---

### Task 8: Pulizia progetto spike temporaneo

**Files:**
- N/A (operazione manuale Resolve)

**Interfaces:**
- Consumes: progetto `zz-quality-spike` in Resolve

- [ ] **Step 1: In Resolve, chiudi progetto `zz-quality-spike`**

- [ ] **Step 2: Elimina progetto `zz-quality-spike` da Project Manager**

- [ ] **Step 3: Rimuovi artifact render temporanei**

```bash
rm -rf /private/var/folders/2n/xstx8kq936v8bx17xxfrdvnw0000gn/T/opencode/render
rm -rf /private/var/folders/2n/xstx8kq936v8bx17xxfrdvnw0000gn/T/opencode/spike_*.py
```

- [ ] **Step 4: Verifica backup integro**

```bash
tar -tzf ~/shorts-studio-backups/shorts-studio-20261115-100056.tar.gz | head -5
```

---

## Execution Order

1. Task 1 (schema) → 2 (placeholders) → 3 (lua) → 4 (render-audio micro-fade) → 5 (mock) → 6 (docs) → 7 (regressione) → 8 (pulizia)

Tasks 1-4 sono dipendenti in sequenza; 5-6 possono andare in parallelo dopo 3; 7 richiede 1-6; 8 è standalone.

## Time Estimate

~8-10 ore di implementazione nativa (questa sessione).