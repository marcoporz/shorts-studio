#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shorts.py - pipeline locale per Shorts / video essay.
OpenCode + DaVinci Resolve (free) + ffmpeg + Whisper.

Comandi:
  doctor                      verifica dipendenze
  init <slug>                 crea un progetto
  scan                        indicizza media/
  transcribe <slug>           Whisper -> transcript.json / .srt / .txt (--language auto|it|en)
  roughcut <slug>             taglia silenzi, riempitivi, ripetizioni -> cuts.json
  render-audio <slug>         applica i tagli -> vo_clean.wav + words.json (--video per talking head)
  validate <slug>             controlla lo shotlist (caption, transizioni e slot faccia inclusi)
  placeholders <slug>         segnaposto animati + caption + transizioni automatiche
  captions <slug>             solo caption (overlay QTRLE + captions.srt)
  lua <slug>                  genera lo script Lua per la Console di Resolve
  qc <slug> [--video FILE]    contact sheet dai fotogrammi finali
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:  # Pillow serve solo per i segnaposto e il QC
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except Exception:  # pragma: no cover
    HAS_PIL = False

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "media"
PROJECTS = ROOT / "projects"
BUILD = ROOT / "build"

KINDS = ("clip", "image", "logo", "screenshot", "text", "ui")
LAYERS = ("base", "overlay")
SOURCES = ("broll", "face")
FACE_FITS = ("crop", "fit")
ANIMATIONS = (
    "static",
    "push-in-slow",
    "pull-out-slow",
    "push-in-fast",
    "pan-lr",
    "pan-rl",
    "drift-up",
)
ANIMATION_MODES = ("baked", "fusion")
TRANSITIONS = ("cut", "cross-dissolve", "dip-to-black", "glitch", "whip-pan", "flash")
BLENDS = ("normal", "add", "multiply", "screen", "overlay")

CAPTION_DEFAULTS = {
    "enabled": True,
    "position": "lower",      # lower | middle | upper
    "max_words": 4,
    "max_chars": 32,
    "max_duration": 3.2,
    "font_size": 66,
    "uppercase": False,
    "background": 0.55,
    "color": "#FFFFFF",
}
CAPTION_POSITIONS = ("lower", "middle", "upper")
AUTO_TRANSITIONS = ("dip-to-black", "glitch", "whip-pan", "flash")

FILLERS_SAFE = {"ehm", "ehmm", "ehm.", "uhm", "umm", "mmm", "hmm", "mm", "boh", "beh"}
FILLERS_AGGRESSIVE = FILLERS_SAFE | {
    "cioè", "cioe", "tipo", "praticamente", "insomma", "diciamo", "niente", "allora",
}

FONT_CANDIDATES_BOLD = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Impact.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
FONT_CANDIDATES_REGULAR = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


# ---------------------------------------------------------------- utilities

def log(msg: str = "") -> None:
    print(msg, flush=True)


def die(msg: str, code: int = 1) -> None:
    print("ERRORE: " + msg, file=sys.stderr, flush=True)
    raise SystemExit(code)


def run(cmd: Sequence[str], check: bool = True, quiet: bool = True) -> subprocess.CompletedProcess:
    res = subprocess.run(
        list(cmd),
        stdout=subprocess.PIPE if quiet else None,
        stderr=subprocess.PIPE if quiet else None,
        text=True,
    )
    if check and res.returncode != 0:
        tail = (res.stderr or "").strip().splitlines()[-8:]
        die("comando fallito:\n  " + " ".join(map(str, cmd)) + "\n" + "\n".join(tail))
    return res


def which(name: str) -> Optional[str]:
    return shutil.which(name)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def slug_ok(slug: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,60}", slug))


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "progetto"


