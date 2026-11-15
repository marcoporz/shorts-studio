# media/logos/

Loghi del canale e dei giochi/siti di cui parli.

- **PNG con trasparenza** (alpha) quando possibile
- lato lungo almeno 800px
- sfondo trasparente = overlay pulito su V2
- se il logo è su fondo bianco, ritaglialo prima (Photoshop, GIMP, Photopea)

## Nomi

```text
logo-canale.png
logo-newvegas.png
logo-spacehey.png
logo-ps2.png
```

## Uso nello shotlist

Un logo è `"kind": "logo"`, di solito `"layer": "overlay"`.
Lo script lo mette su V2 con alpha. Per un effetto "screen" o "add" aggiungi
nello shotlist `"blend": "screen"` (oppure `"add"`).

Dopo aver aggiunto i file: `scan`.
