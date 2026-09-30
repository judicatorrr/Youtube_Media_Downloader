from __future__ import annotations

import os
import platform
import shutil
import stat
import tempfile
import time
import json
import re
import ssl
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional

from .core import app_dir, user_config_dir, macos_keychain_ca_bundle

ProgressCallback = Optional[Callable[[int, str], None]]
LogCallback = Optional[Callable[[str], None]]


def _log(cb: LogCallback, text: str) -> None:
    if cb:
        cb(text)


def _progress(cb: ProgressCallback, value: int, text: str = "") -> None:
    if cb:
        cb(max(0, min(100, int(value))), text)


def platform_key() -> str:
    return {
        "Windows": "windows",
        "Darwin": "macos",
        "Linux": "linux",
    }.get(platform.system(), platform.system().lower())


def arch_key() -> str:
    machine = platform.machine().lower()
    if machine in {"arm64", "aarch64"}:
        return "arm64"
    if machine in {"amd64", "x86_64"}:
        return "amd64"
    if machine in {"x86", "i386", "i686"}:
        return "x86"
    return machine


def local_bin_dir() -> Path:
    # Always use a writable per-user folder. This is important for compiled
    # Windows EXE / macOS .app / Linux binaries where the application bundle
    # itself may be read-only.
    target = user_config_dir() / "bin" / platform_key()
    target.mkdir(parents=True, exist_ok=True)
    return target


def _ssl_context(certificate_mode: str = "Auto") -> ssl.SSLContext:
    """
    SSL context for dependency downloads.

    Important: the dependency updater downloads executable code (yt-dlp,
    Deno, FFmpeg). Unlike ordinary YouTube requests, it must not silently
    disable certificate verification.

    On macOS Auto/MacKeychain reuse the same exported Keychain PEM bundle
    as yt-dlp itself.
    """
    mode = str(certificate_mode or "Auto")

    if mode == "Insecure":
        # Explicit setting only. Never selected automatically.
        return ssl._create_unverified_context()

    if platform.system() == "Darwin" and mode in {"Auto", "MacKeychain"}:
        bundle = macos_keychain_ca_bundle()
        if bundle and bundle.exists():
            return ssl.create_default_context(cafile=str(bundle))

    if mode == "Certifi":
        try:
            import certifi
            return ssl.create_default_context(cafile=certifi.where())
        except Exception:
            pass

    # "System" and all other fallbacks.
    return ssl.create_default_context()


def _opener(proxy: str = "", certificate_mode: str = "Auto"):
    proxy = (proxy or "").strip()
    handlers = []

    if proxy.lower().startswith(("http://", "https://")):
        handlers.append(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        )

    handlers.append(
        urllib.request.HTTPSHandler(
            context=_ssl_context(certificate_mode)
        )
    )
    return urllib.request.build_opener(*handlers)



def _human_bytes(value: float) -> str:
    value = float(max(0.0, value))
    units = ["B", "KB", "MB", "GB"]
    index = 0
    while value >= 1024.0 and index < len(units) - 1:
        value /= 1024.0
        index += 1
    if index == 0:
        return f"{value:.0f} {units[index]}"
    return f"{value:.1f} {units[index]}"


def _transfer_text(name: str, downloaded: int, total: int, speed: float) -> str:
    if total > 0:
        volume = f"{_human_bytes(downloaded)} / {_human_bytes(total)}"
    else:
        volume = _human_bytes(downloaded)
    speed_text = f"{_human_bytes(speed)}/s" if speed > 0 else "—"
    return f"{name} • {volume} • {speed_text}"


def _version_tuple(text: str) -> tuple[int, ...]:
    match = re.search(r"(\d+(?:\.\d+){1,3})", text or "")
    if not match:
        return ()
    try:
        return tuple(int(x) for x in match.group(1).split("."))
    except Exception:
        return ()


def _read_url_text(
    url: str,
    proxy: str = "",
    timeout: int = 10,
    certificate_mode: str = "Auto",
) -> str:
    opener = _opener(proxy, certificate_mode)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "YouTube-Media-Downloader/2",
            "Accept": "application/json,text/html,*/*",
        },
    )
    with opener.open(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def _command_first_line(command: list[str]) -> str:
    try:
        kwargs = {}
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        cp = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
            **kwargs,
        )
        text = cp.stdout.decode("utf-8", "replace").strip()
        if not text:
            text = cp.stderr.decode("utf-8", "replace").strip()
        return text.splitlines()[0] if text else ""
    except Exception:
        return ""


