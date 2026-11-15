# Studio Quality — Design

Data: 2026-11-15
Stato: proposta, in attesa di approvazione

## Intent

Alzare la qualità del montaggio sfruttando DaVinci Resolve Studio 21.1.1, senza
cambiare il flusso di lavoro attuale: shotlist → segnaposto → script Lua nella
Console → sostituzione dei media.

Il problema principale non è aggiungere un effetto. È che oggi zoom e pan sono
cotti dentro il segnaposto MP4: dopo `Replace Selected Clip` spariscono e vanno
riapplicati a mano. Con un Fusion comp attaccato al clip di timeline, il
movimento resta e si applica al media vero.

## Perché ora

- L'utente ha Studio 21.1.1: `AddTransition`, `SetFades`, Voice Isolation e
  scripting esterno sono disponibili.
- Le transizioni native eliminano l'unico caso ancora manuale
  (`cross-dissolve`).
- La BGM non fa ducking e Voice Isolation non viene usata: due migliorie audio
  a basso costo.
- Esiste un backup completo prima di iniziare:
  `~/shorts-studio-backups/shorts-studio-20261115-100056.tar.gz`.

## Goals

1. Animazioni Fusion attaccate al clip di timeline, che sopravvivono alla
   sostituzione del segnaposto.
2. Transizioni native per `cross-dissolve` e `dip-to-black`, con handle nei
   segnaposto; fallback overlay per `glitch`, `flash`, `whip-pan` e per ogni
   caso in cui l'API nativa fallisce.
3. Ducking automatico della BGM sulla voce.
4. Voice Isolation su A1 per i progetti talking-head.
5. Micro-fade su voce e SFX per evitare click.
6. Retrocompatibilità: i progetti esistenti restano identici finché non
   attivano le nuove opzioni.

## Non-goals

- Nessun bridge Python / build diretta da CLI in questa fase.
- Nessuna traccia sottotitoli vera: le caption restano overlay baked.
- Nessuna sostituzione automatica dei segnaposto.
- Nessun nuovo stile visivo.
- Nessun cambio alla regia creativa degli slot.

## Anti-goals

- Rompere la modalità free/Lua dei progetti esistenti.
- Appesantire la timeline con un Fusion comp su ogni clip.
- Doppia animazione (baked + Fusion) sullo stesso slot.
- Dichiarare una transizione nativa "riuscita" senza leggerne la durata.

## Constraints

- Resolve Studio 21.1.1 come target; il codice deve degradare con grazia su
  21.0.x e sulla versione free.
- Il prodotto resta lo script Lua eseguito nella Console. Lo scripting esterno
  Python si usa solo come harness di test, non come dipendenza del prodotto.
- I segnaposto sono generati da ffmpeg; i media veri li fornisce l'utente.
- Gli slot A-roll della faccia restano statici e non si sostituiscono.

## Approcci considerati

- **A — Qualità su 21.0.2**: Fusion + audio, niente transizioni native.
  Scartato perché l'utente ha scelto la qualità completa e sta installando
  21.1.1.
- **B — Qualità completa su 21.1.1**: Fusion + transizioni native + audio.
  Scelto.
- **C — Solo audio/caption**: basso rischio ma non risolve le animazioni perse.
  Scartato.

## Design

### 1. Configurazione nello shotlist

Campi top-level nuovi, tutti opzionali:

```json
"animation_mode": "fusion",        // "baked" (default) | "fusion"
"native_transitions": true,        // default false
"transition_handle": 0.6,          // secondi; default 0.6 se native_transitions
"audio": {
  "voice_isolation": true,
  "voice_isolation_amount": 60
},
"bgm": {
  "duck": true,
  "duck_db": -9
}
```

Regole di validazione:

