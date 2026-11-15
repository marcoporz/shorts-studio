-- ============================================================
--  00_check.lua - diagnostica di shorts-studio
--
--  Come si usa:
--   1. Apri DaVinci Resolve con un progetto aperto.
--   2. Workspace > Console, seleziona Lua in basso.
--   3. Trascina questo file nella Console e premi Invio.
--
--  Non modifica niente: legge e stampa.
-- ============================================================

local function p(...)
  local parts = {}
  for i = 1, select("#", ...) do parts[i] = tostring(select(i, ...)) end
  print(table.concat(parts, " "))
end

local function try(label, fn)
  local ok, value = pcall(fn)
  if ok and value ~= nil then
    p(string.format("%-26s %s", label, tostring(value)))
    return value
  end
  p(string.format("%-26s (non disponibile)", label))
  return nil
end

if resolve == nil then
  p("!! 'resolve' è nil.")
  p("   Apri Workspace > Console e assicurati che il linguaggio sia Lua.")
  return
end

p("== shorts-studio / check ==")
try("Prodotto", function() return resolve:GetProductName() end)
try("Versione", function() return resolve:GetVersionString() end)
try("Pagina attuale", function() return resolve:GetCurrentPage() end)

local pm = resolve:GetProjectManager()
if pm == nil then
  p("!! Project Manager non disponibile.")
  return
end

local project = pm:GetCurrentProject()
if project == nil then
  p("!! Nessun progetto aperto. Creane uno e rilancia.")
  return
end

p("Progetto: " .. project:GetName())
try("Frame rate", function() return project:GetSetting("timelineFrameRate") end)
try("Larghezza", function() return project:GetSetting("timelineResolutionWidth") end)
try("Altezza", function() return project:GetSetting("timelineResolutionHeight") end)
try("Playback fps", function() return project:GetSetting("timelinePlaybackFrameRate") end)

local timeline_count = 0
local ok_count, count_value = pcall(function() return project:GetTimelineCount() end)
if ok_count and count_value ~= nil then
  timeline_count = tonumber(count_value) or 0
end
p("Timeline: " .. timeline_count)
for i = 1, math.min(timeline_count, 10) do
  local t = project:GetTimelineByIndex(i)
  if t ~= nil then p("  " .. i .. ": " .. t:GetName()) end
end

local tl = nil
local ok_tl, value_tl = pcall(function() return project:GetCurrentTimeline() end)
if ok_tl then tl = value_tl end
if tl == nil and timeline_count > 0 then
  local ok_first, value_first = pcall(function() return project:GetTimelineByIndex(1) end)
  if ok_first then tl = value_first end
end

if tl == nil then
  p("!! Nessuna timeline. Creane una (anche vuota) e rilancia.")
else
  p("")
  p("Timeline corrente: " .. tl:GetName())

  for _, kind in ipairs({ "video", "audio", "subtitle" }) do
    local n = 0
    local ok_n, value = pcall(function() return tl:GetTrackCount(kind) end)
    if ok_n and value ~= nil then n = tonumber(value) or 0 end
    p(string.format("  %s: %d tracce", kind, n))

    for i = 1, math.min(n, 4) do
      local items = {}
      local ok_i, value_i = pcall(function() return tl:GetItemListInTrack(kind, i) end)
      if ok_i and value_i ~= nil then items = value_i end

      local info = ""
      if items[1] ~= nil then
        local ok_s, start_frame = pcall(function() return items[1]:GetStart() end)
        if ok_s and start_frame ~= nil then
          info = " | primo a frame " .. tostring(start_frame)
        end
      end
      p(string.format("    %s%d: %d clip%s", kind, i, #items, info))
    end
  end

  local ok_m, markers = pcall(function() return tl:GetMarkers() end)
  if ok_m and markers ~= nil then
    local n = 0
    for _ in pairs(markers) do n = n + 1 end
    p("  marker: " .. n)
  end

  local ok_start, start_frame = pcall(function() return tl:GetStartFrame() end)
  if ok_start and start_frame ~= nil then p("  inizio timeline: frame " .. tostring(start_frame)) end
end

p("")
local mp = project:GetMediaPool()
local root = nil
if mp ~= nil then
  local ok_root, value = pcall(function() return mp:GetRootFolder() end)
  if ok_root then root = value end
end

if root ~= nil then
  p("Media pool: " .. root:GetName())
  local subs = {}
  local ok_subs, value = pcall(function() return root:GetSubFolderList() end)
  if ok_subs and value ~= nil then subs = value end
  p("  sottocartelle: " .. #subs)
  for i = 1, math.min(#subs, 10) do
    p("    - " .. subs[i]:GetName())
  end
else
  p("Media pool: non disponibile")
end

local formats = nil
local ok_formats, value = pcall(function() return project:GetRenderFormats() end)
if ok_formats then formats = value end
if formats ~= nil then
  local names = {}
  for key, _ in pairs(formats) do names[#names + 1] = tostring(key) end
  table.sort(names)
  p("Formati render: " .. table.concat(names, ", "))
end

p("")
p("Atteso per un build shorts-studio:")
p("  V1 B-ROLL | V2 OVERLAY | A1 VOICE | A2 SFX | A3 BGM")
p("Se manca qualcosa, rilancia lo script di build e cerca le righe '!!'.")
