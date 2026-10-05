from __future__ import annotations

import json
import locale
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import webbrowser
import importlib.util
from functools import lru_cache
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

from PySide6.QtCore import QObject, QThread, Signal

from . import APP_NAME


@lru_cache(maxsize=1)
def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def user_config_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / APP_NAME.replace(" ", "")
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "youtube-media-downloader"


def settings_path() -> Path:
    return user_config_dir() / "settings.json"


DEFAULT_SETTINGS = {
    "language": "RU",
    "theme": "Dark",
    "skin": "Graphite Core",
    "output_folder": str(Path.home() / "Downloads"),
    "network_mode": "Auto",
    "manual_proxy": "",
    "certificate_mode": "Auto",
    "cookies_mode": "None",
    "cookies_browser": "chrome",
    "cookies_file": "",
}


def load_settings() -> dict:
    data = dict(DEFAULT_SETTINGS)
    path = settings_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            data.update(raw)
    except Exception:
        pass
    return data


def save_settings(data: dict) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@lru_cache(maxsize=16)
def _candidate_names(tool: str) -> list[str]:
    system = platform.system()
    if tool == "yt-dlp":
        if system == "Windows":
            return ["yt-dlp.exe", "yt-dlp"]
        if system == "Darwin":
            return ["yt-dlp", "yt-dlp_macos"]
        return ["yt-dlp"]
    if tool == "deno":
        return ["deno.exe", "deno"] if system == "Windows" else ["deno"]
    if tool == "ffmpeg":
        return ["ffmpeg.exe", "ffmpeg"] if system == "Windows" else ["ffmpeg"]
    if tool == "ffprobe":
        return ["ffprobe.exe", "ffprobe"] if system == "Windows" else ["ffprobe"]
    return [tool]


@lru_cache(maxsize=16)
def find_tool(tool: str) -> Optional[Path]:
    base = app_dir()
    system_key = {
        "Windows": "windows",
        "Darwin": "macos",
        "Linux": "linux",
    }.get(platform.system(), platform.system().lower())

    # Downloaded dependencies are stored outside a compiled executable/app
    # so updates remain writable and survive application upgrades.
    user_bin = user_config_dir() / "bin" / system_key

    candidates: list[Path] = []
    for name in _candidate_names(tool):
        candidates.extend(
            [
                user_bin / name,
                base / name,
                base / "bin" / name,
                base / "bin" / system_key / name,
            ]
        )

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    for name in _candidate_names(tool):
        found = shutil.which(name)
        if found:
            return Path(found)

    return None


def external_ytdlp_path() -> Optional[Path]:
    """Return a real yt-dlp executable/binary, not the Python module fallback."""
    return find_tool("yt-dlp")


def ytdlp_command() -> list[str]:
    external = external_ytdlp_path()
    if external:
        return [str(external)]

    # Source-mode fallback. Do not import yt_dlp here: importing it just to
    # test availability is noticeably more expensive during startup.
    if not getattr(sys, "frozen", False):
        try:
            if importlib.util.find_spec("yt_dlp") is not None:
                return [sys.executable, "-m", "yt_dlp"]
        except Exception:
            pass

    return []


def clear_tool_cache() -> None:
    """Invalidate cached dependency paths after an in-app install/update."""
    find_tool.cache_clear()
    _candidate_names.cache_clear()


def python_command() -> list[str]:
    return [sys.executable]


def dependency_report() -> dict:
    external_yt = external_ytdlp_path()
    yt = ytdlp_command()
    ff = ffmpeg_path()
    fp = ffprobe_path()
    dn = deno_path()

    python_version = platform.python_version()
    python_recommended = sys.version_info >= (3, 11)

    return {
        "python": {
            "ok": True,
            "recommended": python_recommended,
            "version": python_version,
            "path": sys.executable,
            "frozen": bool(getattr(sys, "frozen", False)),
        },
        "yt_dlp": {
            "ok": bool(yt),
            "path": " ".join(yt) if yt else "",
            "external": bool(external_yt),
            "module_fallback": bool(yt and not external_yt),
        },
        "ffmpeg": {"ok": bool(ff), "path": str(ff) if ff else ""},
        "ffprobe": {"ok": bool(fp), "path": str(fp) if fp else ""},
        "deno": {"ok": bool(dn), "path": str(dn) if dn else ""},
    }


