# Resolve free + Lua: cosa si puo fare davvero

Riferimento per capire cosa lo script generato fa, e cosa l'API non permette.

---

## Contesto

Da **Resolve 21.1** lo scripting Python esterno, il menu `Workspace > Scripts` e il server MCP ufficiale
sono **Studio-only**. La versione free mantiene lo scripting **interno alla Console** (`Workspace > Console`),
che accetta Lua e Python.

Noi usiamo solo Lua in Console. Nel free, `resolve`, `bmd` e `fusion` sono gia definiti come globali:
non serve `Resolve()`.

```lua
print(resolve:GetVersion())
```

---

## Cosa fa `build/<slug>/<slug>_build.lua`

1. `project:SetSetting` per frame rate e risoluzione (1080x1920)
2. crea il bin `SHORTS_<slug>`
3. importa segnaposto, voiceover, SFX, BGM
4. crea la timeline `<slug>_v1` (se esiste, la rinomina `_old_HHMMSS`)
5. aggiunge tracce e le nomina:
   - V1 `B-ROLL` (segnaposto + clip A-roll della faccia)
   - V2 `OVERLAY`
   - V3 `TRANSITIONS` (solo se ci sono transizioni automatiche)
   - V4 `CAPTIONS` (solo se ci sono caption)
   - A1 `VOICE`
   - A2 `SFX`
   - A3 `BGM`
6. appende i clip con `AppendToTimeline({ mediaPoolItem, trackIndex, recordFrame })`;
   per gli slot faccia aggiunge anche `startFrame = 0` e `endFrame = frames` (bound esclusivo),
   cosi la durata A-roll e esatta al frame
7. colora i clip (`SetClipColor`) in base a `kind` (A-roll = `Cyan`)
8. applica lo `zoom` statico (`SetProperty("ZoomX"/"ZoomY", ...)`)
9. applica `opacity` (`SetProperty("Opacity", ...)`) e `blend` (`SetProperty("CompositeMode", ...)`)
10. mette su V3 gli overlay alpha delle transizioni (a cavallo del taglio) e su V4 le card caption
11. mette in timeline i file audio già preparati da `shorts.py lua`:
    SFX con il gain cotto, BGM loopata/tagliata con fade in `build/<slug>/audio/`
12. aggiunge un marker per slot con note multilinea
13. verifica e stampa il report

> Il volume dei clip **non** è esposto dall'API: per questo il gain viene applicato con ffmpeg
> prima dell'import. Non cercare `SetProperty("Volume", ...)`: non esiste.

---

## `recordFrame`: la funzione chiave

```lua
timeline:AppendToTimeline({
  { mediaPoolItem = item, trackIndex = 2, recordFrame = 150 }
})
```

`recordFrame` e il frame di timeline in cui parte il clip. Senza, tutto si accoda.

E disponibile nelle versioni recenti (21.x). Se i clip finiscono tutti a 0, la tua versione e vecchia:
aggiorna Resolve. Il report finale (`V2: N clip`) aiuta a capirlo.

Per gli slot faccia passiamo anche `startFrame`/`endFrame`: nell'API Resolve **`endFrame` e esclusivo**,
quindi `endFrame = frames` da una durata di `frames` frame (non `frames - 1`).

---

## Cosa NON si puo fare dall'API

| Cosa | Stato | Alternativa |
|---|---|---|
| creare una vera transizione tra due clip | non esposto | overlay alpha su V3 (glitch/flash/dip/whip-pan), gia fatto; `cross-dissolve` manuale |
| keyframe di Transform/Opacity in Edit | non esposto | template Fusion, o manuale |
| creare nodi Fusion via script | non documentato | template `.setting` + `ImportFusionComp` |
| creare una traccia sottotitoli / importare SRT | non esposto nel free | card caption QTRLE su V4 + `captions.srt` |
| `CreateSubtitlesFromAudio` | Studio/AI-only | caption gia cotte da `shorts.py` |
| cambiare velocita di un clip | non esposto | manuale |
| volume/pan audio del clip | non esposto | gain con ffmpeg (già fatto) + Fairlight |
| testo con font preciso via API | non esposto | Text+ / template |
| render automatico affidabile | parziale | Deliver page / `90_render_queue.lua` |