def check_dependency_updates(
    report: dict,
    proxy: str = "",
    certificate_mode: str = "Auto",
) -> dict:
    """
    Return update metadata for installed dependencies.

    If an online check fails, the component simply stays in the normal
    'installed' state; no false warning is produced.
    """
    result = {}

    # yt-dlp
    if report.get("yt_dlp", {}).get("ok"):
        try:
            raw = _read_url_text(
                "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest",
                proxy,
                certificate_mode=certificate_mode,
            )
            latest = str(json.loads(raw).get("tag_name") or "").lstrip("v")
            current = _command_first_line(
                [report["yt_dlp"]["path"]] if " " not in report["yt_dlp"]["path"]
                else report["yt_dlp"]["path"].split(" ")
            ).strip().lstrip("v")
            if latest and current:
                result["yt_dlp"] = {
                    "current": current,
                    "latest": latest,
                    "update": _version_tuple(latest) > _version_tuple(current),
                }
        except Exception:
            pass

    # Deno
    if report.get("deno", {}).get("ok"):
        try:
            raw = _read_url_text(
                "https://api.github.com/repos/denoland/deno/releases/latest",
                proxy,
                certificate_mode=certificate_mode,
            )
            latest = str(json.loads(raw).get("tag_name") or "").lstrip("v")
            line = _command_first_line([report["deno"]["path"], "--version"])
            current_match = re.search(r"deno\s+([0-9.]+)", line, re.I)
            current = current_match.group(1) if current_match else ""
            if latest and current:
                result["deno"] = {
                    "current": current,
                    "latest": latest,
                    "update": _version_tuple(latest) > _version_tuple(current),
                }
        except Exception:
            pass

    # FFmpeg and FFprobe share the same upstream release version.
    if report.get("ffmpeg", {}).get("ok") or report.get("ffprobe", {}).get("ok"):
        try:
            html = _read_url_text(
                "https://ffmpeg.org/releases/",
                proxy,
                certificate_mode=certificate_mode,
            )
            versions = re.findall(
                r"ffmpeg-(\d+\.\d+(?:\.\d+)?)\.tar\.(?:xz|bz2|gz)",
                html,
                flags=re.I,
            )
            parsed = [(v, _version_tuple(v)) for v in set(versions)]
            parsed = [x for x in parsed if x[1]]
            latest = max(parsed, key=lambda x: x[1])[0] if parsed else ""

            for key in ("ffmpeg", "ffprobe"):
                if not report.get(key, {}).get("ok"):
                    continue
                line = _command_first_line([report[key]["path"], "-version"])
                current_match = re.search(
                    r"(?:ffmpeg|ffprobe)\s+version\s+([0-9]+(?:\.[0-9]+){1,3})",
                    line,
                    re.I,
                )
                current = current_match.group(1) if current_match else ""
                if latest and current:
                    result[key] = {
                        "current": current,
                        "latest": latest,
                        "update": _version_tuple(latest) > _version_tuple(current),
                    }
        except Exception:
            pass

    return result


