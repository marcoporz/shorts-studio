# Workflow completo

Questo e il flusso operativo. Le fasi 2-7 le prepara l'AI/CLI (OpenCode). Le fasi 8-11 le fai tu
in Resolve: sostituisci gli slot, rifinisci audio/colore, esporti. La fase 12 (QC) torna all'AI.

```text
 voiceover o video con la faccia + media
        |
        v
 [1] scan          media/index.json
        |
        v
 [2] transcribe    transcript.json / .txt / .srt
        |
        v
 [3] roughcut      cuts.json + review.md      (silenzi, riempitivi, ripetizioni)
        |
        v
 [4] render-audio  vo_clean.wav + vo_clean.txt + words.json
        |          (--video: vo_clean.mp4 con la faccia tagliata)
        v
 [5] shotlist      projects/<slug>/shotlist.json    <-- la regia, slot per slot
        |
        v
 [6] validate + placeholders                        <-- segnaposto + A-roll + caption + transizioni
        |
        v
 [7] lua           build/<slug>/<slug>_build.lua
        |
        v
 [8] RESOLVE       timeline + marker + caption + transizioni + SFX + BGM
        |
        v
 [9] tu            sostituisci solo i segnaposto, rifinisci, esporti
```

---

## Fase 1 — Materiali

### Cartelle

| Cartella | Cosa mettere | Formato |
|---|---|---|
| `media/clips/<gioco>/` | gameplay registrato da te | mp4/mov, 1080p+ |
| `media/images/` | artwork, foto, frame estratti | png/jpg |
| `media/logos/` | logo del canale, loghi giochi | png con alpha |
| `media/screenshots/` | screenshot di siti e app | png |
| `media/voiceover/raw/` | la registrazione della voce, anche in video (talking head) | wav 48kHz (meglio) o mp4/mov |
| `media/sfx/` | effetti con nomi fissi | wav 48kHz |
| `media/bgm/` | musica | mp3/wav |

### Nomi dei file

Il nome del file e un'informazione che l'AI usa per capire cosa stai dando:

```text
fallout3-vault101-uscita.mp4
fallout3-downtown-dc-panoramica.mp4
newvegas-dialogo-sunny.mp4
spacehey-profilo-2005.png
spacehey-musica-player.png
logo-canale.png
logo-newvegas.png
```

Regola: `<progetto>-<contenuto>-<dettaglio>`. Niente `IMG_4821.MOV`.

### Copyright

L'AI non scarica niente. Tu puoi usare:

- gameplay registrato da te;
- screenshot che fai tu;
- trailer e press kit ufficiali (con giudizio);
- asset con licenza compatibile (Wikimedia, CC0), citando la fonte.

Non usare clip di altri youtuber, montaggi di terzi, musica non licenziata.
Il campo `suggest` dello shotlist ti dice sempre cosa manca: se inizia con `?`, quello non e nel tuo archivio.

---

## Fase 2 — Trascrizione

```bash
.venv/bin/python scripts/shorts.py transcribe <slug> --language auto
```

Funziona con voiceover **italiano e inglese**. `--language auto` (default) fa rilevare la lingua a
Whisper; puoi forzare `--language it` o `--language en`, oppure scrivere `"language": "it"` in
`projects/<slug>/project.json` e non passare nulla. La CLI usa, in ordine: `--language`, poi
`project.json`, poi `auto`.

Output:

- `build/<slug>/transcript.txt` — leggibile, con timecode
- `build/<slug>/transcript.json` — parole con tempi al centesimo
- `build/<slug>/transcript.srt` — sottotitoli

Se l'audio e rumoroso, passa `--model medium`. Per italiano e inglese `small` e gia buono;
per nomi di giochi e termini tecnici, `medium` riduce gli errori.

L'AI legge il `.txt`, non il `.json` intero: il `.txt` e compatto e sufficiente per capire il contenuto.

---

## Fase 3 — Rough cut

```bash
.venv/bin/python scripts/shorts.py roughcut <slug>
```

Cosa toglie automaticamente:

- silenzi piu lunghi di `--max-gap` (default 0.45s), lasciando `--pad` (0.10s) di respiro;
- riempitivi sicuri (`ehm`, `uhm`, `mmm`, `boh`...), solo se isolati;
- ripetizioni immediate (`questo questo`, balbettii).

Cosa **non** toglie da solo:

- frasi sbagliate ma fluenti;
- false partenze ("volevo dire... no aspetta");
- "cioè", "tipo", "praticamente" (a meno di `--aggressive`).