def fmt_tc(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    m, s = divmod(seconds, 60)
    return "%d:%05.2f" % (int(m), s)


def fmt_srt(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def parse_rate(value: Optional[str]) -> float:
    if not value:
        return 0.0
    if "/" in value:
        a, b = value.split("/", 1)
        try:
            return float(a) / float(b) if float(b) else 0.0
        except Exception:
            return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def ffprobe(path: Path) -> Dict[str, Any]:
    res = run([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ])
    try:
        data = json.loads(res.stdout or "{}")
    except Exception:
        return {}

    streams = data.get("streams") or []
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = data.get("format") or {}

    duration = 0.0
    for candidate in (fmt.get("duration"), (v or {}).get("duration"), (a or {}).get("duration")):
        try:
            if candidate is not None:
                duration = float(candidate)
                break
        except Exception:
            pass

    info: Dict[str, Any] = {
        "duration": round(duration, 4),
        "has_video": bool(v),
        "has_audio": bool(a),
    }
    if v:
        info.update({
            "width": int(v.get("width") or 0),
            "height": int(v.get("height") or 0),
            "fps": round(parse_rate(v.get("avg_frame_rate")) or parse_rate(v.get("r_frame_rate")), 4),
            "vcodec": v.get("codec_name"),
            "pix_fmt": v.get("pix_fmt"),
        })
    if a:
        info.update({
            "acodec": a.get("codec_name"),
            "sample_rate": int(a.get("sample_rate") or 0),
            "channels": int(a.get("channels") or 0),
        })
    return info


def project_dir(slug: str) -> Path:
    return PROJECTS / slug


def build_dir(slug: str) -> Path:
    return BUILD / slug


def load_project(slug: str) -> Dict[str, Any]:
    p = project_dir(slug) / "project.json"
    if not p.exists():
        die("progetto '%s' inesistente. Esegui: python scripts/shorts.py init %s" % (slug, slug))
    return read_json(p)


def load_shotlist(slug: str) -> Dict[str, Any]:
    p = project_dir(slug) / "shotlist.json"
    if not p.exists():
        die("manca projects/%s/shotlist.json" % slug)
    return read_json(p)


def index_path() -> Path:
    return MEDIA / "index.json"


def load_index() -> Dict[str, Any]:
    if not index_path().exists():
        die("indice media assente. Esegui: python scripts/shorts.py scan")
    return read_json(index_path())


def all_index_entries(index: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for key in ("clips", "images", "logos", "screenshots", "sfx", "bgm", "voiceover_raw"):
        out.extend(index.get(key) or [])
    return out


# ---------------------------------------------------------------- doctor

def cmd_doctor(args: argparse.Namespace) -> int:
    log("shorts-studio - controllo ambiente")
    log("root: %s" % ROOT)
    ok = True

    for tool in ("ffmpeg", "ffprobe"):
        p = which(tool)
        if p:
            log("  [ok] %s -> %s" % (tool, p))
        else:
            log("  [!!] %s mancante" % tool)
            ok = False

    if which("ffmpeg"):
        enc = run(["ffmpeg", "-hide_banner", "-encoders"]).stdout or ""
        for name in ("libx264", "prores_ks", "qtrle", "aac", "pcm_s16le"):
            log("  [%s] encoder %s" % ("ok" if name in enc else "!!", name))
        flt = run(["ffmpeg", "-hide_banner", "-filters"]).stdout or ""
        log("  [%s] filtro zoompan" % ("ok" if " zoompan " in flt else "!!"))
        log("  [%s] filtro drawtext (non richiesto)" % ("ok" if " drawtext " in flt else "assente"))

    log("  [%s] Pillow" % ("ok" if HAS_PIL else "!!  -> pip install pillow"))
    if not HAS_PIL:
        ok = False

    try:
        import faster_whisper  # noqa: F401
        log("  [ok] faster-whisper")
    except Exception:
        log("  [--] faster-whisper assente (serve solo per transcribe)")

    resolve_mac = Path("/Applications/DaVinci Resolve/DaVinci Resolve.app")
    resolve_lin = Path("/opt/resolve/bin/resolve")
    if resolve_mac.exists() or resolve_lin.exists():
        log("  [ok] DaVinci Resolve installato")
    else:
        log("  [--] DaVinci Resolve non trovato nei percorsi standard")

    if not FONT_CANDIDATES_BOLD or not any(Path(f).exists() for f in FONT_CANDIDATES_BOLD):
        log("  [!!] nessun font bold trovato per i segnaposto")
        ok = False
    else:
        log("  [ok] font per segnaposto")

    log("")
    log("Risultato: %s" % ("pronto" if ok else "mancano dipendenze"))
    return 0 if ok else 1


# ---------------------------------------------------------------- init

PROJECT_TEMPLATE_JSON = {
    "slug": "",
    "title": "",
    "format": {"width": 1080, "height": 1920, "fps": 30},
    "style": "ps2-crt",
    "language": "auto",
    "voiceover": "",
    "notes": "",
}

SCRIPT_TEMPLATE = """# {title}

## Hook (0-3s)

## Corpo

## Chiusura / CTA

## Asset che so di avere

- 

## Cose da procurarmi (miei screenshot / gameplay)

- 
"""

CUTS_MANUAL_TEMPLATE = {
    "_commento": "Aggiungi qui i tagli che vuole l'AI oltre a quelli automatici. I tempi sono in secondi sul file originale.",
    "drop": [],
    "keep": [],
}


def cmd_init(args: argparse.Namespace) -> int:
    slug = args.slug
    if not slug_ok(slug):
        die("slug non valido: usa minuscole, numeri, trattino (es. fallout3-vs-newvegas)")
    pdir = project_dir(slug)
    if pdir.exists() and not args.force:
        die("projects/%s esiste gia (usa --force per sovrascrivere i template)" % slug)

    pdir.mkdir(parents=True, exist_ok=True)
    tpl = dict(PROJECT_TEMPLATE_JSON)
    tpl["slug"] = slug
    tpl["title"] = args.title or slug.replace("-", " ").title()
    tpl["language"] = getattr(args, "language", None) or "auto"
    write_json(pdir / "project.json", tpl)
    (pdir / "script.md").write_text(SCRIPT_TEMPLATE.format(title=tpl["title"]), encoding="utf-8")
    write_json(pdir / "cuts.manual.json", CUTS_MANUAL_TEMPLATE)
    if not (pdir / "shotlist.json").exists():
        write_json(pdir / "shotlist.json", {
            "project": slug,
            "title": tpl["title"],
            "format": tpl["format"],
            "style": tpl["style"],
            "voiceover": "build/%s/vo_clean.wav" % slug,
            "voiceover_duration": 0,
            "bgm": None,
            "captions": {
                "enabled": True,
                "position": "lower",
                "max_words": 4,
                "max_chars": 32,
                "uppercase": False,
            },
            "slots": [],
        })
    (pdir / "notes.md").write_text("# Note %s\n\n" % slug, encoding="utf-8")
    build_dir(slug).mkdir(parents=True, exist_ok=True)

    log("Creato projects/%s/" % slug)
    log("  1. metti il voiceover in media/voiceover/raw/")
    log("  2. python scripts/shorts.py scan")
    log("  3. python scripts/shorts.py transcribe %s" % slug)
    return 0


# ---------------------------------------------------------------- scan

SCAN_GROUPS = [
    ("clips", "clips"),
    ("images", "images"),
    ("logos", "logos"),
    ("screenshots", "screenshots"),
    ("sfx", "sfx"),
    ("bgm", "bgm"),
    ("voiceover_raw", "voiceover/raw"),
]

MEDIA_EXT = {
    ".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff",
    ".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus",
}


def tags_from_name(path: Path) -> List[str]:
    stem = path.stem.lower()
    parts = re.split(r"[^a-z0-9]+", stem)
    return [p for p in parts if p and not p.isdigit()]


def cmd_scan(args: argparse.Namespace) -> int:
    cache_file = MEDIA / ".scan-cache.json"
    cache: Dict[str, Any] = {}
    if cache_file.exists():
        try:
            cache = read_json(cache_file)
        except Exception:
            cache = {}

    index: Dict[str, Any] = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "root": str(ROOT),
    }
    new_cache: Dict[str, Any] = {}
    total = 0

    for key, sub in SCAN_GROUPS:
        folder = MEDIA / sub
        folder.mkdir(parents=True, exist_ok=True)
        entries: List[Dict[str, Any]] = []
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            if path.suffix.lower() not in MEDIA_EXT:
                continue
            st = path.stat()
            sig = "%d:%d" % (st.st_size, int(st.st_mtime))
            cached = cache.get(str(path))
            if cached and cached.get("sig") == sig:
                info = cached.get("info") or {}
            else:
                info = ffprobe(path)
            new_cache[str(path)] = {"sig": sig, "info": info}
            entry = {
                "path": rel(path),
                "name": path.name,
                "folder": key,
                "tags": tags_from_name(path),
            }
            entry.update(info)
            entries.append(entry)
        index[key] = entries
        total += len(entries)
        log("  %-14s %3d file" % (key, len(entries)))

    write_json(cache_file, new_cache)
    write_json(index_path(), index)
    log("\nIndice scritto in media/index.json (%d file)." % total)
    if not index.get("clips"):
        log("Suggerimento: metti i gameplay in media/clips/<gioco>/...")
    return 0


# ---------------------------------------------------------------- transcribe

def cmd_transcribe(args: argparse.Namespace) -> int:
    slug = args.slug
    project = load_project(slug)
    requested_language = (args.language or project.get("language") or "auto").strip()
    bdir = build_dir(slug)

    if args.input:
        src = Path(args.input).expanduser().resolve()
    else:
        index = load_index()
        vo = index.get("voiceover_raw") or []
        if not vo:
            die("nessun file in media/voiceover/raw/. Metti il voiceover e rilancia scan.")
        if len(vo) > 1:
            log("Piu file trovati, uso il primo (--input per sceglierne un altro):")
            for e in vo:
                log("  - %s" % e["path"])
        src = (ROOT / vo[0]["path"]).resolve()

    if not src.exists():
        die("file non trovato: %s" % src)

    try:
        from faster_whisper import WhisperModel
    except Exception:
        die("faster-whisper non installato.\n  .venv/bin/pip install faster-whisper\n"
            "  poi rilancia con .venv/bin/python scripts/shorts.py transcribe %s" % slug)

    log("Trascrivo %s" % src.name)
    log("  modello: %s  lingua: %s" % (args.model, requested_language))

    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    segments_iter, info = model.transcribe(
        str(src),
        language=None if requested_language == "auto" else requested_language,
        word_timestamps=True,
        vad_filter=True,
        beam_size=5,
        condition_on_previous_text=False,
    )

    segments: List[Dict[str, Any]] = []
    for i, seg in enumerate(segments_iter):
        words = []
        for w in (seg.words or []):
            words.append({
                "word": w.word.strip(),
                "start": round(float(w.start), 3),
                "end": round(float(w.end), 3),
                "probability": round(float(getattr(w, "probability", 0.0)), 3),
            })
        segments.append({
            "id": i,
            "start": round(float(seg.start), 3),
            "end": round(float(seg.end), 3),
            "text": seg.text.strip(),
            "words": words,
        })

    duration = float(getattr(info, "duration", 0.0) or 0.0)
    if duration <= 0 and segments:
        duration = segments[-1]["end"]

    transcript = {
        "source": rel(src),
        "language": getattr(info, "language", requested_language),
        "language_probability": round(float(getattr(info, "language_probability", 0.0) or 0.0), 3),
        "duration": round(duration, 3),
        "segments": segments,
    }
    bdir.mkdir(parents=True, exist_ok=True)
    write_json(bdir / "transcript.json", transcript)

    # SRT
    srt_lines = []
    for i, seg in enumerate(segments, 1):
        srt_lines.append(str(i))
        srt_lines.append("%s --> %s" % (fmt_srt(seg["start"]), fmt_srt(seg["end"])))
        srt_lines.append(seg["text"])
        srt_lines.append("")
    (bdir / "transcript.srt").write_text("\n".join(srt_lines), encoding="utf-8")

    # TXT con timecode per la lettura dell'agente
    txt_lines = ["# Trascrizione %s" % src.name, "# durata %s" % fmt_tc(duration), ""]
    for seg in segments:
        txt_lines.append("[%s -> %s] %s" % (fmt_tc(seg["start"]), fmt_tc(seg["end"]), seg["text"]))
    (bdir / "transcript.txt").write_text("\n".join(txt_lines) + "\n", encoding="utf-8")

    words = sum(len(s["words"]) for s in segments)
    log("\nOK: %d segmenti, %d parole, durata %s" % (len(segments), words, fmt_tc(duration)))
    log("  build/%s/transcript.txt" % slug)
    log("  build/%s/transcript.json" % slug)
    return 0


# ---------------------------------------------------------------- roughcut

def normalize_word(w: str) -> str:
    w = unicodedata.normalize("NFKD", w).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", w.lower())


def load_words(transcript: Dict[str, Any]) -> List[Dict[str, Any]]:
    words: List[Dict[str, Any]] = []
    for seg in transcript.get("segments") or []:
        for w in seg.get("words") or []:
            if not w.get("word"):
                continue
            words.append({
                "word": w["word"],
                "norm": normalize_word(w["word"]),
                "start": float(w["start"]),
                "end": float(w["end"]),
                "prob": float(w.get("probability") or 0.0),
            })
    words.sort(key=lambda x: x["start"])
    return words


def cmd_roughcut(args: argparse.Namespace) -> int:
    slug = args.slug
    load_project(slug)
    bdir = build_dir(slug)
    tpath = bdir / "transcript.json"
    if not tpath.exists():
        die("manca build/%s/transcript.json. Lancia prima transcribe." % slug)

    transcript = read_json(tpath)
    duration = float(transcript.get("duration") or 0.0)
    words = load_words(transcript)
    if not words:
        die("la trascrizione non contiene parole (audio vuoto?)")

    step = 0.02
    n = int(math.ceil(duration / step)) + 2
    keep = bytearray(b"\x01") * n
    removed: List[Dict[str, Any]] = []

    def mark(a: float, b: float, value: int) -> None:
        a = max(0.0, a)
        b = min(duration, b)
        if b <= a:
            return
        i0 = max(0, int(a / step))
        i1 = min(n, int(math.ceil(b / step)))
        for i in range(i0, i1):
            keep[i] = value

    # 1) silenzi
    silence_count = 0
    if words[0]["start"] > args.max_gap:
        a, b = 0.0, words[0]["start"] - args.pad
        if b > 0.05:
            mark(a, b, 0)
            removed.append({"start": round(a, 3), "end": round(b, 3), "reason": "silenzio iniziale"})
            silence_count += 1

    for prev, nxt in zip(words, words[1:]):
        gap = nxt["start"] - prev["end"]
        if gap > args.max_gap:
            a = prev["end"] + args.pad
            b = nxt["start"] - args.pad
            if b - a > 0.08:
                mark(a, b, 0)
                removed.append({
                    "start": round(a, 3), "end": round(b, 3),
                    "reason": "silenzio %.2fs" % gap,
                })
                silence_count += 1

    last = words[-1]
    if duration - last["end"] > args.max_gap:
        a, b = last["end"] + args.pad, duration
        if b - a > 0.08:
            mark(a, b, 0)
            removed.append({"start": round(a, 3), "end": round(b, 3), "reason": "silenzio finale"})
            silence_count += 1

    # 2) riempitivi
    fillers = FILLERS_AGGRESSIVE if args.aggressive else FILLERS_SAFE
    filler_count = 0
    if not args.keep_fillers:
        filler_set = {normalize_word(f) for f in fillers}
        for idx, w in enumerate(words):
            if w["norm"] and w["norm"] in filler_set:
                prev_end = words[idx - 1]["end"] if idx > 0 else 0.0
                next_start = words[idx + 1]["start"] if idx + 1 < len(words) else duration
                before = w["start"] - prev_end
                after = next_start - w["end"]
                if before > 0.18 or after > 0.18:
                    mark(w["start"] - 0.02, w["end"] + 0.04, 0)
                    removed.append({
                        "start": round(max(0.0, w["start"] - 0.02), 3),
                        "end": round(w["end"] + 0.04, 3),
                        "reason": "riempitivo '%s'" % w["word"],
                    })
                    filler_count += 1

    # 3) ripetizioni immediate (balbettio)
    repeat_count = 0
    for i in range(len(words) - 1):
        a, b = words[i], words[i + 1]
        if a["norm"] and a["norm"] == b["norm"] and (b["start"] - a["end"]) < 0.35:
            mark(a["start"] - 0.02, a["end"] + 0.02, 0)
            removed.append({
                "start": round(max(0.0, a["start"] - 0.02), 3),
                "end": round(a["end"] + 0.02, 3),
                "reason": "ripetizione '%s'" % a["word"],
            })
            repeat_count += 1

    # 4) interventi manuali (i keep vincono sui drop)
    manual = {}
    mpath = project_dir(slug) / "cuts.manual.json"
    if mpath.exists():
        try:
            manual = read_json(mpath)
        except Exception:
            log("!! cuts.manual.json non leggibile, lo ignoro")

    for item in manual.get("drop") or []:
        a, b = float(item["start"]), float(item["end"])
        mark(a, b, 0)
        removed.append({"start": round(a, 3), "end": round(b, 3),
                        "reason": item.get("reason") or "taglio manuale"})
    for item in manual.get("keep") or []:
        a, b = float(item["start"]), float(item["end"])
        mark(a, b, 1)

    # 5) estrai i segmenti
    segments: List[Dict[str, Any]] = []
    i = 0
    out_t = 0.0
    while i < n:
        if not keep[i]:
            i += 1
            continue
        j = i
        while j < n and keep[j]:
            j += 1
        s, e = i * step, min(duration, j * step)
        if e - s >= args.min_keep:
            segments.append({
                "i": len(segments),
                "src_start": round(s, 3),
                "src_end": round(e, 3),
                "out_start": round(out_t, 3),
                "out_end": round(out_t + (e - s), 3),
            })
            out_t += e - s
        i = j

    if not segments:
        die("tutti i tagli hanno rimosso l'audio: controlla i parametri")

    removed.sort(key=lambda x: x["start"])
    cleaned = out_t
    cuts = {
        "source": transcript.get("source"),
        "duration": round(duration, 3),
        "settings": {
            "max_gap": args.max_gap,
            "pad": args.pad,
            "min_keep": args.min_keep,
            "aggressive": bool(args.aggressive),
            "keep_fillers": bool(args.keep_fillers),
        },
        "segments": segments,
        "removed": removed,
        "stats": {
            "original": round(duration, 3),
            "cleaned": round(cleaned, 3),
            "removed_seconds": round(duration - cleaned, 3),
            "cuts": len(removed),
            "silences": silence_count,
            "fillers": filler_count,
            "repeats": repeat_count,
            "segments": len(segments),
        },
    }
    write_json(bdir / "cuts.json", cuts)
    write_review(slug, cuts, words)

    st = cuts["stats"]
    log("Rough cut: %s -> %s  (-%s, %d tagli)" % (
        fmt_tc(st["original"]), fmt_tc(st["cleaned"]), fmt_tc(st["removed_seconds"]), st["cuts"]))
    log("  silenzi %d | riempitivi %d | ripetizioni %d | %d segmenti" % (
        st["silences"], st["fillers"], st["repeats"], st["segments"]))
    log("  review: build/%s/review.md" % slug)
    return 0


def write_review(slug: str, cuts: Dict[str, Any], words: List[Dict[str, Any]]) -> None:
    lines = ["# Review rough cut - %s" % slug, ""]
    st = cuts["stats"]
    lines += [
        "- Durata originale: **%s**" % fmt_tc(st["original"]),
        "- Durata stimata: **%s**" % fmt_tc(st["cleaned"]),
        "- Rimosso: **%s** in %d tagli" % (fmt_tc(st["removed_seconds"]), st["cuts"]),
        "- Silenzi: %d | riempitivi: %d | ripetizioni: %d" % (
            st["silences"], st["fillers"], st["repeats"]),
        "",
        "## Tagli",
        "",
        "| # | da | a | durata | motivo | contesto |",
        "|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(cuts["removed"], 1):
        ctx_words = [w["word"] for w in words if r["start"] - 2.0 <= w["start"] <= r["end"] + 2.0]
        ctx = " ".join(ctx_words).replace("|", "/")[:110]
        lines.append("| %d | %s | %s | %.2fs | %s | %s |" % (
            i, fmt_tc(r["start"]), fmt_tc(r["end"]), r["end"] - r["start"], r["reason"], ctx))

    low_conf = [w for w in words if 0 < w["prob"] < 0.35]
    lines += ["", "## Parole con bassa confidenza (da verificare)", ""]
    if low_conf:
        for w in low_conf[:60]:
            lines.append("- `%s` a %s (%.2f)" % (w["word"], fmt_tc(w["start"]), w["prob"]))
    else:
        lines.append("Nessuna.")

    lines += [
        "",
        "## Tagli manuali",
        "",
        "Aggiungi in `projects/%s/cuts.manual.json`:" % slug,
        "",
        "```json",
        "{",
        '  "drop": [{"start": 12.40, "end": 13.10, "reason": "frase sbagliata"}],',
        '  "keep": [{"start": 20.00, "end": 22.00, "reason": "non togliere"}]',
        "}",
        "```",
        "",
        "Poi rilancia: `python scripts/shorts.py roughcut %s && python scripts/shorts.py render-audio %s`" % (slug, slug),
        "",
    ]
    (BUILD / slug / "review.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------- render audio

def cmd_render_audio(args: argparse.Namespace) -> int:
    slug = args.slug
    load_project(slug)
    bdir = build_dir(slug)
    cpath = bdir / "cuts.json"
    if not cpath.exists():
        die("manca build/%s/cuts.json. Lancia prima roughcut." % slug)

    cuts = read_json(cpath)
    src = ROOT / cuts["source"]
    if not src.exists():
        die("sorgente non trovata: %s" % src)

    segments = cuts["segments"]
    if not segments:
        die("nessun segmento da renderizzare")

    info = ffprobe(src)
    with_video = bool(args.video and info.get("has_video"))
    if args.video and not info.get("has_video"):
        log("  [warn] --video richiesto ma il sorgente non ha una traccia video: genero solo audio")

    filter_lines: List[str] = []
    concat_inputs: List[str] = []
    for i, seg in enumerate(segments):
        a, b = seg["src_start"], seg["src_end"]
        filter_lines.append(
            "[0:a]atrim=start=%.3f:end=%.3f,asetpts=PTS-STARTPTS[a%d];" % (a, b, i))
        if with_video:
            filter_lines.append(
                "[0:v]trim=start=%.3f:end=%.3f,setpts=PTS-STARTPTS[v%d];" % (a, b, i))
            concat_inputs.append("[v%d][a%d]" % (i, i))
        else:
            concat_inputs.append("[a%d]" % i)

    if with_video:
        filter_lines.append("%sconcat=n=%d:v=1:a=1[outv][outa];" % ("".join(concat_inputs), len(segments)))
    else:
        filter_lines.append("%sconcat=n=%d:v=0:a=1[out];" % ("".join(concat_inputs), len(segments)))

    # Micro-fade 5ms su voce per evitare click ai bordi
    clean_dur = cuts["stats"]["cleaned"]
    fade_filter = f"afade=t=in:st=0:d=0.005,afade=t=out:st={clean_dur-0.005}:d=0.005"
    if with_video:
        filter_lines.append("[outa]%s[outa_faded];" % fade_filter)
    else:
        filter_lines.append("[out]%s[out_faded];" % fade_filter)

    filter_complex = "\n".join(filter_lines)
    (bdir / "cuts.ffscript").write_text(filter_complex, encoding="utf-8")

    if with_video:
        out = bdir / "vo_clean.mp4"
        cmd = ["ffmpeg", "-y", "-i", str(src), "-filter_complex", filter_complex,
               "-map", "[outv]", "-map", "[outa_faded]",
               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2",
               "-movflags", "+faststart", str(out)]
    else:
        out = bdir / "vo_clean.wav"
        cmd = ["ffmpeg", "-y", "-i", str(src), "-filter_complex", filter_complex,
               "-map", "[out_faded]", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(out)]
    run(cmd)

    if with_video:
        # La traccia A1 vuole sempre un wav: estrailo dal video gia tagliato.
        wav = bdir / "vo_clean.wav"
        run(["ffmpeg", "-y", "-i", str(out), "-vn", "-c:a", "pcm_s16le",
             "-ar", "48000", "-ac", "2", str(wav)])
        log("  audio per A1: %s" % rel(wav))

    if args.normalize:
        norm = bdir / ("vo_clean_norm.wav" if not with_video else "vo_clean_norm.mp4")
        log("Normalizzo a -16 LUFS...")
        if with_video:
            run(["ffmpeg", "-y", "-i", str(out), "-c:v", "copy",
                 "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "320k",
                 "-ar", "48000", str(norm)])
            norm_wav = bdir / "vo_clean_norm.wav"
            run(["ffmpeg", "-y", "-i", str(norm), "-vn", "-c:a", "pcm_s16le",
                 "-ar", "48000", "-ac", "2", str(norm_wav)])
        else:
            run(["ffmpeg", "-y", "-i", str(out), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                 "-c:a", "pcm_s16le", "-ar", "48000", str(norm)])
        log("  %s" % rel(norm))

    # mappa parole nel tempo pulito
    transcript_path = bdir / "transcript.json"
    words_clean: List[Dict[str, Any]] = []
    if transcript_path.exists():
        transcript = read_json(transcript_path)
        for w in load_words(transcript):
            mid = (w["start"] + w["end"]) / 2.0
            seg = next((s for s in segments if s["src_start"] <= mid < s["src_end"]), None)
            if not seg:
                continue
            ns = seg["out_start"] + (w["start"] - seg["src_start"])
            ne = seg["out_start"] + (w["end"] - seg["src_start"])
            words_clean.append({
                "word": w["word"],
                "start": round(max(seg["out_start"], ns), 3),
                "end": round(min(seg["out_end"], ne), 3),
            })
        write_json(bdir / "words.json", words_clean)

        lines = ["# Voiceover pulito - %s" % slug,
                 "# durata %s" % fmt_tc(cuts["stats"]["cleaned"]), ""]
        for seg in segments:
            seg_words = [w["word"] for w in words_clean
                         if seg["out_start"] <= w["start"] < seg["out_end"]]
            lines.append("[%s -> %s] %s" % (
                fmt_tc(seg["out_start"]), fmt_tc(seg["out_end"]), " ".join(seg_words)))
        (bdir / "vo_clean.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    write_json(bdir / "timemap.json", {
        "source": cuts["source"],
        "original": cuts["stats"]["original"],
        "cleaned": cuts["stats"]["cleaned"],
        "segments": segments,
    })

    log("\nAudio pulito: %s (%s)" % (rel(out), fmt_tc(cuts["stats"]["cleaned"])))
    log("  mappa tempi: build/%s/timemap.json" % slug)
    log("  testo pulito: build/%s/vo_clean.txt" % slug)
    return 0


# ---------------------------------------------------------------- validate

def is_placeholder_suggestion(value: Optional[str]) -> bool:
    return isinstance(value, str) and value.strip().startswith("?")


def cmd_validate(args: argparse.Namespace) -> int:
    slug = args.slug
    load_project(slug)
    shotlist = load_shotlist(slug)
    errors: List[str] = []
    warnings: List[str] = []

    fmt = shotlist.get("format") or {}
    width = int(fmt.get("width") or 0)
    height = int(fmt.get("height") or 0)
    fps = float(fmt.get("fps") or 0)
    if width <= 0 or height <= 0:
        errors.append("format.width/height mancanti")
    if fps <= 0:
        errors.append("format.fps mancante")
    if width and height and width > height and not args.allow_landscape:
        warnings.append("formato orizzontale: per Shorts usa 1080x1920")

    face_video = shotlist.get("face_video")
    if face_video is not None and not isinstance(face_video, str):
        errors.append("face_video deve essere un percorso stringa")
    face_fit = str(shotlist.get("face_fit") or "crop")
    if face_fit not in FACE_FITS:
        errors.append("face_fit '%s' non valido (%s)" % (face_fit, ", ".join(FACE_FITS)))

    slots = shotlist.get("slots") or []
    if not slots:
        errors.append("nessuno slot nello shotlist")

    index = None
    if index_path().exists():
        index = load_index()
    else:
        warnings.append("media/index.json assente: salto i controlli sui file (lancia scan)")

    known = {e["path"] for e in all_index_entries(index)} if index else set()

    ids = set()
    total = 0.0
    base_slots: List[Dict[str, Any]] = []
    face_slots: List[Dict[str, Any]] = []
    auto_trs: List[Tuple[float, float, str]] = []
    for i, slot in enumerate(slots):
        label = slot.get("id") or "#%d" % (i + 1)
        for field in ("id", "start", "duration", "layer", "kind", "intent", "suggest", "animation"):
            if field not in slot:
                errors.append("%s: manca '%s'" % (label, field))
        if slot.get("id") in ids:
            errors.append("%s: id duplicato" % label)
        ids.add(slot.get("id"))

        if slot.get("kind") not in KINDS:
            errors.append("%s: kind '%s' non valido (%s)" % (label, slot.get("kind"), ", ".join(KINDS)))
        if slot.get("layer") not in LAYERS:
            errors.append("%s: layer '%s' non valido" % (label, slot.get("layer")))
        source = slot.get("source") or "broll"
        if source not in SOURCES:
            errors.append("%s: source '%s' non valido (%s)" % (
                label, source, ", ".join(SOURCES)))
        elif source == "face":
            face_slots.append(slot)
            if slot.get("layer") != "base":
                errors.append("%s: source=face richiede layer=base (la faccia va su V1)" % label)
            if slot.get("kind") != "clip":
                warnings.append("%s: source=face con kind '%s': usa 'clip'" % (label, slot.get("kind")))
            if slot.get("animation") not in (None, "static"):
                warnings.append(
                    "%s: source=face con animation '%s': il taglio A-roll e statico, "
                    "l'animazione va applicata dopo in Resolve" % (label, slot.get("animation")))
        if slot.get("animation") not in ANIMATIONS:
            errors.append("%s: animation '%s' non valida (%s)" % (
                label, slot.get("animation"), ", ".join(ANIMATIONS)))
        if slot.get("blend") is not None and slot.get("blend") not in BLENDS:
            errors.append("%s: blend '%s' non valido (%s)" % (
                label, slot.get("blend"), ", ".join(BLENDS)))
        if slot.get("opacity") is not None:
            try:
                op = float(slot["opacity"])
                if op < 0 or op > 100:
                    errors.append("%s: opacity fuori da 0-100" % label)
            except Exception:
                errors.append("%s: opacity non numerica" % label)

        tr = (slot.get("transition_in") or {}).get("type", "cut")
        if tr not in TRANSITIONS:
            errors.append("%s: transition_in.type '%s' non valida (%s)" % (
                label, tr, ", ".join(TRANSITIONS)))

        try:
            start = float(slot.get("start") or 0.0)
            dur = float(slot.get("duration") or 0.0)
        except Exception:
            errors.append("%s: start/duration non numerici" % label)
            continue
        if dur <= 0:
            errors.append("%s: durata <= 0" % label)
        if start < 0:
            errors.append("%s: start negativo" % label)

        if tr != "cut":
            if tr == "cross-dissolve":
                warnings.append(
                    "%s: cross-dissolve resta manuale (l'API free non crea transizioni); "
                    "usa glitch/flash/dip-to-black/whip-pan per l'automatico" % label)
            try:
                tdur = float((slot.get("transition_in") or {}).get("duration") or 0.4)
            except Exception:
                tdur = 0.4
                errors.append("%s: transition_in.duration non numerica" % label)
            if tdur < 0.2 or tdur > 0.8:
                warnings.append("%s: transition_in.duration %.2fs fuori da 0.2-0.8s "
                                "(verra limitata)" % (label, tdur))
            if start < tdur / 2.0:
                warnings.append("%s: transizione a inizio timeline: copre il primo frame" % label)
            if tr in AUTO_TRANSITIONS:
                adur = max(0.2, min(0.8, tdur, max(0.2, dur)))
                at = max(0.0, start - adur / 2.0)
                auto_trs.append((at, at + adur, label))
        total = max(total, start + dur)
        if slot.get("layer") == "base":
            base_slots.append(slot)

        intent = (slot.get("intent") or "").strip()
        if len(intent) < 8:
            errors.append("%s: 'intent' troppo corta (spiega cosa si deve vedere)" % label)

        suggest = slot.get("suggest") or {}
        primary = suggest.get("primary")
        why = (suggest.get("why") or "").strip()
        if not primary and not is_placeholder_suggestion(primary):
            errors.append("%s: suggest.primary mancante" % label)
        if not why:
            errors.append("%s: suggest.why mancante (devi dire perche)" % label)
        elif len(why) < 15:
            warnings.append("%s: suggest.why molto corta" % label)

        for key, value in (("primary", primary), ("alternatives", suggest.get("alternatives") or [])):
            values = value if isinstance(value, list) else [value]
            for v in values:
                if not v or is_placeholder_suggestion(v):
                    continue
                if not isinstance(v, str):
                    errors.append("%s: %s non e una stringa" % (label, key))
                    continue
                if not (v.startswith("media/") or v.startswith("build/")):
                    warnings.append("%s: %s non parte da media/ (%s)" % (label, key, v))
                if index and v.startswith("media/") and v not in known:
                    errors.append("%s: file inesistente nell'indice: %s" % (label, v))

        for sfx in slot.get("sfx") or []:
            f = sfx.get("file")
            if not f:
                errors.append("%s: sfx senza 'file'" % label)
            elif index and f.startswith("media/") and f not in known:
                errors.append("%s: sfx inesistente: %s" % (label, f))
            at = float(sfx.get("at") or 0.0)
            if at < 0 or at > float(slot.get("duration") or 0):
                warnings.append("%s: sfx a %.2fs fuori dallo slot" % (label, at))

        if slot.get("kind") == "text" and not (slot.get("text") or "").strip():
            errors.append("%s: kind=text ma 'text' vuoto" % label)

    # slot faccia: il video sorgente deve esistere e coprire tutti gli slot
    if face_slots and (face_video is None or isinstance(face_video, str)):
        face_src = face_source_path(shotlist, slug)
        if not face_src.exists():
            errors.append("slot faccia presenti ma manca %s: lancia render-audio %s --video" % (
                rel(face_src), slug))
        else:
            info = ffprobe(face_src)
            if not info.get("has_video"):
                errors.append("slot faccia: %s non ha una traccia video" % rel(face_src))
            else:
                face_end = max(float(s.get("start") or 0.0) + float(s.get("duration") or 0.0)
                               for s in face_slots)
                src_dur = float(info.get("duration") or 0.0)
                if src_dur > 0 and face_end > src_dur + 0.15:
                    errors.append(
                        "slot faccia fino a %.2fs ma %s dura %.2fs: controlla i tempi" % (
                            face_end, rel(face_src), src_dur))

    # copertura del layer base
    base_sorted = sorted(base_slots, key=lambda s: float(s["start"]))
    cursor = 0.0
    for s in base_sorted:
        st = float(s["start"])
        if st > cursor + 0.02:
            warnings.append("buco nel layer base: %.2fs -> %.2fs" % (cursor, st))
        cursor = max(cursor, st + float(s["duration"]))
    vo_dur = float(shotlist.get("voiceover_duration") or 0.0)
    if vo_dur > 0:
        if abs(cursor - vo_dur) > 0.25:
            warnings.append("gli slot coprono %.2fs ma il voiceover dura %.2fs" % (cursor, vo_dur))

    # overlay dentro un base
    for s in slots:
        if s.get("layer") != "overlay":
            continue
        st = float(s["start"])
        en = st + float(s["duration"])
        inside = any(float(b["start"]) <= st + 0.01 and en <= float(b["start"]) + float(b["duration"]) + 0.01
                     for b in base_sorted)
        if not inside:
            warnings.append("%s: overlay fuori da qualsiasi slot base" % s.get("id"))

    auto_trs.sort(key=lambda x: x[0])
    for i in range(1, len(auto_trs)):
        if auto_trs[i][0] < auto_trs[i - 1][1] - 1e-6:
            warnings.append(
                "transizioni sovrapposte: %s e %s; la seconda verra saltata "
                "(riduci duration o distanzia gli slot)" % (auto_trs[i - 1][2], auto_trs[i][2]))

    bgm = shotlist.get("bgm")
    if bgm:
        f = (bgm or {}).get("file")
        if not f:
            errors.append("bgm senza 'file'")
        elif index and f.startswith("media/") and f not in known:
            errors.append("bgm inesistente: %s" % f)

    captions = shotlist.get("captions")
    if captions is not None:
        if not isinstance(captions, dict):
            errors.append("captions deve essere un oggetto")
        else:
            unknown = set(captions) - set(CAPTION_DEFAULTS)
            for key in sorted(unknown):
                warnings.append("captions: chiave sconosciuta '%s'" % key)
            if not captions.get("enabled", True):
                warnings.append("captions disattivate: per gli Shorts sono fortemente consigliate")
            pos = captions.get("position", "lower")
            if pos not in CAPTION_POSITIONS:
                errors.append("captions.position '%s' non valida (%s)" % (
                    pos, ", ".join(CAPTION_POSITIONS)))
            for key, lo, hi in (("max_words", 1, 8), ("max_chars", 8, 60),
                                ("max_duration", 0.6, 8.0), ("font_size", 30, 120)):
                if key not in captions:
                    continue
                try:
                    val = float(captions[key])
                except Exception:
                    errors.append("captions.%s non numerico" % key)
                    continue
                if val < lo or val > hi:
                    warnings.append("captions.%s %.2f fuori da %s-%s (verra limitato)" % (
                        key, val, lo, hi))
            if "background" in captions:
                try:
                    bg = float(captions["background"])
                    if bg < 0.0 or bg > 1.0:
                        warnings.append("captions.background fuori da 0-1 (verra limitato)")
                except Exception:
                    errors.append("captions.background non numerico")

    # --- Studio 21.1.1 quality fields ---
    # animation_mode
    anim_mode = shotlist.get("animation_mode", "baked")
    if anim_mode not in ANIMATION_MODES:
        errors.append("animation_mode '%s' non valido (%s)" % (anim_mode, ", ".join(ANIMATION_MODES)))

    # native_transitions
    native_tr = shotlist.get("native_transitions", False)
    if native_tr and anim_mode != "fusion":
        errors.append("native_transitions richiede animation_mode: fusion")

    # transition_handle
    handle = shotlist.get("transition_handle")
    if handle is not None:
        try:
            h = float(handle)
            if h < 0.2 or h > 1.5:
                errors.append("transition_handle fuori da 0.2-1.5s")
        except Exception:
            errors.append("transition_handle non numerico")

    # audio.voice_isolation
    audio = shotlist.get("audio") or {}
    if audio.get("voice_isolation"):
        amt = audio.get("voice_isolation_amount", 60)
        try:
            a = int(amt)
            if a < 0 or a > 100:
                errors.append("audio.voice_isolation_amount fuori da 0-100")
        except Exception:
            errors.append("audio.voice_isolation_amount non numerico")

    # bgm.duck
    bgm = shotlist.get("bgm") or {}
    duck = bgm.get("duck", False)
    duck_db = bgm.get("duck_db")
    if duck and duck_db is not None:
        try:
            d = float(duck_db)
            if d > -3 or d < -24:
                warnings.append("bgm.duck_db fuori da -24..-3 (verra limitato)")
        except Exception:
            errors.append("bgm.duck_db non numerico")

    for w in warnings:
        log("  [warn] %s" % w)
    for e in errors:
        log("  [ERR ] %s" % e)

    log("")
    log("%d slot, durata timeline %.2fs (%s)" % (len(slots), total, fmt_tc(total)))
    log("Errori: %d | Avvisi: %d" % (len(errors), len(warnings)))

    if not errors and total > 0:
        log("OK: shotlist valido. Puoi generare i segnaposto.")
    return 0 if not errors else 1


# ---------------------------------------------------------------- placeholders

CARD_W, CARD_H = 1350, 2400
OUT_W, OUT_H = 1080, 1920

PALETTE = {
    "clip":       {"base": (13, 27, 62),   "accent": (96, 165, 250)},
    "image":      {"base": (12, 43, 30),   "accent": (74, 222, 128)},
    "logo":       {"base": (58, 24, 12),   "accent": (251, 146, 60)},
    "screenshot": {"base": (38, 18, 70),   "accent": (196, 181, 253)},
    "text":       {"base": (60, 30, 8),    "accent": (252, 211, 77)},
    "ui":         {"base": (60, 12, 32),   "accent": (249, 168, 212)},
}


def font(size: int, bold: bool = False) -> Any:
    if not HAS_PIL:
        return None
    candidates = FONT_CANDIDATES_BOLD if bold else FONT_CANDIDATES_REGULAR
    for path in candidates:
        if not Path(path).exists():
            continue
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def text_len(draw: Any, text: str, f: Any) -> float:
    try:
        return float(draw.textlength(text, font=f))
    except Exception:
        return float(len(text) * 0.55 * (f.size if hasattr(f, "size") else 10))


def wrap_text(draw: Any, text: str, f: Any, max_w: float, max_lines: int = 99) -> List[str]:
    words = str(text).split()
    lines: List[str] = []
    cur = ""
    for w in words:
        candidate = (cur + " " + w).strip()
        if text_len(draw, candidate, f) <= max_w or not cur:
            cur = candidate
        else:
            lines.append(cur)
            cur = w
            if len(lines) >= max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines:
        joined = " ".join(lines)
        if text_len(draw, joined, f) > max_w * max_lines:
            lines[-1] = lines[-1].rstrip(". ") + "..."
    return lines


def vgradient(w: int, h: int, c1: Tuple[int, int, int], c2: Tuple[int, int, int]) -> "Image.Image":
    strip = Image.new("RGB", (1, h))
    px = strip.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = (
            int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t),
        )
    return strip.resize((w, h))


def scanlines(size: Tuple[int, int], alpha: int = 16, step: int = 5) -> "Image.Image":
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for y in range(0, size[1], step):
        d.line([(0, y), (size[0], y)], fill=(0, 0, 0, alpha), width=1)
    return layer


def draw_corners(d: Any, box: Tuple[int, int, int, int], color: Tuple[int, int, int], size: int = 46, w: int = 6) -> None:
    x0, y0, x1, y1 = box
    d.line([(x0, y0), (x0 + size, y0)], fill=color, width=w)
    d.line([(x0, y0), (x0, y0 + size)], fill=color, width=w)
    d.line([(x1 - size, y0), (x1, y0)], fill=color, width=w)
    d.line([(x1, y0), (x1, y0 + size)], fill=color, width=w)
    d.line([(x0, y1 - size), (x0, y1)], fill=color, width=w)
    d.line([(x0, y1), (x0 + size, y1)], fill=color, width=w)
    d.line([(x1 - size, y1), (x1, y1)], fill=color, width=w)
    d.line([(x1, y1 - size), (x1, y1)], fill=color, width=w)


def short_path(value: Optional[str], max_chars: int = 46) -> str:
    if not value:
        return "-"
    v = str(value)
    if v.startswith("?"):
        return v[1:].strip()
    parts = v.split("/")
    if len(parts) > 3:
        v = ".../" + "/".join(parts[-2:])
    if len(v) > max_chars:
        v = "..." + v[-max_chars:]
    return v


def make_base_card(slot: Dict[str, Any], shotlist: Dict[str, Any]) -> "Image.Image":
    kind = slot.get("kind", "clip")
    pal = PALETTE.get(kind, PALETTE["clip"])
    accent = pal["accent"]

    rgb = vgradient(CARD_W, CARD_H, pal["base"], (8, 10, 18)).convert("RGB")

    margin = 80
    f_id = font(150, True)
    f_kind = font(46, True)
    f_meta = font(40)
    f_label = font(34, True)
    f_intent = font(62, True)
    f_body = font(40)
    f_small = font(32)

    # livello traslucido (Pillow non fa blending in RGBA: si compone a parte)
    ov = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)

    wm = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    ImageDraw.Draw(wm).text((CARD_W // 2 + 40, CARD_H // 2), "PLACEHOLDER", font=font(140, True),
                            fill=(255, 255, 255, 14), anchor="mm")
    wm = wm.rotate(28, resample=Image.BICUBIC)
    ov = Image.alpha_composite(ov, wm)
    od = ImageDraw.Draw(ov)

    badge = kind.upper()
    bw = text_len(od, badge, f_kind) + 52
    bx1 = CARD_W - margin
    od.rounded_rectangle([bx1 - bw, margin + 40, bx1, margin + 112], radius=16,
                         fill=(accent[0], accent[1], accent[2], 52),
                         outline=(accent[0], accent[1], accent[2], 235), width=3)

    box = (margin, margin + 300, CARD_W - margin, CARD_H - 600)
    od.rounded_rectangle(box, radius=28, fill=(255, 255, 255, 12),
                         outline=(accent[0], accent[1], accent[2], 120), width=3)

    od.line([(margin, margin + 245), (CARD_W - margin, margin + 245)],
            fill=(255, 255, 255, 45), width=2)

    rgb = Image.alpha_composite(rgb.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(rgb)

    # header
    d.text((margin, margin - 12), str(slot.get("id", "?")), font=f_id, fill=(255, 255, 255))
    d.text((bx1 - bw / 2, margin + 76), badge, font=f_kind, fill=(255, 255, 255), anchor="mm")

    start = float(slot.get("start") or 0.0)
    dur = float(slot.get("duration") or 0.0)
    meta = "%s  |  %s  |  %.1fs  |  %s -> %s" % (
        slot.get("layer", "base"), shotlist.get("style", "-"),
        dur, fmt_tc(start), fmt_tc(start + dur))
    d.text((margin, margin + 168), meta, font=f_meta, fill=(214, 224, 240))

    draw_corners(d, box, accent, size=60, w=7)

    inner_x = margin + 50
    inner_w = CARD_W - 2 * margin - 100
    y = box[1] + 55
    d.text((inner_x, y), "COSA METTERE QUI", font=f_label, fill=accent)
    y += 58

    intent = slot.get("intent") or "(intent mancante)"
    for line in wrap_text(d, intent, f_intent, inner_w, max_lines=4):
        d.text((inner_x, y), line, font=f_intent, fill=(255, 255, 255))
        y += 76

    # suggerimento
    y = max(y + 55, box[1] + 500)
    suggest = slot.get("suggest") or {}
    d.text((inner_x, y), "CONSIGLIATO", font=f_label, fill=(200, 208, 225))
    y += 50
    for line in wrap_text(d, short_path(suggest.get("primary")), f_body, inner_w, max_lines=2):
        d.text((inner_x, y), line, font=f_body, fill=accent)
        y += 50

    alts = [short_path(a) for a in (suggest.get("alternatives") or [])][:2]
    if alts:
        y += 14
        d.text((inner_x, y), "alternative", font=f_small, fill=(170, 178, 195))
        y += 42
        for alt in alts:
            d.text((inner_x, y), "- " + alt, font=f_small, fill=(222, 228, 240))
            y += 40

    # perche: occupa lo spazio che resta, senza uscire dal riquadro
    y = max(y + 40, box[3] - 300)
    d.text((inner_x, y), "PERCHE", font=f_label, fill=(200, 208, 225))
    y += 48
    why_lines = wrap_text(d, suggest.get("why") or "-", f_body, inner_w, max_lines=5)
    while len(why_lines) > 1 and y + len(why_lines) * 46 > box[3] - 40:
        why_lines.pop()
        why_lines[-1] = why_lines[-1].rstrip(". ") + "..."
    for line in why_lines:
        d.text((inner_x, y), line, font=f_body, fill=(230, 236, 248))
        y += 46

    # footer
    fy = CARD_H - 290
    d.line([(margin, fy), (CARD_W - margin, fy)], fill=(120, 130, 150), width=2)
    anim = "ANIM  %s" % slot.get("animation", "static")
    tr = slot.get("transition_in") or {}
    if tr.get("type") and tr.get("type") != "cut":
        anim += "   |   TRANS  %s %.2fs" % (
            tr.get("type"), float(tr.get("duration") or 0.4))
    d.text((margin, fy + 38), anim, font=f_small, fill=(235, 240, 250))
    sfx = slot.get("sfx") or []
    if sfx:
        d.text((margin, fy + 86), "SFX   %s" % ", ".join(short_path(s.get("file"), 24) for s in sfx),
               font=f_small, fill=(210, 218, 232))
    d.text((margin, fy + 140), "SOSTITUISCI QUESTO FILE CON IL TUO MEDIA", font=f_small, fill=accent)

    # scanline leggere
    sl = scanlines((CARD_W, CARD_H), alpha=12, step=6)
    rgb = Image.alpha_composite(rgb.convert("RGBA"), sl).convert("RGB")
    return rgb


def make_overlay_card(slot: Dict[str, Any], shotlist: Dict[str, Any]) -> "Image.Image":
    kind = slot.get("kind", "logo")
    pal = PALETTE.get(kind, PALETTE["logo"])
    accent = pal["accent"]
    img = Image.new("RGBA", (OUT_W, OUT_H), (0, 0, 0, 0))

    margin = 90
    box = (margin, OUT_H // 2 - 420, OUT_W - margin, OUT_H // 2 + 420)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle(box, radius=36, fill=(8, 10, 18, 205),
                         outline=(accent[0], accent[1], accent[2], 240), width=5)
    img = Image.alpha_composite(img, layer)
    d = ImageDraw.Draw(img)
    draw_corners(d, box, accent, size=54, w=7)

    f_id = font(120, True)
    f_kind = font(40, True)
    f_intent = font(52, True)
    f_small = font(32)

    d.text((box[0] + 50, box[1] + 40), str(slot.get("id", "?")), font=f_id, fill=(255, 255, 255))
    d.text((box[0] + 50, box[1] + 175), "OVERLAY / " + kind.upper(), font=f_kind, fill=accent)
    y = box[1] + 250
    for line in wrap_text(d, slot.get("intent") or "-", f_intent, box[2] - box[0] - 100, max_lines=4):
        d.text((box[0] + 50, y), line, font=f_intent, fill=(255, 255, 255))
        y += 64
    y += 20
    for line in wrap_text(d, short_path((slot.get("suggest") or {}).get("primary")), f_small,
                          box[2] - box[0] - 100, max_lines=3):
        d.text((box[0] + 50, y), line, font=f_small, fill=(228, 234, 246))
        y += 44

    d.text((box[0] + 50, box[3] - 70), "anim: %s" % slot.get("animation", "static"),
           font=f_small, fill=(200, 208, 222))
    return img


def zoompan_filter(animation: str, frames: int, fps: float) -> str:
    fr = max(1, frames)
    cx = "iw/2-(iw/zoom/2)"
    cy = "ih/2-(ih/zoom/2)"
    if animation == "push-in-slow":
        zmax, slope = 1.16, (1.16 - 1.0) / fr
        z = "min(1+%.8f*on,%.4f)" % (slope, zmax)
        return "zoompan=z='%s':x='%s':y='%s':d=%d:s=%dx%d:fps=%s" % (z, cx, cy, fr, OUT_W, OUT_H, fps)
    if animation == "push-in-fast":
        zmax, slope = 1.14, (1.14 - 1.0) / max(1, int(fr * 0.35))
        z = "min(1+%.8f*on,%.4f)" % (slope, zmax)
        return "zoompan=z='%s':x='%s':y='%s':d=%d:s=%dx%d:fps=%s" % (z, cx, cy, fr, OUT_W, OUT_H, fps)
    if animation == "pull-out-slow":
        z = "max(1.16-%.8f*on,1.0)" % ((1.16 - 1.0) / fr)
        return "zoompan=z='%s':x='%s':y='%s':d=%d:s=%dx%d:fps=%s" % (z, cx, cy, fr, OUT_W, OUT_H, fps)
    if animation == "pan-lr":
        return ("zoompan=z='1.18':x='(iw-iw/zoom)*min(on/%d,1)':y='%s':d=%d:s=%dx%d:fps=%s"
                % (fr, cy, fr, OUT_W, OUT_H, fps))
    if animation == "pan-rl":
        return ("zoompan=z='1.18':x='(iw-iw/zoom)*(1-min(on/%d,1))':y='%s':d=%d:s=%dx%d:fps=%s"
                % (fr, cy, fr, OUT_W, OUT_H, fps))
    if animation == "drift-up":
        return ("zoompan=z='1.14':x='%s':y='(ih-ih/zoom)*(1-min(on/%d,1))':d=%d:s=%dx%d:fps=%s"
                % (cx, fr, fr, OUT_W, OUT_H, fps))
    return "zoompan=z='1.0':x='0':y='0':d=%d:s=%dx%d:fps=%s" % (fr, OUT_W, OUT_H, fps)


def has_encoder(name: str) -> bool:
    try:
        out = run(["ffmpeg", "-hide_banner", "-encoders"]).stdout or ""
        return name in out
    except Exception:
        return False


def frame_at(sec: float, fps: float) -> int:
    """Stesso arrotondamento usato nello script Lua, per avere clip a filo."""
    return int(math.floor(float(sec) * fps + 0.5))


def slot_frames(slot: Dict[str, Any], fps: float) -> int:
    start = float(slot.get("start") or 0.0)
    dur = float(slot.get("duration") or 0.0)
    return max(1, frame_at(start + dur, fps) - frame_at(start, fps))


def encode_base(card_path: Path, out_path: Path, slot: Dict[str, Any], fps: float) -> None:
    frames = slot_frames(slot, fps)
    vf = zoompan_filter(slot.get("animation", "static"), frames, fps) + ",format=yuv420p"
    run([
        "ffmpeg", "-y", "-i", str(card_path), "-vf", vf,
        "-frames:v", str(frames), "-r", str(fps),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path),
    ])


def encode_overlay(card_path: Path, out_path: Path, slot: Dict[str, Any], fps: float) -> None:
    frames = slot_frames(slot, fps)
    if has_encoder("prores_ks"):
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(card_path), "-frames:v", str(frames),
               "-r", str(fps), "-c:v", "prores_ks", "-profile:v", "4444",
               "-pix_fmt", "yuva444p10le", "-vendor", "apl0", str(out_path)]
    else:
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(card_path), "-frames:v", str(frames),
               "-r", str(fps), "-c:v", "qtrle", "-pix_fmt", "argb", str(out_path)]
    run(cmd)