def dependency_version(command: list[str], args: list[str]) -> str:
    try:
        kwargs = {}
        if platform.system() == "Windows":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        cp = subprocess.run(
            command + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=12,
            **kwargs,
        )
        text = cp.stdout.decode("utf-8", "replace").strip() or cp.stderr.decode("utf-8", "replace").strip()
        return text.splitlines()[0] if text else ""
    except Exception:
        return ""


def ffmpeg_path() -> Optional[Path]:
    return find_tool("ffmpeg")


def ffprobe_path() -> Optional[Path]:
    return find_tool("ffprobe")


def deno_path() -> Optional[Path]:
    return find_tool("deno")



def macos_keychain_ca_bundle(force: bool = False) -> Optional[Path]:
    """
    Create a PEM CA bundle that the OpenSSL runtime inside yt-dlp can read.

    macOS Keychain trust is not always visible to standalone Python/OpenSSL.
    Export public roots + System/login Keychains lazily and cache the bundle.
    """
    if platform.system() != "Darwin":
        return None

    cert_dir = user_config_dir() / "certs"
    cert_dir.mkdir(parents=True, exist_ok=True)
    bundle = cert_dir / "macos-keychain-ca.pem"

    if bundle.exists() and not force:
        try:
            age = time.time() - bundle.stat().st_mtime
            if age < 7 * 24 * 3600 and bundle.stat().st_size > 4096:
                return bundle
        except Exception:
            pass

    pem_blocks: list[bytes] = []

    def add_pem_bytes(data: bytes) -> None:
        if not data:
            return
        for match in re.finditer(
            rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
            data,
            flags=re.S,
        ):
            block = match.group(0).strip() + b"\n"
            if block not in pem_blocks:
                pem_blocks.append(block)

    try:
        import certifi
        certifi_path = Path(certifi.where())
        if certifi_path.exists():
            add_pem_bytes(certifi_path.read_bytes())
    except Exception:
        pass

    for system_bundle in (
        Path("/etc/ssl/cert.pem"),
        Path("/private/etc/ssl/cert.pem"),
    ):
        try:
            if system_bundle.exists():
                add_pem_bytes(system_bundle.read_bytes())
        except Exception:
            pass

    security = shutil.which("security") or "/usr/bin/security"
    keychains = [
        Path("/System/Library/Keychains/SystemRootCertificates.keychain"),
        Path("/Library/Keychains/System.keychain"),
        Path.home() / "Library/Keychains/login.keychain-db",
    ]

    for keychain in keychains:
        if not keychain.exists():
            continue
        try:
            cp = subprocess.run(
                [security, "find-certificate", "-a", "-p", str(keychain)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=20,
            )
            if cp.returncode == 0:
                add_pem_bytes(cp.stdout)
        except Exception:
            pass

    if not pem_blocks:
        return None

    tmp = bundle.with_suffix(".tmp")
    tmp.write_bytes(b"\n".join(pem_blocks))
    tmp.replace(bundle)
    try:
        bundle.chmod(0o600)
    except Exception:
        pass
    return bundle


def certificate_process_env(mode: str = "Auto") -> dict[str, str]:
    """
    Extra environment passed to yt-dlp.

    Auto on macOS exports Apple Keychain certificates into SSL_CERT_FILE.
    """
    mode = str(mode or "Auto")
    env: dict[str, str] = {}

    if platform.system() == "Darwin" and mode in {"Auto", "MacKeychain"}:
        bundle = macos_keychain_ca_bundle()
        if bundle:
            env["SSL_CERT_FILE"] = str(bundle)

    return env


def certificate_args(mode: str = "Auto") -> list[str]:
    """
    yt-dlp certificate strategy.

    yt-dlp standalone builds bundle certifi. On macOS/Linux that can reject
    a locally trusted CA (VPN / filtering proxy / organization certificate)
    which the OS itself trusts. yt-dlp documents `no-certifi` specifically
    for using system certificates.

    Auto:
      Windows -> bundled certifi (existing behavior)
      macOS/Linux -> system certificate store
    """
    mode = str(mode or "Auto")

    if mode in {"System", "MacKeychain"}:
        return ["--compat-options", "no-certifi"]

    if mode == "Certifi":
        return []

    if mode == "Insecure":
        return ["--no-check-certificates"]

    if mode == "Auto" and platform.system() in {"Darwin", "Linux"}:
        return ["--compat-options", "no-certifi"]

    return []


def is_ssl_certificate_error(text: str) -> bool:
    return bool(
        re.search(
            r"CERTIFICATE_VERIFY_FAILED|certificate verify failed|"
            r"unable to get local issuer certificate|self signed certificate",
            text or "",
            flags=re.I,
        )
    )


def ytdlp_common_args(certificate_mode: str = "Auto") -> list[str]:
    args = [
        "--ignore-config",
        "--no-playlist",
        "--encoding", "utf-8",
        "--file-access-retries", "10",
        "--retry-sleep", "file_access:1",
    ]
    args += certificate_args(certificate_mode)

    deno = deno_path()
    if deno:
        args += ["--js-runtimes", f"deno:{deno}"]
    return args


@dataclass
class ProxyResolution:
    ok: bool
    proxy: str
    name: str
    detail: str


def get_system_proxy() -> str:
    proxies = urllib.request.getproxies()
    # HTTPS first; HTTP is also valid for tunnelling HTTPS via CONNECT.
    return str(proxies.get("https") or proxies.get("http") or "").strip()


def normalize_proxy(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if "://" not in value:
        value = "http://" + value
    if not re.match(r"^(https?|socks4a?|socks5h?)://", value, flags=re.I):
        return ""
    return value


def resolve_proxy(mode: str, manual_proxy: str = "") -> ProxyResolution:
    if mode == "Direct":
        return ProxyResolution(True, "", "Direct / TUN", "Explicit proxy is disabled")

    if mode == "Manual":
        value = normalize_proxy(manual_proxy)
        if not value:
            return ProxyResolution(False, "", "Manual proxy", "Invalid proxy URL")
        return ProxyResolution(True, value, "Manual proxy", safe_proxy_display(value))

    system_proxy = get_system_proxy()

    if mode in {"INCY", "Happ"}:
        if not system_proxy:
            return ProxyResolution(
                False, "", mode,
                "System proxy is not detected. Enable Proxy/System Proxy mode in the VPN client."
            )
        return ProxyResolution(True, system_proxy, mode, f"System proxy: {safe_proxy_display(system_proxy)}")

    # Auto: prefer system proxy; otherwise Direct/TUN.
    if system_proxy:
        return ProxyResolution(
            True, system_proxy, "Auto → System Proxy", safe_proxy_display(system_proxy)
        )
    return ProxyResolution(True, "", "Auto → Direct / TUN", "System proxy is not enabled")


def safe_proxy_display(proxy: str) -> str:
    return re.sub(r"(?<=://)[^/@:]+:[^/@]+@", "***:***@", proxy)


def proxy_args(mode: str, manual_proxy: str = "") -> tuple[list[str], ProxyResolution]:
    resolved = resolve_proxy(mode, manual_proxy)
    if resolved.ok and resolved.proxy:
        return ["--proxy", resolved.proxy], resolved
    return [], resolved


def open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    system = platform.system()
    if system == "Windows":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif system == "Darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def open_url(url: str) -> None:
    webbrowser.open(url)


def local_interface_hint() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "unavailable"


def external_ip(proxy: str = "") -> str:
    try:
        if proxy and proxy.lower().startswith(("http://", "https://")):
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({"http": proxy, "https": proxy})
            )
        else:
            opener = urllib.request.build_opener()
        req = urllib.request.Request(
            "https://api.ipify.org",
            headers={"User-Agent": APP_NAME},
        )
        with opener.open(req, timeout=5) as resp:
            return resp.read().decode("ascii", "replace").strip()
    except Exception:
        return "unavailable"


def sanitize_filename(name: str) -> str:
    bad = r'\/:*?"<>|'
    clean = "".join("_" if c in bad else c for c in name).strip().rstrip(".")
    return clean or "Track"


def format_bytes(value) -> str:
    try:
        n = float(value)
    except Exception:
        return "—"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    if i == 0:
        return f"{n:.0f} {units[i]}"
    return f"{n:.1f} {units[i]}"


def format_rate(kbps) -> str:
    try:
        return f"~{float(kbps):.0f} kbps"
    except Exception:
        return "bitrate —"


def format_hz(hz) -> str:
    try:
        hz = float(hz)
        if hz >= 1000:
            return f"{hz/1000:.1f}".replace(".0", "") + " kHz"
        return f"{hz:.0f} Hz"
    except Exception:
        return "Hz —"


def audio_codec(acodec: str) -> str:
    a = (acodec or "").lower()
    if "opus" in a:
        return "Opus"
    if "mp4a" in a or "aac" in a:
        return "AAC"
    return acodec or "Other"


def video_codec(vcodec: str) -> str:
    v = (vcodec or "").lower()
    if v.startswith("avc1") or "h264" in v:
        return "H.264"
    if v.startswith("vp09") or "vp9" in v:
        return "VP9"
    if v.startswith("av01") or "av1" in v:
        return "AV1"
    return vcodec or "Other"


@dataclass
class AudioFormat:
    id: str
    codec: str
    acodec: str
    ext: str
    abr: float
    asr: float
    size: float
    is_drc: bool
    label: str
    language: str = ""
    is_original: bool = False
    language_preference: float = 0.0
    is_dubbed: bool = False


def audio_preference_key(fmt: AudioFormat):
    return (not fmt.is_original, fmt.is_dubbed, fmt.is_drc, -fmt.abr, -fmt.language_preference)


def audio_display_label(fmt: AudioFormat, lang: str = "RU") -> str:
    details = [fmt.label]
    if fmt.language:
        details.append(fmt.language)
    if fmt.is_original:
        details.append("Оригинал" if lang == "RU" else "Original")
    elif fmt.is_dubbed:
        details.append("Дубляж" if lang == "RU" else "Dubbed")
    return " • ".join(details)


def video_container_compatible(fmt, container: str) -> bool:
    return fmt.codec in ({"H.264", "AV1"} if container == "MP4" else {"VP9", "AV1"} if container == "WebM" else {"H.264", "VP9", "AV1"})


def audio_container_compatible(fmt, container: str) -> bool:
    return fmt.codec in ({"AAC"} if container == "MP4" else {"Opus"} if container == "WebM" else {"AAC", "Opus"})


def ipod_classic_6g_video_compatible(fmt) -> bool:
    """Conservative direct-play filter for iPod classic 6G/120GB-era video.

    Apple specifies H.264 Baseline up to Level 3.0, 640x480, 30 fps and
    up to 2.5 Mbps. YouTube AVC codec strings normally expose profile/level
    as avc1.PPCCLL, so reject clearly non-Baseline streams.
    """
    if fmt.codec != "H.264":
        return False
    if fmt.width and fmt.width > 640:
        return False
    if fmt.height and fmt.height > 480:
        return False
    if fmt.fps and fmt.fps > 30.01:
        return False
    if fmt.tbr and fmt.tbr > 2500:
        return False

    raw = (fmt.vcodec or "").lower()
    m = re.search(r"avc1\.([0-9a-f]{6})", raw)
    if m:
        profile_idc = int(m.group(1)[0:2], 16)
        level_idc = int(m.group(1)[4:6], 16)
        if profile_idc != 0x42:  # Baseline profile
            return False
        if level_idc > 30:      # Level 3.0
            return False
    return True


def ipod_classic_6g_audio_compatible(fmt) -> bool:
    """AAC-LC, <=160 kbps, <=48 kHz, stereo-compatible YouTube audio."""
    if fmt.codec != "AAC":
        return False
    raw = (fmt.acodec or "").lower()
    if raw and not ("mp4a.40.2" in raw or raw in {"aac", "aaclc", "aac-lc"}):
        return False
    if fmt.abr and fmt.abr > 160:
        return False
    if fmt.asr and fmt.asr > 48000:
        return False
    return True


def container_has_4k(videos, audios, container: str) -> bool:
    return any(audio_container_compatible(a, container) for a in audios) and any(
        video_container_compatible(v, container) and (min(v.width, v.height) if v.width and v.height else v.height) >= 2160
        for v in videos
    )


@dataclass
class VideoFormat:
    id: str
    codec: str
    vcodec: str
    ext: str
    width: int
    height: int
    fps: float
    tbr: float
    size: float
    label: str


def parse_formats(info: dict) -> tuple[list[AudioFormat], list[VideoFormat]]:
    audio: list[AudioFormat] = []
    video: list[VideoFormat] = []

    try:
        media_duration = float(info.get("duration") or 0)
    except Exception:
        media_duration = 0.0

    def size_label(raw_size, bitrate_kbps, fallback: str) -> tuple[str, float]:
        try:
            size_value = float(raw_size or 0)
        except Exception:
            size_value = 0.0

        if size_value > 0:
            return format_bytes(size_value), size_value

        # Manifest streams often have no filesize/filesize_approx.
        # Estimate from duration and bitrate instead of showing misleading 0 B.
        try:
            rate = float(bitrate_kbps or 0)
        except Exception:
            rate = 0.0

        if media_duration > 0 and rate > 0:
            estimated = media_duration * rate * 1000.0 / 8.0
            return "≈" + format_bytes(estimated), estimated

        return fallback, 0.0

    for f in info.get("formats") or []:
        fid = str(f.get("format_id") or "")
        if not fid:
            continue

        vcodec = str(f.get("vcodec") or "none")
        acodec = str(f.get("acodec") or "none")
        ext = str(f.get("ext") or "")
        filesize = f.get("filesize") or f.get("filesize_approx") or 0

        if vcodec == "none" and acodec != "none":
            codec = audio_codec(acodec)
            if codec not in {"Opus", "AAC"}:
                continue
            abr = float(f.get("abr") or f.get("tbr") or 0)
            asr = float(f.get("asr") or 0)
            note = str(f.get("format_note") or "")
            is_drc = "drc" in note.lower() or "drc" in str(f.get("format") or "").lower()
            drc = " • DRC" if is_drc else ""
            audio_size_text, audio_size_value = size_label(filesize, abr, "HQ Audio")
            label = (
                f"{codec} • {format_rate(abr)} • {format_hz(asr)} • "
                f"{audio_size_text} • {ext.upper()}{drc}"
            )
            audio.append(
                AudioFormat(fid, codec, acodec, ext, abr, asr, audio_size_value, is_drc, label,
                            str(f.get("language") or ""),
                            "original" in note.lower() or float(f.get("language_preference") or 0) >= 10,
                            float(f.get("language_preference") or 0),
                            bool(re.search(r"dubbed|dub|дубляж|auto.translat", note, re.I)))
            )
            continue

        if vcodec != "none" and acodec == "none":
            codec = video_codec(vcodec)
            if codec not in {"H.264", "VP9", "AV1"}:
                continue
            width = int(f.get("width") or 0)
            height = int(f.get("height") or 0)
            fps = float(f.get("fps") or 0)
            tbr = float(f.get("tbr") or 0)
            res = f"{width}×{height}" if width and height else str(f.get("resolution") or "—")
            fps_text = f" • {fps:.0f} fps" if fps else ""
            tbr_text = f" • ~{tbr:.0f} kbps" if tbr else ""
            video_size_text, video_size_value = size_label(filesize, tbr, "HQ Stream")
            label = f"{res}{fps_text} • {codec}{tbr_text} • {video_size_text} • id {fid}"
            video.append(
                VideoFormat(
                    fid, codec, vcodec, ext, width, height, fps, tbr,
                    video_size_value, label
                )
            )

    original_languages = {a.language for a in audio if a.is_original and a.language}
    for a in audio:
        if a.language and a.language in original_languages:
            a.is_original = True
        if original_languages and a.language and a.language not in original_languages:
            a.is_dubbed = True
    audio.sort(key=audio_preference_key)
    video.sort(key=lambda x: (x.codec, -x.height, -x.fps, -x.tbr))
    return audio, video


def is_valid_youtube_url(url: str) -> bool:
    return bool(re.match(
        r"^https?://(?:www\.)?(?:youtube\.com|youtu\.be|music\.youtube\.com)/",
        (url or "").strip(),
        flags=re.I,
    ))


def find_latest_file(folder: Path, extensions: Iterable[str], after_ts: float) -> Optional[Path]:
    exts = {e.lower() if e.startswith(".") else "." + e.lower() for e in extensions}
    candidates = []
    try:
        for p in folder.iterdir():
            if p.is_file() and p.suffix.lower() in exts and p.stat().st_mtime >= after_ts - 2:
                candidates.append(p)
    except Exception:
        return None
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)



