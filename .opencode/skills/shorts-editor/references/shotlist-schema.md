# Shotlist — schema completo

File: `projects/<slug>/shotlist.json`
Validato da: `python scripts/shorts.py validate <slug>`

---

## Struttura

```json
{
  "project": "slug",
  "title": "Titolo del video",
  "format": { "width": 1080, "height": 1920, "fps": 30 },
  "style": "ps2-crt",
  "voiceover": "build/<slug>/vo_clean.wav",
  "voiceover_duration": 58.4,
  "face_fit": "crop",
  "bgm": {
    "file": "media/bgm/ps2-menu.mp3",
    "gain_db": -24,
    "duck_db": -9,
    "loop": true
  },
  "captions": {
    "enabled": true,
    "position": "lower",
    "max_words": 4,
    "max_chars": 32,
    "max_duration": 3.2,
    "font_size": 66,
    "uppercase": false,
    "background": 0.55,
    "color": "#FFFFFF"
  },
  "slots": []
}
```

| Campo | Tipo | Obbligatorio | Note |
|---|---|---|---|
| `project` | string | si | deve coincidere con lo slug |
| `title` | string | no | usato solo per leggibilita |
| `format` | object | si | **1080x1920 @ 30** e il default per Shorts |
| `style` | string | si | `anime90`, `crt`, `ps2`, `frutiger-aero`, `clean` |
| `voiceover` | string | si | percorso di `vo_clean.wav` (o `.mp4`) |
| `voiceover_duration` | number | si | durata in secondi del voiceover pulito |
| `face_fit` | string | no | `crop` (default) o `fit`: come adattare il talking head al verticale |
| `face_video` | string | no | override avanzato: A-roll gia tagliato in sync. Default `build/<slug>/vo_clean.mp4` |
| `bgm` | object/null | no | se `null`, niente musica |
| `captions` | object | no | default attivo, terzo inferiore; vedi sotto |
| `slots` | array | si | almeno uno |

> La lingua del voiceover non sta nello shotlist: si imposta in `projects/<slug>/project.json`
> (`"language": "auto" | "it" | "en" | ...`) oppure con `transcribe --language`.
> Vale per italiano e inglese senza cambiare pipeline.

### `bgm`

| Campo | Tipo | Note |
|---|---|---|
| `file` | string | percorso in `media/bgm/` |
| `gain_db` | number | negativo. -24 e un buon punto di partenza |
| `duck_db` | number | quanto abbassare sotto la voce (indicativo, il ducking e manuale) |
| `loop` | bool | se true la BGM viene loopata fino alla durata della timeline |

Da `lua` viene creato `build/<slug>/audio/bgm_mix.wav`: loop, taglio esatto alla durata
della timeline, fade in/out e gain sono già dentro. In timeline c'è **un solo clip**.
Il ducking sotto la voce resta manuale (Fairlight, keyframe).

### `captions`

Per gli Shorts sono **obbligatorie**. Sono card statiche (non word-by-word), nel terzo inferiore,
max 2 righe, con sfondo semi-trasparente. Vengono generate da `words.json` (prodotto da
`render-audio`) e messe su una traccia video dedicata, sopra le transizioni.

| Campo | Default | Note |
|---|---|---|
| `enabled` | `true` | se `false`, niente caption (sconsigliato) |
| `position` | `lower` | `lower`, `middle`, `upper` |
| `max_words` | `4` | 3-5 e il range leggibile |
| `max_chars` | `32` | limita la larghezza della card |
| `max_duration` | `3.2` | secondi; evita card che restano troppo |
| `font_size` | `66` | a 1080x1920 e gia grande; il codice riduce per far stare 2 righe |
| `uppercase` | `false` | per l'italiano lascialo false |
| `background` | `0.55` | alpha del pannello nero, 0-1 |
| `color` | `#FFFFFF` | colore del testo |

Output: `build/<slug>/captions/c###.mov` (QTRLE alpha), `manifest.json` e `captions.srt`.
Il testo non e modificabile in Resolve come sottotitolo: le caption sono clip video. L'SRT e la copia
esportabile per YouTube/TikTok o per un altro editor.

---

## Slot

