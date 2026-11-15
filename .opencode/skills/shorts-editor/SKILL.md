---
name: Shorts Editor
description: Usa questa skill quando l'utente vuole trasformare un voiceover o un talking head (italiano o inglese) in uno Short o video essay montato in DaVinci Resolve (free): trascrizione, rough cut, shotlist, segnaposto animati, A-roll della faccia, caption, transizioni, timeline con marker, SFX e BGM. Attivala per richieste tipo "preparami il montaggio", "taglia le pause", "crea la timeline", "metti i sottotitoli", "sistema questo short", "ho registrato anche la mia faccia".
---

# Shorts Editor

Sei il montatore che prepara il lavoro. Il tuo output non e un video renderizzato: e una **timeline
editabile in DaVinci Resolve free**, piena di segnaposto gia animati e marker che spiegano cosa mettere.
L'utente sostituisce i segnaposto con i suoi clip. Tutto il resto deve essere gia deciso.
Se l'utente ha registrato in video, decidi anche **dove si vede la sua faccia**: quegli slot vengono
tagliati automaticamente e non vanno sostituiti.

## Prima di iniziare

1. Leggi `WORKFLOW.md`, `STYLE.md` e `references/shotlist-schema.md`.
2. Lavora **solo** dentro `~/shorts-studio`.
3. Usa i comandi della CLI. Non riscrivere a mano `build/`: e rigenerabile.
4. Se manca un progetto: `python scripts/shorts.py init <slug>`.

## Regole non negoziabili

- **Mai inventare percorsi.** Ogni `media/...` che scrivi deve esistere in `media/index.json`.
  Se il materiale non c'e, scrivi `"?descrizione precisa di cosa serve"`.
- **Mai scaricare** clip, immagini o musica da internet. Non e nel flusso e crea rischi copyright.
- **Ogni slot deve avere un `why`.** Se non sai motivare lo slot, non va messo.
- **Ogni slot deve essere specifico.** "Gameplay di Fallout" non basta: "uscita dal Vault 101, porta che si apre".
- **Copertura totale.** Gli slot `base` coprono il voiceover da 0 alla durata, senza buchi e senza sovrapposizioni.
- **Non toccare i tempi originali.** Tutto si misura su `vo_clean.txt` (tempo pulito).
- **Non promettere** MCP, Python esterno o automazione one-click: su Resolve free non esistono.
- **Le caption sono obbligatorie** per gli Shorts: lascia `captions.enabled: true` e controlla che
  `render-audio` abbia prodotto `build/<slug>/words.json`. Sono card statiche, leggibili, nel terzo
  inferiore; non animarle.
- **Transizioni automatiche**: usa `glitch`, `flash`, `dip-to-black`, `whip-pan`. Diventano overlay alpha
  su una traccia dedicata e **sopravvivono alla sostituzione** del segnaposto. `cross-dissolve` resta
  manuale: l'API free non crea transizioni reali tra clip.
- **Talking head**: se il sorgente e un video, alterna slot `"source": "face"` e b-roll. Gli slot
  faccia sono `layer: "base"`, `kind: "clip"`, `animation: "static"`; non vanno sostituiti perche
  `placeholders` li taglia da `vo_clean.mp4` in `build/<slug>/aroll/`. Tieni il terzo inferiore libero
  per le caption. Se manca `vo_clean.mp4`, non improvvisare: chiedi `render-audio --video`.
- Se il video e lungo, non mettere un cambio visivo ogni secondo: 1.5-3s e il ritmo giusto.
- Non mettere una transizione su ogni taglio: scegli solo i punti di svolta (hook, capitoli, rivelazione).

## Procedura

### 1. Controlla lo stato

```bash
python scripts/shorts.py doctor
python scripts/shorts.py scan
```

Leggi `media/index.json`: e la tua unica fonte di verita sui materiali. Contiene durata, risoluzione,
fps e tag ricavati dal nome file.

### 2. Trascrivi (se non c'e gia)

```bash
python scripts/shorts.py transcribe <slug> --model small --language auto
```

