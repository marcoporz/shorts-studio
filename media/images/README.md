# media/images/

Immagini statiche: artwork, foto, frame estratti da un video, copertine.

- PNG o JPG, almeno 1080px sul lato corto
- per il verticale, meglio immagini che reggono il crop 9:16
- se hai un frame da un video, estrailo con:

```bash
ffmpeg -ss 00:01:23 -i video.mp4 -frames:v 1 frame.png
```

## Nomi

```text
fallout3-copertina.png
newvegas-boxart.jpg
spacehey-profilo-2005.png
```

## Attenzione

Immagini trovate su Google **non** sono automaticamente utilizzabili.
Preferisci: screenshot tuoi, press kit ufficiali, Wikimedia/CC0, artwork tuo.

Dopo aver aggiunto i file: `scan`.
