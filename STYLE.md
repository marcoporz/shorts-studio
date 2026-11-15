# Stile

Quattro famiglie visive. Si scelgono con il campo `style` nello shotlist e influenzano
colori dei segnaposto, ritmo, transizioni, SFX e grade.

```json
"style": "ps2-crt"
```

Valori: `anime90`, `crt`, `ps2`, `frutiger-aero`, `clean`.

---

## Regola comune: il testo

- Font **bold**, mai sottile: su un telefono il contrasto e tutto.
- Massimo **6-8 parole** per cartello.
- Sempre ombra o bordo: il testo deve reggere anche sopra un'immagine chiara.
- Margini: 8% per lato. Sulla destra lascia spazio ai pulsanti di YouTube.
- Non mettere testo sopra un volto o sopra l'HUD del gioco.

## Caption (tutti gli stili)

Le caption degli Shorts non seguono il font decorativo dello stile: devono solo essere lette.

- Font sans **bold**, bianco, con pannello nero al 55% e ombra. Niente VT323/Press Start per i sottotitoli.
- Terzo inferiore, **max 2 righe**, larghezza contenuta (default `font_size: 66`, `max_words: 4`).
- **Statiche**: niente bounce, shake o parola-per-parola. Il video si muove, il testo no.
- Non coprono volti, HUD o pulsanti di YouTube/TikTok: se lo slot e un primo piano, valuta `position: "middle"`.
- La configurazione sta nel blocco `captions` dello shotlist; non si edita la card a mano.

## Transizioni automatiche

`glitch`, `flash`, `dip-to-black`, `whip-pan` sono overlay alpha generati dallo script e messi su V3:
restano dopo la sostituzione del segnaposto. Scegli 2-4 punti di svolta, non ogni taglio.
`cross-dissolve` e una vera transizione tra clip e resta manuale in Edit: l'API free non la crea.

---

## Talking head (video con la faccia)

Se registri in video, il volto e il materiale piu importante: non coprirlo.

- **Inquadratura**: volto nella **meta alta**, occhi circa a un terzo dall'alto. Lascia aria sopra la
  testa e taglia il petto, non la fronte.
- **Verticale**: registra in 9:16 se puoi. Se il file e 16:9, `face_fit: "crop"` riempie il formato
  tagliando i lati; `"fit"` aggiunge bande nere. Per un volto centrato, crop e la scelta giusta.
- **Caption**: terzo inferiore libero. Se il volto e molto centrale, sposta il volto in alto con
  Transform in Resolve invece di spostare le caption.
- **Overlay**: loghi e testi lontani da occhi e bocca; meglio angoli o meta inferiore, ma sopra la
  fascia caption.
- **Tagli**: alterna faccia e b-roll. La faccia a tutto schermo per 30s stanca; 2-4s per blocco,
  poi mostra quello di cui parli.
- **Grade**: pelle naturale, non applicare scanline o grana pesante sul volto. Se lo stile e CRT o
  PS2, tieni l'effetto sul b-roll e lascia la faccia piu pulita.
- **Audio**: la voce del talking head passa gia dal rough cut e dalla normalizzazione; A1 e quel file.
  Non alzare il volume del clip video su V1: il video e muto, la voce e su A1.

---

## 1. Anime anni 90

**Riferimenti**: cel animation, VHS, opening di serie robot, palette satura ma sporca.

| Elemento | Scelta |
|---|---|
| Palette | blu notte `#101A3A`, ciano `#25D0FF`, magenta `#FF3E9D`, giallo `#FFD84D`, crema `#F4E9D8` |
| Sfondo testi | blu notte 85%, bordo ciano 2px |
| Font | **Anton**, **Bebas Neue**, **Noto Sans JP** per i kanji |
| Motion | zoom rapidi, pan laterali, flash bianco di 2 frame |
| Transizioni | cut secco, whip pan, flash |
| SFX | `whoosh-1`, `impatto-1`, `stab-1`, `riser-1` |
| Grade | saturazione +10, neri leggermente alzati, leggero bloom |
| Grana | si, 6-10%, visibile |
| Da evitare | gradienti moderni, emoji, angoli arrotondati enormi |

**Come si riconosce**: sembra un frame di un'animazione giapponese registrato su VHS.

---

## 2. CRT

**Riferimenti**: monitor a tubo, scanline, aberrazione cromatica, rumore analogico.

| Elemento | Scelta |
|---|---|
| Palette | nero `#050505`, verde fosforo `#39FF88`, ambra `#FFB000`, bianco caldo `#F2F2E9` |
| Sfondo testi | nero 90%, testo verde o ambra |
| Font | **VT323**, **Share Tech Mono**, **Press Start 2P** (solo titoli) |
| Motion | quasi fermo, micro drift, tremolio di 1px |
| Transizioni | cut, glitch, distorsione di 3-4 frame |
| SFX | `glitch-1`, `crt-on`, `crt-off`, `typing-1`, `ui-click-1` |
| Grade | contrasto alto, highlight che bruciano, scanline in overlay |
| Grana | rumore + scanline + leggero chroma shift |
| Da evitare | colori pastello, testo troppo piccolo |

**Trucco in Resolve**: Adjustment Clip sopra tutta la timeline con
*Grain* + *Scanline* (Resolve FX Texture) + *Chromatic Aberration* leggero.
Le scanline si possono anche generare come PNG e metterle su una traccia V3 in modalità Screen.

---

## 3. PS2

**Riferimenti**: menu di console 2000-2006, sfondi blu petrolio, sfere, gradienti metallici, bassa risoluzione.