```json
{
  "id": "s03",
  "start": 12.4,
  "duration": 2.1,
  "layer": "base",
  "kind": "screenshot",
  "intent": "Screenshot del profilo SpaceHey del 2005, pan da sinistra a destra",
  "suggest": {
    "primary": "media/screenshots/spacehey-profilo-2005.png",
    "alternatives": [
      "media/screenshots/spacehey-home.png"
    ],
    "why": "La frase descrive il profilo personalizzabile: e la feature che lo distingueva da MySpace."
  },
  "animation": "pan-lr",
  "zoom": 1.0,
  "opacity": 100,
  "blend": "normal",
  "transition_in": { "type": "cut" },
  "sfx": [
    { "file": "media/sfx/transizione-1.wav", "at": 0.0, "gain_db": -12 }
  ],
  "text": null
}
```

### Campi

| Campo | Tipo | Obbligatorio | Vincoli |
|---|---|---|---|
| `id` | string | si | univoco, `s01`... |
| `start` | number | si | >= 0, secondi nel tempo pulito |
| `duration` | number | si | > 0 |
| `layer` | enum | si | `base` o `overlay` |
| `source` | enum | no | `broll` (default) o `face` (talking head gia tagliato) |
| `kind` | enum | si | `clip`, `image`, `logo`, `screenshot`, `text`, `ui` |
| `intent` | string | si | >= 8 caratteri, specifico |
| `suggest.primary` | string | si | percorso esistente **oppure** `?descrizione` |
| `suggest.alternatives` | array | no | stessa regola |
| `suggest.why` | string | si | >= 15 caratteri, spiega la scelta |
| `animation` | enum | si | vedi sotto |
| `zoom` | number | no | 1.0 = nessuno. Transform statico (`ZoomX`/`ZoomY`) |
| `opacity` | number | no | 0–100, default 100. Utile per overlay |
| `blend` | enum | no | `normal`, `add`, `multiply`, `screen`, `overlay` |
| `transition_in` | object | no | `{ "type": "...", "duration": 0.3 }` |
| `sfx` | array | no | `file`, `at`, `gain_db` |
| `text` | string/null | solo `kind: text` | il testo da mostrare |

### Enumerazioni

**layer**

- `base` → V1, copre il voiceover
- `overlay` → V2, sopra un base, con alpha

**source**

- `broll` (default) → il normale segnaposto da sostituire
- `face` → talking head gia registrato: `placeholders` taglia `build/<slug>/vo_clean.mp4` in
  `build/<slug>/aroll/<id>_face.mp4` e lo mette su V1. Richiede `layer: "base"`, `kind: "clip"` e
  `animation: "static"`; il clip non va sostituito. Serve `render-audio --video`.
  Il campo `suggest` resta obbligatorio per documentare lo slot, ma il file suggerito non viene usato:
  scrivi `"?la tua faccia, gia tagliata dal video"` e spiega nel `why` perche li si vede il volto.

**face_fit** (top-level, solo talking head)

| valore | effetto | quando |
|---|---|---|
| `crop` | riempie 1080x1920 tagliando i lati | default; video orizzontale con volto centrale |
| `fit` | letterbox, niente tagli | volto o testo che non puoi tagliare, video gia verticale con margini |

Se il volto non e centrato, usa `crop` e sposta il clip in Resolve con Transform: il file A-roll e
comunque generato a 1080x1920.

Le tracce V3 `TRANSITIONS` e V4 `CAPTIONS` vengono aggiunte dallo script Lua solo se ci sono
transizioni automatiche o caption. Non sono slot: non metterle nello shotlist.

**kind**

| valore | colore | significato |
|---|---|---|
| `clip` | blu | video in movimento |
| `image` | verde | immagine statica |
| `logo` | arancione | logo, con alpha |
| `screenshot` | viola | sito, app, UI |
| `text` | giallo | cartello |
| `ui` | rosa | elemento grafico/HUD |

**animation**

| valore | effetto | quando |
|---|---|---|
| `static` | fermo | gameplay gia movimentato |
| `push-in-slow` | zoom 1.0 → 1.16 | immagini, momenti importanti |
| `pull-out-slow` | zoom 1.16 → 1.0 | chiusura di un concetto |
| `push-in-fast` | zoom rapido a inizio slot | logo, reveal |
| `pan-lr` | panoramica sinistra → destra | screenshot larghi |
| `pan-rl` | panoramica destra → sinistra | screenshot, alternativa |
| `drift-up` | leggero movimento verso l'alto | immagini verticali |

**blend**

| valore | effetto | uso |
|---|---|---|
| `normal` | normale | default |
| `screen` | schiarisce | scanline, light leak, loghi chiari |
| `add` | somma | bagliori, particelle |
| `multiply` | moltiplica | ombre, texture scure |
| `overlay` | contrasto | grana, texture |

