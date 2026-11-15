# Audio: nomi, cue, volumi

---

## Nomi fissi degli effetti

Metti i file in `media/sfx/` con questi nomi (minuscolo, trattino, numero progressivo).
Puoi aggiungerne altri: basta che il nome sia stabile e descrittivo.

### Transizioni

| File | Uso |
|---|---|
| `transizione-1.wav` | tendina / cambio scena |
| `transizione-2.wav` | variante piu corta |
| `transizione-3.wav` | variante aggressiva |
| `whoosh-1.wav` | passaggio veloce |
| `whoosh-2.wav` | passaggio morbido |

### Impatto

| File | Uso |
|---|---|
| `impatto-1.wav` | colpo secco, hook |
| `impatto-2.wav` | colpo piu profondo |
| `sub-drop-1.wav` | caduta dei bassi, rivelazione |
| `stab-1.wav` | accento drammatico |
| `riser-1.wav` | tensione crescente prima di un reveal |

### Interfaccia / digitale

| File | Uso |
|---|---|
| `ui-click-1.wav` | click, selezione |
| `pop-1.wav` | comparsa di un elemento |
| `typing-1.wav` | testo che appare |
| `glitch-1.wav` | errore digitale, CRT |
| `crt-on.wav` | accensione monitor |
| `crt-off.wav` | spegnimento monitor |
| `ps2-boot.wav` | avvio console |

### Altro

| File | Uso |
|---|---|
| `bubble-1.wav` | Frutiger Aero |
| `risata-1.wav` | momento comico |
| `record-scratch-1.wav` | stop, "aspetta" |

---

## Regole di piazzamento

- Un SFX va **sul taglio**, non a meta del clip.
- Il picco dell'effetto deve coincidere con il primo frame del nuovo clip.
- Massimo **1 SFX ogni 2-3 secondi**. Oltre, il video diventa una demo di libreria audio.
- Non mettere SFX sotto la voce piena: scegli i momenti di pausa o le prime sillabe.
- Lo stesso SFX ripetuto 10 volte stanca: alterna le varianti.

Nel shotlist:

```json
"sfx": [
  { "file": "media/sfx/whoosh-2.wav", "at": 0.0, "gain_db": -12 }
]
```

`at` e in secondi dall'inizio dello slot.

---

## Volumi di partenza

| Traccia | Picco | Note |
|---|---|---|
| Voce (A1) | -6 / -3 dB | normalizzata a -16 LUFS |
| SFX (A2) | -15 / -10 dB | sotto la voce, sopra la BGM |
| BGM (A3) | -25 / -20 dB | deve "esserci", non competere |

Se usi `gain_db` nello shotlist, lo script crea una copia del file con il gain già applicato
(`build/<slug>/audio/`) e mette quella in timeline: i file originali in `media/` non vengono toccati.
L'API di Resolve non espone il volume dei clip, quindi questa è l'unica strada automatica.

La BGM viene anche loopata, tagliata alla durata e con fade in/out nello stesso passaggio.
Poi rifinisci a orecchio: i numeri sono un punto di partenza, non una legge.

---

## Ducking della BGM

Obiettivo: la musica scende di 6-9 dB quando parli.

Modo veloce in Fairlight:

1. Seleziona la traccia BGM.
2. Attiva l'automazione del volume (tasto `A` o il pulsante nella track head).
3. Metti un keyframe prima di ogni frase e uno dopo, con -6/-9 dB.
4. Fade in all'inizio (1-2s) e fade out alla fine (2s).

Modo alternativo: sidechain non disponibile nel free in modo semplice, quindi vai di keyframe.
Per uno Short da 60s sono 10-15 keyframe: 2 minuti di lavoro.

---

## Loudness

- YouTube normalizza a circa **-14 LUFS integrated**.
- Se il master e troppo alto, il video viene abbassato e perde impatto.
- Se e troppo basso, viene alzato e il rumore sale.

Controllo: Fairlight > Loudness Meter, oppure:

```bash
ffmpeg -i export.mp4 -af loudnorm=print_format=summary -f null -
```

Mira a **-14 LUFS** con true peak **-1 dB**.

---

## BGM: dove trovarla gratis

- YouTube Audio Library (dentro YouTube Studio)
- Free Music Archive (controlla la licenza)
- ccMixter
- produzioni tue

Evita tutto cio che non ha una licenza chiara: e il modo piu rapido per perdere un video.
