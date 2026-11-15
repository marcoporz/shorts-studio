-- ============================================================
--  90_render_queue.lua - export verticale per Shorts
--
--  Imposta formato, codec, risoluzione, cartella e aggiunge il job.
--  Non fa polling: il render parte e puoi seguirlo dalla pagina Deliver.
--
--  Come si usa:
--   1. Apri il progetto con la timeline da esportare.
--   2. Controlla la CONFIG qui sotto (in particolare OUT_DIR).
--   3. Workspace > Console, linguaggio Lua.
--   4. Trascina questo file nella Console e premi Invio.
--
--  Se il codec non è disponibile, lo script stampa i formati
--  supportati da `project:GetRenderFormats()` e non fa danni.
-- ============================================================

-- ----------------------------- CONFIG

-- nil = timeline corrente. Altrimenti il nome esatto, es. "fallout_v1".
local TIMELINE_NAME = nil

-- Cartella di destinazione. Deve poter essere creata/scritta.
local OUT_DIR = (os.getenv and os.getenv("HOME") or "/tmp") .. "/shorts-studio/build/render"

-- nil = "<nome timeline>_export"
local OUTPUT_NAME = nil

local FORMAT = "mp4"    -- chiave di GetRenderFormats(), di solito "mp4" o "mov"
local CODEC = "H264"    -- chiave di GetRenderCodecs(format)
local WIDTH = 1080
local HEIGHT = 1920
local FPS = 30

-- ----------------------------- helper

local function p(...)
  local parts = {}
  for i = 1, select("#", ...) do parts[i] = tostring(select(i, ...)) end
  print(table.concat(parts, " "))
end

if resolve == nil then
  p("!! 'resolve' è nil: apri Workspace > Console e seleziona Lua.")
  return
end

local pm = resolve:GetProjectManager()
local project = pm and pm:GetCurrentProject()
if project == nil then
  p("!! Nessun progetto aperto.")
  return
end

-- ----------------------------- timeline

local tl = nil
if TIMELINE_NAME ~= nil then
  for i = 1, project:GetTimelineCount() do
    local candidate = project:GetTimelineByIndex(i)
    if candidate ~= nil and candidate:GetName() == TIMELINE_NAME then
      tl = candidate
    end
  end
else
  local ok_tl, value_tl = pcall(function() return project:GetCurrentTimeline() end)
  if ok_tl then tl = value_tl end
end

if tl == nil then
  p("!! Timeline non trovata.")
  p("   Metti TIMELINE_NAME = \"<nome>\" oppure aprine una nella pagina Edit.")
  return
end

pcall(function() project:SetCurrentTimeline(tl) end)
pcall(function() resolve:OpenPage("deliver") end)

p("== render ==")
p("timeline: " .. tl:GetName())

-- crea la cartella (macOS/Linux)
pcall(function() os.execute("mkdir -p '" .. OUT_DIR .. "'") end)

-- ----------------------------- formato e codec

local ok_format, format_result = pcall(function()
  return project:SetCurrentRenderFormatAndCodec(FORMAT, CODEC)
end)
p("formato " .. FORMAT .. "/" .. CODEC .. ": " .. tostring(ok_format and format_result))

local ok_current, current = pcall(function() return project:GetCurrentRenderFormatAndCodec() end)
if ok_current and current ~= nil then
  p("  attuale: " .. tostring(current.format) .. " / " .. tostring(current.codec))
end

if not (ok_format and format_result) then
  p("!! Formato/codec non accettati. Formati disponibili:")
  local ok_formats, formats = pcall(function() return project:GetRenderFormats() end)
  if ok_formats and formats ~= nil then
    for key, value in pairs(formats) do
      p("   - " .. tostring(key) .. " (" .. tostring(value) .. ")")
    end
  end
  return
end

-- ----------------------------- impostazioni

local name = OUTPUT_NAME or (tl:GetName() .. "_export")

local base = {
  SelectAllFrames = true,
  TargetDir = OUT_DIR,
  CustomName = name,
  ExportVideo = true,
  ExportAudio = true,
  FormatWidth = WIDTH,
  FormatHeight = HEIGHT,
  FrameRate = FPS,
}

local ok_base, base_result = pcall(function() return project:SetRenderSettings(base) end)
p("settings base: " .. tostring(ok_base and base_result))
if not (ok_base and base_result) then
  p("!! SetRenderSettings ha rifiutato i valori base.")
  p("   Controlla TargetDir e che la cartella esista.")
  return
end

-- Le chiavi extra possono non essere supportate: le provo una per una.
local extras = {
  { "VideoQuality", "High" },
  { "VideoQuality", 0 },
  { "EncodingProfile", "High" },
  { "MultiPassEncode", true },
  { "AudioCodec", "aac" },
  { "AudioBitDepth", 24 },
  { "AudioSampleRate", 48000 },
  { "NetworkOptimization", true },
}

for _, pair in ipairs(extras) do
  local key, value = pair[1], pair[2]
  local ok, result = pcall(function()
    return project:SetRenderSettings({ [key] = value })
  end)
  p(string.format("  %-20s %s (%s)", key, tostring(ok and result), tostring(value)))
end

-- ----------------------------- coda

local job = project:AddRenderJob()
if job == nil then
  p("!! AddRenderJob ha restituito nil. Il job non è stato creato.")
  return
end
p("job: " .. tostring(job))

local ok_start, started = pcall(function() return project:StartRendering(job) end)
if not (ok_start and started) then
  -- fallback: avvia tutta la coda
  ok_start, started = pcall(function() return project:StartRendering() end)
end
p("avvio render: " .. tostring(ok_start and started))

local ok_status, status = pcall(function() return project:GetRenderJobStatus(job) end)
if ok_status and status ~= nil then
  for key, value in pairs(status) do
    p("  " .. tostring(key) .. ": " .. tostring(value))
  end
end

p("")
p("File atteso: " .. OUT_DIR .. "/" .. name .. "." .. FORMAT)
p("Stato: project:GetRenderJobStatus(\"" .. tostring(job) .. "\")")
p("Se il render non parte, controlla la pagina Deliver.")
