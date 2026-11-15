-- Mock Resolve per test regressione script generati
local M = {}

M.resolve = {
  GetProjectManager = function() return M.pm end,
  OpenPage = function() return true end,
}

M.pm = {
  GetCurrentProject = function() return M.project end,
  GetMediaPool = function() return M.mp end,
}

M.project = {
  GetName = function(self) return "test" end,
  GetSetting = function(self, k) return M.settings[k] end,
  SetSetting = function(self, k, v) M.settings[k] = v; return true end,
  GetMediaPool = function(self) return M.mp end,
  GetCurrentTimeline = function(self) return M.timeline end,
  GetTimelineCount = function(self) return 1 end,
  GetTimelineByIndex = function(self, i) return M.timeline end,
  SetVoiceIsolationState = function(self, track, state) M.voice_isolation = state; return true end,
  GetVoiceIsolationState = function(self, track) return M.voice_isolation or {isEnabled=false, amount=0} end,
}

M.mp = {
  GetRootFolder = function(self) return M.folder end,
  AddSubFolder = function(self) return M.folder end,
  SetCurrentFolder = function(self) return true end,
  ImportMedia = function(self, paths)
    print("Mock ImportMedia called with:", table.concat(paths, ", "))
    local items = {}
    for _, p in ipairs(paths) do
      table.insert(items, {GetName=function() return p:match("([^/]+)$") end})
    end
    print("Mock ImportMedia returning " .. #items .. " items")
    return items
  end,
  CreateEmptyTimeline = function(self, name) return M.timeline end,
  SetCurrentTimeline = function(self, tl) return true end,
  AppendToTimeline = function(self, infos)
    print("Mock AppendToTimeline called with " .. #infos .. " items")
    local items = {}
    for _, info in ipairs(infos) do
      local trackIdx = info.trackIndex or 1
      local startFrame = info.recordFrame or 0
      local startF = info.startFrame or 0
      local endF = info.endFrame or 0
      local dur = endF - startF
      local endFrame = startFrame + dur
      if dur <= 0 then endFrame = startFrame + 1 end
      local item = {
        GetName = function() return info.mediaPoolItem.GetName() end,
        GetType = function() return "video" end,
        GetStart = function() return startFrame end,
        GetEnd = function() return endFrame end,
        GetDuration = function() return endFrame - startFrame end,
        GetLeftOffset = function() return 100 end,
        GetRightOffset = function() return 100 end,
        GetFusionCompCount = function() return 0 end,
        AddFusionComp = function(self)
          print("Mock AddFusionComp called on item: " .. (self.GetName and self:GetName() or "unknown"))
          M.comp_count = M.comp_count + 1
          return M.fusion_comp
        end,
        GetFusionCompByIndex = function() return M.fusion_comp end,
        GetFusionCompNameList = function() return {"Composition 1"} end,
        SetClipColor = function() return true end,
        SetProperty = function() return true end,
      }
      -- Add to track_items for verification
      M.track_items = M.track_items or {video={[1]={}, [2]={}}, audio={[1]={}, [2]={}, [3]={}}}
      local trackType = "video"
      if info.mediaType == 2 then trackType = "audio" end
      M.track_items[trackType] = M.track_items[trackType] or {}
      M.track_items[trackType][trackIdx] = M.track_items[trackType][trackIdx] or {}
      
      -- Add AddTransition method to timeline item for native transitions
      item.AddTransition = function(self, opts)
        print("Mock Item AddTransition called: " .. opts.type .. " for item " .. (self.GetName and self:GetName() or "unknown"))
        if not M.transition_allowed then return nil end
        local transItem = {
          GetType = function() return "transition" end,
          GetName = function() return opts.type end,
          GetStart = function() return M.transition_start end,
          GetEnd = function() return M.transition_start + (opts.duration or 0) end,
          GetDuration = function() return opts.duration or 0 end,
        }
        M.transition_created = transItem
        return transItem
      end
      
      table.insert(M.track_items[trackType][trackIdx], item)
      table.insert(items, item)
    end
    return items
  end,
}

M.folder = {
  GetName = function(self) return "root" end,
  GetSubFolderList = function(self) return {} end,
  GetClipList = function(self) return {} end,
}

M.timeline = {
  GetName = function() return "test_tl" end,
  GetTrackCount = function(self, t) return M.track_counts[t] or 0 end,
  AddTrack = function(self, t) M.track_counts[t] = (M.track_counts[t] or 0) + 1; return true end,
  SetTrackName = function(self, t, i, n) return true end,
  GetItemListInTrack = function(self, t, i) return (M.track_items[t] or {})[i] or {} end,
  AppendToTimeline = function(self, infos) return M.mp.AppendToTimeline(M.mp, infos) end,
  AddTransition = function(self, opts)
    if not M.transition_allowed then return nil end
    local item = {
      GetType = function() return "transition" end,
      GetName = function() return opts.type end,
      GetStart = function() return M.transition_start end,
      GetEnd = function() return M.transition_start + (opts.duration or 0) end,
      GetDuration = function() return opts.duration or 0 end,
    }
    M.transition_created = item
    return item
  end,
  DeleteClips = function(items, ripple) return true end,
  AddMarker = function(f, c, title, note, dur) return true end,
  SetCurrentTimecode = function(tc) return true end,
  SetVoiceIsolationState = function(self, track, state) return M.project.SetVoiceIsolationState(M.project, track, state) end,
}

M.fusion_comp = {
  GetToolList = function(self) return {MediaIn1={ID="MediaIn"}, MediaOut1={ID="MediaOut"}} end,
  FindTool = function(self, name) return M.tools[name] end,
  AddTool = function(self, type)
    if type == "Transform" then
      local t = {}
      -- Store keyframes in t._keyframes
      t._keyframes = {}
      t.ConnectInput = function(self, inp, src) print("Mock ConnectInput called"); return true end
      t.AddModifier = function(self, inp, kind) 
        print("Mock AddModifier: " .. inp .. " with " .. kind)
        self._keyframes[inp] = self._keyframes[inp] or {}
        return true 
      end
      t.GetInput = function(self, inp, frame) 
        return self._keyframes[inp] and self._keyframes[inp][frame] 
      end
      -- Allow indexing like t.Size[frame] = val
      setmetatable(t, {
        __index = function(self, key)
          if key == "_keyframes" then return rawget(self, "_keyframes") end
          -- Return a proxy table for keyframe assignment
          return setmetatable({}, {
            __newindex = function(_, frame, val)
              self._keyframes[key] = self._keyframes[key] or {}
              self._keyframes[key][frame] = val
              print("Mock keyframe set: " .. key .. "[" .. frame .. "] = " .. tostring(val))
            end,
            __index = function(_, frame)
              return self._keyframes[key] and self._keyframes[key][frame]
            end,
          })
        end,
        __newindex = function(self, key, val)
          rawset(self, key, val)
        end,
      })
      M.tools.Transform1 = t
      return t
    end
    return {ConnectInput=function() return true end}
  end,
  StartUndo = function(self) end,
  EndUndo = function(self, commit) end,
  SetAttrs = function(self, t) end,
  Render = function(self, opts) return true end,
}

M.settings = {}
M.track_counts = {video=2, audio=3}
M.track_items = {video={[1]={}, [2]={}}, audio={[1]={}, [2]={}, [3]={}}}
M.comp_count = 0
M.transition_allowed = true
M.transition_start = 100
M.transition_created = nil
M.voice_isolation = nil
M.keyframes = {}
M.tools = {
  MediaIn1 = {ID="MediaIn", ConnectInput = function(self, inp, src) return true end},
  MediaOut1 = {ID="MediaOut", ConnectInput = function(self, inp, src) return true end},
}

return M