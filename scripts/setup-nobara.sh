#!/usr/bin/env bash
# Setup Nobara Linux per shorts-studio.
# Uso: ./scripts/setup-nobara.sh [--no-whisper]
set -euo pipefail
cd "$(dirname "$0")/.."

WITH_WHISPER=1
for arg in "$@"; do
  case "$arg" in
    --whisper) WITH_WHISPER=1 ;;
    --no-whisper) WITH_WHISPER=0 ;;
    *) echo "Opzione sconosciuta: $arg"; exit 2 ;;
  esac
done

echo "== shorts-studio / setup Nobara =="

if ! command -v dnf >/dev/null 2>&1; then
  echo "Questo script è per Nobara/Fedora (dnf). Su altre distro installa: ffmpeg, python3, python3-pip, python3-virtualenv."
  exit 1
fi

echo "-> pacchetti base (chiedo sudo)"
sudo dnf install -y ffmpeg python3 python3-pip

# Librerie che servono a Resolve su Fedora/Nobara
echo "-> librerie per DaVinci Resolve"
sudo dnf install -y libxcrypt-compat mesa-libGLU alsa-lib fuse-libs || true

PYTHON_BIN=""
for candidate in python3.13 python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v "$candidate")"
    break
  fi
done

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 10):
    sys.exit("Serve Python 3.10 o superiore (trovato %s)" % sys.version.split()[0])
if sys.version_info >= (3, 15):
    sys.exit("Python 3.15+ non ha i wheel di 'av': installa python3.13 e rilancia.")
print("-> python", sys.version.split()[0])
PY

if [ -d .venv ]; then
  VENV_VER="$(.venv/bin/python -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "?")"
  case "$VENV_VER" in
    3.10|3.11|3.12|3.13|3.14) ;;
    *)
      echo "-> .venv usa Python $VENV_VER, non compatibile con faster-whisper: lo ricreo"
      rm -rf .venv
      ;;
  esac
fi

if [ ! -d .venv ]; then
  echo "-> creo .venv con $("$PYTHON_BIN" --version)"
  "$PYTHON_BIN" -m venv .venv
fi

echo "-> aggiorno pip e installo le dipendenze"
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python -m pip install -r requirements.txt

if [ "$WITH_WHISPER" -eq 1 ]; then
  echo "-> installo faster-whisper"
  .venv/bin/python -m pip install faster-whisper "av<17"
  echo "   Con GPU NVIDIA: transcribe --device cuda --compute-type float16"
fi

if [ -x /opt/resolve/bin/resolve ]; then
  echo "-> DaVinci Resolve trovato in /opt/resolve"
else
  echo "!! DaVinci Resolve non trovato. Installa il .run di Blackmagic (versione free)."
  echo "   Poi verifica che parta con: /opt/resolve/bin/resolve"
fi

echo
.venv/bin/python scripts/shorts.py doctor || true

echo
echo "Fatto. Prossimo passo:"
echo "  1. metti il voiceover in media/voiceover/raw/"
echo "  2. .venv/bin/python scripts/shorts.py init <slug>"
echo "  3. .venv/bin/python scripts/shorts.py scan"
echo "  4. .venv/bin/python scripts/shorts.py transcribe <slug>"
