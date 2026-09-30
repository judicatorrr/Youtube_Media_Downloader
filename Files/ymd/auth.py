"""Explicit, optional cookie settings for yt-dlp. No browser access here."""
from pathlib import Path
import re

BROWSERS = ("chrome", "firefox", "safari", "edge", "chromium", "opera", "yandex")

def cookie_args(settings: dict) -> list[str]:
    mode = settings.get("cookies_mode", "None")
    if mode == "None":
        return []
    if mode == "Browser":
        browser = settings.get("cookies_browser", "chrome")
        if browser not in BROWSERS:
            raise ValueError("Выбери поддерживаемый браузер / Select a supported browser.")
        if browser == "yandex":
            # yt-dlp has no native Yandex extractor; use an explicit export.
            return cookie_args({"cookies_mode": "File", "cookies_file": settings.get("cookies_file", "")})
        return ["--cookies-from-browser", browser]
    if mode == "File":
        value = str(settings.get("cookies_file", "")).strip()
        path = Path(value).expanduser()
        if not value or not path.is_file():
            raise ValueError("Файл cookies не найден. Выбери cookies.txt / Select an existing cookies.txt file.")
        try:
            with path.open("r", encoding="utf-8-sig") as f:
                header = f.readline(4096).strip()
        except (OSError, UnicodeError) as exc:
            raise ValueError("Не удалось прочитать cookies / Could not read cookies.") from exc
        if header not in {"# Netscape HTTP Cookie File", "# HTTP Cookie File"}:
            raise ValueError("Нужен файл cookies в формате Netscape / Cookies must be in Netscape format.")
        return ["--cookies", str(path)]
    raise ValueError("Неизвестный режим cookies / Unknown cookies mode.")

def is_youtube_bot_error(text: str) -> bool:
    return bool(re.search(r"sign in to confirm you[’']?re not a bot", text, re.I))

def bot_error_help(lang: str = "RU") -> str:
    if lang == "EN":
        return ("YouTube requires confirmation that you are not a bot.\n\n"
                "1. Open this video in your browser using the same VPN/proxy as the app. Complete any verification.\n"
                "2. In Connection settings (network icon in the top right), choose Cookies → From browser and select that browser.\n"
                "3. If access is still denied, try another VPN server/IP and update yt-dlp. Cookies do not guarantee access.\n\n"
                "If cookie extraction fails, use a Netscape cookies.txt file. Do not share cookies: they may grant access to your account.")
    return ("YouTube просит подтвердить, что вы не бот.\n\n"
            "1. Открой это видео в браузере через тот же VPN/proxy, что и программа. Пройди проверку, если она появится.\n"
            "2. В настройках подключения (значок сети справа вверху) выбери Cookies → Из браузера и укажи этот браузер.\n"
            "3. Если доступ по-прежнему закрыт, попробуй другой сервер/IP VPN и обнови yt-dlp. Cookies не гарантируют доступ.\n\n"
            "Если cookies не извлекаются, можно выбрать файл cookies.txt в формате Netscape. Не передавай cookies другим: они могут дать доступ к аккаунту.")