def download_file(
    url: str,
    destination: Path,
    proxy: str = "",
    progress_cb: ProgressCallback = None,
    log_cb: LogCallback = None,
    certificate_mode: str = "Auto",
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    _log(log_cb, f"GET {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "YouTube-Media-Downloader/2", "Accept": "*/*"})
    opener = _opener(proxy, certificate_mode)
    with opener.open(request, timeout=60) as response:
        try:
            total = int(response.headers.get("Content-Length") or 0)
        except Exception:
            total = 0

        downloaded = 0
        started = time.monotonic()
        last_emit = 0.0

        with destination.open("wb") as out:
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                out.write(chunk)
                downloaded += len(chunk)

                now = time.monotonic()
                elapsed = max(0.001, now - started)
                speed = downloaded / elapsed

                if now - last_emit >= 0.12:
                    percent = int(downloaded * 100 / total) if total else 0
                    _progress(
                        progress_cb,
                        percent,
                        _transfer_text(destination.name, downloaded, total, speed),
                    )
                    last_emit = now

        elapsed = max(0.001, time.monotonic() - started)
        speed = downloaded / elapsed
        _progress(
            progress_cb,
            100,
            _transfer_text(destination.name, downloaded, total or downloaded, speed),
        )
        _log(
            log_cb,
            f"Downloaded {destination.name}: {_human_bytes(downloaded)} • avg {_human_bytes(speed)}/s",
        )

    return destination


def _make_executable(path: Path) -> None:
    if os.name == "nt":
        return
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _extract_named_from_zip(zip_path: Path, wanted_name: str, output_path: Path) -> None:
    wanted = wanted_name.lower()
    with zipfile.ZipFile(zip_path, "r") as z:
        matches = [n for n in z.namelist() if not n.endswith("/") and Path(n).name.lower() == wanted]
        if not matches:
            raise RuntimeError(f"{wanted_name} не найден внутри {zip_path.name}")
        matches.sort(key=lambda n: ("/bin/" not in n.replace("\\", "/").lower(), len(n)))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with z.open(matches[0]) as src, output_path.open("wb") as dst:
            shutil.copyfileobj(src, dst)
    _make_executable(output_path)


def _replace_download(temp_path: Path, final_path: Path) -> None:
    final_path.parent.mkdir(parents=True, exist_ok=True)
    if final_path.exists():
        try:
            final_path.unlink()
        except PermissionError:
            backup = final_path.with_suffix(final_path.suffix + ".old")
            if backup.exists():
                backup.unlink()
            final_path.replace(backup)
    temp_path.replace(final_path)
    _make_executable(final_path)


def install_ytdlp(
    proxy: str = "",
    progress_cb: ProgressCallback = None,
    log_cb: LogCallback = None,
    certificate_mode: str = "Auto",
) -> list[Path]:
    system = platform_key()
    arch = arch_key()
    target_dir = local_bin_dir()
    if system == "windows":
        asset = "yt-dlp_arm64.exe" if arch == "arm64" else "yt-dlp.exe"
        final = target_dir / "yt-dlp.exe"
    elif system == "macos":
        asset = "yt-dlp_macos"
        final = target_dir / "yt-dlp"
    elif system == "linux":
        if arch == "arm64":
            asset = "yt-dlp_linux_aarch64"
        elif arch == "amd64":
            asset = "yt-dlp_linux"
        else:
            raise RuntimeError(f"Автообновление yt-dlp пока не настроено для Linux/{arch}.")
        final = target_dir / "yt-dlp"
    else:
        raise RuntimeError(f"Автообновление yt-dlp не настроено для {system}/{arch}.")
    url = f"https://github.com/yt-dlp/yt-dlp/releases/latest/download/{asset}"
    with tempfile.TemporaryDirectory(prefix="ymd_ytdlp_") as td:
        temp = Path(td) / asset
        download_file(
            url, temp, proxy, progress_cb, log_cb,
            certificate_mode=certificate_mode,
        )
        _replace_download(temp, final)
    _log(log_cb, f"yt-dlp → {final}")
    return [final]


def _deno_asset() -> tuple[str, str]:
    system = platform_key()
    arch = arch_key()
    if system == "windows":
        target = "aarch64-pc-windows-msvc" if arch == "arm64" else "x86_64-pc-windows-msvc"
        return f"deno-{target}.zip", "deno.exe"
    if system == "macos":
        target = "aarch64-apple-darwin" if arch == "arm64" else "x86_64-apple-darwin"
        return f"deno-{target}.zip", "deno"
    if system == "linux":
        if arch == "arm64":
            target = "aarch64-unknown-linux-gnu"
        elif arch == "amd64":
            target = "x86_64-unknown-linux-gnu"
        else:
            raise RuntimeError(f"Автообновление Deno пока не настроено для Linux/{arch}.")
        return f"deno-{target}.zip", "deno"
    raise RuntimeError(f"Автообновление Deno не настроено для {system}/{arch}.")


def install_deno(
    proxy: str = "",
    progress_cb: ProgressCallback = None,
    log_cb: LogCallback = None,
    certificate_mode: str = "Auto",
) -> list[Path]:
    asset, binary = _deno_asset()
    target = local_bin_dir() / binary
    url = f"https://github.com/denoland/deno/releases/latest/download/{asset}"
    with tempfile.TemporaryDirectory(prefix="ymd_deno_") as td:
        archive = Path(td) / asset
        download_file(
            url, archive, proxy, progress_cb, log_cb,
            certificate_mode=certificate_mode,
        )
        extracted = Path(td) / binary
        _extract_named_from_zip(archive, binary, extracted)
        _replace_download(extracted, target)
    _log(log_cb, f"Deno → {target}")
    return [target]


def _ffmpeg_urls() -> tuple[str, str, str]:
    system = platform_key()
    arch = arch_key()
    if system == "windows":
        return "windows_bundle", "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip", ""
    if system in {"macos", "linux"}:
        if arch not in {"arm64", "amd64"}:
            raise RuntimeError(f"Автозагрузка FFmpeg пока не настроена для {system}/{arch}.")
        provider_platform = "macos" if system == "macos" else "linux"
        provider_arch = "arm64" if arch == "arm64" else "amd64"
        base = f"https://ffmpeg.martin-riedl.de/redirect/latest/{provider_platform}/{provider_arch}/release"
        return "separate_zips", f"{base}/ffmpeg.zip", f"{base}/ffprobe.zip"
    raise RuntimeError(f"Автозагрузка FFmpeg не настроена для {system}/{arch}.")


def install_ffmpeg_pair(
    proxy: str = "",
    progress_cb: ProgressCallback = None,
    log_cb: LogCallback = None,
    certificate_mode: str = "Auto",
) -> list[Path]:
    kind, first_url, second_url = _ffmpeg_urls()
    target_dir = local_bin_dir()
    exe = ".exe" if platform_key() == "windows" else ""
    ffmpeg_out = target_dir / f"ffmpeg{exe}"
    ffprobe_out = target_dir / f"ffprobe{exe}"

    with tempfile.TemporaryDirectory(prefix="ymd_ffmpeg_") as td_name:
        td = Path(td_name)
        if kind == "windows_bundle":
            archive = td / "ffmpeg.zip"
            download_file(
                first_url, archive, proxy, progress_cb, log_cb,
                certificate_mode=certificate_mode,
            )
            tmp_ffmpeg = td / f"ffmpeg{exe}"
            tmp_ffprobe = td / f"ffprobe{exe}"
            _extract_named_from_zip(archive, f"ffmpeg{exe}", tmp_ffmpeg)
            _extract_named_from_zip(archive, f"ffprobe{exe}", tmp_ffprobe)
            _replace_download(tmp_ffmpeg, ffmpeg_out)
            _replace_download(tmp_ffprobe, ffprobe_out)
        else:
            ff_archive = td / "ffmpeg.zip"
            fp_archive = td / "ffprobe.zip"
            _log(log_cb, "FFmpeg: 1/2")
            download_file(
                first_url,
                ff_archive,
                proxy,
                lambda p, t: _progress(progress_cb, int(p * 0.5), "FFmpeg"),
                log_cb,
                certificate_mode=certificate_mode,
            )
            tmp_ffmpeg = td / f"ffmpeg{exe}"
            _extract_named_from_zip(ff_archive, f"ffmpeg{exe}", tmp_ffmpeg)
            _replace_download(tmp_ffmpeg, ffmpeg_out)
            _log(log_cb, "FFprobe: 2/2")
            download_file(
                second_url,
                fp_archive,
                proxy,
                lambda p, t: _progress(progress_cb, 50 + int(p * 0.5), "FFprobe"),
                log_cb,
                certificate_mode=certificate_mode,
            )
            tmp_ffprobe = td / f"ffprobe{exe}"
            _extract_named_from_zip(fp_archive, f"ffprobe{exe}", tmp_ffprobe)
            _replace_download(tmp_ffprobe, ffprobe_out)

    _progress(progress_cb, 100, "FFmpeg / FFprobe")
    _log(log_cb, f"FFmpeg → {ffmpeg_out}")
    _log(log_cb, f"FFprobe → {ffprobe_out}")
    return [ffmpeg_out, ffprobe_out]


def install_dependency(
    key: str,
    proxy: str = "",
    progress_cb: ProgressCallback = None,
    log_cb: LogCallback = None,
    certificate_mode: str = "Auto",
) -> list[Path]:
    if key == "yt_dlp":
        return install_ytdlp(
            proxy, progress_cb, log_cb,
            certificate_mode=certificate_mode,
        )
    if key in {"ffmpeg", "ffprobe"}:
        return install_ffmpeg_pair(
            proxy, progress_cb, log_cb,
            certificate_mode=certificate_mode,
        )
    if key == "deno":
        return install_deno(
            proxy, progress_cb, log_cb,
            certificate_mode=certificate_mode,
        )
    raise RuntimeError(f"Неизвестная зависимость: {key}")
