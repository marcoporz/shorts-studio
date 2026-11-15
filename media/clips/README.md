# media/clips/

Gameplay e video registrati da te.

## Come organizzarli

Una sottocartella per gioco/progetto:

```text
media/clips/
├── fallout3/
│   ├── fallout3-vault101-uscita.mp4
│   └── fallout3-downtown-dc-panoramica.mp4
└── newvegas/
    ├── newvegas-dialogo-sunny.mp4
    └── newvegas-strip-notte.mp4
```

## Specifiche

- 1080p o superiore (anche 1440p: Resolve scala)
- 30 o 60 fps, costanti
- H.264/H.265 in MP4/MOV, oppure ProRes se hai spazio
- audio: puoi lasciarlo, ma in timeline usiamo solo la voce + SFX + BGM

## Come registrare

- OBS Studio (gratis): 60 fps, CQP 18-20, MKV poi remux in MP4.
- Su console: capture card o share integrato, 1080p.
- Registra **più materiale del necessario**: 3-5 secondi prima e dopo il momento che ti serve.
- Per gli short verticali, registra anche momenti "larghi": poi il crop 9:16 funziona meglio.

## Nomi

```text
<gioco>-<momento>-<dettaglio>.mp4
```

`newvegas-dialogo-sunny.mp4` è utile. `clip1.mp4` no.

Dopo aver aggiunto i file: `scan`.
