#!/usr/bin/env bash
# Setup macOS per shorts-studio.
# Uso: ./scripts/setup-macos.sh [--no-whisper]
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

echo "== shorts-studio / setup macOS =="

if ! command -v brew >/dev/null 2>&1; then
  if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -x /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  else
    echo "Homebrew non trovato. Installalo da https://brew.sh e rilancia."
    exit 1
  fi
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "-> installo ffmpeg"
  brew install ffmpeg
else
  echo "-> ffmpeg già presente: $(ffmpeg -version | head -1)"
fi

# Python 3.15 non ha ancora i wheel di `av`, che serve a faster-whisper.
# Uso 3.13, che è supportato da tutto.
PYTHON_BIN=""
for candidate in python3.13 python3.12 python3.11; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v "$candidate")"
    break
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  echo "-> installo python@3.13"
  brew install python@3.13
  PYTHON_BIN="$(brew --prefix python@3.13)/bin/python3.13"
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 10):
    sys.exit("Serve Python 3.10 o superiore (trovato %s)" % sys.version.split()[0])
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
  echo "-> installo faster-whisper (modelli scaricati al primo uso)"
  .venv/bin/python -m pip install faster-whisper "av<17"
fi

if [ -d "/Applications/DaVinci Resolve/DaVinci Resolve.app" ]; then
  echo "-> DaVinci Resolve trovato"
else
  echo "!! DaVinci Resolve non trovato in /Applications. Installalo (versione free)."
fi

echo
.venv/bin/python scripts/shorts.py doctor || true

echo
echo "Fatto. Prossimo passo:"
echo "  1. metti il voiceover in media/voiceover/raw/"
echo "  2. .venv/bin/python scripts/shorts.py init <slug>"
echo "  3. .venv/bin/python scripts/shorts.py scan"
echo "  4. .venv/bin/python scripts/shorts.py transcribe <slug>"