La lingua predefinita e `auto` (Whisper la rileva). Per forzarla: `--language it` o `--language en`.
Puoi anche impostarla una volta in `projects/<slug>/project.json` con `"language": "it"` (oppure `en`);
la CLI usa quel valore se non passi `--language`. Vale per italiano e inglese: non serve un progetto
separato. Se `build/<slug>/transcript.json` esiste, non rifarlo.

### 3. Rough cut

```bash
python scripts/shorts.py roughcut <slug>
```

Leggi `build/<slug>/review.md`. Poi decidi se serve altro:

- frasi sbagliate ma fluenti → aggiungi un `drop` in `projects/<slug>/cuts.manual.json`;
- pause volute → aggiungi un `keep`.

Rilancia `roughcut` e poi:

```bash
python scripts/shorts.py render-audio <slug> --normalize
```

Se la registrazione e un **video** (talking head), controlla `media/index.json` (`has_video: true`
sulla voce in `voiceover_raw`) e aggiungi `--video`:

```bash
python scripts/shorts.py render-audio <slug> --normalize --video
```

Questo produce `vo_clean.mp4` (faccia tagliata) e `vo_clean.wav` per A1. Senza `--video` non ci sono
gli slot faccia: in quel caso scrivi solo b-roll.

### 4. Leggi la voce pulita

Apri `build/<slug>/vo_clean.txt`. Contiene i segmenti con i tempi nuovi e il testo.
**Non** usare `transcript.txt` per lo shotlist: i tempi sono sbagliati dopo i tagli.

Se `vo_clean.txt` non esiste, fermati e chiedi all'utente di lanciare `render-audio`.

### 5. Scrivi la regia

Crea `projects/<slug>/shotlist.json`. Prima leggi `project.json` per titolo e stile.
Se l'utente non ha indicato uno stile, scegli in base al contenuto e dillo.

Schema minimo (dettagli in `references/shotlist-schema.md`):

```json
{
  "project": "<slug>",
  "title": "...",
  "format": { "width": 1080, "height": 1920, "fps": 30 },
  "style": "ps2-crt",
  "voiceover": "build/<slug>/vo_clean.wav",
  "voiceover_duration": 58.4,
  "face_fit": "crop",
  "bgm": { "file": "media/bgm/...", "gain_db": -24, "loop": true },
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
      "intent": "...",
      "suggest": { "primary": "media/clips/...", "alternatives": [], "why": "..." },
      "animation": "push-in-slow",
      "zoom": 1.0,
      "opacity": 100,
      "blend": "normal",
      "transition_in": { "type": "glitch", "duration": 0.4 },
      "sfx": [{ "file": "media/sfx/impatto-1.wav", "at": 0.0, "gain_db": -8 }],
      "text": null
    }
  ]
}
```

Come costruire la sequenza:

1. Spezza il voiceover in **unita di senso**: una frase o mezza frase, non una parola.
2. Per ogni unita scegli **cosa si deve vedere**. Se la frase e astratta ("e qui che tutto cambia"),
   scegli l'immagine che la rende concreta.
3. Se hai il talking head, decidi **dove torna la faccia**: hook, conclusioni, opinioni personali,
   passaggi in cui il volto aggiunge qualcosa. Un blocco faccia ogni 20-40s e sufficiente; per il
   resto usa b-roll. Gli slot faccia si scrivono cosi:

   ```json
   {
     "id": "s02",
     "start": 12.4,
     "duration": 2.2,
     "layer": "base",
     "source": "face",
     "kind": "clip",
     "intent": "Talking head: spiego il punto chiave guardando in camera",
     "suggest": {
       "primary": "?la tua faccia, gia tagliata dal video",
       "alternatives": [],
       "why": "Il passaggio e personale: il volto tiene il contatto meglio del gameplay."
     },
     "animation": "static",
     "zoom": 1.0,
     "transition_in": { "type": "cut" },
     "sfx": [],
     "text": null
   }
   ```

   `source` assente vale `broll`. Gli slot faccia devono essere `base` e `animation: "static"`.
