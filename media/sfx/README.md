# media/sfx/

Effetti sonori. Il nome del file è l'interfaccia: l'AI li sceglie dall'indice e li piazza sui tagli.

## Specifiche consigliate

- WAV, 48 kHz, 16 o 24 bit, stereo
- durata 0.1–2.5s (transizioni e impatti), fino a 4s per i riser
- picco intorno a **-6 dBFS**, niente clipping
- niente silenzio iniziale: il picco deve partire al primo frame

Non serve normalizzare a -14 LUFS: gli SFX sono effetti, non musica.
Il gain finale lo decide lo shotlist (`gain_db`) e lo script lo applica con ffmpeg
creando una copia in `build/<slug>/audio/`. I file originali non vengono toccati.

## Nomi fissi

Puoi usarne altri, ma questi sono quelli che l'AI conosce già.

### Transizioni

| File | Uso |
|---|---|
| `transizione-1.wav` | tendina / cambio scena |
| `transizione-2.wav` | variante più corta |
| `transizione-3.wav` | variante aggressiva |
| `whoosh-1.wav` | passaggio veloce |
| `whoosh-2.wav` | passaggio morbido |

### Impatto

| File | Uso |
|---|---|
| `impatto-1.wav` | colpo secco, hook |
| `impatto-2.wav` | colpo più profondo |
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

## Come aggiungerne di nuovi

1. Metti il file in `media/sfx/` con un nome descrittivo (`metal-hit-1.wav`).
2. `scan`.
3. Usa `media/sfx/metal-hit-1.wav` nello shotlist.

## Dove trovarli gratis

- Freesound (controlla la licenza di ogni suono)
- Pixabay Audio
- Zapsplat (account gratuito, controlla i termini)
- registrazioni tue (battere su un tavolo funziona)

Evita i pacchetti "free" senza licenza scritta.
