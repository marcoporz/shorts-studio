-- Test mock per script generati
local M = dofile("scripts/lua/mock_resolve.lua")

-- Imposta resolve globalmente per lo script generato
resolve = M.resolve

-- Imposta SHORTS_ROOT per trovare i file
SHORTS_ROOT = "/Users/marcokat/shorts-studio"

-- Override io.open per simulare file esistenti
print("Setting io.open override...")
local real_io_open = io.open
io.open = function(path, mode)
  -- Accetta qualsiasi percorso in modalità lettura (r, rb, etc.)
  if mode and (mode:match("r") or mode:match("b")) then
    print("io.open mock:", path, mode)
    return {close = function() end}
  end
  return real_io_open(path, mode)
end
print("io.open override set")

-- Carica lo script generato
print("Loading generated script...")
local success, err = pcall(dofile, "build/test-demo/test-demo_build.lua")
print("Script loaded, success=" .. tostring(success))
if not success then
  print("ERRORE caricamento script: " .. tostring(err))
  os.exit(1)
end

-- Verifiche
print("=== VERIFICHE MOCK ===")
print("DATA.animation_mode = " .. tostring(DATA.animation_mode))
print("DATA.slots count = " .. #DATA.slots)

-- Check placed_by_id
print("placed_by_id keys:")
for k, v in pairs(placed_by_id or {}) do
  print("  " .. k .. " = " .. tostring(v))
end

-- 1. Fusion comp count (s01-s04, s06 = 5 slot animati base)
print("Fusion comp creati: " .. M.comp_count)
assert(M.comp_count == 5, "Expected 5 fusion comps, got " .. M.comp_count)

-- 2. Voice Isolation
print("Voice Isolation: enabled=" .. tostring(M.voice_isolation and M.voice_isolation.isEnabled) .. ", amount=" .. tostring(M.voice_isolation and M.voice_isolation.amount))
assert(M.voice_isolation and M.voice_isolation.isEnabled == true, "Voice Isolation should be enabled")
assert(M.voice_isolation and M.voice_isolation.amount == 60, "Voice Isolation amount should be 60")

-- 3. Transizioni native
print("Transizioni native create: " .. (M.transition_created and "sì" or "no"))
assert(M.transition_created ~= nil, "Native transition should be created")

-- 4. Conteggi track (simulati)
print("Track counts: video=" .. (M.track_counts.video or 0) .. ", audio=" .. (M.track_counts.audio or 0))
assert(M.track_counts.video >= 4, "Should have at least 4 video tracks (V1, V2, V3, V4)")
assert(M.track_counts.audio == 3, "Should have 3 audio tracks")

print("=== TUTTE LE VERIFICHE PASSATE ===")