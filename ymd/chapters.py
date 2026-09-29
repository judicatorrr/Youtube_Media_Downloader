from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .core import sanitize_filename


@dataclass
class Chapter:
    start_ms: int
    end_ms: int
    title: str


def timecode_to_ms(value: str) -> Optional[int]:
    value = (value or "").strip()
    parts = value.split(":")
    try:
        if len(parts) == 2:
            return int((int(parts[0]) * 60 + float(parts[1])) * 1000)
        if len(parts) == 3:
            return int((int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])) * 1000)
    except Exception:
        pass
    return None


def parse_manual_chapters(text: str, duration_ms: int) -> list[Chapter]:
    rows: list[tuple[int, str]] = []
    rx = re.compile(r"^\s*(\d{1,3}:\d{2}(?::\d{2}(?:\.\d+)?)?)\s+(.+?)\s*$")
    for line in (text or "").splitlines():
        m = rx.match(line)
        if not m:
            continue
        ms = timecode_to_ms(m.group(1))
        if ms is not None:
            rows.append((ms, m.group(2).strip()))

    # Unique start positions, sorted.
    unique = {}
    for start, title in rows:
        unique[start] = title
    ordered = sorted(unique.items())

    chapters: list[Chapter] = []
    for i, (start, title) in enumerate(ordered):
        end = ordered[i + 1][0] if i + 1 < len(ordered) else duration_ms
        if end > start:
            chapters.append(Chapter(start, end, title))
    return chapters


def chapters_from_info(info: dict, duration_ms: int) -> list[Chapter]:
    raw = info.get("chapters") or []
    result: list[Chapter] = []
    for i, ch in enumerate(raw):
        try:
            start = int(float(ch.get("start_time") or 0) * 1000)
        except Exception:
            start = 0
        end_value = ch.get("end_time")
        if end_value is None:
            if i + 1 < len(raw):
                end_value = raw[i + 1].get("start_time")
            else:
                end_value = duration_ms / 1000
        try:
            end = int(float(end_value or 0) * 1000)
        except Exception:
            end = 0
        if end > start:
            result.append(Chapter(start, end, str(ch.get("title") or f"Chapter {i+1}")))
    return result


def clip_chapters(chapters: Iterable[Chapter], from_ms: int, to_ms: int) -> list[Chapter]:
    result: list[Chapter] = []
    for ch in chapters:
        start = max(ch.start_ms, from_ms)
        end = min(ch.end_ms, to_ms)
        if end <= start:
            continue
        result.append(Chapter(start - from_ms, end - from_ms, ch.title))
    return result


def write_ffmetadata(chapters: list[Chapter], path: Path) -> bool:
    if not chapters:
        return False

    def esc(value: str) -> str:
        return (
            value.replace("\\", "\\\\")
            .replace("=", "\\=")
            .replace(";", "\\;")
            .replace("#", "\\#")
        )

    lines = [";FFMETADATA1"]
    for ch in chapters:
        lines += [
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={ch.start_ms}",
            f"END={ch.end_ms}",
            f"title={esc(ch.title)}",
        ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def media_duration_ms(ffprobe: Path, path: Path) -> int:
    try:
        cp = subprocess.run(
            [
                str(ffprobe), "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        value = float(cp.stdout.decode("utf-8", "replace").strip())
        return int(value * 1000)
    except Exception:
        return 86_400_000


def embed_chapters_copy(ffmpeg: Path, input_path: Path, chapters: list[Chapter]) -> tuple[bool, str]:
    if not chapters:
        return False, "No chapters"

    with tempfile.TemporaryDirectory(prefix="ymd_chapters_") as td:
        meta = Path(td) / "chapters.txt"
        if not write_ffmetadata(chapters, meta):
            return False, "Could not build chapter metadata"

        temp_out = input_path.with_name(input_path.stem + ".chapters-temp" + input_path.suffix)
        cmd = [
            str(ffmpeg),
            "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(input_path),
            "-i", str(meta),
            "-map", "0",
            "-map_metadata", "0",
            "-map_chapters", "1",
            "-c", "copy",
            str(temp_out),
        ]
        cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if cp.returncode != 0 or not temp_out.exists():
            return False, cp.stderr.decode("utf-8", "replace")
        temp_out.replace(input_path)
        return True, ""


def split_audio_copy(
    ffmpeg: Path,
    input_path: Path,
    chapters: list[Chapter],
    on_progress=None,
) -> tuple[bool, str, list[Path]]:
    if not chapters:
        return False, "No chapters", []

    created: list[Path] = []
    total = len(chapters)
    for i, ch in enumerate(chapters):
        if ch.end_ms <= ch.start_ms:
            continue
        start = ch.start_ms / 1000.0
        duration = (ch.end_ms - ch.start_ms) / 1000.0
        track = f"{i + 1:02d} - {sanitize_filename(ch.title)}{input_path.suffix}"
        out = input_path.parent / track

        cmd = [
            str(ffmpeg),
            "-hide_banner", "-nostats", "-loglevel", "error", "-y",
            "-ss", f"{start:.3f}",
            "-i", str(input_path),
            "-t", f"{duration:.3f}",
            "-map", "0:a:0",
            "-c", "copy",
            str(out),
        ]
        cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if cp.returncode != 0 or not out.exists():
            return False, cp.stderr.decode("utf-8", "replace"), created
        created.append(out)
        if on_progress:
            on_progress(i + 1, total, out)

    return bool(created), "", created
