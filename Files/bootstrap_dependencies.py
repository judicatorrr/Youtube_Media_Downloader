from __future__ import annotations

"""
First-run dependency bootstrap.

This script is executed only AFTER a Python virtual environment exists and
requirements.txt has been installed. It then makes sure the external tools
used by the GUI are present in the app's writable per-user bin directory.
"""

from ymd.core import dependency_report
from ymd.dependencies import install_dependency


def main() -> int:
    report = dependency_report()

    jobs: list[tuple[str, str]] = []

    # Prefer the official platform binary even if the Python package is
    # available in the venv. This decouples yt-dlp from the app's Python
    # runtime and avoids Python-version warnings in source builds.
    if not report["yt_dlp"].get("external"):
        jobs.append(("yt_dlp", "yt-dlp (official platform binary)"))

    if not report["ffmpeg"]["ok"] or not report["ffprobe"]["ok"]:
        jobs.append(("ffmpeg", "FFmpeg + FFprobe"))

    if not report["deno"]["ok"]:
        jobs.append(("deno", "Deno JS runtime"))

    if not jobs:
        print("All dependencies are already installed.")
        return 0

    print("Missing components will be installed automatically:")

    for key, label in jobs:
        print(f"\n== {label} ==")
        try:
            install_dependency(
                key,
                progress_cb=lambda percent, text: print(
                    f"\r{percent:3d}%  {text}",
                    end="",
                    flush=True,
                ),
                log_cb=lambda text: print(f"\n{text}"),
            )
            print("\nOK")
        except Exception as exc:
            # Do not prevent the GUI from opening. Its dependency dialog will
            # still show the missing item and allow a retry.
            print(f"\nWARNING: {label}: {exc}")

    print("\nDependency bootstrap finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