def decode_process_bytes(data: bytes) -> str:
    """
    Decode child-process output without turning Russian filenames into "��".

    yt-dlp/FFmpeg usually emit UTF-8, but Windows standalone binaries can
    occasionally inherit an ANSI/OEM code page. Try UTF-8 first, then the
    active Windows code page and common Cyrillic fallbacks.
    """
    if not data:
        return ""

    encodings: list[str] = ["utf-8-sig", "utf-8"]

    preferred = locale.getpreferredencoding(False)
    if preferred:
        encodings.append(preferred)

    if platform.system() == "Windows":
        encodings.extend(["cp1251", "cp866"])

    seen = set()
    for encoding in encodings:
        key = encoding.lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            return data.decode(encoding, errors="strict")
        except (UnicodeDecodeError, LookupError):
            pass

    return data.decode("utf-8", errors="replace")


class CaptureWorker(QThread):
    completed = Signal(int, str, str)
    failed = Signal(str)

    def __init__(
        self,
        cmd: list[str],
        cwd: Path | None = None,
        timeout: int | None = None,
        extra_env: Optional[dict[str, str]] = None,
    ):
        super().__init__()
        self.cmd = cmd
        self.cwd = cwd
        self.timeout = timeout
        self.extra_env = dict(extra_env or {})
        self.proc: Optional[subprocess.Popen] = None

    def cancel(self) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass

    def run(self) -> None:
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            env.update(self.extra_env)
            kwargs = {}
            if platform.system() == "Windows":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self.proc = subprocess.Popen(
                self.cmd,
                cwd=str(self.cwd) if self.cwd else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                **kwargs,
            )
            try:
                out, err = self.proc.communicate(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                out, err = self.proc.communicate()
                self.completed.emit(124, decode_process_bytes(out), decode_process_bytes(err))
                return
            self.completed.emit(
                int(self.proc.returncode or 0),
                decode_process_bytes(out),
                decode_process_bytes(err),
            )
        except Exception as exc:
            self.failed.emit(str(exc))


class StreamWorker(QThread):
    line = Signal(str)
    completed = Signal(int)
    failed = Signal(str)

    def __init__(
        self,
        cmd: list[str],
        cwd: Path | None = None,
        extra_env: Optional[dict[str, str]] = None,
    ):
        super().__init__()
        self.cmd = cmd
        self.cwd = cwd
        self.extra_env = dict(extra_env or {})
        self.proc: Optional[subprocess.Popen] = None
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass

    def run(self) -> None:
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            env.update(self.extra_env)
            kwargs = {}
            if platform.system() == "Windows":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self.proc = subprocess.Popen(
                self.cmd,
                cwd=str(self.cwd) if self.cwd else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                bufsize=1,
                **kwargs,
            )
            assert self.proc.stdout is not None
            while True:
                raw = self.proc.stdout.readline()
                if not raw:
                    break
                self.line.emit(decode_process_bytes(raw).rstrip("\r\n"))
                if self._cancelled:
                    break
            code = self.proc.wait()
            self.completed.emit(int(code))
        except Exception as exc:
            self.failed.emit(str(exc))


_PROGRESS_PERCENT_RE = re.compile(
    r"\[download\]\s+([0-9.]+)%",
    re.I,
)

_PROGRESS_SPEED_RE = re.compile(
    r"\bat\s+([^\s]+)",
    re.I,
)


def parse_progress(line: str) -> tuple[Optional[int], Optional[str]]:
    """
    Parse yt-dlp's progress line.

    Percent and speed are searched independently. The previous single-regex
    implementation made the speed group optional after a non-greedy match,
    so Python could successfully match the line before ever consuming
    "at 4.2MiB/s", leaving speed as None.
    """
    pct_match = _PROGRESS_PERCENT_RE.search(line)
    if not pct_match:
        return None, None

    try:
        pct = max(0, min(100, int(float(pct_match.group(1)))))
    except Exception:
        pct = None

    speed_match = _PROGRESS_SPEED_RE.search(line)
    speed = speed_match.group(1) if speed_match else None
    return pct, speed