- `animation_mode` in `baked|fusion`.
- `native_transitions` richiede `animation_mode: "fusion"` (in baked gli handle
  non avrebbero senso: l'animazione è cotta solo sulla parte visibile).
- `transition_handle` tra 0.2 e 1.5 secondi.
- `audio.voice_isolation_amount` tra 0 e 100.
- `bgm.duck_db` negativo, tra -24 e -3.

L'agente imposta `animation_mode: "fusion"` e `native_transitions: true` per i
progetti Studio 21.1.1. I progetti esistenti senza campi restano in `baked`.

### 2. Animazioni Fusion

`placeholders`, con `animation_mode: "fusion"`:

- genera i segnaposto degli slot animati come **statici** (niente `zoompan`);
- lascia invariati gli slot `static`;
- scrive nel manifest `animation`, `frames`, `handle_frames`, `animation_mode`.

`lua`, per ogni slot b-roll con `animation != "static"` **e** `layer == "base"`:

1. `comp = tlItem:AddFusionComp()`
2. trova `MediaIn1` e `MediaOut1` (fallback: primo tool per ID)
3. aggiunge un `Transform` e collega `MediaIn → Transform → MediaOut`
4. crea i keyframe con `AddModifier(input, "BezierSpline")` e poi
   `input[frame] = value` (es. `t.Size[0] = 1.0; t.Size[119] = 1.16`)
5. legge indietro un keyframe per verificare che l'animazione esista
6. se qualcosa fallisce, avvisa e lascia il segnaposto statico

Mappatura animazioni (frame 0 → frame N-1):

| Animazione | Input | Da | A |
|---|---|---|---|
| `push-in-slow` | Size | 1.00 | 1.16 |
| `push-in-fast` | Size | 1.00 | 1.14 entro il 35% |
| `pull-out-slow` | Size | 1.16 | 1.00 |
| `pan-lr` | Size 1.18, Center.x | 0.41 | 0.59 |
| `pan-rl` | Size 1.18, Center.x | 0.59 | 0.41 |
| `drift-up` | Size 1.14, Center.y | 0.43 | 0.57 |

Note:

- Niente `comp:Lock()` durante i keyframe (rompe l'animazione).
- `comp:StartUndo()` / `EndUndo(True)` per un undo unico.
- Gli slot faccia restano statici: nessun comp.
- Con `baked` il comportamento è quello attuale, senza comp.

**Risultato spike (15 Nov):**
- `AddFusionComp()` funziona.
- `Transform` + wiring `MediaIn → Transform → MediaOut` funziona.
- `AddModifier("Size","BezierSpline")` + assegnazione indicizzata `t.Size[frame]`
  crea keyframe reali (letti indietro interpolati).
- `SetInput("Size", value, frame)` **non** crea keyframe: lascia solo
  l'ultimo valore costante.
- Point animation richiede `Path` modifier (non testato).
- Render del comp via `Saver` + `comp:Render({Start=0, End=N, Wait=true, Tool=saver})`
  produce frame PNG con animazione visibile (1.0 → 1.08 → 1.16).
- **Sostituzione confermata**: `MediaPoolItem:ReplaceClipPreserveSubClip("green.mp4")`
  mantiene clip timeline, source range (30..150), handle (30/30), comp e keyframe.
  Il render post-sostituzione mostra l'animazione sul nuovo media.
- **`ReplaceClip` semplice restituisce `None`**: non sostituisce il clip.

### 3. Transizioni native

`placeholders`, con `native_transitions: true`:

- calcola `handle_frames = ceil(transition_handle * fps)`;
- genera ogni segnaposto b-roll con `frames + 2*handle_frames` frame;
- il manifest registra `frames` e `handle_frames`.

`lua`:

- posiziona i clip con `startFrame = handle_frames` e
  `endFrame = handle_frames + frames`, così la durata visibile resta esatta;
- dopo aver posizionato tutti i clip V1, tenta la transizione nativa sullo slot
  in ingresso:
  - `cross-dissolve` → `type = "Cross Dissolve"`, `category = "simple"`,
    `position = "start"`, `alignment = "center"`, `duration = round(transition_in.duration * fps)`;
  - `dip-to-black` → `type = "Dip To Color Dissolve"` (capitalizzazione esatta);
    se il tipo non esiste, fallback overlay;
- legge `GetDuration()` dell'oggetto transizione restituito; se è 0, 1 frame o
  palesemente sbagliata (es. richiesto 999, ottenuto 30), la rimuove con
  `timeline:DeleteClips({transizione}, false)` e usa l'overlay;
- usa la transizione nativa solo se entrambi gli slot adiacenti sono b-roll e
  hanno handle; per faccia e bordi timeline resta l'overlay;
- verifica gli offset: il clip in ingresso deve avere `GetLeftOffset() >= duration/2`,
  quello in uscita `GetRightOffset() >= duration/2`; senza handle la chiamata
  restituisce `nil`;
- posiziona l'overlay V3 solo per le transizioni non native o fallite;
- stampa un riepilogo: native, overlay, fallite;
- tiene conto che `AddTransition` aggiunge un item alla traccia: i conteggi di
  verifica e il mock vanno aggiornati.

`glitch`, `flash`, `whip-pan` restano overlay: sono effetti, non transizioni
semplici.

**Risultato spike (15 Nov):**
- `Cross Dissolve` funziona con handle ≥ duration/2.
  - `alignment="center"` centra la transizione sul taglio.
  - Durata letta da `GetDuration()` coincide con quella richiesta.
  - Transizione appare come item separato nella traccia (`GetType() == "transition"`).
- `Dip To Color Dissolve` (con **T** maiuscola in `To`) funziona.
  - `Dip to Color Dissolve` (minuscolo) fallisce → `nil`.
  - **Il parametro colore non è esposto via scripting** (GUI-only). Default attuale
    in Resolve 21 è nero, ma non garantito. Se serve nero garantito, serve
    fallback overlay o preset utente.
- Richiesta durata eccessiva (es. 999 frame) → transizione creata con durata
  limitata (30 frame nel test), **nessun errore**. Lettura durata obbligatoria.
- `DeleteClips({transition}, false)` rimuove correttamente la transizione.
- Stesso bordo non può avere due transizioni: serve cancellare la prima.
- Offset confermati: `GetLeftOffset()`/`GetRightOffset()` restituiscono handle
  in frame. Se incoming ha 0 handle, `AddTransition` restituisce `nil`.

### 4. Audio

- **BGM ducking**: in `cmd_lua`, se `bgm.duck` (default true) genera
  `build/<slug>/audio/bgm_duck.wav` con `sidechaincompress` usando la voce come
  sidechain, poi applica gain e fade. `duck_db` mappa il ratio (valore assoluto
  limitato 2..12). Se il filtro fallisce, torna al mix attuale e avvisa.
- **Voce**: 5 ms di fade in/out su `vo_clean.wav` e `vo_clean_norm.wav` in
  `render-audio`, per evitare click ai bordi.
- **SFX**: 5 ms di fade in/out in `prep_sfx`, usando la durata dall'indice.
- **Voice Isolation**: in Lua, dopo A1, se `audio.voice_isolation` e il metodo
  esiste, chiama `timeline:SetVoiceIsolationState(1, {isEnabled=true,
  amount=N})`; stampa l'esito. Default dell'agente per i talking head: true.
- Loudness resta `-16 LUFS`, true peak `-1.5 dB`.

**Risultato spike (15 Nov):**
- `SetVoiceIsolationState(1, {isEnabled=true, amount=60})` funziona su A1.
- `GetVoiceIsolationState(1)` conferma lo stato.
- Ducking ffmpeg con `sidechaincompress` testato: threshold=0.05, ratio=8,
  attack=20ms, release=350ms, makeup=1 produce ducking udibile.
- `duck_db` → mappatura ratio: -9dB ≈ ratio 8; limitare ratio tra 2 e 12.

### 5. Rilevamento capacità e fallback

Il Lua non parsa la versione: verifica i metodi con `pcall` / nil check.

- `tlItem.AddFusionComp` assente → avviso forte; il segnaposto è statico.
  Il messaggio dice di rigenerare con `animation_mode: "baked"`.
- `tlItem.AddTransition` assente → fallback overlay, con avviso una volta sola.
- `timeline.SetVoiceIsolationState` assente → salta, con avviso.
- `SetFades` non usato in questa fase (i fade BGM sono già in ffmpeg).

### 6. Invalidazione segnaposto

Per evitare doppia animazione (baked + Fusion) quando si passa da `baked` a
`fusion` o viceversa:

- `placeholders` calcola un **fingerprint delle impostazioni** che influenzano
  i segnaposto: `animation_mode`, `native_transitions`, `transition_handle`,
  `format.fps`, `format.width`, `format.height`, versione del generatore.
- Lo salva in `build/<slug>/placeholders/settings_fingerprint.json`.
- Se il fingerprint cambia, rigenera **tutti** i segnaposto (come `--force`).
- Il manifest include `animation_mode` e `handle_frames` per ogni slot.

### 7. Mock Resolve per regressioni

Un mock locale in `scripts/lua/mock_resolve.lua` che espone:

- `TimelineItem`: `AddFusionComp`, `AddTransition`, `GetFusionCompCount`,
  `GetFusionCompByIndex`, `GetLeftOffset`, `GetRightOffset`, `GetDuration`,
  `GetType`, `GetStart`, `GetEnd`, `SetProperties`, `GetProperties`.
- `FusionComp`: `AddTool`, `FindTool`, `GetToolList`, `ConnectInput`,
  `StartUndo`, `EndUndo`, `SetAttrs`, `Render`.
- `Timeline`: `AppendToTimeline`, `GetItemListInTrack`, `GetTrackCount`,
  `AddTrack`, `SetTrackName`, `SetVoiceIsolationState`,
  `GetVoiceIsolationState`, `DeleteClips`, `AddMarker`.
- `Project`: `GetMediaPool`, `GetSetting`, `SetSetting`, `GetCurrentTimeline`.
- `MediaPool`: `ImportMedia`, `AddSubFolder`, `SetCurrentFolder`,
  `CreateEmptyTimeline`, `AppendToTimeline`.

Il mock verifica che lo script generato:
- non chiami API inesistenti;
- gestisca i fallback;
- produca i conteggi attesi (V1, V2, V3, V4, A1, A2, A3).

### 8. Documentazione e skill

Aggiornare:

- `README.md`: sezione "Studio 21.1.1: qualità" e nuovi flag.
- `WORKFLOW.md`: animazioni Fusion, transizioni native, handle, audio.
- `STYLE.md`: cosa cambia per il volto e per le transizioni.
- `AGENTS.md`: regole e checklist.
- `SKILL.md`: quando usare `fusion`/`native_transitions`, cosa dire all'utente.
- `references/shotlist-schema.md`: nuovi campi e regole.
- `references/resolve-lua.md`: nuovo flusso di posizionamento e fallback.

Punti da spiegare all'utente:

- dopo la sostituzione le animazioni restano: non vanno riapplicate;
- `cross-dissolve` e `dip-to-black` sono native, `glitch`/`flash`/`whip-pan`
  restano overlay;
- la BGM ora si abbassa da sola sotto la voce;
- Voice Isolation è attiva su A1 nei talking head.

## Testing

### Statico

- `python -m py_compile scripts/shorts.py`
- `luac -p` sullo script generato
- mock Resolve esteso con `AddTransition`, `AddFusionComp`,
  `SetVoiceIsolationState`, `GetDuration` sulla transizione

### Mock / regressione

- `test-demo` (baked, niente native): stessi conteggi di oggi.
- nuovo fixture `test-quality` (fusion + native): conteggi attesi, nessun
  percorso assoluto, marker corretti.
- `validate` sui casi limite: native senza fusion, handle fuori range,
  voice isolation fuori range.

### Spike dal vivo su progetto usa-e-getta

**COMPLETATO (15 Nov 2026)** su progetto `zz-quality-spike`, timeline
`spike_tl_185342`:

1. ✅ Crea progetto 1080x1920 30 fps.
2. ✅ Importa 3 clip sintetiche (grid, orange, blue) + green per sostituzione.
3. ✅ Aggiunge Fusion comp, verifica `GetFusionCompCount() == 1` e keyframe.
4. ✅ Render frame via Saver: animazione **visibile** nel render (1.0 → 1.08 → 1.16).
5. ✅ Sostituzione con `ReplaceClipPreserveSubClip`: comp e keyframe sopravvivono,
   render post-sostituzione mostra animazione sul nuovo media (green).
6. ✅ `Cross Dissolve` nativa con handle 30/30, durata 30 frame (1s), letta e
   verificata; `Dip To Color Dissolve` funziona (colore GUI-only).
7. ✅ Voice Isolation testata su A1.
8. 🔄 Da cancellare: progetto `zz-quality-spike` e artifact render temporanei.

Se il comp non sopravvive alla sostituzione, o se l'animazione non arriva
nell'export, il design cambia: il fallback è applicare le animazioni dopo la
sostituzione con un comando separato, e va approvato di nuovo.

### End-to-end

- genera il Lua di `test-quality`, eseguilo in Console su un progetto
  usa-e-getta, verifica i conteggi stampati e un frame esportato.

### Pulizia

- rimuovere i progetti temporanei, tenere solo i fixture.
- nessun percorso assoluto negli script generati.

## Rischi

| Rischio | Mitigazione |
|---|---|
| I keyframe Fusion non vengono committati | `AddModifier` + `SetInput`, lettura indietro, spike ✅ |
| I keyframe Fusion non arrivano nell'export | spike su frame esportato via Saver: **confermato arrivano** ✅ |
| La sostituzione perde il comp | spike: **ReplaceClipPreserveSubClip mantiene tutto** ✅ |
| `AddTransition` restituisce durata sbagliata | lettura `GetDuration`, `DeleteClips` + fallback overlay ✅ |
| Handle insufficienti dopo la sostituzione | verifica `GetLeftOffset`/`GetRightOffset` ≥ duration/2, fallback overlay ✅ |
| Comp su molti clip rallenta | solo slot `layer: "base"` non statici ✅ |
| Ducking pomposo | threshold/ratio conservativi, `duck: false` per disattivare ✅ |
| Colore `Dip To Color` non garantito | fallback overlay se serve nero garantito; documentare |

## Rollback

Ripristinare il backup:

```bash
mkdir -p ~/restore && tar -xzf ~/shorts-studio-backups/shorts-studio-20261115-100056.tar.gz -C ~/restore
```

## Questioni aperte — RISOLTE DALLO SPIKE

- ~~Il nome esatto `"Dip to Color Dissolve"` va verificato sull'installazione.~~
  → **Confermato: `"Dip To Color Dissolve"` (T maiuscola).** `Dip to Color Dissolve` fallisce.
- ~~Se non esiste, `dip-to-black` resta overlay.~~ → Esiste e funziona. Colore non
  controllabile via API; default nero in 21.1.1. Documentato come fallback overlay
  se serve garanzia.
- Gli slot faccia sono esclusi dalle transizioni native in questa fase; se
  servono, si aggiungono handle anche a `vo_clean.mp4`.

## Questioni ancora aperte — RICHIEDONO DECISIONE

1. **Default `bgm.duck`**: `true` (opt-out) o `false` (opt-in)?
   - *Pro true*: qualità immediata per tutti i progetti Studio.
   - *Pro false*: retrocompatibilità assoluta; progetti esistenti non cambiano.
   - *Proposta*: **`false` default**, l'agente lo imposta a `true` per i talking head.

2. **Micro-fade voce/SFX (5ms)**: opt-in o sempre attivi?
   - Sono impercettibili e prevengono click. Non cambiano la durata percepita.
   - *Proposta*: **sempre attivi** in `render-audio` e `prep_sfx`; nessun flag.

3. **Sostituzione manuale F11 / "Replace Selected Clip"**: preserva gli handle
   subclip come `ReplaceClipPreserveSubClip`?
   - Lo spike ha testato solo l'API. Il workflow manuale va verificato
     dall'utente in Resolve (seleziona clip in Media Pool → Clip Operations →
     Replace Selected Clip → scegli file). Se non preserva, serve nota nel
     WORKFLOW.md.

4. **Fallback `cross-dissolve` senza handle**: messaggio manuale "serve
   `transition_handle` nei segnaposto" oppure overlay `dip-to-black`?
   - *Proposta*: **messaggio esplicito** — l'utente rigenera con handle o accetta
     l'overlay.

5. **`test-quality` fixture**: creare ora o dopo l'implementazione?
   - *Proposta*: dopo, come primo test end-to-end.

---

**Prossimo passo**: Approvazione del design aggiornato → invoco `writing-plans` → implementazione in `scripts/shorts.py` + aggiornamento docs/skill.