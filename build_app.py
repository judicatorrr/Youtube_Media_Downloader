from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

APP_NAME = "YouTube Media Downloader"
ROOT = Path(__file__).resolve().parent


def run(cmd: list[str]) -> None:
    print(">", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except Exception:
        print("PyInstaller not found. Installing build dependency...")
        run([sys.executable, "-m", "pip", "install", "-U", "pyinstaller"])


def main() -> int:
    ensure_pyinstaller()

    system = platform.system()
    separator = ";" if system == "Windows" else ":"
    onefile = "--onefile" in sys.argv[1:]
    bundle_mode = "--onefile" if onefile else "--onedir"

    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        bundle_mode,
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build" / "_pyinstaller"),
        "--specpath",
        str(ROOT / "build"),
        "--add-data",
        str(ROOT / "resources") + separator + "resources",
        str(ROOT / "main.py"),
    ]

    if system == "Windows":
        args[ -1:-1 ] = ["--icon", str(ROOT / "resources" / "app_icon.ico")]
    elif system == "Darwin":
        args[ -1:-1 ] = ["--icon", str(ROOT / "resources" / "app_icon.icns")]

    # PySide6 is automatically handled by PyInstaller hooks.
    # yt-dlp, FFmpeg and Deno are intentionally NOT bundled. The compiled
    # application checks/downloads them on first launch into a writable
    # per-user data folder, exactly like the source build.

    run(args)

    if system == "Windows":
        output = (
            ROOT / "dist" / f"{APP_NAME}.exe"
            if onefile
            else ROOT / "dist" / APP_NAME / f"{APP_NAME}.exe"
        )
    elif system == "Darwin":
        output = ROOT / "dist"
    else:
        output = (
            ROOT / "dist" / APP_NAME
            if onefile
            else ROOT / "dist" / APP_NAME / APP_NAME
        )

    print()
    print("Build complete.")
    print("Mode:", "ONEFILE (portable, slower cold start)" if onefile else "ONEDIR (recommended, faster start)")
    print("Output:", output)
    print()
    print("Important: build separately on Windows, macOS and Linux.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