# ---------------------------------------------------------------- captions

def hex_rgb(value: Any, default: Tuple[int, int, int] = (255, 255, 255)) -> Tuple[int, int, int]:
    s = str(value or "").strip().lstrip("#")
    try:
        if len(s) == 3:
            s = "".join(c * 2 for c in s)
        if len(s) != 6:
            return default
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except Exception:
        return default


def caption_config(shotlist: Dict[str, Any]) -> Dict[str, Any]:
    raw = shotlist.get("captions")
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    cfg = dict(CAPTION_DEFAULTS)
    for key in CAPTION_DEFAULTS:
        if key in raw:
            cfg[key] = raw[key]
    cfg["enabled"] = bool(cfg.get("enabled", True))
    if cfg.get("position") not in CAPTION_POSITIONS:
        cfg["position"] = "lower"
    for key, lo, hi in (("max_words", 1, 8), ("max_chars", 8, 60),
                        ("max_duration", 0.6, 8.0), ("font_size", 30, 120)):
        try:
            cfg[key] = max(lo, min(hi, type(CAPTION_DEFAULTS[key])(cfg[key])))
        except Exception:
            cfg[key] = CAPTION_DEFAULTS[key]
    try:
        cfg["background"] = max(0.0, min(1.0, float(cfg.get("background", 0.55))))
    except Exception:
        cfg["background"] = 0.55
    cfg["uppercase"] = bool(cfg.get("uppercase", False))
    return cfg


