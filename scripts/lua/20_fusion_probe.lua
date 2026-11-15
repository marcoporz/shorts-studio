-- ============================================================
--  20_fusion_probe.lua - test sperimentale dell'API Fusion
--
--  Verifica se la tua versione di Resolve (anche free) permette
--  dalla Console:
--    - TimelineItem:AddFusionComp()
--    - TimelineItem:ExportFusionComp()
--    - TimelineItem:ImportFusionComp()
--
--  Se funziona, possiamo applicare una composizione .comp preparata
--  in Fusion a ogni clip, senza trascinare template a mano.
--
--  ATTENZIONE: usa una timeline di prova.
--  Lo script crea una comp sul primo clip di V1 e la elimina alla fine.
--  Non tocca i tuoi clip, i media o le altre tracce.
--
--  Come si usa:
--   1. Apri il progetto con la timeline da testare.
--   2. Workspace > Console, linguaggio Lua.
--   3. Trascina questo file nella Console e premi Invio.
-- ============================================================

local CONFIRM = true -- metti false per non eseguire nulla

local function p(...)
  local parts = {}
  for i = 1, select("#", ...) do parts[i] = tostring(select(i, ...)) end
  print(table.concat(parts, " "))
end

if not CONFIRM then
  p("Probe disattivato: imposta CONFIRM = true per eseguirlo.")
  return
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

local tl = nil
local ok_tl, value_tl = pcall(function() return project:GetCurrentTimeline() end)
if ok_tl then tl = value_tl end
if tl == nil then
  p("!! Nessuna timeline corrente. Aprine una e rilancia.")
  return
end

local items = tl:GetItemListInTrack("video", 1) or {}
if #items == 0 then
  p("!! V1 è vuota: serve un clip per il test.")
  return
end

local item = items[1]
p("== Fusion probe ==")
p("timeline: " .. tl:GetName())
local ok_name, clip_name = pcall(function() return item:GetName() end)
p("clip: " .. tostring(ok_name and clip_name or "(senza nome)"))

local function comp_names()
  local ok, list = pcall(function() return item:GetFusionCompNameList() end)
  if ok and list ~= nil then return list end
  return {}
end

local function comp_count()
  local ok, n = pcall(function() return item:GetFusionCompCount() end)
  if ok and n ~= nil then return tonumber(n) or 0 end
  return 0
end

local before_count = comp_count()
local before = {}
for _, name in ipairs(comp_names()) do before[name] = true end
p("comp prima: " .. before_count)

-- 1) AddFusionComp
local ok_add, comp = pcall(function() return item:AddFusionComp() end)
if not ok_add or comp == nil then
  p("AddFusionComp:      NON funziona")
  p("-> usa i Fusion Effect Template (presets/fusion/README.md)")
  return
end
p("AddFusionComp:      OK")

local created = nil
for _, name in ipairs(comp_names()) do
  if not before[name] then created = name end
end
p("comp creata:        " .. tostring(created))

-- 2) ExportFusionComp
local exported = false
local path = os.tmpname() .. ".comp"
if created ~= nil then
  local index = 1
  local names = comp_names()
  for i, name in ipairs(names) do
    if name == created then index = i end
  end

  local ok_export, result = pcall(function()
    return item:ExportFusionComp(path, index)
  end)
  exported = ok_export and (result == true or result == 1)
  p("ExportFusionComp:   " .. tostring(exported))

  local fh = io.open(path, "rb")
  if fh ~= nil then
    local size = fh:seek("end")
    fh:close()
    p("file .comp:         " .. tostring(size) .. " byte")
  else
    p("file .comp:         non creato")
  end
end

-- 3) ImportFusionComp (solo se l'export è riuscito)
if exported then
  local ok_import, result = pcall(function() return item:ImportFusionComp(path) end)
  p("ImportFusionComp:   " .. tostring(ok_import and result ~= nil))
end

-- pulizia: elimina solo le comp create da questo test
local removed = 0
for _, name in ipairs(comp_names()) do
  if not before[name] then
    local ok_del = pcall(function() item:DeleteFusionCompByName(name) end)
    if ok_del then removed = removed + 1 end
  end
end
pcall(function() os.remove(path) end)

p("comp rimosse:       " .. removed)
p("comp finale:        " .. comp_count() .. " (atteso " .. before_count .. ")")

p("")
p("Interpretazione:")
p("  Add + Export + Import OK  -> possiamo importare una .comp preparata su ogni clip.")
p("  Add OK, Export/Import KO  -> resta la strada dei Fusion Effect Template.")
p("  Add KO                    -> API Fusion non disponibile: usa i template.")
p("")
p("Creare NODI via script non è documentato: la composizione")
p("va costruita una volta nella pagina Fusion.")