Sono invece esposti e li usiamo: `ZoomX`/`ZoomY`, `Opacity`, `CompositeMode` (blend mode).

Quindi lo script costruisce **struttura, timing, audio, caption e transizioni a overlay**. Le uniche
cose che restano manuali sono la dissolvenza reale (`cross-dissolve`), i movimenti di camera animati
dopo la sostituzione (template Fusion) e la rifinitura fine di audio/colore.

---

## Marker

```lua
timeline:AddMarker(frame, "Blue", "s03 SCREENSHOT", note, duration)
```

- il colore segue `kind` (gli A-roll sono `Cyan`)
- `note` contiene: cosa mettere, consigliato, perche, animazione, transizione; per gli slot faccia
  la prima riga e `A-ROLL/FACCIA: gia tagliata, non sostituire`
- cliccando il marker in Edit leggi tutto

I marker sono la documentazione del montaggio: non cancellarli finche non hai finito.

---

## Sostituzione e cosa resta

- **V1/V2**: `Replace Selected Clip` (o F11) sostituisce il segnaposto. Zoom/opacity/blend statici
  restano; i movimenti di camera cotti nel segnaposto no (riapplica il template Fusion).
- **V1 A-roll**: le clip `source: "face"` sono gia media veri, tagliati da `vo_clean.mp4`. Non vanno
  sostituite: non hanno una card e il marker lo dice. Un eventuale push-in si applica a mano.
- **V3**: le transizioni sono clip separati. Non si toccano quando sostituisci V1/V2, quindi
  glitch/flash/dip/whip-pan restano gia a posto.
- **V4**: le caption sono clip video, non una traccia sottotitoli. Restano sopra il montaggio e non
  vanno rifatte. Se cambi una parola, rigenera da `words.json` con `shorts.py captions <slug> --force`
  e rilancia il Lua (la caption e cotta nell'immagine, non e testo editabile in Resolve).

---

## Import e percorsi

Lo script non contiene percorsi assoluti. All'avvio cerca la radice del progetto in:

1. `SHORTS_ROOT`, se l'utente l'ha impostata in Console;
2. `~/shorts-studio`;
3. la cartella corrente.

Controlla che esista `build/<slug>/placeholders/manifest.json` e poi costruisce i percorsi dei media
come `DATA.root .. "/" .. percorso relativo`. Se la cartella è altrove basta:

```lua
SHORTS_ROOT = "/percorso/della/cartella"
```

prima di lanciare lo script. Non serve rigenerare niente.

---

## Debug dalla Console

Errori comuni:

```text
attempt to index a nil value (global 'resolve')
```
Stai lanciando lo script da terminale. Trascinalo nella Console.

```text
CreateEmptyTimeline → nil
```
Nessun progetto aperto.

```text
!! file mancante: /.../s07_ovl.mov
```
Manca un segnaposto: `placeholders --force`.

```text
A2 sfx: 0
```
`recordFrame` ignorato o file audio non importati. Controlla la versione e rilancia `scan`.

```text
V3 transizioni: 0
V4 caption: 0
```
Nessun asset generato: lancia `placeholders --force` (le caption richiedono `words.json` da
`render-audio`). Se lo shotlist non ha transizioni automatiche o caption, le tracce non vengono create:
e normale.

```text
[warn] captions saltate: manca build/<slug>/words.json
```
Hai lanciato `placeholders` prima di `render-audio`. Rilancia `render-audio`, poi `placeholders --force`.

```text
mancano le clip faccia: build/<slug>/vo_clean.mp4 non esiste
```
Hai slot `source: "face"` ma non hai tagliato il video. Lancia
`render-audio <slug> --video` (con `--normalize` se vuoi) e poi `placeholders --force`.

Per ispezionare a mano:

```lua
local p = resolve:GetProjectManager():GetCurrentProject()
print(p:GetName())
print(p:GetTimelineCount())
local tl = p:GetCurrentTimeline()
```

---

## Limiti del free da ricordare

- niente Magic Mask, Voice Isolation, speech-to-text nativo
- niente Python esterno / MCP
- niente alcuni preset AI
- il resto (edit, Fusion, Fairlight, color, render 1080p) c'e

Per un Short a 1080x1920 il free e piu che sufficiente.