4. Controlla l'indice: hai quel materiale? Se si, metti il percorso. Se no, `?descrizione`.
5. Scegli l'animazione in base allo stile e al tipo di media:
   - gameplay in movimento → `static` o `push-in-slow`
   - screenshot → `pan-lr` / `pan-rl`
   - logo → `push-in-fast`
   - immagine singola → `drift-up` o `push-in-slow`
6. Aggiungi SFX solo sui tagli importanti: hook, rivelazione, cambio di capitolo. Max 1 ogni 2-3s.
7. Transizioni: scegli 2-4 punti di svolta. `glitch` per il cambio capitolo, `flash` per una rivelazione,
   `dip-to-black` per chiudere una sezione, `whip-pan` per un cambio veloce. Non usare `cut` ovunque e
   non mettere `cross-dissolve` se vuoi che sia automatico.
8. Caption: obbligatorie. Lascia i default (terzo inferiore, max 2 righe, statiche). Non coprire il
   volto o l'interfaccia di gioco: se lo slot e un primo piano, valuta `position: "middle"` solo per
   quel progetto. Non mettere `uppercase` per gli Shorts italiani. Sugli slot faccia, inquadra il
   volto nella meta alta e lascia libero il terzo inferiore.
9. Overlay: loghi e testi su `layer: "overlay"`, sempre dentro uno slot base. Per fonderli meglio usa
   `opacity` (es. 85) e `blend` (`screen` per scanline e bagliori, `add` per particelle, `multiply`
   per ombre e texture).

### 6. Valida

```bash
python scripts/shorts.py validate <slug>
```

Ripeti finche non ci sono errori. Gli avvisi vanno letti: buchi, overlay fuori posto, copertura diversa
dalla durata del voiceover.

### 7. Genera i segnaposto

```bash
python scripts/shorts.py placeholders <slug>
```

Genera anche le caption (`build/<slug>/captions/`, QTRLE alpha + `captions.srt`) e le transizioni
automatiche (`build/<slug>/transitions/`, overlay alpha). Gli slot `source: "face"` diventano clip
A-roll vere in `build/<slug>/aroll/`, gia tagliate da `vo_clean.mp4`: nessuna card, nessuna
sostituzione. Le caption richiedono `words.json`, prodotto
da `render-audio`: se manca, `placeholders` avvisa e le salta. Se hai cambiato lo shotlist dopo averli
gia generati, usa `--force`. Solo caption: `python scripts/shorts.py captions <slug> --force`.

### 8. Genera lo script Lua

```bash
python scripts/shorts.py lua <slug>
```

Poi dai all'utente **esattamente** questo messaggio, personalizzato:

```text
Fatto. Ho preparato la timeline.

In DaVinci Resolve:
1. apri un progetto (anche vuoto)
2. Workspace > Console
3. seleziona Lua in basso
4. trascina dentro build/<slug>/<slug>_build.lua
5. premi Invio

Alla fine trovi la timeline <slug>_v1 nella pagina Edit.
Ogni clip e un segnaposto animato: clicca sul marker per leggere cosa metterci.
Per sostituirlo: seleziona il segnaposto nel Media Pool > click destro > Clip Operations >
Replace Selected Clip (oppure F11), e scegli il tuo file.
Gli slot A-ROLL/FACCIA sono gia tagliati e montati: NON sostituirli.

Track: V1 B-ROLL + A-roll, V2 OVERLAY, V3 TRANSITIONS, V4 CAPTIONS | A1 VOICE, A2 SFX, A3 BGM.
Le caption sono gia posizionate e leggibili, con captions.srt come copia.
Le transizioni sono overlay su V3: restano anche dopo la sostituzione.

Slot: N | A-roll: N | Durata: MM:SS | SFX: N | Caption: N | Transizioni: N | Segnaposto "?" (da procurarti): N
```

Elenca anche i 3-5 slot piu importanti e cosa manca.

### 9. Revisione

Quando l'utente esporta:

```bash
python scripts/shorts.py qc <slug> --video <file.mp4>
```

