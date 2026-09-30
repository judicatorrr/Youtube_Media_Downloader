# Сборка полноценного приложения

В v2.0.0-alpha6 добавлена готовая система сборки через PyInstaller.

## Windows

Двойной клик:

`../Windows/BUILD_WINDOWS.bat`

После завершения:

`dist/YouTube Media Downloader.exe`

## macOS

Первый раз:

```bash
chmod +x ../macOS/BUILD_MAC.command
```

Затем запускай `../macOS/BUILD_MAC.command`.

Результат будет в папке `dist/` (обычно приложение `.app` / executable,
в зависимости от версии PyInstaller).

## Linux

```bash
chmod +x ../Linux/build_linux.sh
./../Linux/build_linux.sh
```

Результат:

`dist/YouTube Media Downloader`

## Важно

Собирать нужно **на каждой целевой ОС отдельно**:

- Windows-сборка создаётся на Windows;
- macOS-сборка — на macOS;
- Linux-сборка — на Linux.

PyInstaller не является кросс-компилятором.

GUI, PySide6 и Python-runtime входят в собранное приложение.

`yt-dlp`, `FFmpeg`, `FFprobe` и `Deno` специально не зашиваются внутрь:
при первом запуске приложение проверяет их и при необходимости скачивает
актуальные версии само.

Для скомпилированного приложения скачанные зависимости сохраняются в
пользовательской папке данных, поэтому программе не нужны права администратора
и она может обновлять инструменты даже если само приложение находится в
Program Files или в macOS `.app`.

Папки зависимостей:

- Windows: `%APPDATA%/YouTubeMediaDownloader/bin/windows`
- macOS: `~/Library/Application Support/YouTube Media Downloader/bin/macos`
- Linux: `~/.config/youtube-media-downloader/bin/linux`


## Python в standalone-сборке

PyInstaller включает Python runtime внутрь готового приложения. Поэтому
скомпилированный `YouTube Media Downloader.exe` / `.app` не требует
предварительно установленного Python.

Проверка и автоустановка Python относится к source/portable-python workflow,
который запускается через `../Windows/START_WINDOWS.bat`, `../macOS/START_MAC.command` или
`../Linux/start_linux.sh`.


## Быстрый запуск: ONEDIR vs ONEFILE

По умолчанию build-скрипты alpha19 используют PyInstaller `--onedir`.
Для PySide6-приложения это заметно сокращает холодный запуск, потому что
при каждом старте не нужно распаковывать весь Python/Qt bundle.

Для единственного portable-файла используй отдельные `*_ONEFILE` скрипты.
Функциональность приложения одинакова в обоих вариантах.