Per quelle serve la revisione. Output: `build/<slug>/review.md` con una tabella di ogni taglio e il contesto.

### Correzione manuale o dell'AI

`projects/<slug>/cuts.manual.json`:

```json
{
  "drop": [
    {"start": 42.10, "end": 44.80, "reason": "frase sbagliata, riparte"}
  ],
  "keep": [
    {"start": 61.00, "end": 63.50, "reason": "pausa voluta, non togliere"}
  ]
}
```

Poi:

```bash
.venv/bin/python scripts/shorts.py roughcut <slug>
.venv/bin/python scripts/shorts.py render-audio <slug> --normalize
```

`keep` vince su `drop`: se un taglio automatico cade dentro un `keep`, viene annullato.

---

## Fase 4 — Voce pulita

```bash
.venv/bin/python scripts/shorts.py render-audio <slug> --normalize
```

Output:

- `vo_clean.wav` — la voce tagliata, 48kHz stereo
- `vo_clean.txt` — la stessa trascrizione ma con i **tempi nuovi**, quelli che userai per lo shotlist
- `words.json` — ogni parola con il tempo nuovo
- `timemap.json` — mappa originale → pulito

Se registri in video (talking head) aggiungi `--video`: taglia anche l'immagine.

```bash
.venv/bin/python scripts/shorts.py render-audio <slug> --normalize --video
```

Con `--video` ottieni in piu:

- `vo_clean.mp4` — la tua faccia gia tagliata, con gli stessi tagli dell'audio (risoluzione originale;
  gli A-roll vengono poi adattati a 1080x1920);
- `vo_clean_norm.mp4` — la stessa cosa normalizzata a -16 LUFS (se usi `--normalize`);
- `vo_clean.wav` / `vo_clean_norm.wav` — l'audio per la traccia A1.

Gli slot con `"source": "face"` vengono tagliati da `vo_clean.mp4` in `build/<slug>/aroll/` e messi
direttamente su V1: **non sono segnaposto e non vanno sostituiti**. Il resto degli slot resta b-roll
da sostituire. Se il video e orizzontale, il default `face_fit: "crop"` riempie il verticale tagliando
i lati; usa `"fit"` se preferisci il letterbox.

> Da qui in poi **tutti i tempi sono nel tempo pulito**, cioe quello del video finale. Non tornare
> mai ai tempi del file originale, se non per correggere i tagli.

---

## Fase 5 — La regia (shotlist)

Qui l'AI fa il lavoro vero. Legge `build/<slug>/vo_clean.txt` e `media/index.json`, e scrive
`projects/<slug>/shotlist.json`: una sequenza di **slot** che copre tutto il voiceover.

Un slot = un blocco visivo. Non un fotogramma, non una parola: un'inquadratura.

### Regole di montaggio che l'AI deve seguire

- **Hook**: il primo slot dura 1-2s e mostra la cosa piu forte che hai.
- **Ritmo**: cambio visivo ogni **1.5-3s**. Mai piu di 4s sulla stessa immagine, tranne se e un momento
  volutamente lento.
- **Copertura**: gli slot `base` devono coprire il voiceover dall'inizio alla fine, senza buchi.
- **Overlay**: loghi e testi vanno su `layer: "overlay"`, dentro la durata di uno slot base.
- **Fedelta**: il suggerimento deve essere specifico ("uscita dal Vault 101", non "gameplay di Fallout").
- **Motivazione**: ogni slot ha un `why`. Se non sai motivarlo, lo slot non serve.
- **Caption**: obbligatorie, statiche, nel terzo inferiore, max 2 righe. Non coprono il volto ne
  l'interfaccia importante. Niente parola-per-parola o rimbalzi: l'utente le vuole leggibili.
- **Transizioni**: scegli 2-4 punti di svolta e usa `glitch`, `flash`, `dip-to-black` o `whip-pan`.
  Diventano overlay su V3 e restano dopo la sostituzione. `cross-dissolve` e manuale.
- **Talking head**: se hai registrato in video, alterna la faccia al b-roll. Usa `"source": "face"`
  per gli slot in cui si vede il volto (hook, conclusioni, passaggi personali) e lascia il resto
  b-roll. Gli slot faccia sono `layer: "base"`, `kind: "clip"`, `animation: "static"`, durata 1.5-4s.
  Non metterli su `overlay` e non chiedere la sostituzione: la clip e gia tagliata da `vo_clean.mp4`.
  Tieni libero il terzo inferiore del volto: le caption vanno li.