CAPTION_WEAK_END = {
    # articoli, preposizioni, congiunzioni, ausiliari: brutti da lasciare a fine blocco
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una",
    "di", "a", "da", "in", "con", "su", "per", "tra", "fra",
    "e", "ed", "o", "od", "ma", "che", "perche", "se", "come", "quando",
    "ha", "ho", "hai", "hanno", "sono", "sei", "siamo", "siete", "era", "erano",
    "the", "a", "an", "of", "to", "in", "on", "at", "with", "for", "from",
    "and", "or", "but", "that", "because", "if", "when", "as",
    "is", "are", "was", "were", "has", "have", "had", "be", "been",
}


def group_caption_words(words: List[Dict[str, Any]], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Raggruppa le parole in blocchi leggibili, senza tagliare a metà frase."""
    clean: List[Dict[str, Any]] = []
    for w in words or []:
        text = str(w.get("word") or "").strip()
        try:
            start = float(w.get("start"))
            end = float(w.get("end"))
        except Exception:
            continue
        if not text or end <= start:
            continue
        clean.append({"word": text, "start": start, "end": end})
    clean.sort(key=lambda w: w["start"])

    chunks: List[Dict[str, Any]] = []
    cur: List[Dict[str, Any]] = []

    def flush() -> None:
        nonlocal cur
        if not cur:
            return
        text = " ".join(w["word"] for w in cur)
        if text:
            text = text[0].upper() + text[1:]
        chunks.append({
            "start": round(float(cur[0]["start"]), 3),
            "end": round(float(cur[-1]["end"]), 3),
            "text": text,
        })
        cur = []

    max_words = int(cfg["max_words"])
    max_chars = int(cfg["max_chars"])
    max_duration = float(cfg["max_duration"])

    def is_weak(word: str) -> bool:
        bare = word.lower().strip(".,;:!?…\"'«»()[]")
        return bare in CAPTION_WEAK_END

    for w in clean:
        candidate = (" ".join(x["word"] for x in cur) + " " + w["word"]).strip()
        too_long = len(candidate) > max_chars
        too_many = len(cur) >= max_words
        too_slow = bool(cur) and (w["end"] - cur[0]["start"]) > max_duration
        if cur and (too_long or too_many or too_slow):
            # non chiudere su "di", "perche", "the"...: sposta la coda debole
            # nel blocco successivo, cosi la frase resta leggibile.
            moved: List[Dict[str, Any]] = []
            while len(cur) > 1 and is_weak(str(cur[-1]["word"])):
                moved.insert(0, cur.pop())
            flush()
            cur.extend(moved)
        cur.append(w)
        if re.search(r"[.!?…]$", w["word"]) and len(cur) >= 2:
            flush()
    flush()

    # un piccolo hold aiuta la lettura, senza invadere il blocco successivo.
    # Il limite e sempre il start del blocco dopo: niente clip sovrapposte su V4.
    for i, ch in enumerate(chunks):
        if i + 1 < len(chunks):
            limit = max(ch["start"] + 0.04, chunks[i + 1]["start"] - 0.01)
            ch["end"] = min(ch["end"] + 0.10, limit)
        else:
            ch["end"] = ch["end"] + 0.10
        ch["end"] = round(max(ch["start"] + 0.04, ch["end"]), 3)

    return [c for c in chunks if c["end"] > c["start"]]


def caption_layout(draw: Any, text: str, cfg: Dict[str, Any], max_w: float) -> Tuple[List[str], Any]:
    size = int(cfg["font_size"])
    f = None
    lines: List[str] = []
    for candidate_size in range(size, 43, -2):
        candidate_font = font(candidate_size, True)
        candidate_lines = wrap_text(draw, text, candidate_font, max_w, max_lines=2)
        if len(candidate_lines) <= 2 and all(
                text_len(draw, line, candidate_font) <= max_w for line in candidate_lines):
            f = candidate_font
            lines = candidate_lines
            break
    if f is None:
        f = font(44, True)
        lines = wrap_text(draw, text, f, max_w, max_lines=2)
    return lines, f


def make_caption_card(text: str, cfg: Dict[str, Any]) -> "Image.Image":
    img = Image.new("RGBA", (OUT_W, OUT_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    shown = str(text).strip()
    if cfg.get("uppercase"):
        shown = shown.upper()
    max_w = OUT_W - 180
    lines, f = caption_layout(d, shown, cfg, max_w)
    if not lines:
        return img

    probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    line_h = max(1, int(probe.textbbox((0, 0), "Ag", font=f)[3]))
    gap = 10
    pad_x, pad_y = 34, 22
    text_w = max(text_len(d, line, f) for line in lines)
    text_h = line_h * len(lines) + gap * (len(lines) - 1)
    box_w = min(OUT_W - 120, int(text_w + pad_x * 2))
    box_h = int(text_h + pad_y * 2)
    center_y = {"lower": 1490, "middle": 960, "upper": 430}.get(cfg.get("position"), 1490)
    box_x = (OUT_W - box_w) // 2
    box_y = int(center_y - box_h // 2)

    bg_alpha = int(255 * float(cfg.get("background", 0.55)))
    d.rounded_rectangle([box_x, box_y, box_x + box_w, box_y + box_h],
                        radius=26, fill=(0, 0, 0, bg_alpha),
                        outline=(255, 255, 255, 34), width=2)

    color = hex_rgb(cfg.get("color"), (255, 255, 255))
    for i, line in enumerate(lines):
        cy = box_y + pad_y + i * (line_h + gap) + line_h // 2
        d.text((OUT_W // 2 + 3, cy + 3), line, font=f, fill=(0, 0, 0, 190), anchor="mm")
        d.text((OUT_W // 2, cy), line, font=f, fill=(*color, 255), anchor="mm")
    return img


def encode_alpha_image(card_path: Path, out_path: Path, frames: int, fps: float) -> None:
    """QTRLE: molto piu leggero di ProRes per testi con tanto alpha."""
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(card_path), "-frames:v", str(max(1, frames)),
        "-r", str(fps), "-c:v", "qtrle", "-pix_fmt", "argb", str(out_path),
    ])


def encode_alpha_frames(frames: List["Image.Image"], out_path: Path, fps: float) -> None:
    tmp = out_path.parent / ("_frames_" + out_path.stem)
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        for i, img in enumerate(frames):
            img.save(tmp / ("frame_%04d.png" % i))
        run([
            "ffmpeg", "-y", "-framerate", str(fps), "-start_number", "0",
            "-i", str(tmp / "frame_%04d.png"), "-frames:v", str(len(frames)),
            "-r", str(fps), "-c:v", "qtrle", "-pix_fmt", "argb", str(out_path),
        ])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def build_captions(slug: str, shotlist: Dict[str, Any], force: bool = False) -> List[Dict[str, Any]]:
    cfg = caption_config(shotlist)
    bdir = build_dir(slug)
    cdir = bdir / "captions"
    cdir.mkdir(parents=True, exist_ok=True)
    manifest_path = cdir / "manifest.json"

    if not cfg["enabled"]:
        write_json(manifest_path, [])
        log("  captions: disattivate nello shotlist")
        return []

    wpath = bdir / "words.json"
    if not wpath.exists():
        write_json(manifest_path, [])
        log("  [warn] captions saltate: manca build/%s/words.json" % slug)
        log("         lancia prima: render-audio %s" % slug)
        return []

    words = read_json(wpath)
    chunks = group_caption_words(words, cfg)
    if not chunks:
        write_json(manifest_path, [])
        log("  [warn] captions: nessuna parola utilizzabile in words.json")
        return []

    fps = float((shotlist.get("format") or {}).get("fps") or 30)
    manifest: List[Dict[str, Any]] = []
    for i, ch in enumerate(chunks, 1):
        name = "c%03d" % i
        card = cdir / ("%s.png" % name)
        out = cdir / ("%s.mov" % name)
        frames = max(1, frame_at(ch["end"], fps) - frame_at(ch["start"], fps))
        duration = frames / fps
        if force or not card.exists():
            make_caption_card(ch["text"], cfg).save(card)
        if force or not out.exists():
            encode_alpha_image(card, out, frames, fps)
        manifest.append({
            "file": rel(out),
            "at": round(float(ch["start"]), 3),
            "duration": round(duration, 3),
            "text": ch["text"],
        })

    write_json(manifest_path, manifest)

    srt_lines: List[str] = []
    for i, cap in enumerate(manifest, 1):
        srt_lines.append(str(i))
        srt_lines.append("%s --> %s" % (
            fmt_srt(cap["at"]), fmt_srt(cap["at"] + cap["duration"])))
        srt_lines.append(cap["text"])
        srt_lines.append("")
    (cdir / "captions.srt").write_text("\n".join(srt_lines), encoding="utf-8")

    log("  captions: %d blocchi (%s) + captions.srt" % (len(manifest), cfg["position"]))
    return manifest


# ---------------------------------------------------------------- transitions

def transition_frames(kind: str, frames: int, seed: int) -> List["Image.Image"]:
    n = max(2, frames)
    out: List["Image.Image"] = []
    if kind in ("dip-to-black", "flash"):
        base = (0, 0, 0) if kind == "dip-to-black" else (255, 255, 255)
        for i in range(n):
            t = i / (n - 1)
            alpha = int(255 * (math.sin(math.pi * t) ** 2))
            out.append(Image.new("RGBA", (OUT_W, OUT_H), (*base, alpha)))
        return out

    rng = random.Random(seed)
    for i in range(n):
        img = Image.new("RGBA", (OUT_W, OUT_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        t = i / (n - 1)
        if kind == "glitch":
            for _ in range(rng.randint(3, 7)):
                y = rng.randint(0, OUT_H - 20)
                h = rng.randint(8, 70)
                color = rng.choice([(0, 255, 255), (255, 0, 200), (255, 255, 255)])
                d.rectangle([0, y, OUT_W, y + h], fill=(*color, rng.randint(35, 120)))
            for y in range(0, OUT_H, 6):
                d.line([(0, y), (OUT_W, y)], fill=(0, 0, 0, rng.randint(20, 70)), width=1)
            for _ in range(rng.randint(10, 24)):
                x = rng.randint(0, OUT_W - 10)
                y = rng.randint(0, OUT_H - 10)
                d.rectangle([x, y, x + rng.randint(4, 90), y + rng.randint(2, 18)],
                            fill=(255, 255, 255, rng.randint(30, 100)))
        elif kind == "whip-pan":
            for _ in range(rng.randint(16, 30)):
                y = rng.randint(0, OUT_H)
                w = rng.randint(2, 10)
                color = rng.choice([(255, 255, 255), (180, 240, 255), (255, 230, 180)])
                d.line([(0, y), (OUT_W, y + rng.randint(-30, 30))],
                       fill=(*color, rng.randint(30, 120)), width=w)
            flash = int(150 * (1.0 - abs(2.0 * t - 1.0)))
            if flash > 0:
                d.rectangle([0, 0, OUT_W, OUT_H], fill=(255, 255, 255, flash))
        out.append(img)
    return out


def build_transitions(slug: str, shotlist: Dict[str, Any], force: bool = False) -> List[Dict[str, Any]]:
    bdir = build_dir(slug)
    tdir = bdir / "transitions"
    tdir.mkdir(parents=True, exist_ok=True)
    fps = float((shotlist.get("format") or {}).get("fps") or 30)
    native_tr = shotlist.get("native_transitions", False)
    manifest: List[Dict[str, Any]] = []
    warned_dissolve = False
    last_end = -1.0

    for slot in shotlist.get("slots") or []:
        tr = slot.get("transition_in") or {}
        kind = str(tr.get("type") or "cut")
        if kind == "cut":
            continue
        
        is_native_candidate = kind in ("cross-dissolve", "dip-to-black")
        is_native = native_tr and is_native_candidate
        
        if kind == "cross-dissolve" and not is_native:
            if not warned_dissolve:
                log("  [warn] cross-dissolve resta manuale: l'API free non crea transizioni")
                warned_dissolve = True
            continue
        if kind not in AUTO_TRANSITIONS and not is_native:
            continue

        sid = str(slot.get("id"))
        start = float(slot.get("start") or 0.0)
        slot_dur = float(slot.get("duration") or 0.4)
        try:
            dur = float(tr.get("duration") or 0.4)
        except Exception:
            dur = 0.4
        dur = max(0.2, min(0.8, dur, max(0.2, slot_dur)))
        at = max(0.0, start - dur / 2.0)
        frames = max(2, int(round(dur * fps)))
        dur = frames / fps
        if at < last_end - 1e-6:
            log("  [warn] transizione %s sovrapposta alla precedente: la salto" % sid)
            continue
        last_end = at + dur
        
        entry = {
            "at": round(at, 3),
            "duration": round(dur, 3),
            "type": kind,
            "slot": sid,
            "native": is_native,
        }
        
        if is_native:
            # Transizione nativa: niente file overlay, solo manifest per Lua
            log("  transizione nativa: %s su %s (%.2fs)" % (kind, sid, dur))
            manifest.append(entry)
        else:
            # Overlay generato (glitch, flash, whip-pan)
            out = tdir / ("t_%s_%s.mov" % (sid, kind))
            if force or not out.exists():
                seed = int(hashlib.md5(("%s:%s" % (sid, kind)).encode("utf-8")).hexdigest()[:8], 16)
                frames_img = transition_frames(kind, frames, seed)
                encode_alpha_frames(frames_img, out, fps)
            entry["file"] = rel(out)
            manifest.append(entry)

    write_json(tdir / "manifest.json", manifest)
    native_count = sum(1 for m in manifest if m.get("native"))
    overlay_count = len(manifest) - native_count
    if manifest:
        log("  transizioni: %d native, %d overlay (%s)" % (
            native_count, overlay_count, ", ".join(sorted({m["type"] for m in manifest}))))
    return manifest


def face_source_path(shotlist: Dict[str, Any], slug: str) -> Path:
    """Video originale del talking head, gia tagliato da render-audio --video."""
    value = shotlist.get("face_video")
    if value:
        if not isinstance(value, str):
            die("face_video deve essere un percorso stringa")
        path = Path(value).expanduser()
        return path if path.is_absolute() else ROOT / path
    return build_dir(slug) / "vo_clean.mp4"


def build_face_clip(src: Path, out: Path, slot: Dict[str, Any], fps: float,
                    fit: str = "crop") -> None:
    """Taglia la faccia dal video pulito e la adatta al formato verticale."""
    frames = slot_frames(slot, fps)
    start = float(slot.get("start") or 0.0)
    rate = "%.6g" % fps
    vf = ["fps=%s" % rate]
    if fit == "fit":
        vf.append("scale=%d:%d:force_original_aspect_ratio=decrease" % (OUT_W, OUT_H))
        vf.append("pad=%d:%d:(ow-iw)/2:(oh-ih)/2:black" % (OUT_W, OUT_H))
    else:
        vf.append("scale=%d:%d:force_original_aspect_ratio=increase" % (OUT_W, OUT_H))
        vf.append("crop=%d:%d" % (OUT_W, OUT_H))
    vf += ["setsar=1", "format=yuv420p"]
    run([
        "ffmpeg", "-y", "-ss", "%.3f" % start, "-i", str(src), "-an",
        "-vf", ",".join(vf), "-frames:v", str(frames), "-r", rate,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ])


def cmd_placeholders(args: argparse.Namespace) -> int:
    if not HAS_PIL:
        die("Pillow non installato: .venv/bin/pip install pillow")
    slug = args.slug
    load_project(slug)
    shotlist = load_shotlist(slug)
    fmt = shotlist.get("format") or {}
    fps = float(fmt.get("fps") or 30)
    if int(fmt.get("width") or 0) != OUT_W or int(fmt.get("height") or 0) != OUT_H:
        die("questo pipeline genera segnaposto 1080x1920. Cambia format nello shotlist.")

    # --- Fingerprint per invalidazione segnaposto ---
    import hashlib, json
    settings_fp = hashlib.md5(json.dumps({
        "animation_mode": shotlist.get("animation_mode", "baked"),
        "native_transitions": shotlist.get("native_transitions", False),
        "transition_handle": shotlist.get("transition_handle", 0.6),
        "fps": fps,
        "width": int(fmt.get("width") or 1080),
        "height": int(fmt.get("height") or 1920),
        "generator_version": 2,
    }, sort_keys=True).encode()).hexdigest()[:12]

    bdir = build_dir(slug)
    pdir = bdir / "placeholders"
    pdir.mkdir(parents=True, exist_ok=True)

    fp_path = pdir / "settings_fingerprint.json"
    force_regen = args.force
    if fp_path.exists():
        try:
            old = read_json(fp_path).get("fingerprint")
            if old != settings_fp:
                force_regen = True
                log("  [info] fingerprint cambiato ({} -> {}): rigenero segnaposto".format(old, settings_fp))
        except Exception:
            force_regen = True
    else:
        force_regen = True

    if force_regen:
        for f in pdir.glob("*_base.mp4"):
            f.unlink(missing_ok=True)
        for f in pdir.glob("*_ovl.mov"):
            f.unlink(missing_ok=True)
        for f in pdir.glob("*.png"):
            f.unlink(missing_ok=True)

    # Handle frames per transizioni native
    handle_frames = 0
    if shotlist.get("native_transitions"):
        handle_sec = float(shotlist.get("transition_handle", 0.6))
        handle_frames = max(1, math.ceil(handle_sec * fps))

    manifest: Dict[str, Dict[str, Any]] = {}
    slots = shotlist.get("slots") or []
    face_slots = [s for s in slots if s.get("source") == "face"]
    face_src: Optional[Path] = None
    face_fit = str(shotlist.get("face_fit") or "crop")
    if face_fit not in FACE_FITS:
        die("face_fit '%s' non valido: usa crop o fit" % face_fit)
    if face_slots:
        face_src = face_source_path(shotlist, slug)
        if not face_src.exists():
            die("mancano le clip faccia: %s non esiste.\n"
                "  registra il talking head in media/voiceover/raw/ e lancia:\n"
                "  .venv/bin/python scripts/shorts.py render-audio %s --video" % (rel(face_src), slug))
        info = ffprobe(face_src)
        if not info.get("has_video"):
            die("il video per gli slot faccia non ha una traccia video: %s" % face_src)
        face_end = max(float(s.get("start") or 0.0) + float(s.get("duration") or 0.0)
                       for s in face_slots)
        src_dur = float(info.get("duration") or 0.0)
        if src_dur > 0 and face_end > src_dur + 0.15:
            die("gli slot faccia arrivano a %.2fs ma il video dura %.2fs.\n"
                "  Controlla i tempi in vo_clean.txt e rilancia roughcut/render-audio." % (
                    face_end, src_dur))

    log("Genero %d elementi (segnaposto + A-roll)..." % len(slots))

    anim_mode = shotlist.get("animation_mode", "baked")
    native_tr = shotlist.get("native_transitions", False)

    for i, slot in enumerate(slots, 1):
        sid = str(slot.get("id"))
        source = slot.get("source") or "broll"
        if source == "face":
            if slot.get("layer") != "base":
                die("%s: source=face richiede layer=base" % sid)
            if face_src is None:
                die("%s: sorgente faccia non disponibile" % sid)
            adir = bdir / "aroll"
            adir.mkdir(parents=True, exist_ok=True)
            out = adir / ("%s_face.mp4" % sid)
            if args.force or not out.exists():
                build_face_clip(face_src, out, slot, fps, face_fit)
            manifest[sid] = {"base": rel(out)}
        elif slot.get("layer") == "overlay":
            card = pdir / ("%s_card.png" % sid)
            out = pdir / ("%s_ovl.mov" % sid)
            if args.force or not card.exists():
                make_overlay_card(slot, shotlist).save(card)
            if args.force or not out.exists():
                encode_overlay(card, out, slot, fps)
            manifest[sid] = {"overlay": rel(out)}
        else:
            card = pdir / ("%s_card.png" % sid)
            out = pdir / ("%s_base.mp4" % sid)
            if args.force or not card.exists():
                make_base_card(slot, shotlist).save(card, quality=92)
            if args.force or not out.exists():
                frames = slot_frames(slot, fps)
                is_animated = slot.get("animation", "static") != "static"
                if anim_mode == "fusion" and is_animated:
                    # Fusion: genera statico, niente zoompan
                    vf = "format=yuv420p"
                else:
                    vf = zoompan_filter(slot.get("animation", "static"), frames, fps) + ",format=yuv420p"
                
                source_start = 30  # handle sinistro fisso 1s sorgente
                if native_tr:
                    total_frames = frames + 2 * handle_frames
                    run([
                        "ffmpeg", "-y", "-ss", "%.3f" % (source_start / 30.0), "-i", str(card), "-vf", vf,
                        "-frames:v", str(total_frames), "-r", str(fps),
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
                    ])
                else:
                    run([
                        "ffmpeg", "-y", "-i", str(card), "-vf", vf,
                        "-frames:v", str(frames), "-r", str(fps),
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
                    ])
            manifest[sid] = {
                "base": rel(out),
                "animation_mode": anim_mode,
                "handle_frames": handle_frames if native_tr else 0,
                "animation": slot.get("animation", "static"),
            }
        if i % 5 == 0 or i == len(slots):
            log("  %d/%d" % (i, len(slots)))

    write_json(pdir / "manifest.json", manifest)
    # Salva fingerprint
    write_json(fp_path, {"fingerprint": settings_fp, "animation_mode": anim_mode})
    log("\nSegnaposto in build/%s/placeholders/" % slug)
    log("  manifest.json")
    if face_slots:
        log("  A-roll gia tagliata in build/%s/aroll/ (%d clip)" % (slug, len(face_slots)))

    build_transitions(slug, shotlist, force=args.force)
    build_captions(slug, shotlist, force=args.force)
    return 0


def cmd_captions(args: argparse.Namespace) -> int:
    if not HAS_PIL:
        die("Pillow non installato: .venv/bin/pip install pillow")
    slug = args.slug
    load_project(slug)
    shotlist = load_shotlist(slug)
    log("Genero le caption per %s..." % slug)
    caps = build_captions(slug, shotlist, force=args.force)
    if caps:
        log("  file: build/%s/captions/" % slug)
    return 0


# ---------------------------------------------------------------- lua

def lua_str(value: Any) -> str:
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return ("%d" % value) if float(value).is_integer() else ("%.4f" % value)
    s = str(value)
    s = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")
    return '"%s"' % s


def lua_table(value: Any, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(value, dict):
        if not value:
            return "{}"
        parts = ["{"]
        for k, v in value.items():
            key = k if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(k)) else "[%s]" % lua_str(k)
            parts.append("%s  %s = %s," % (pad, key, lua_table(v, indent + 1)))
        parts.append(pad + "}")
        return "\n".join(parts)
    if isinstance(value, (list, tuple)):
        if not value:
            return "{}"
        parts = ["{"]
        for v in value:
            parts.append("%s  %s," % (pad, lua_table(v, indent + 1)))
        parts.append(pad + "}")
        return "\n".join(parts)
    return lua_str(value)


LUA_BODY = r"""
local function p(...)
  local parts = {}
  for i = 1, select("#", ...) do parts[i] = tostring(select(i, ...)) end
  print(table.concat(parts, " "))
end

local function fail(msg) p("!! " .. msg) end

if resolve == nil then
  fail("Apri Workspace > Console, seleziona Lua e incolla questo script li.")
  return
end

-- Radice del progetto: lo script non contiene percorsi assoluti.
-- Cerca nell'ordine: SHORTS_ROOT (se lo imposti), ~/shorts-studio, cartella corrente.
-- Se la cartella ha un altro nome o percorso, scrivi prima in Console:
--   SHORTS_ROOT = "/percorso/della/cartella"
if DATA.root == nil then
  local mark = "/build/" .. DATA.project .. "/placeholders/manifest.json"
  local candidates = {}
  if type(SHORTS_ROOT) == "string" and SHORTS_ROOT ~= "" then
    table.insert(candidates, SHORTS_ROOT)
  end
  local home = os.getenv and os.getenv("HOME")
  if home ~= nil and home ~= "" then
    table.insert(candidates, home .. "/shorts-studio")
  end
  table.insert(candidates, ".")
  for _, dir in ipairs(candidates) do
    local fh = io.open(dir .. mark, "rb")
    if fh ~= nil then
      fh:close()
      DATA.root = dir
      break
    end
  end
end

if DATA.root == nil then
  fail("Cartella di shorts-studio non trovata.")
  p("   Apri la Console col progetto giusto e scrivi prima:")
  p("   SHORTS_ROOT = \"/percorso/della/cartella/shorts-studio\"")
  return
end

p("root: " .. DATA.root)

local pm = resolve:GetProjectManager()
local project = pm and pm:GetCurrentProject()
if project == nil then
  fail("Nessun progetto aperto in Resolve. Creane uno e rilancia.")
  return
end

p("== shorts-studio ==")
p("progetto: " .. project:GetName())
p("timeline: " .. DATA.timeline .. "  |  " .. DATA.width .. "x" .. DATA.height .. " @ " .. DATA.fps .. "fps")

-- impostazioni progetto
pcall(function() project:SetSetting("timelineFrameRate", tostring(DATA.fps)) end)
pcall(function() project:SetSetting("timelineResolutionWidth", tostring(DATA.width)) end)
pcall(function() project:SetSetting("timelineResolutionHeight", tostring(DATA.height)) end)

local fps = DATA.fps
local function frame(sec) return math.floor(sec * fps + 0.5) end

-- bin
local mp = project:GetMediaPool()
local mpRoot = mp:GetRootFolder()
local binName = "SHORTS_" .. DATA.project
local bin = nil
for _, f in ipairs(mpRoot:GetSubFolderList()) do
  if f:GetName() == binName then bin = f end
end
if bin == nil then bin = mp:AddSubFolder(mpRoot, binName) end

local cache = {}
local missing = 0
local function importFile(relPath)
  if relPath == nil or relPath == "" then return nil end
  local abs = DATA.root .. "/" .. relPath
  if cache[abs] ~= nil then return cache[abs] end
  local fh = io.open(abs, "rb")
  if fh == nil then
    fail("file mancante: " .. abs)
    missing = missing + 1
    return nil
  end
  fh:close()
  mp:SetCurrentFolder(bin)
  local items = mp:ImportMedia({ abs })
  if items == nil or items[1] == nil then
    fail("import fallito: " .. abs)
    missing = missing + 1
    return nil
  end
  cache[abs] = items[1]
  return items[1]
end

-- timeline
local old = nil
for i = 1, project:GetTimelineCount() do
  local tl = project:GetTimelineByIndex(i)
  if tl ~= nil and tl:GetName() == DATA.timeline then old = tl end
end
if old ~= nil then
  local newName = DATA.timeline .. "_old_" .. os.date("%H%M%S")
  old:SetName(newName)
  p("timeline precedente rinominata: " .. newName)
end

local timeline = mp:CreateEmptyTimeline(DATA.timeline)
if timeline == nil then
  fail("creazione timeline fallita")
  return
end
mp:SetCurrentTimeline(timeline)

local function ensureTracks(kind, wanted)
  local cur = timeline:GetTrackCount(kind)
  while cur < wanted do
    timeline:AddTrack(kind)
    cur = timeline:GetTrackCount(kind)
  end
end
local videoTracks = 2
local transTrack = nil
local capTrack = nil
if DATA.transitions ~= nil and #DATA.transitions > 0 then
  videoTracks = videoTracks + 1
  transTrack = videoTracks
end
if DATA.captions ~= nil and #DATA.captions > 0 then
  videoTracks = videoTracks + 1
  capTrack = videoTracks
end
ensureTracks("video", videoTracks)
ensureTracks("audio", 3)

pcall(function() timeline:SetTrackName("video", 1, "B-ROLL") end)
pcall(function() timeline:SetTrackName("video", 2, "OVERLAY") end)
if transTrack ~= nil then
  pcall(function() timeline:SetTrackName("video", transTrack, "TRANSITIONS") end)
end
if capTrack ~= nil then
  pcall(function() timeline:SetTrackName("video", capTrack, "CAPTIONS") end)
end
pcall(function() timeline:SetTrackName("audio", 1, "VOICE") end)
pcall(function() timeline:SetTrackName("audio", 2, "SFX") end)
pcall(function() timeline:SetTrackName("audio", 3, "BGM") end)

local function addClip(item, trackIndex, mediaType, recFrame, startF, endF)
  if item == nil then return nil end
  local info = { mediaPoolItem = item, trackIndex = trackIndex, recordFrame = recFrame }
  if mediaType ~= nil then info.mediaType = mediaType end
  if startF ~= nil then info.startFrame = startF end
  if endF ~= nil then info.endFrame = endF end
  local r = timeline:AppendToTimeline({ info })
  if r ~= nil and r[1] ~= nil then return r[1] end
  return nil
end

local colorByKind = {
  clip = "Blue", image = "Green", logo = "Orange",
  screenshot = "Purple", text = "Yellow", ui = "Pink",
}

-- CompositeMode: 0 normal, 1 add, 4 multiply, 5 screen, 6 overlay
local BLEND = { normal = 0, add = 1, multiply = 4, screen = 5, overlay = 6 }

local placed = {}
local placed_by_id = {}
local function placeSlot(slot, trackIndex, mediaType)
  if slot.file == nil or slot.file == "" then return nil end
  local item = importFile(slot.file)
  local tlItem = nil
  if slot.frames ~= nil and tonumber(slot.frames) ~= nil and tonumber(slot.frames) > 0 then
    -- A-roll: endFrame e esclusivo, quindi frames = durata esatta.
    tlItem = addClip(item, trackIndex, mediaType, frame(slot.start), 0, tonumber(slot.frames))
  else
    tlItem = addClip(item, trackIndex, mediaType, frame(slot.start))
  end
  if tlItem ~= nil then
    pcall(function() tlItem:SetClipColor(colorByKind[slot.kind] or "Blue") end)
    if slot.zoom ~= nil and tonumber(slot.zoom) ~= nil and tonumber(slot.zoom) ~= 1.0 then
      local z = tonumber(slot.zoom)
      pcall(function() tlItem:SetProperty("ZoomX", z) end)
      pcall(function() tlItem:SetProperty("ZoomY", z) end)
    end
    if slot.opacity ~= nil and tonumber(slot.opacity) ~= nil and tonumber(slot.opacity) < 100 then
      pcall(function() tlItem:SetProperty("Opacity", tonumber(slot.opacity)) end)
    end
    if slot.blend ~= nil and BLEND[slot.blend] ~= nil then
      pcall(function() tlItem:SetProperty("CompositeMode", BLEND[slot.blend]) end)
    end
    placed[#placed + 1] = { id = slot.id, track = trackIndex, start = slot.start, dur = slot.duration }
    placed_by_id[slot.id] = tlItem
  end
  return tlItem
end

-- V1 base
local baseCount = 0
for _, slot in ipairs(DATA.slots) do
  if slot.layer == "base" then
    if placeSlot(slot, 1, 1) ~= nil then baseCount = baseCount + 1 end
  end
end
p("V1 base: " .. baseCount .. " clip")

-- V2 overlay
local ovlCount = 0
for _, slot in ipairs(DATA.slots) do
  if slot.layer == "overlay" then
    if placeSlot(slot, 2, 1) ~= nil then ovlCount = ovlCount + 1 end
  end
end
p("V2 overlay: " .. ovlCount .. " clip")

-- Fusion comp per slot base animati (solo se animation_mode == fusion)
if DATA.animation_mode == "fusion" then
  local function addFusionAnim(tlItem, animName, frames)
    if animName == "static" then return end
    local comp = tlItem:AddFusionComp()
    if not comp then
      p("!! Fusion comp fallito per " .. tlItem:GetName() .. " (API non disponibile)")
      return
    end
    comp:StartUndo()
    local mi = comp:FindTool("MediaIn1")
    local mo = comp:FindTool("MediaOut1")
    if not mi or not mo then
      p("!! MediaIn/MediaOut non trovati nel comp")
      comp:EndUndo(false)
      return
    end
    local t = comp:AddTool("Transform")
    if not t then
      p("!! Transform tool non disponibile")
      comp:EndUndo(false)
      return
    end
    local ok1 = t:ConnectInput("Input", mi)
    local ok2 = mo:ConnectInput("Input", t)
    if not ok1 or not ok2 then
      p("!! Wiring Transform fallito")
      comp:EndUndo(false)
      return
    end
    -- Keyframe mapping
    local keyframes = {}
    if animName == "push-in-slow" then
      keyframes = { {input="Size", [0]=1.0, [frames-1]=1.16} }
    elseif animName == "push-in-fast" then
      local f35 = math.floor(frames * 0.35)
      keyframes = { {input="Size", [0]=1.0, [f35]=1.14} }
    elseif animName == "pull-out-slow" then
      keyframes = { {input="Size", [0]=1.16, [frames-1]=1.0} }
    elseif animName == "pan-lr" then
      keyframes = {
        {input="Size", [0]=1.18, [frames-1]=1.18},
        {input="Center", [0]={0.41, 0.5}, [frames-1]={0.59, 0.5}}
      }
    elseif animName == "pan-rl" then
      keyframes = {
        {input="Size", [0]=1.18, [frames-1]=1.18},
        {input="Center", [0]={0.59, 0.5}, [frames-1]={0.41, 0.5}}
      }
    elseif animName == "drift-up" then
      keyframes = {
        {input="Size", [0]=1.14, [frames-1]=1.14},
        {input="Center", [0]={0.5, 0.43}, [frames-1]={0.5, 0.57}}
      }
    end
    for _, kf in ipairs(keyframes) do
      local inp = kf.input
      t:AddModifier(inp, "BezierSpline")
      for frame, val in pairs(kf) do
        if type(frame) == "number" then
          t[inp][frame] = val
        end
      end
      -- Verifica lettura indietro
      local check = t:GetInput(inp, frames-1)
      if check == nil then
        p("!! Keyframe " .. inp .. " non scritto")
      end
    end
    comp:EndUndo(true)
  end

  for _, slot in ipairs(DATA.slots) do
    if slot.layer == "base" and slot.animation and slot.animation ~= "static" then
      local tlItem = placed_by_id[slot.id]
      if tlItem then
        local frames = slot.frames or math.floor(slot.duration * fps + 0.5)
        addFusionAnim(tlItem, slot.animation, frames)
      end
    end
  end
end

-- Transizioni native (cross-dissolve, dip-to-black) se native_transitions attivo
local nativeCount, overlayCount, failedCount = 0, 0, 0
if DATA.native_transitions and DATA.transitions then
  for _, tr in ipairs(DATA.transitions) do
    if tr.native and (tr.type == "cross-dissolve" or tr.type == "dip-to-black") then
      local incoming = placed_by_id[tr.slot]
      if incoming then
        local durFrames = math.floor((tr.duration or 0.4) * fps + 0.5)
        local leftHandle = incoming:GetLeftOffset() or 0
        local rightHandle = 0
        -- trova outgoing clip (quello prima sullo stesso track)
        local items = timeline:GetItemListInTrack("video", 1) or {}
        for i, it in ipairs(items) do
          if it:GetType() == "video" and it:GetEnd() == incoming:GetStart() then
            rightHandle = it:GetRightOffset() or 0
            break
          end
        end
        if leftHandle >= durFrames/2 and rightHandle >= durFrames/2 then
          local trType = (tr.type == "cross-dissolve") and "Cross Dissolve" or "Dip To Color Dissolve"
          local trans = incoming:AddTransition({
            type = trType,
            category = "simple",
            position = "start",
            alignment = "center",
            duration = durFrames
          })
          if trans and trans:GetDuration() >= durFrames * 0.5 then
            p("Native transition: " .. trType .. " " .. trans:GetDuration() .. "f su " .. tr.slot)
            nativeCount = nativeCount + 1
          else
            if trans then
              timeline:DeleteClips({trans}, false)
            end
            p("!! Native transition fallita/insufficiente: fallback overlay su " .. tr.slot)
            failedCount = failedCount + 1
          end
        else
          p("!! Handle insufficienti per native transition su " .. tr.slot .. " (L=" .. leftHandle .. " R=" .. rightHandle .. " need=" .. math.ceil(durFrames/2) .. ")")
          failedCount = failedCount + 1
        end
      end
    end
  end
end

-- V3 transizioni (overlay alpha per glitch/flash/whip-pan + fallback native fallite)
if transTrack ~= nil then
  local trCount = 0
  for _, tr in ipairs(DATA.transitions) do
    local isNative = tr.native and (tr.type == "cross-dissolve" or tr.type == "dip-to-black")
    if not isNative then
      local item = importFile(tr.file)
      if addClip(item, transTrack, 1, frame(tr.at)) ~= nil then trCount = trCount + 1 end
    end
  end
  p("V" .. transTrack .. " transizioni: " .. trCount .. " overlay, " .. nativeCount .. " native, " .. failedCount .. " fallite")
end

-- V4 caption (overlay alpha gia posizionate)
if capTrack ~= nil then
  local capCount = 0
  for _, cap in ipairs(DATA.captions) do
    local item = importFile(cap.file)
    if addClip(item, capTrack, 1, frame(cap.at)) ~= nil then capCount = capCount + 1 end
  end
  p("V" .. capTrack .. " caption: " .. capCount .. " clip")
end

-- A1 voiceover
local voItem = importFile(DATA.vo)
if addClip(voItem, 1, 2, 0) ~= nil then p("A1 voiceover: ok") end

-- Voice Isolation su A1 se richiesto
if DATA.audio and DATA.audio.voice_isolation then
  local amt = DATA.audio.voice_isolation_amount or 60
  local ok = false
  if timeline.SetVoiceIsolationState then
    ok = timeline:SetVoiceIsolationState(1, {isEnabled=true, amount=amt})
    p("Voice Isolation A1: " .. (ok and ("enabled amount=" .. amt) or "fallito (API)"))
  else
    p("!! Voice Isolation non disponibile in questa versione")
  end
end

-- A2 sfx (il gain e gia stato cotto nei file da shorts.py)
local sfxCount = 0
for _, cue in ipairs(DATA.sfx) do
  local item = importFile(cue.file)
  if addClip(item, 2, 2, frame(cue.at)) ~= nil then sfxCount = sfxCount + 1 end
end
p("A2 sfx: " .. sfxCount)

-- A3 bgm (usa bgm_duck se disponibile, altrimenti bgm)
local bgmFile = nil
if DATA.bgm_duck and DATA.bgm_duck.file then
  bgmFile = DATA.bgm_duck.file
  p("A3 bgm: usando file con ducking")
elseif DATA.bgm and DATA.bgm.file then
  bgmFile = DATA.bgm.file
end
if bgmFile then
  local item = importFile(bgmFile)
  if addClip(item, 3, 2, 0) ~= nil then
    p("A3 bgm: ok")
  else
    p("!! A3 bgm: non aggiunta")
  end
end

-- marker
for _, slot in ipairs(DATA.slots) do
  local ok = timeline:AddMarker(frame(slot.start), slot.color or "Blue",
                                slot.markerTitle or slot.id, slot.markerNote or "", frame(slot.duration))
  if not ok then p("!! marker fallito: " .. tostring(slot.id)) end
end
p("marker: " .. #DATA.slots)

-- verifica posizioni
local function verify(trackType, trackIndex, label)
  local items = timeline:GetItemListInTrack(trackType, trackIndex) or {}
  local bad = 0
  for _, it in ipairs(items) do
    local startF = it:GetStart()
    if startF == nil or startF < 0 then bad = bad + 1 end
  end
  -- Per transizioni, conta solo type=="transition"
  if label:find("transizioni") then
    local transCount = 0
    for _, it in ipairs(items) do
      if it:GetType() == "transition" then transCount = transCount + 1 end
    end
    p("  " .. label .. ": " .. #items .. " clip (" .. transCount .. " transizioni native)")
  else
    p("  " .. label .. ": " .. #items .. " clip sulla timeline")
  end
  if #items == 0 then p("  !! " .. label .. " vuoto") end
end
p("verifica:")
verify("video", 1, "V1")
verify("video", 2, "V2")
if transTrack ~= nil then verify("video", transTrack, "V" .. transTrack .. " transizioni") end
if capTrack ~= nil then verify("video", capTrack, "V" .. capTrack .. " caption") end
verify("audio", 1, "A1")
verify("audio", 2, "A2")
verify("audio", 3, "A3")

if missing > 0 then
  p("!! " .. missing .. " file mancanti: rigenera i segnaposto o controlla media/index.json")
end

pcall(function() timeline:SetCurrentTimecode("00:00:00:00") end)
pcall(function() resolve:OpenPage("edit") end)

p("")
p("FATTO. Timeline: " .. DATA.timeline)
p("Durata: " .. string.format("%.1f", DATA.total) .. "s su " .. #DATA.slots .. " slot")
p("Prossimo passo: sostituisci i segnaposto (vedi WORKFLOW.md, fase 8).")
if (DATA.face_slots or 0) > 0 then
  p("Gli slot A-ROLL/FACCIA sono gia tagliati: non sostituirli.")
end
p("Caption e transizioni automatiche sono gia su V4/V3: non si toccano.")
"""


def cmd_lua(args: argparse.Namespace) -> int:
    slug = args.slug
    load_project(slug)
    shotlist = load_shotlist(slug)
    bdir = build_dir(slug)
    pdir = bdir / "placeholders"
    mpath = pdir / "manifest.json"
    if not mpath.exists():
        die("manca build/%s/placeholders/manifest.json. Lancia prima: placeholders" % slug)

    manifest = read_json(mpath)
    fmt = shotlist.get("format") or {}
    fps = float(fmt.get("fps") or 30)
    face_count = sum(1 for s in (shotlist.get("slots") or []) if s.get("source") == "face")

    index = load_index() if index_path().exists() else {}
    sfx_durations = {e["path"]: e.get("duration", 0.0) for e in index.get("sfx") or []}
    bgm_durations = {e["path"]: e.get("duration", 0.0) for e in index.get("bgm") or []}

    total = 0.0
    for slot in shotlist.get("slots") or []:
        total = max(total, float(slot.get("start") or 0.0) + float(slot.get("duration") or 0.0))

    adir = bdir / "audio"
    adir.mkdir(parents=True, exist_ok=True)
    audio_cache: Dict[Tuple[str, float], str] = {}
    audio_made = 0

    def prep_sfx(rel_path: str, gain_db: float, duration: float = 0.0) -> str:
        """Applica il gain e micro-fade 5ms con ffmpeg: l'API di Resolve non espone il volume dei clip."""
        nonlocal audio_made
        key = (rel_path, round(float(gain_db), 2), round(duration, 3))
        if key in audio_cache:
            return audio_cache[key]
        if abs(gain_db) < 0.05 and duration <= 0:
            audio_cache[key] = rel_path
            return rel_path
        src = ROOT / rel_path
        if not src.exists():
            die("sfx non trovato: %s" % src)
        name = "%s_g%+d.wav" % (slugify(Path(rel_path).stem), int(round(gain_db)))
        out = adir / name
        af = "volume=%.2fdB" % gain_db
        if duration > 0.01:
            fade_out_start = max(0.0, duration - 0.005)
            af += ",afade=t=in:st=0:d=0.005,afade=t=out:st=%.3f:d=0.005" % fade_out_start
        run(["ffmpeg", "-y", "-i", str(src), "-af", af,
             "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(out)])
        audio_made += 1
        audio_cache[key] = rel(out)
        return audio_cache[key]

    slots_lua: List[Dict[str, Any]] = []
    sfx_cues: List[Dict[str, Any]] = []

    for slot in shotlist.get("slots") or []:
        sid = str(slot.get("id"))
        files = manifest.get(sid) or {}
        start = float(slot.get("start") or 0.0)
        dur = float(slot.get("duration") or 0.0)
        total = max(total, start + dur)

        is_face = slot.get("source") == "face"
        marker_note_parts = [
            "COSA: " + str(slot.get("intent") or "-"),
        ]
        if is_face:
            marker_note_parts.append("A-ROLL/FACCIA: gia tagliata, non sostituire")
        else:
            marker_note_parts.append(
                "CONSIGLIATO: " + str((slot.get("suggest") or {}).get("primary") or "-"))
        marker_note_parts += [
            "PERCHE: " + str((slot.get("suggest") or {}).get("why") or "-"),
            "ANIM: " + str(slot.get("animation") or "static"),
        ]
        if slot.get("text"):
            marker_note_parts.append("TESTO: " + str(slot.get("text")))
        tr = slot.get("transition_in") or {}
        if tr.get("type") and tr.get("type") != "cut":
            marker_note_parts.append("TRANSIZIONE: %s %.2fs" % (tr.get("type"), float(tr.get("duration") or 0)))

        kind = slot.get("kind") or "clip"
        color = {"clip": "Blue", "image": "Green", "logo": "Orange",
                 "screenshot": "Purple", "text": "Yellow", "ui": "Pink"}.get(kind, "Blue")
        if is_face:
            color = "Cyan"

        if slot.get("layer") == "overlay":
            file_path = files.get("overlay")
        else:
            file_path = files.get("base")

        opacity = float(slot.get("opacity") if slot.get("opacity") is not None else 100.0)
        opacity = max(0.0, min(100.0, opacity))
        blend = slot.get("blend") or "normal"
        if blend not in BLENDS:
            blend = "normal"

        slots_lua.append({
            "id": sid,
            "start": round(start, 3),
            "duration": round(dur, 3),
            "layer": slot.get("layer", "base"),
            "kind": kind,
            "file": file_path,
            "zoom": float(slot.get("zoom") or 1.0),
            "opacity": round(opacity, 2),
            "blend": blend,
            "color": color,
            "animation": slot.get("animation", "static"),
            "markerTitle": "%s %s - %s" % (
                sid, "A-ROLL" if is_face else kind.upper(), str(slot.get("intent") or "")[:48]),
            "markerNote": "\n".join(marker_note_parts),
        })
        if is_face:
            slots_lua[-1]["frames"] = slot_frames(slot, fps)

        for cue in slot.get("sfx") or []:
            f = cue.get("file")
            if not f:
                continue
            at = start + float(cue.get("at") or 0.0)
            gain = float(cue.get("gain_db") or 0.0)
            sfx_dur = float(sfx_durations.get(f) or 0.0)
            sfx_cues.append({
                "file": prep_sfx(f, gain, sfx_dur),
                "at": round(at, 3),
                "slot": sid,
                "gain": gain,
                "duration": sfx_dur,
            })

    bgm = shotlist.get("bgm")
    bgm_lua = None
    if bgm and bgm.get("file"):
        bgm_src = ROOT / bgm["file"]
        if not bgm_src.exists():
            die("bgm non trovata: %s" % bgm_src)
        if total <= 0.5:
            die("durata timeline non valida per la BGM: %.2fs" % total)
        bgm_out = adir / "bgm_mix.wav"
        gain = float(bgm.get("gain_db") or 0.0)
        fade_in = min(0.8, total / 10.0)
        fade_out = min(2.0, total / 5.0)
        fades = ""
        if total > fade_in + fade_out + 0.2:
            fades = ",afade=t=in:st=0:d=%.2f,afade=t=out:st=%.2f:d=%.2f" % (
                fade_in, total - fade_out, fade_out)
        cmd = ["ffmpeg", "-y"]
        if bgm.get("loop", True):
            cmd += ["-stream_loop", "-1"]
        cmd += ["-i", str(bgm_src), "-t", "%.3f" % total,
                "-af", "volume=%.2fdB%s" % (gain, fades),
                "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(bgm_out)]
        run(cmd)
        audio_made += 1
        src_dur = float(bgm_durations.get(bgm["file"]) or 0.0)
        if not bgm.get("loop", True) and 0 < src_dur < total - 0.2:
            log("  [warn] la BGM dura %.1fs ma la timeline %.1fs: resta un buco finale" % (src_dur, total))
        bgm_lua = {"file": rel(bgm_out)}

    cpath = bdir / "captions" / "manifest.json"
    captions_lua = read_json(cpath) if cpath.exists() else []
    tpath = bdir / "transitions" / "manifest.json"
    transitions_lua = read_json(tpath) if tpath.exists() else []

    default_vo = "build/%s/vo_clean.wav" % slug
    vo = shotlist.get("voiceover") or default_vo
    norm_vo = bdir / "vo_clean_norm.wav"
    if vo == default_vo and norm_vo.exists():
        vo = rel(norm_vo)

    # BGM ducking se richiesto (dopo che vo e definito)
    bgm_duck_lua = None
    bgm = shotlist.get("bgm")
    if bgm and bgm.get("duck"):
        duck_db = float(bgm.get("duck_db", -9))
        ratio = max(2.0, min(12.0, abs(duck_db) * 0.9))
        bgm_duck_path = adir / "bgm_duck.wav"
        try:
            run(["ffmpeg", "-y",
                 "-i", str(ROOT / bgm["file"]),
                 "-i", str(ROOT / vo),
                 "-filter_complex",
                 f"[0:a]volume={bgm.get('gain_db',0)}dB,aloop=loop=-1:size=2e9,atrim=0:{total}[bgm];"
                 f"[1:a]aresample=48000,apad=whole_dur={total},atrim=0:{total}[voice];"
                 f"[bgm][voice]sidechaincompress=threshold=0.05:ratio={ratio}:attack=20:release=350:makeup=1[out]",
                 "-map", "[out]", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(bgm_duck_path)])
            bgm_duck_lua = {"file": rel(bgm_duck_path)}
            log("  BGM ducking generato: %s (ratio=%.1f)" % (bgm_duck_path.name, ratio))
        except Exception as e:
            log("  [warn] BGM ducking fallito: %s, uso mix standard" % e)
            bgm_duck_lua = None

    data = {
        "project": slug,
        "timeline": "%s_v1" % slug,
        "fps": fps,
        "width": int(fmt.get("width") or 1080),
        "height": int(fmt.get("height") or 1920),
        "total": round(total, 3),
        "vo": vo,
        "face_slots": face_count,
        "slots": slots_lua,
        "sfx": sfx_cues,
        "bgm": bgm_lua,
        "bgm_duck": bgm_duck_lua,
        "captions": captions_lua,
        "transitions": transitions_lua,
        "native_transitions": shotlist.get("native_transitions", False),
        "audio": shotlist.get("audio", {}),
        "animation_mode": shotlist.get("animation_mode", "baked"),
        "transition_handle": shotlist.get("transition_handle", 0.6),
    }

    header = [
        "-- ============================================================",
        "--  shorts-studio - build timeline per DaVinci Resolve (free)",
        "--  generato: %s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "--  progetto: %s" % slug,
        "--",
        "--  COME SI USA",
        "--   1. Apri DaVinci Resolve e un progetto qualsiasi.",
        "--   2. Workspace > Console, seleziona 'Lua' in basso.",
        "--   3. Trascina questo file nella Console e premi Invio.",
        "--",
        "--  Lo script cerca la cartella in ~/shorts-studio o nella",
        "--  cartella corrente. Se e altrove, scrivi prima in Console:",
        "--    SHORTS_ROOT = \"/percorso/della/cartella\"",
        "-- ============================================================",
        "",
        "DATA = " + lua_table(data),
        "",
    ]

    out = bdir / ("%s_build.lua" % slug)
    out.write_text("\n".join(header) + LUA_BODY, encoding="utf-8")

    track_lines = [
        "V1 B-ROLL (segnaposto base + A-roll gia tagliata)" if face_count
        else "V1 B-ROLL (segnaposto base)",
        "V2 OVERLAY (loghi/grafiche)",
    ]
    if transitions_lua:
        track_lines.append("V3 TRANSITIONS (transizioni automatiche, restano dopo la sostituzione)")
    if captions_lua:
        track_lines.append("V4 CAPTIONS (caption gia posizionate)")
    track_lines += ["A1 VOICE", "A2 SFX", "A3 BGM"]
    replace_note = (
        "Sostituzione: seleziona il segnaposto nel Media Pool > click destro >\n"
        "Clip Operations > Replace Selected Clip (oppure F11) e scegli il tuo file.\n"
    )
    if face_count:
        replace_note += (
            "Gli slot A-ROLL/FACCIA su V1 sono gia tagliati dal tuo video: NON sostituirli.\n"
            "Sostituisci solo i segnaposto colorati.\n"
        )
    (bdir / "LEGGIMI-build.txt").write_text(
        "SCRIPT LUA PRONTO\n\n"
        "File: %s\n\n"
        "1. Apri DaVinci Resolve (versione free va bene) e apri un progetto.\n"
        "2. Menu Workspace > Console.\n"
        "3. In basso nella Console seleziona Lua.\n"
        "4. Trascina il file .lua dentro la Console e premi Invio.\n"
        "5. Alla fine torna nella pagina Edit: trovi la timeline '%s_v1'.\n\n"
        "Tracce:\n  %s\n\n"
        "%s"
        "Le caption e le transizioni automatiche sono su tracce separate: non si toccano.\n"
        "%s\n"
        "Se qualcosa va storto, copia l'output della Console e incollalo in OpenCode.\n" % (
            rel(out), slug, "\n  ".join(track_lines), replace_note,
            "Copia SRT: %s\n" % rel(bdir / "captions" / "captions.srt") if captions_lua else ""),
        encoding="utf-8")

    log("Script Lua: %s" % rel(out))
    log("  %d slot%s, %d cue sfx, %d caption, %d transizioni, %.1fs" % (
        len(slots_lua), " (%d A-roll)" % face_count if face_count else "",
        len(sfx_cues), len(captions_lua), len(transitions_lua), total))
    log("  istruzioni: build/%s/LEGGIMI-build.txt" % slug)
    return 0


# ---------------------------------------------------------------- qc

def cmd_qc(args: argparse.Namespace) -> int:
    if not HAS_PIL:
        die("Pillow non installato: .venv/bin/pip install pillow")
    slug = args.slug
    load_project(slug)
    shotlist = load_shotlist(slug)
    bdir = build_dir(slug)

    video = Path(args.video).expanduser() if args.video else (bdir / "export" / ("%s.mp4" % slug))
    if not video.exists():
        die("video non trovato: %s\n  esporta il video o passa --video PATH" % video)

    qdir = bdir / "qc"
    qdir.mkdir(parents=True, exist_ok=True)
    slots = shotlist.get("slots") or []
    shots: List[Tuple[str, Path, str]] = []

    for slot in slots:
        mid = float(slot.get("start") or 0.0) + float(slot.get("duration") or 0.0) / 2.0
        out = qdir / ("%s.jpg" % slot.get("id"))
        run(["ffmpeg", "-y", "-ss", "%.3f" % mid, "-i", str(video),
             "-frames:v", "1", "-q:v", "3", str(out)], check=False)
        if out.exists():
            label = "A-ROLL" if slot.get("source") == "face" else str(slot.get("kind") or "")
            shots.append((str(slot.get("id")), out, label))

    if not shots:
        die("nessun fotogramma estratto (video piu corto dello shotlist?)")

    per_sheet = 24
    cols = 6
    thumb_w, thumb_h = 240, 427
    pad = 14
    label_h = 34

    sheets: List[Path] = []
    for page in range(0, len(shots), per_sheet):
        chunk = shots[page:page + per_sheet]
        rows = int(math.ceil(len(chunk) / cols))
        sheet_w = cols * (thumb_w + pad) + pad
        sheet_h = rows * (thumb_h + label_h + pad) + pad
        sheet = Image.new("RGB", (sheet_w, sheet_h), (14, 14, 18))
        d = ImageDraw.Draw(sheet)
        f = font(22, True)

        for idx, (sid, path, kind) in enumerate(chunk):
            r, c = divmod(idx, cols)
            x = pad + c * (thumb_w + pad)
            y = pad + r * (thumb_h + label_h + pad)
            try:
                im = Image.open(path).convert("RGB")
                im = im.resize((thumb_w, thumb_h), Image.LANCZOS)
                sheet.paste(im, (x, y))
            except Exception:
                d.rectangle([x, y, x + thumb_w, y + thumb_h], fill=(60, 20, 20))
            d.text((x, y + thumb_h + 6), "%s  %s" % (sid, kind), font=f, fill=(230, 230, 235))

        out = qdir / ("sheet_%02d.jpg" % (len(sheets) + 1))
        sheet.save(out, quality=88)
        sheets.append(out)

    log("QC: %d fotogrammi, %d contact sheet" % (len(shots), len(sheets)))
    for s in sheets:
        log("  %s" % rel(s))
    log("")
    log("Apri il foglio (o allegalo a OpenCode) e chiedi una revisione visiva.")
    return 0


# ---------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="shorts.py", description="Pipeline Shorts con Resolve free")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="verifica dipendenze")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("init", help="crea un progetto")
    p.add_argument("slug")
    p.add_argument("--title", default="")
    p.add_argument("--language", default="auto",
                   help="lingua del voiceover: auto, it, en, ... (default: auto)")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("scan", help="indicizza media/")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("transcribe", help="Whisper -> transcript")
    p.add_argument("slug")
    p.add_argument("--input", default="")
    p.add_argument("--model", default="small")
    p.add_argument("--language", default="",
                   help="auto, it, en, ... (default: project.json, poi auto)")
    p.add_argument("--device", default="auto")
    p.add_argument("--compute-type", default="int8")
    p.set_defaults(func=cmd_transcribe)

    p = sub.add_parser("roughcut", help="tagli automatici")
    p.add_argument("slug")
    p.add_argument("--max-gap", type=float, default=0.45)
    p.add_argument("--pad", type=float, default=0.10)
    p.add_argument("--min-keep", type=float, default=0.12)
    p.add_argument("--aggressive", action="store_true", help="taglia anche cioe/tipo/praticamente...")
    p.add_argument("--keep-fillers", action="store_true")
    p.set_defaults(func=cmd_roughcut)

    p = sub.add_parser("render-audio", help="applica i tagli al voiceover")
    p.add_argument("slug")
    p.add_argument("--normalize", action="store_true")
    p.add_argument("--video", action="store_true",
                   help="taglia anche il video (talking head) e prepara A-roll + vo_clean.wav")
    p.set_defaults(func=cmd_render_audio)

    p = sub.add_parser("validate", help="valida lo shotlist")
    p.add_argument("slug")
    p.add_argument("--allow-landscape", action="store_true")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("placeholders", help="genera segnaposto animati + A-roll + caption + transizioni")
    p.add_argument("slug")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_placeholders)

    p = sub.add_parser("captions", help="genera solo le caption (overlay + SRT)")
    p.add_argument("slug")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_captions)

    p = sub.add_parser("lua", help="genera lo script per la Console di Resolve")
    p.add_argument("slug")
    p.set_defaults(func=cmd_lua)

    p = sub.add_parser("qc", help="contact sheet dal video esportato")
    p.add_argument("slug")
    p.add_argument("--video", default="")
    p.set_defaults(func=cmd_qc)

    return ap


def main(argv: Optional[List[str]] = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    ROOT.mkdir(parents=True, exist_ok=True)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