| Elemento | Scelta |
|---|---|
| Palette | blu petrolio `#0B1E33`, azzurro `#3FA9F5`, argento `#C9D6E3`, arancio `#FF7A1A` |
| Sfondo testi | blu petrolio 90%, linea argento |
| Font | **Jost**, **Inter Bold**, **Michroma** per i titoli |
| Motion | push-in lento, rotazioni di 2-3 gradi, riflessi che scorrono |
| Transizioni | cross dissolve breve, dip to black |
| SFX | `ps2-boot`, `ui-click-1`, `whoosh-2`, `sub-drop-1` |
| Grade | blu nei neri, highlight freddi, leggera vignettatura |
| Grana | bassa, ma bordi morbidi (upscale da 480p) |
| Da evitare | 4K nitido, colori naturali, font sottili |

**Trucco**: per un look autentico, upscala il materiale a 480p e riportalo a 1080p con un filtro
leggero (in Resolve: *Super Scale* off, *Sharpen* 0). Il pubblico deve "sentire" il 2004.

---

## 4. Frutiger Aero

**Riferimenti**: Windows Vista/7, bolle, vetro, onde, prato verde + cielo azzurro, pesci, tecnologia ottimista.

| Elemento | Scelta |
|---|---|
| Palette | cielo `#7FD4FF`, acqua `#2BB3C0`, verde `#8FD14F`, bianco `#FFFFFF`, blu profondo `#123A5A` |
| Sfondo testi | bianco 90% con testo blu profondo, oppure vetro blur |
| Font | **Jost**, **Inter**, **Quicksand** |
| Motion | bolle che salgono, riflessi, orbite lente |
| Transizioni | cross dissolve, zoom morbido, lens flare |
| SFX | `bubble-1`, `whoosh-2`, `pop-1`, `ui-click-1` |
| Grade | luminoso, saturazione media, highlight morbidi, niente neri puri |
| Grana | zero, tutto pulito e lucido |
| Da evitare | horror vacui, texture sporche, colori cupi |

**Trucco**: il Frutiger Aero funziona se e **luminoso**. Se il gameplay e scuro, mettilo dentro una
cornice di vetro con sfondo cielo: il contrasto e parte dello stile.

---

## 5. Clean (fallback)

Quando il video e lungo e lo stile diventerebbe stancante.

- sfondo nero, testo bianco, un solo accento
- font **Inter Bold**
- solo cut
- nessuna grana
- SFX minimi (`whoosh-2`, `pop-1`)

---

## Abbinamenti

| Tipo di video | Stile | Perche |
|---|---|---|
| Videogioco retrogame / PS2 | `ps2` + `crt` | coerente col materiale |
| Lore, creepypasta, "il clone dimenticato" | `crt` o `anime90` | atmosfera |
| Social sconosciuti / indieweb / Y2K | `frutiger-aero` + `crt` | il web di quegli anni |
| Confronto tra giochi | `ps2` | neutralita + nostalgia |
| Video lungo, 10+ min | `clean` con inserti a tema | leggibilita |

Si puo cambiare stile a meta video: `style` e globale, ma nulla vieta di usare `anime90` per
l'intro e `clean` per il corpo. In quel caso mettilo in `notes.md` e dillo all'AI.

---

## Come lo stile arriva nei segnaposto

I segnaposto usano il colore del `kind`, non dello `style`. Lo stile compare:

- nel campo `style` della card (in alto);
- nelle animazioni suggerite;
- nel testo dei marker;
- nella colonna `ANIM` in basso.

Quindi puoi cambiare stile senza rigenerare tutto: cambia l'animazione e i template Fusion.

---

## Palette rapida (hex)

```text
anime90        #101A3A  #25D0FF  #FF3E9D  #FFD84D  #F4E9D8
crt            #050505  #39FF88  #FFB000  #F2F2E9
ps2            #0B1E33  #3FA9F5  #C9D6E3  #FF7A1A
frutiger-aero  #7FD4FF  #2BB3C0  #8FD14F  #FFFFFF  #123A5A
clean          #000000  #FFFFFF  #FF4D4D
```

---

## SFX per stile

| Stile | Set base |
|---|---|
| anime90 | `whoosh-1`, `impatto-1`, `stab-1`, `riser-1` |
| crt | `glitch-1`, `crt-on`, `crt-off`, `typing-1` |
| ps2 | `ps2-boot`, `ui-click-1`, `whoosh-2`, `sub-drop-1` |
| frutiger-aero | `bubble-1`, `pop-1`, `whoosh-2`, `ui-click-1` |
| clean | `whoosh-2`, `pop-1` |

Regola: **massimo 1 SFX ogni 2-3 secondi**. Se ce ne sono di piu, il video diventa rumore.
La transizione sonora va sul **taglio**, non a meta del clip.

---

## Studio 21.1.1: cosa cambia per volto e transizioni

- **Volto**: con `animation_mode: fusion` i segnaposto della faccia sono statici; eventuali zoom/pan sul volto vanno applicati come Fusion comp dopo la sostituzione (template in `presets/fusion/`).
- **Transizioni native**: `cross-dissolve` e `dip-to-black` diventano transizioni native di Resolve se `native_transitions: true`. `glitch`, `flash`, `whip-pan` restano overlay V3. Le transizioni native richiedono handle nei segnaposto (default 0.6s).
- **Animazioni**: con `animation_mode: fusion` le animazioni vivono in Fusion comp sul clip timeline e **sopravvivono** alla sostituzione del segnaposto. Non serve riapplicarle.