### Formato

```json
{
  "project": "fallout-3-vs-new-vegas",
  "title": "Perché FALLOUT 3 è ODIATO e NEW VEGAS AMATO?",
  "format": { "width": 1080, "height": 1920, "fps": 30 },
  "style": "ps2-crt",
  "voiceover": "build/fallout-3-vs-new-vegas/vo_clean.wav",
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
    "background": 0.55
  },
  "slots": [
    {
      "id": "s01",
      "start": 0.0,
      "duration": 1.8,
      "layer": "base",
      "kind": "clip",
      "intent": "Gameplay Fallout 3: uscita dal Vault 101, la porta che si apre",
      "suggest": {
        "primary": "media/clips/fallout3/vault101-uscita.mp4",
        "alternatives": ["media/screenshots/fallout3/vault101.png"],
        "why": "La frase parla di 'dove tutto e iniziato': serve il momento piu riconoscibile del gioco."
      },
      "animation": "push-in-slow",
      "zoom": 1.0,
      "opacity": 100,
      "blend": "normal",
      "transition_in": { "type": "cut" },
      "sfx": [
        { "file": "media/sfx/impatto-1.wav", "at": 0.0, "gain_db": -8 }
      ],
      "text": null
    }
  ]
}
```

### Campi

| Campo | Obbligatorio | Note |
|---|---|---|
| `id` | si | `s01`, `s02`... univoco |
| `start` / `duration` | si | secondi, tempo pulito |
| `layer` | si | `base` (V1) o `overlay` (V2) |
| `source` | no | `broll` (default) o `face`: la clip viene tagliata dal talking head |
| `kind` | si | `clip`, `image`, `logo`, `screenshot`, `text`, `ui` |
| `intent` | si | cosa deve vedersi, in modo specifico |
| `suggest.primary` | si | percorso in `media/` **oppure** `?descrizione` se non ce l'hai |
| `suggest.alternatives` | no | altri candidati |
| `suggest.why` | si | perche proprio quello |
| `animation` | si | `static`, `push-in-slow`, `pull-out-slow`, `push-in-fast`, `pan-lr`, `pan-rl`, `drift-up` |
| `zoom` | no | zoom statico applicato al clip (sopravvive alla sostituzione) |
| `opacity` | no | 0–100, default 100 |
| `blend` | no | `normal`, `add`, `multiply`, `screen`, `overlay` |
| `transition_in.type` | no | `cut`, `cross-dissolve`, `dip-to-black`, `glitch`, `whip-pan`, `flash` |
| `transition_in.duration` | no | 0.2-0.8s, default 0.4 |
| `sfx` | no | `file`, `at` (secondi dall'inizio slot), `gain_db` |
| `text` | solo se `kind: text` | il testo da mostrare |

Esempio di slot faccia (talking head):

```json
{
  "id": "s01",
  "start": 0.0,
  "duration": 2.6,
  "layer": "base",
  "source": "face",
  "kind": "clip",
  "intent": "Talking head: gancio guardando in camera",
  "suggest": {
    "primary": "?la tua faccia, gia tagliata dal video",
    "alternatives": [],
    "why": "Il gancio funziona se il volto tiene il contatto con lo spettatore."
  },
  "animation": "static",
  "zoom": 1.0,
  "transition_in": { "type": "cut" },
  "sfx": [],
  "text": null
}
```

La durata e i tempi sono sempre nel **tempo pulito** di `vo_clean.txt`. `shorts.py placeholders`
taglia `build/<slug>/aroll/s01_face.mp4` da `vo_clean.mp4`: nessuna card, nessuna sostituzione.
Lascia `suggest.primary` con `?` per documentare che e la tua faccia: non verra mai importata come file.

Le transizioni automatiche sono overlay alpha in `build/<slug>/transitions/`, posizionati a cavallo
del taglio su **V3**. Non sono dentro il segnaposto, quindi **sopravvivono** a `Replace Selected Clip`.
`cross-dissolve` no: quella e una vera transizione tra clip e va fatta a mano in Edit.

Le caption sono descritte dal blocco `captions` (vedi sopra): il default e gia buono per gli Shorts.
Metti `"enabled": false` solo se l'utente lo chiede esplicitamente.

`kind` decide il colore del segnaposto e del marker:

| kind | colore Resolve | uso |
|---|---|---|
| `clip` | blu | gameplay |
| `image` | verde | immagini statiche |
| `logo` | arancione | loghi |
| `screenshot` | viola | siti, app, UI |
| `text` | giallo | cartelli, citazioni |
| `ui` | rosa | HUD, elementi grafici |

---

## Fase 6 — Validazione e segnaposto

```bash
.venv/bin/python scripts/shorts.py validate <slug>
```

Controlla: campi mancanti, file inesistenti, sovrapposizioni, buchi, animazioni non valide,
SFX fuori slot, copertura del voiceover, configurazione caption e tipi di transizione. Per il
talking head controlla anche `source`, `face_fit`, che gli slot faccia siano `base` e che
`build/<slug>/vo_clean.mp4` esista e copra tutti i tempi. Se ci sono
errori **non** generare i segnaposto. L'avviso su `cross-dissolve` e voluto: quella transizione
restera manuale.

```bash
.venv/bin/python scripts/shorts.py placeholders <slug>
```

Genera per ogni slot:

- una card PNG 1350x2400 con ID, tipo, intent, suggerimento, motivo, animazione, SFX;
- un MP4 1080x1920 con l'animazione gia dentro (zoom/pan);
- per gli overlay un MOV con alpha (ProRes 4444).

Per gli slot `source: "face"` non genera card: taglia `build/<slug>/vo_clean.mp4` in
`build/<slug>/aroll/<id>_face.mp4`, gia a 1080x1920, e lo mette nel manifest come base. Questi clip
**non vanno sostituiti**. Se `vo_clean.mp4` manca, `placeholders` si ferma e ti dice di lanciare
`render-audio --video`.

E inoltre:

- `build/<slug>/captions/` — card QTRLE alpha (`c001.mov`...), `manifest.json`, `captions.srt`;
- `build/<slug>/transitions/` — overlay alpha per `glitch`, `flash`, `dip-to-black`, `whip-pan`.

Le caption richiedono `build/<slug>/words.json`: se manca, `placeholders` avvisa e le salta.
Puoi rigenerare solo le caption con `shorts.py captions <slug> --force`.

I segnaposto durano **esattamente** quanto lo slot. Questo e importante per la sostituzione.

---

## Fase 7 — Costruire la timeline in Resolve

```bash
.venv/bin/python scripts/shorts.py lua <slug>
```

Genera `build/<slug>/<slug>_build.lua`.

In Resolve:

1. Apri un progetto (anche vuoto).
2. **Workspace > Console**.
3. Seleziona **Lua** nel menu in basso.
4. Trascina il file `.lua` nella Console.
5. Invio.

Lo script:

- imposta 1080x1920 e il frame rate;
- crea un bin `SHORTS_<slug>` e importa segnaposto, voce, SFX, BGM, transizioni e caption;
- crea la timeline `<slug>_v1` (se esiste gia, la rinomina `_old_HHMMSS` e ne crea una nuova);
- layout tracce: **V1** B-ROLL + A-roll della faccia, **V2** OVERLAY, **V3** TRANSITIONS,
  **V4** CAPTIONS; **A1** VOICE, **A2** SFX, **A3** BGM;
- V3/V4 vengono create solo se ci sono transizioni/caption;
- usa i file audio già preparati in `build/<slug>/audio/` (gain degli SFX, BGM loopata e tagliata);
- colora i clip per tipo, applica `zoom`, `opacity` e `blend`;
- mette un **marker per ogni slot** con dentro: cosa mettere, consigliato, perche, animazione, transizione;
  per gli slot faccia il marker dice `A-ROLL/FACCIA: gia tagliata, non sostituire`;
- stampa un report e verifica che i clip siano alla posizione giusta.

Alla fine torna in **Edit**: la timeline e pronta.

> Se nella Console vedi `!! file mancante`, manca un segnaposto: rilancia `placeholders`.
> Se vedi `A2 sfx: 0`, il parametro `recordFrame` non e supportato dalla tua versione: aggiorna Resolve.
> Se `V4 caption: 0`, manca `words.json`: lancia `render-audio` e poi `placeholders --force`.

---

## Fase 8 — Sostituire i segnaposto

Ogni segnaposto e un file unico (`s01_base.mp4`), usato una sola volta. Questo rende la sostituzione sicura.

> **Talking head**: gli slot `source: "face"` non sono segnaposto. Sono clip vere in
> `build/<slug>/aroll/`, gia tagliate e montate su V1. Non sostituirle: passa direttamente al
> segnaposto successivo. Anche il marker te lo ricorda.

### Metodo consigliato — Replace Selected Clip

1. Importa il tuo clip in un bin (trascinalo nel Media Pool).
2. Nel Media Pool seleziona il **segnaposto** (`s01_base`), non il tuo clip.
3. Click destro → **Clip Operations > Replace Selected Clip...**
4. Scegli il tuo file.

Cosa succede: il file dietro al Media Pool item cambia, la timeline non viene toccata.
Quindi restano **posizione, durata, transform, zoom, effetti, grade, marker, Fusion comp**.

> Questo metodo sostituisce il file in *tutte* le sue occorrenze. Il segnaposto e usato una volta sola,
> quindi equivale a sostituire un solo slot. Se duplichi un segnaposto su piu slot, usa F11 invece.

### Metodo alternativo — F11 (Replace edit)

1. Doppio click sul tuo clip nel Media Pool (si apre nel Source Viewer).
2. Metti il playhead nel punto giusto del sorgente.
3. Metti il playhead della timeline sopra il segnaposto.
4. Premi **F11**.

Resolve adatta la durata del nuovo clip allo slot. Effetti e grade restano.

### Cosa sopravvive e cosa no

| Elemento | Dopo sostituzione |
|---|---|
| posizione, durata, marker | resta |
| transform, zoom statico, crop | resta |
| effetti Edit, grade | resta |
| Fusion composition sul clip | resta |
| **animazione dentro il file segnaposto** | **sparisce** (era nel file) |
| transizioni automatiche su V3 | **restano** (sono clip separati, non dentro il segnaposto) |
| caption su V4 | **restano** (sono clip separati, gia posizionate) |
| clip A-roll della faccia | sono gia media veri: **non vanno sostituite** |
| `cross-dissolve` | resta manuale: va creata in Edit tra i due clip |

L'animazione dei segnaposto e una **anteprima** di come dovrebbe muoversi lo slot. Dopo la sostituzione
la rimetti sul clip vero con uno dei metodi della fase 9. Le transizioni automatiche e le caption,
invece, non le devi rifare: sono su tracce separate.

---

## Fase 9 — Animazioni sul media vero

Gli slot A-roll della faccia nascono **statici**: il taglio automatico non cuoce zoom o pan. Se vuoi
un push-in sul volto, applicalo qui con un template Fusion o a mano. Per il b-roll vale quanto segue.

Tre strade, dalla piu veloce alla piu potente.

### A. Zoom statico (già fatto)

Se nello shotlist hai `"zoom": 1.05`, lo script lo applica al clip (`ZoomX`/`ZoomY`): è un transform
statico, quindi sopravvive alla sostituzione. Per un "punch-in" senza movimento è sufficiente.
Lo stesso vale per `opacity` e `blend`.

### B. Template Fusion (consigliato)

In `presets/fusion/README.md` c'e la ricetta per creare **una volta sola** 5 animazioni
(zoom-in, zoom-out, pan L→R, pan R→L, drift up) come Fusion Effect. Poi:

1. sostituisci il clip;
2. trascini il template dall'Effects Library sul clip;
3. fatto.

Un template si applica anche a piu clip selezionati insieme.

### C. Automatico (sperimentale)

`scripts/lua/20_fusion_probe.lua` testa se la tua versione free accetta `AddFusionComp` /
`ImportFusionComp` dalla Console. Se funziona, possiamo far applicare le animazioni direttamente
dallo script di build (una riga per slot). Finche non e verificato, restano A e B.

---

## Fase 10 — Audio

Lo script ha già messo:

- voce su A1 (normalizzata a -16 LUFS se hai usato `render-audio --normalize`);
- SFX su A2 ai frame calcolati, con il gain già applicato;
- BGM su A3 come **un solo clip**, già loopato, tagliato alla durata esatta della timeline e con
  fade in/out.

Come funziona il gain: l'API di Resolve **non espone il volume dei clip**. Quando lanci `lua`,
`shorts.py` crea in `build/<slug>/audio/` una copia di ogni SFX con il `gain_db` dello shotlist
(`impatto-1_g-8.wav`) e una `bgm_mix.wav` con gain, loop, taglio e fade. In timeline finiscono quei
file: i tuoi originali in `media/` non vengono toccati.

Cosa fare a mano:

1. **Livelli**: ascolta. Voce a -6/-3 dB di picco, SFX -15/-10, BGM -25/-20. Se un SFX è troppo
   forte, cambia `gain_db` nello shotlist e rilancia `lua` (5 secondi, non si rifà la timeline).
2. **Ducking**: la BGM deve scendere di 6-9 dB sotto la voce. In Fairlight: keyframe del volume
   sulla traccia A3, oppure clip volume + automazione. La GUI lo fa in 20 secondi per uno short.
3. **Silenzi**: se un taglio respira male, aggiungi 2-3 frame di room tone invece del silenzio assoluto.
4. **Loudness finale**: target YouTube circa **-14 LUFS integrated**. Se la voce è a -16, alza il
   master di 1-2 dB in Fairlight.

I nomi degli SFX sono fissi: vedi `media/sfx/README.md`. Se rinomini un file, rifai `scan` e `lua`.
Se cambi la durata della timeline (tagli, slot), rilancia `lua`: la BGM viene ritagliata alla nuova durata.

---

## Fase 11 — Export

Impostazioni per Shorts:

| Parametro | Valore |
|---|---|
| Formato | MP4 |
| Codec | H.264 |
| Risoluzione | 1080x1920 |
| Frame rate | 30 (o 60 se il progetto e 60) |
| Qualita | 20-24 Mbps (o "High") |
| Audio | AAC 320 kbps, 48 kHz |
| Color | Rec.709 / sRGB |

In Deliver: seleziona la timeline, imposta e aggiungi alla coda. Oppure usa
`scripts/lua/90_render_queue.lua` (imposta formato, codec e cartella, poi aggiunge il job).

---

## Fase 12 — QC e iterazione

```bash
.venv/bin/python scripts/shorts.py qc <slug> --video build/<slug>/export/<slug>.mp4
```

Estrae un fotogramma al centro di ogni slot e li mette in una contact sheet con il numero di slot.
Apri `build/<slug>/qc/sheet_01.jpg` oppure allegalo a OpenCode: l'agente puo leggerlo e commentare
inquadrature, testi, coerenza e leggibilita delle caption (posizione, dimensione, copertura).

Se devi cambiare il montaggio:

1. modifica `projects/<slug>/shotlist.json`;
2. `validate` → `placeholders --force` → `lua`;
3. in Resolve rilancia lo script: rinomina la vecchia timeline e ne crea una nuova.

Non perdere tempo a modificare la timeline a mano se il problema e nella regia: torna allo shotlist.

---

## Divisione del lavoro

| Attivita | Chi |
|---|---|
| trascrivere, togliere pause ed errori | AI + script |
| decidere cosa si vede e perche | AI, tu approvi |
| scegliere quali clip usare davvero | tu |
| costruire timeline, marker, SFX, BGM, caption | script Lua |
| transizioni automatiche (glitch/flash/dip/whip-pan) | script Lua, su V3 |
| riempire gli slot | tu |
| animazioni di camera e cross-dissolve | tu (template Fusion / Edit) |
| testi e grafiche extra | tu |
| color, audio mix, export | tu |

L'AI ti risparmia il 70-80% del tempo meccanico. Il restante 20% e la parte che rende il video tuo.

---

## Troubleshooting

| Problema | Causa | Soluzione |
|---|---|---|
| `resolve == nil` in Console | script lanciato da terminale | trascinalo nella Console di Resolve |
| `CreateEmptyTimeline` restituisce nil | nessun progetto aperto | apri/crea un progetto |
| i clip finiscono tutti a 0 | `recordFrame` non supportato | aggiorna Resolve 21.x |
| `!! file mancante` | percorso segnaposto errato | rilancia `placeholders`, poi `lua` |
| l'audio non c'e | file non importato | controlla che `vo_clean.wav` esista |
| i segnaposto sono neri | codec non supportato | rigenera con `--force` (H.264 + ProRes) |
| Resolve free rifiuta uno script | Scripts menu = Studio | usa solo la Console |
| Whisper non parte | venv sbagliato | usa `.venv/bin/python` |
| i tempi non tornano | stai usando i tempi del file originale | usa `vo_clean.txt` |
| `captions saltate: manca words.json` | `placeholders` lanciato prima di `render-audio` | `render-audio`, poi `placeholders --force` |
| niente caption in timeline | V4 non creata o manifest vuoto | controlla `captions.enabled` e `build/<slug>/captions/manifest.json` |
| `cross-dissolve` non appare | l'API free non crea transizioni reali | falla a mano in Edit, oppure usa un tipo automatico |
