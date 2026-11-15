# presets/fusion/

Le animazioni dei segnaposto sono **dentro i file MP4**: quando sostituisci il segnaposto con il tuo
clip, quel movimento sparisce. Qui impari a ricrearlo una volta sola come effetto riutilizzabile.

Hai tre strade, dalla più semplice:

1. **Zoom statico** — già applicato dallo script (`zoom` nello shotlist). Nessun movimento, ma
   l'inquadratura è già tagliata. Sopravvive alla sostituzione.
2. **Fusion Effect Template** — la strada consigliata: crei 5 effetti e li trascini sui clip.
3. **ImportFusionComp da Console** — sperimentale: vedi `scripts/lua/20_fusion_probe.lua`.

---

## 1. Creare un Fusion Effect Template (zoom in)

Serve una volta sola, poi vale per tutti i progetti.

### Passo per passo

1. Apri un progetto in Resolve, metti un clip qualsiasi su V1 e selezionalo.
2. Vai nella pagina **Fusion**.
3. Nel Node Editor vedi `MediaIn` e `MediaOut`.
4. Seleziona `MediaIn`, premi **Shift+Spazio**, scrivi `Transform` e premi Invio.
5. Collega: `MediaIn` → `Transform` → `MediaOut`.
6. Seleziona il nodo `Transform`. Nell'Inspector:
   - porta il playhead al frame **0**;
   - su **Size** imposta `1.0`, click sul diamante a sinistra del valore per creare il keyframe;
   - porta il playhead al frame **24**;
   - imposta **Size** `1.16` (crea il secondo keyframe automaticamente);
   - premi play: il clip deve spingere avanti e poi restare fermo.
7. Con il solo nodo `Transform` selezionato, click destro → **Macro > Create Macro**.
8. Nella finestra Macro Editor puoi spuntare i parametri che vuoi vedere in Inspector
   (es. `Size`). Per un effetto semplice puoi anche chiudere subito con **Close**.
9. Si apre **Save Macro As**. Salva in:

```text
macOS:   ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/Effects
Linux:   ~/.local/share/DaVinciResolve/Fusion/Templates/Edit/Effects
Windows: %APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Templates\Edit\Effects
```

Crea una sottocartella `ShortsStudio` e salva come `Zoom In Slow.setting`.

10. **Chiudi e riapri Resolve.**
11. Vai in Edit → Effects Library → **Effects > Fusion Effects > ShortsStudio**.
    Trovi `Zoom In Slow`.
12. Seleziona uno o più clip e fai doppio click sull'effetto (oppure trascinalo sul clip).

> Se non vedi la cartella giusta: click destro sulla categoria nella Effects Library →
> **Show Folder**. È il percorso vero della tua installazione, più affidabile di qualsiasi tutorial.

### Il problema della durata

I keyframe sono in **frame**, non in secondi. Un template da 24 frame dura 0.8s a 30fps:
su un clip da 1s fa in tempo, su uno da 4s spinge per 0.8s e poi resta fermo. Va bene.
Se vuoi un movimento più lento, crea una variante con i keyframe a 48 frame.

Non provare a far adattare l'animazione alla lunghezza del clip con le espressioni se non sei
pratico: è possibile, ma fragile. Due varianti (fast/slow) coprono quasi tutto.

---

## I 5 template da creare

Tutti con `MediaIn → Transform → MediaOut`, solo il nodo Transform nella macro.

| Nome file | Keyframe | Valori |
|---|---|---|
| `Zoom In Slow.setting` | 0 → 24 | Size `1.0` → `1.16` |
| `Zoom In Fast.setting` | 0 → 10 | Size `1.0` → `1.14` |
| `Zoom Out Slow.setting` | 0 → 24 | Size `1.16` → `1.0` |
| `Pan Left Right.setting` | 0 → 30 | Size `1.15` fisso; Center X `-0.04` → `0.04` |
| `Drift Up.setting` | 0 → 30 | Size `1.14` fisso; Center Y `0.03` → `-0.03` |

Per il pan opposto (`pan-rl`) duplica `Pan Left Right` e inverti i valori di Center X.

Suggerimenti:

- Con `Size` a 1.15–1.18 non vedi bordi neri durante il pan.
- Se il movimento è troppo brusco, apri lo **Spline Editor** e cambia i keyframe da spline a lineare
  (o aggiungi ease).
- Un template applicato a un clip che ha già una Fusion comp aggiunge una seconda comp:
  controlla la lista delle comp nella pagina Fusion e tieni quella che ti serve.

---

## 2. Effetti globali (CRT, grana, scanline)

Questi non vanno sul singolo clip: vanno su tutta la timeline.

1. Metti un **Adjustment Clip** su V3, sopra tutti i clip e lungo quanto la timeline.
2. Applica da Effects Library:
   - **Resolve FX Texture > Film Grain** (dosaggio leggero)
   - **Resolve FX Texture > Scanline** (se presente nella tua versione)
   - oppure un PNG di scanline tuo, con blend mode **Screen**.
3. Per il blend mode: Inspector → Composite → **Blend Mode**. Nei clip gestiti dallo script
   puoi anche usare il campo `"blend"` dello shotlist.

Il risultato è lo stesso per tutti i clip e non devi rifarlo dopo ogni sostituzione.

---

## 3. Alternativa: copiare gli attributi

Se hai già un clip animato e vuoi lo stesso movimento su un altro:

1. Seleziona il clip sorgente, **Cmd+C** (Ctrl+C su Linux).
2. Seleziona i clip di destinazione.
3. Click destro → **Paste Attributes**.
4. Spunta **Fusion Composition** (e ciò che ti serve).

È più veloce che ricreare l'effetto, ma non è riutilizzabile tra progetti.

---

## Verifica

Dopo aver sostituito un segnaposto e applicato il template:

- il clip deve muoversi nei primi frame e poi restare stabile;
- non devono apparire bordi neri;
- il marker dello slot deve essere ancora al suo posto;
- il grade e il transform del clip devono essere intatti.

Se qualcosa non torna, il problema è quasi sempre l'ordine dei nodi nel template:
`MediaIn` deve entrare nel `Transform`, e il `Transform` deve uscire in `MediaOut`.
