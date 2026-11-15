# media/bgm/

Musica di sottofondo, una traccia per progetto (o più, se vuoi alternare).

## Cosa fa lo script

Da `lua`, la BGM viene **loopata e tagliata esattamente alla durata della timeline**, con:

- gain da `"gain_db"` (default -24 dB);
- fade in 0.8s e fade out 2s;
- conversione a WAV 48 kHz stereo.

Il risultato è `build/<slug>/audio/bgm_mix.wav`: in timeline c'è **un solo clip**,
quindi niente pezzi da allineare a mano.

Il ducking sotto la voce **non** è automatico: fallo in Fairlight con i keyframe
(vedi `WORKFLOW.md`, fase 10). 6–9 dB sono sufficienti.

## Formati

- WAV 48 kHz (meglio)
- MP3 320 kbps
- M4A/AAC

## Dove trovarla gratis

- YouTube Audio Library (dentro YouTube Studio)
- Free Music Archive (controlla la licenza)
- ccMixter
- produzioni tue

La licenza deve essere scritta e compatibile con la monetizzazione.
Se non è chiaro, non usarla.

## Nomi

```text
ps2-menu.mp3
y2k-loop.wav
crt-drone.wav
```

Un nome descriptivo aiuta l'AI a scegliere la traccia giusta per lo stile.
