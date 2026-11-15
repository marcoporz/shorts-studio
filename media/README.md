# media/

Qui metti **solo materiale tuo o con licenza chiara**. L'AI non scarica niente.

| Cartella | Cosa | Formati |
|---|---|---|
| `clips/` | gameplay e video registrati da te | mp4, mov, mkv, webm |
| `images/` | artwork, foto, frame | png, jpg, webp |
| `logos/` | logo del canale e dei giochi (meglio con alpha) | png |
| `screenshots/` | screenshot di siti, app, UI | png, jpg |
| `voiceover/raw/` | la registrazione della voce | wav (meglio), mp3, mp4 |
| `sfx/` | effetti con nomi fissi | wav 48kHz |
| `bgm/` | musica di sottofondo | wav, mp3, m4a |

## Nomi dei file

Il nome è un'informazione che l'AI usa. Regola:

```text
<progetto>-<contenuto>-<dettaglio>.<ext>
```

Esempi:

```text
fallout3-vault101-uscita.mp4
newvegas-dialogo-sunny.mp4
spacehey-profilo-2005.png
logo-canale.png
transizione-1.wav
```

Evita `IMG_4821.MOV`, `video finale(2).mp4`, nomi con spazi o caratteri strani.
Minuscole, numeri e trattini: funzionano su macOS e su Linux senza sorprese.

## Dopo aver aggiunto file

```bash
.venv/bin/python scripts/shorts.py scan
```

L'indice finisce in `media/index.json` (non si versiona: è rigenerabile).

## Copyright

Puoi usare:

- gameplay registrato da te;
- screenshot che fai tu;
- trailer e press kit ufficiali, con giudizio;
- asset con licenza compatibile (Wikimedia, CC0), citando la fonte.

Non usare clip di altri creator, montaggi di terzi o musica senza licenza.
Se un asset manca, nello shotlist compare `?descrizione`: quello è il tuo shopping list.
