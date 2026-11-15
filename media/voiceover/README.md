# media/voiceover/raw/

La registrazione della voce, così come esce dal microfono.

## Specifiche

- **WAV 48 kHz** (o 44.1), 16/24 bit, mono o stereo
- picchi intorno a **-12/-6 dBFS**, mai a 0
- stanza silenziosa, microfono a 15-20 cm, niente ventola addosso
- un file per progetto
- leggi il copione dall'inizio alla fine: i tagli li fa lo script

Non serve rimuovere il rumore o normalizzare prima: `render-audio --normalize`
porta la voce a -16 LUFS dopo il taglio.

## Nomi

```text
fallout3-vs-newvegas-voce.wav
spacehey-voce.wav
```

Se hai più file, `transcribe` usa il primo dell'indice: per sceglierne un altro
passa `--input /percorso/file.wav`.

## Flusso

```bash
.venv/bin/python scripts/shorts.py scan
.venv/bin/python scripts/shorts.py transcribe <slug>
.venv/bin/python scripts/shorts.py roughcut <slug>
.venv/bin/python scripts/shorts.py render-audio <slug> --normalize
```

Il risultato pulito è in `build/<slug>/vo_clean.wav`, con la trascrizione
ritemporizzata in `vo_clean.txt`.