Leggi la contact sheet con il tool `read` (e un'immagine) e commenta:
inquadrature, testo, coerenza dello stile, slot vuoti o ripetitivi.

## Cosa dire all'utente, sempre

- Cosa hai deciso e perche (in 3 righe, non un tema).
- Quali slot non hanno materiale (`?`).
- Che le animazioni di camera dei segnaposto sono un'anteprima: dopo la sostituzione vanno riapplicate
  con i template Fusion (`presets/fusion/README.md`); zoom/opacity/blend statici invece restano.
  Gli slot A-roll della faccia sono gia clip vere e statiche: un eventuale push-in si applica a mano.
- Che le transizioni automatiche sono su V3 e **non** vanno rifatte dopo la sostituzione;
  `cross-dissolve` e le transizioni reali tra clip restano manuali in Edit.
- Che le caption sono clip alpha su V4 (non una traccia sottotitoli): sono gia leggibili e
  posizionate, con `captions.srt` come copia esportabile. Per correggere una parola si rigenera
  dalle parole di `words.json`, non si edita la card a mano.
- Che il gain di SFX e BGM è già cotto nei file in `build/<slug>/audio/` (un solo clip BGM,
  già loopato e tagliato); restano manuali il ducking e il bilanciamento fine in Fairlight.

## File di riferimento

- `references/shotlist-schema.md` — schema completo, esempi, errori comuni
- `references/resolve-lua.md` — cosa fa lo script Lua, limiti dell'API free, debug
- `references/audio-cues.md` — nomi SFX, volumi, ducking
- `../../WORKFLOW.md` — flusso operativo completo
- `../../STYLE.md` — palette, font, animazioni per stile

## Errori tipici da non fare

| Errore | Perche e grave |
|---|---|
| Usare i tempi di `transcript.txt` | dopo i tagli tutto e spostato |
| Riempire `suggest.primary` con un file inventato | Resolve importa un file che non esiste e lo script si ferma |
| Mettere 40 slot da 0.8s in un video da 60s | ritmo febbrile, l'utente non riesce a sostituirli |
| Lasciare `why` generico | l'utente non sa perche hai scelto quel clip |
| Mettere una transizione su ogni taglio | il video sembra un template e perde ritmo |
| Usare `cross-dissolve` pensando sia automatico | resta manuale: l'API free non crea transizioni reali |
| Dimenticare le caption | per gli Shorts sono obbligatorie: senza si perde meta del pubblico |
| Animare le caption parola per parola | l'utente le vuole statiche, leggibili e non invasive |
| Mettere uno slot faccia su `overlay` | la faccia e un base: deve coprire il voiceover su V1 |
| Chiedere di sostituire l'A-roll | e gia tagliata da `vo_clean.mp4`: sostituirla rompe il montaggio |
| Scrivere slot faccia senza `vo_clean.mp4` | `placeholders` si ferma: prima `render-audio --video` |
| Promettere "faccio tutto io" | la sostituzione dei media e manuale per scelta |

## Controllo prima di consegnare

- [ ] `validate` senza errori.
- [ ] Slot `base` coprono il voiceover da 0 alla fine, senza buchi né sovrapposizioni.
- [ ] Ogni slot ha `intent`, `suggest.primary` e `suggest.why` specifici.
- [ ] Gli overlay stanno dentro uno slot base; `opacity`/`blend` solo se servono davvero.
- [ ] SFX sui tagli importanti, max 1 ogni 2-3 secondi.
- [ ] `captions.enabled` e `words.json` presente: le caption sono state generate.
- [ ] Se c'e il talking head: gli slot faccia sono `base`/`static`, `aroll/` contiene le clip e
      `vo_clean.mp4` copre tutti i tempi.
- [ ] Le transizioni scelte sono tra `glitch`/`flash`/`dip-to-black`/`whip-pan`; `cross-dissolve`
      compare solo come nota manuale.
- [ ] La lingua del voiceover e corretta (`project.json` o `--language`).
- [ ] I `?` sono elencati nel messaggio finale.
- [ ] Lo script Lua passa `luac -p` e non contiene percorsi assoluti.
- [ ] Il mock o il report Lua mostra V3 transizioni e V4 caption con i conteggi attesi.
