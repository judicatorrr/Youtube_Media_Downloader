
## v2.0.0-alpha36

### alpha36 — FFmpeg ASCII progress for iPod conversion
- Added an ASCII conversion progress bar to the event log for iPod Classic 6G transcodes.
- The top progress bar now follows FFmpeg conversion progress as well as downloading.
- Conversion log shows percentage, elapsed/output timestamp, total duration and FFmpeg speed when available.

- Общий прогресс скачивания перенесён в верхнюю карточку рядом с папкой сохранения.
- В режиме iPod Classic 6G временные video/audio потоки сохраняются отдельно.
- Если yt-dlp не может объединить, например, HLS MP4 + WebM/Opus во временный MKV, программа больше не обрывает задачу: она передаёт оба скачанных потока напрямую FFmpeg и делает финальный iPod MP4.
- Временное встраивание metadata/chapters для iPod-ветки отключено до финальной конвертации, чтобы не ломать промежуточный merge.


- iPod Classic 6G checkbox is now a conversion preset instead of a direct-stream filter.
- Source video choices remain available up to 1080p; 1440p/4K are intentionally hidden in iPod mode.
- Final iPod file: MP4, H.264 Baseline Level 3.0, up to 640×480, up to 30 fps, AAC-LC 160 kbps / 48 kHz stereo.
- VP9/AV1/H.264 source streams are accepted and transcoded automatically.

# YouTube Media Downloader v2.0.0-alpha33

Распакуй архив целиком. Открой папку своей ОС и запусти:

| ОС | Папка | Запуск |
| --- | --- | --- |
| Windows | Windows | START_WINDOWS.bat |
| macOS | macOS | START_MAC.command |
| Linux | Linux | start_linux.sh |

Files — общие файлы программы. Оставь её рядом с папками ОС; ничего переносить не нужно.
При первом запуске скрипт подготовит Python и зависимости. Нужен Интернет.

В каждой папке ОС также находятся скрипты сборки обычной и однофайловой версии.
Результат сборки — Files/dist. Подробности — Files/README.md и Files/BUILD.md.

На Linux запуск из терминала: bash Linux/start_linux.sh.
Если macOS не открывает .command двойным щелчком, открой Терминал,
введи bash и пробел, перетащи START_MAC.command в окно и нажми Enter.

Все функции alpha29 сохранены, включая восстановление галочек после AAC,
группировку аудиоформатов и краткие подсказки.

Косметические правки alpha32: убраны подсказки справа у заголовков аудио, видео, фрагмента и журнала; подсказка перепаковки расположена рядом с названием раздела.

## AAC 320 для iTunes / iPod

После анализа ссылки выбери аудиодорожку, затем в «Формат файла» открой группу OPUS
и выбери «AAC 320 (.m4a)». В «Вариант потока» выбери исходный Opus.
Программа скачает именно выбранную дорожку и преобразует её в AAC-LC
с целевым битрейтом 320 кбит/с, 44,1 кГц, стерео, в контейнере M4A.
Фактический средний битрейт зависит от содержимого и может быть ниже 320 кбит/с.
Это отдельный режим с перекодированием; исходные .opus/.ogg/.m4a/.aac работают как прежде.
Битрейт 320 — параметр кодирования, а не обещание повышения качества исходного YouTube.
Поддерживаются метаданные, обложка, главы и сохранение фрагмента.
Нужен FFmpeg. Итоговый M4A сохраняется в выбранную папку; временный Opus удаляется.


## Изменения alpha33 — iPod Classic 6G / AAC metadata / M4A chapters
- Добавлен фильтр видео «Только совместимое с iPod Classic 6G»: MP4 + H.264 Baseline до 640×480, 30 fps, 2.5 Mbps и AAC-LC до 160 kbps.
- В режиме Opus → AAC 320 в M4A автоматически записывается английский Comment с фактическим битрейтом исходного Opus: `Source audio: Opus X kbps; transcoded to AAC 320 kbps`.
- Исправлено ложное падение FFmpeg при встраивании глав в M4A с thumbnail: служебные text/data streams больше не копируются при chapter-remux. Готовый файл не считается испорченным из-за этой постобработки.