Viene applicato come `CompositeMode` sul clip. Se il blend non serve, lascia `normal`.

**transition_in.type**

`cut`, `cross-dissolve`, `dip-to-black`, `glitch`, `whip-pan`, `flash`

| tipo | automatico | effetto |
|---|---|---|
| `cut` | si | nessun overlay, taglio netto |
| `glitch` | si | bande RGB/scanline per 0.2-0.8s sul taglio |
| `flash` | si | lampo bianco |
| `dip-to-black` | si | buio e ritorno |
| `whip-pan` | si | strisce di movimento orizzontali |
| `cross-dissolve` | **no** | vera dissolvenza tra clip: va fatta a mano in Edit |

Gli automatici diventano overlay alpha in `build/<slug>/transitions/`, messi su V3 a cavallo del
taglio. **Restano anche dopo `Replace Selected Clip`**, perche non sono dentro il segnaposto.
`duration` e opzionale (default 0.4s, limitata a 0.2-0.8s e alla durata dello slot).
Usali solo sui punti di svolta: 2-4 per Short, non su ogni taglio.

**sfx**

```json
{ "file": "media/sfx/whoosh-2.wav", "at": 0.4, "gain_db": -10 }
```

- `at` e relativo all'inizio dello slot (secondi)
- deve stare dentro la durata dello slot
- `gain_db` e opzionale, default 0

---

## Esempio talking head (2 slot)

```json
{
  "project": "mia-faccia",
  "title": "Ho provato per 30 giorni...",
  "format": { "width": 1080, "height": 1920, "fps": 30 },
  "style": "clean",
  "voiceover": "build/mia-faccia/vo_clean.wav",
  "voiceover_duration": 4.8,
  "face_fit": "crop",
  "bgm": null,
  "captions": { "enabled": true, "position": "lower" },
  "slots": [
    {
      "id": "s01",
      "start": 0.0,
      "duration": 2.6,
      "layer": "base",
      "source": "face",
      "kind": "clip",
      "intent": "Talking head: gancio, guardo in camera e dico la promessa del video",
      "suggest": {
        "primary": "?la tua faccia, gia tagliata dal video",
        "alternatives": [],
        "why": "Il gancio personale funziona se lo spettatore vede la faccia e sente il tono."
      },
      "animation": "static",
      "zoom": 1.0,
      "transition_in": { "type": "cut" },
      "sfx": [],
      "text": null
    },
    {
      "id": "s02",
      "start": 2.6,
      "duration": 2.2,
      "layer": "base",
      "kind": "clip",
      "intent": "B-roll: il risultato di cui parlo, ripresa dal mio footage",
      "suggest": {
        "primary": "?clip tuo del risultato",
        "alternatives": [],
        "why": "Quando arriva il dato concreto, lascia la faccia e mostra la prova."
      },
      "animation": "static",
      "zoom": 1.05,
      "transition_in": { "type": "dip-to-black", "duration": 0.4 },
      "sfx": [],
      "text": null
    }
  ]
}
```

Prima di questo shotlist servono `render-audio --video` e `vo_clean.mp4`. `placeholders` crea
`build/mia-faccia/aroll/s01_face.mp4`; lo slot s02 resta un segnaposto da sostituire.

---

## Esempio completo (4 slot)

```json
{
  "project": "esempio-spacehey",
  "title": "Cosa sono questi social che NESSUNO conosce?",
  "format": { "width": 1080, "height": 1920, "fps": 30 },
  "style": "frutiger-aero",
  "voiceover": "build/esempio-spacehey/vo_clean.wav",
  "voiceover_duration": 9.0,
  "bgm": { "file": "media/bgm/y2k-loop.mp3", "gain_db": -26, "loop": true },
  "captions": {
    "enabled": true,
    "position": "lower",
    "max_words": 4,
    "max_chars": 32,
    "font_size": 66,
    "uppercase": false
  },
  "slots": [
    {
      "id": "s01",
      "start": 0.0,
      "duration": 2.0,
      "layer": "base",
      "kind": "screenshot",
      "intent": "Home di SpaceHey nel 2005, sfondo azzurro e profilo personalizzato",
      "suggest": {
        "primary": "media/screenshots/spacehey-home-2005.png",
        "alternatives": ["media/screenshots/spacehey-profilo.png"],
        "why": "Il gancio e la domanda: devi mostrare subito la cosa di cui nessuno parla."
      },
      "animation": "push-in-slow",
      "zoom": 1.0,
      "transition_in": { "type": "cut" },
      "sfx": [{ "file": "media/sfx/whoosh-2.wav", "at": 0.0, "gain_db": -12 }],
      "text": null
    },
    {
      "id": "s02",
      "start": 2.0,
      "duration": 3.0,
      "layer": "base",
      "kind": "clip",
      "intent": "Screen recording: scroll del profilo, musica che parte dal player",
      "suggest": {
        "primary": "media/clips/spacehey/scroll-profilo.mp4",
        "alternatives": ["?registrazione tua dello scroll"],
        "why": "SpaceHey si capisce usandolo: il movimento mostra le funzioni meglio di una foto."
      },
      "animation": "static",
      "zoom": 1.0,
      "transition_in": { "type": "glitch", "duration": 0.4 },
      "sfx": [{ "file": "media/sfx/ui-click-1.wav", "at": 0.2, "gain_db": -14 }],
      "text": null
    },
    {
      "id": "s03",
      "start": 5.0,
      "duration": 2.5,
      "layer": "base",
      "kind": "logo",
      "intent": "Logo SpaceHey su fondo cielo, reveal con zoom",
      "suggest": {
        "primary": "?logo SpaceHey (screenshot del sito, ritagliato da te)",
        "alternatives": [],
        "why": "Nomini la piattaforma: il logo chiude il primo blocco e fissa il nome."
      },
      "animation": "push-in-fast",
      "zoom": 1.0,
      "transition_in": { "type": "flash", "duration": 0.35 },
      "sfx": [{ "file": "media/sfx/pop-1.wav", "at": 0.05, "gain_db": -10 }],
      "text": null
    },
    {
      "id": "s04",
      "start": 7.5,
      "duration": 1.5,
      "layer": "overlay",
      "kind": "text",
      "intent": "Cartello: 'esiste dal 2003'",
      "suggest": {
        "primary": "?testo animato, lo crei in Resolve",
        "alternatives": [],
        "why": "Il dato chiave va letto, non ascoltato di sfuggita."
      },
      "animation": "static",
      "zoom": 1.0,
      "transition_in": { "type": "cut" },
      "sfx": [],
      "text": "esiste dal 2003"
    }
  ]
}
```

---

## Errori di validazione comuni

| Messaggio | Correzione |
|---|---|
| `file inesistente nell'indice` | il file non e in `media/`. Cambia percorso o metti `?` |
| `buco nel layer base` | due slot non si toccano: aggiusta `start`/`duration` |
| `gli slot coprono X ma il voiceover dura Y` | la somma delle durate deve essere Y (tolleranza 0.25s) |
| `overlay fuori da qualsiasi slot base` | l'overlay deve stare dentro un base |
| `suggest.why mancante` | scrivi perche hai scelto quel materiale |
| `animation non valida` | usa uno dei 7 valori |
| `sfx a X fuori dallo slot` | `at` deve essere < durata |
| `transition_in.type non valida` | usa `cut`, `cross-dissolve`, `dip-to-black`, `glitch`, `whip-pan`, `flash` |
| `cross-dissolve resta manuale` | e un avviso: nessun overlay automatico per la dissolvenza |
| `captions.position non valida` | usa `lower`, `middle` o `upper` |
| `captions.X non numerico` | controlla i numeri della configurazione caption |
| `source 'X' non valido` | usa `broll` o `face` |
| `source=face richiede layer=base` | la faccia e un base, non un overlay |
| `manca build/<slug>/vo_clean.mp4` | registra in video e lancia `render-audio --video` |
| `slot faccia fino a X ma il video dura Y` | i tempi superano il video: ricontrolla `vo_clean.txt` |

---

## Suggerimenti di regia

- **Hook**: primo slot 1-2s, il materiale piu forte che hai. Non iniziare con un logo.
- **Pattern**: alterna piani larghi e dettagli. Tre screenshot di fila annoiano.
- **Numeri**: quando dici un numero, mettilo a schermo (`kind: text`).
- **Nomi**: quando nomini un gioco/sito, mostra il logo o il titolo.
- **Fine**: l'ultimo slot puo essere piu lungo (3-4s) e chiudere con una domanda o un logo.
- **Faccia**: se hai il talking head, non lasciarla per tutto il video. Torna sul volto ogni 20-40s,
  all'inizio e alla fine; nel mezzo usa b-roll per mostrare quello che dici.
- **Slot "?"**: se sono piu di 5, il video non e pronto. Dillo all'utente prima di generare.
