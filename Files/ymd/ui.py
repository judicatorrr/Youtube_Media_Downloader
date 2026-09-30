from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import time
import random
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QDesktopServices, QPalette, QColor, QStandardItemModel, QStandardItem, QPixmap, QIcon, QPainter, QImage
from PySide6.QtCore import QUrl, QSize, QEvent
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QStyle,
    QStyleOptionGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSpacerItem,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME, APP_VERSION
from .auth import BROWSERS, cookie_args, is_youtube_bot_error, bot_error_help
from .dependencies import install_dependency, check_dependency_updates, _ssl_context

from .skins import SKIN_ORDER, get_skin

from .chapters import (
    chapters_from_info,
    clip_chapters,
    embed_chapters_copy,
    media_duration_ms,
    parse_manual_chapters,
    split_audio_copy,
    timecode_to_ms,
)
from .core import (
    AudioFormat,
    audio_preference_key,
    audio_display_label,
    video_container_compatible,
    audio_container_compatible,
    container_has_4k,
    CaptureWorker,
    clear_tool_cache,
    certificate_process_env,
    StreamWorker,
    app_dir,
    dependency_report,
    dependency_version,
    external_ytdlp_path,
    deno_path,
    external_ip,
    ffmpeg_path,
    ffprobe_path,
    find_latest_file,
    format_bytes,
    get_system_proxy,
    is_valid_youtube_url,
    is_ssl_certificate_error,
    load_settings,
    local_interface_hint,
    open_folder,
    open_url,
    parse_formats,
    parse_progress,
    proxy_args,
    resolve_proxy,
    save_settings,
    ytdlp_command,
    ytdlp_common_args,
)


TEXT = {
    "RU": {
        "subtitle": "Выбор оригинальных потоков YouTube + перепаковка без перекодирования",
        "url": "Ссылка YouTube",
        "analyze": "Анализировать ссылку",
        "cancel": "Отмена",
        "not_analyzed": "Видео не проанализировано",
        "audio": "Аудио",
        "audio_stream": "1. Аудиопоток",
        "chapters": "2. Главы",
        "chapters_none": "Не использовать",
        "chapters_embed": "Встроить в файл",
        "chapters_split": "Разделить на треки",
        "metadata": "Встроить метаданные",
        "thumbnail": "Встроить thumbnail",
        "manual_chapters": "Главы вручную...",
        "download_audio": "Скачать аудио",
        "video": "Видео",
        "container": "1. Контейнер",
        "video_stream": "2. Качество / видеопоток",
        "video_audio": "3. Аудио",
        "best": "Лучшее совместимое",
        "download_video": "Скачать видео",
        "download_thumbnail": "Скачать обложку",
        "embed_chapters": "Встроить главы",
        "fragment": "Сохранить фрагмент",
        "use_range": "Использовать диапазон",
        "from": "С:",
        "to": "До:",
        "format": "Формат: ЧЧ:ММ:СС",
        "hour_short": "ч",
        "minute_short": "мин",
        "second_short": "сек",
        "output": "Папка сохранения",
        "browse": "Обзор...",
        "open": "Открыть папку",
        "remux": "Перепаковка контейнера (без перекодирования)",
        "choose": "Выбрать файл...",
        "remux_btn": "Перепаковать",
        "drop_title": "Перетащи медиафайл сюда",
        "drop_hint": "или нажми на эту область / «Выбрать файл…»",
        "event_log": "Журнал событий",
        "update_ytdlp": "Обновить yt-dlp",
        "update_ffmpeg": "Проверить FFmpeg",
        "ready": "Готово",
        "skin": "Скин:",
    },
    "EN": {
        "subtitle": "Original YouTube streams + remuxing without re-encoding",
        "url": "YouTube URL",
        "analyze": "Analyze URL",
        "cancel": "Cancel",
        "not_analyzed": "Video not analyzed",
        "audio": "Audio",
        "audio_stream": "1. Audio stream",
        "chapters": "2. Chapters",
        "chapters_none": "Do not use",
        "chapters_embed": "Embed in file",
        "chapters_split": "Split into tracks",
        "metadata": "Embed metadata",
        "thumbnail": "Embed thumbnail",
        "manual_chapters": "Manual chapters...",
        "download_audio": "Download audio",
        "video": "Video",
        "container": "1. Container",
        "video_stream": "2. Quality / video stream",
        "video_audio": "3. Audio",
        "best": "Best compatible",
        "download_video": "Download video",
        "download_thumbnail": "Download thumbnail",
        "embed_chapters": "Embed chapters",
        "fragment": "Save fragment",
        "use_range": "Use time range",
        "from": "From:",
        "to": "To:",
        "format": "Format: HH:MM:SS",
        "hour_short": "h",
        "minute_short": "min",
        "second_short": "sec",
        "output": "Save folder",
        "browse": "Browse...",
        "open": "Open folder",
        "remux": "Container remuxing (no re-encoding)",
        "choose": "Choose file...",
        "remux_btn": "Remux",
        "drop_title": "Drop a media file here",
        "drop_hint": "or click this area / “Choose file…”",
        "event_log": "Event log",
        "update_ytdlp": "Update yt-dlp",
        "update_ffmpeg": "Check FFmpeg",
        "ready": "Ready",
        "skin": "Skin:",
    },
}


class ChevronComboBox(QComboBox):
    """Combo box with an explicit visible chevron inside the drop-down area."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chevron = QLabel("˅", self)
        self.chevron.setObjectName("comboChevron")
        self.chevron.setAlignment(Qt.AlignCenter)
        self.chevron.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.chevron.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.chevron.setGeometry(max(0, self.width() - 27), 0, 24, self.height())
        self.chevron.raise_()



def help_indicator(target, parent=None):
    button = QToolButton(parent)
    button.setText("i")
    button.setObjectName("helpIndicator")
    button.setFixedSize(18, 18)
    button.setCursor(Qt.PointingHandCursor)
    button.clicked.connect(lambda: QToolTip.showText(button.mapToGlobal(button.rect().bottomLeft()), target.toolTip(), button, button.rect(), 9000))
    button.help_target = target
    return button


def attach_label_help(label, target):
    parent = label.parentWidget()
    box = QWidget(parent)
    row = QHBoxLayout(box)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(4)
    old_item = parent.layout().replaceWidget(label, box, Qt.FindChildrenRecursively)
    if old_item is None:
        box.deleteLater()
        return None
    row.addWidget(label)
    button = help_indicator(target, box)
    row.addWidget(button)
    row.addStretch(1)
    return button


class OverallProgressBar(QProgressBar):
    """Progress bar with centered percent and an inset speed readout on the left."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFormat("%p%")
        self.setTextVisible(True)

        self.speed_label = QLabel("—", self)
        self.speed_label.setObjectName("progressSpeedLabel")
        self.speed_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.speed_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.speed_label.setMinimumWidth(118)
        self.speed_label.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        margin = 10
        width = min(170, max(120, self.width() // 5))
        self.speed_label.setGeometry(margin, 0, width, self.height())
        self.speed_label.raise_()

    def set_speed(self, speed: Optional[str]):
        self.speed_label.setText(speed or "—")



class SuccessToast(QFrame):
    """Small non-modal completion signal shown over the main window."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("successToast")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setVisible(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        self.icon = QLabel("✓")
        self.icon.setObjectName("successToastIcon")

        self.text = QLabel("")
        self.text.setObjectName("successToastText")
        self.text.setWordWrap(True)

        layout.addWidget(self.icon)
        layout.addWidget(self.text, 1)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def show_message(self, text: str, timeout_ms: int = 3800):
        self.text.setText(text)
        self.adjustSize()
        self.setMinimumWidth(300)
        self.setMaximumWidth(460)
        self.adjustSize()

        parent = self.parentWidget()
        if parent is not None:
            x = max(18, parent.width() - self.width() - 28)
            y = 82
            self.move(x, y)

        self.show()
        self.raise_()
        self.timer.start(timeout_ms)


class CollapsibleGroup(QGroupBox):
    """A group box whose body can be folded without changing section order."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._collapsed = False
        self.setProperty("collapsible", True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        self.collapse_button = QToolButton(self)
        self.collapse_button.setObjectName("sectionCollapseButton")
        self.collapse_button.setText("▾")
        self.collapse_button.setAutoRaise(True)
        self.collapse_button.setToolTip("Свернуть / Развернуть")
        self.collapse_button.setCursor(Qt.PointingHandCursor)
        self.collapse_button.clicked.connect(self.toggle_collapsed)
        self.collapse_button.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Integrated into the title line; the group background hides the border
        # behind the glyph so it reads as part of the section caption.
        self.collapse_button.setGeometry(9, 3, 26, 22)
        self.collapse_button.raise_()
        self.position_section_help()

    def position_section_help(self):
        if not hasattr(self, "section_help"):
            return
        option = QStyleOptionGroupBox()
        self.initStyleOption(option)
        title_rect = self.style().subControlRect(QStyle.CC_GroupBox, option, QStyle.SC_GroupBoxLabel, self)
        x = min(title_rect.right() + 8, self.width() - self.section_help.width() - 6)
        y = max(0, title_rect.center().y() - self.section_help.height() // 2)
        self.section_help.move(x, y)
        self.section_help.raise_()

    def setTitle(self, title):
        super().setTitle(title)
        self.position_section_help()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.StyleChange, QEvent.FontChange):
            self.position_section_help()

    def _set_layout_visible(self, layout, visible: bool):
        if layout is None:
            return
        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget()
            if widget is not None and widget is not self.collapse_button:
                widget.setVisible(visible)
            child_layout = item.layout()
            if child_layout is not None:
                self._set_layout_visible(child_layout, visible)

    def set_collapsed(self, collapsed: bool):
        collapsed = bool(collapsed)
        if collapsed == self._collapsed:
            return
        self._collapsed = collapsed
        self._set_layout_visible(self.layout(), not collapsed)
        self.collapse_button.setText("▸" if collapsed else "▾")
        if collapsed:
            self.setMinimumHeight(34)
            self.setMaximumHeight(38)
        else:
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
        self.updateGeometry()

    def toggle_collapsed(self):
        self.set_collapsed(not self._collapsed)


class PreviewWorker(QThread):
    loaded = Signal(bytes)
    failed = Signal(str)

    def __init__(self, urls, proxy: str = "", certificate_mode: str = "Auto", parent=None):
        super().__init__(parent)
        self.urls = [urls] if isinstance(urls, str) else list(urls)
        self.proxy = proxy
        self.certificate_mode = certificate_mode

    def run(self):
        errors = []
        for url in self.urls[:3]:
            if self.isInterruptionRequested():
                return
            try:
                if self.proxy.lower().startswith(("socks4", "socks5")):
                    curl = shutil.which("curl")
                    if not curl:
                        raise RuntimeError("SOCKS preview requires curl")
                    cmd = [curl, "--silent", "--show-error", "--fail", "--location", "--max-time", "12", "--proxy", self.proxy]
                    if self.certificate_mode == "Insecure":
                        cmd.append("--insecure")
                    else:
                        ca_file = certificate_process_env(self.certificate_mode).get("SSL_CERT_FILE")
                        if self.certificate_mode == "Certifi":
                            import certifi
                            ca_file = certifi.where()
                        if ca_file:
                            cmd += ["--cacert", ca_file]
                    result = subprocess.run(cmd + [url], capture_output=True, timeout=15)
                    if result.returncode:
                        raise RuntimeError(result.stderr.decode("utf-8", "replace")[-300:])
                    data = result.stdout
                else:
                    # An explicit empty proxy map respects Direct/TUN instead of
                    # accidentally inheriting proxy variables from the OS.
                    proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else {}
                    opener = urllib.request.build_opener(
                        urllib.request.ProxyHandler(proxies),
                        urllib.request.HTTPSHandler(context=_ssl_context(self.certificate_mode)),
                    )
                    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "image/jpeg,image/webp,image/*"})
                    with opener.open(request, timeout=12) as response:
                        data = response.read(6 * 1024 * 1024 + 1)
                if not data or len(data) > 6 * 1024 * 1024:
                    raise RuntimeError("empty or oversized thumbnail")
                if QImage.fromData(data).isNull():
                    raise RuntimeError("thumbnail is not a supported image")
                if not self.isInterruptionRequested():
                    self.loaded.emit(data)
                return
            except Exception as exc:
                errors.append(str(exc))
        if not self.isInterruptionRequested():
            self.failed.emit("; ".join(errors)[-800:])


class RemuxDropArea(QFrame):
    fileDropped = Signal(str)
    clicked = Signal()

    ALLOWED_EXTENSIONS = {
        ".opus", ".ogg", ".aac", ".webm", ".m4a", ".mp4", ".mkv",
        ".mov", ".m4v", ".avi", ".ts", ".m2ts", ".flac", ".wav",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("remuxDropArea")
        self.setAcceptDrops(True)
        self.setMinimumHeight(82)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("dragActive", False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(3)

        self.title_label = QLabel("")
        self.title_label.setObjectName("remuxDropTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self.hint_label = QLabel("")
        self.hint_label.setObjectName("remuxDropHint")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        layout.addStretch(1)
        layout.addWidget(self.title_label)
        layout.addWidget(self.hint_label)
        layout.addStretch(1)

    def set_texts(self, title: str, hint: str):
        self.title_label.setText(title)
        self.hint_label.setText(hint)

    def _set_drag_active(self, active: bool):
        self.setProperty("dragActive", bool(active))
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _first_local_file(self, event) -> str:
        mime = event.mimeData()
        if not mime.hasUrls():
            return ""
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.is_file() and path.suffix.lower() in self.ALLOWED_EXTENSIONS:
                return str(path)
        return ""

    def dragEnterEvent(self, event):
        if self._first_local_file(event):
            event.acceptProposedAction()
            self._set_drag_active(True)
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._first_local_file(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._set_drag_active(False)
        event.accept()

    def dropEvent(self, event):
        self._set_drag_active(False)
        path = self._first_local_file(event)
        if not path:
            event.ignore()
            return
        self.fileDropped.emit(path)
        event.acceptProposedAction()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class NetworkWorker(QThread):
    done = Signal(str, str)

    def __init__(self, proxy: str):
        super().__init__()
        self.proxy = proxy

    def run(self):
        self.done.emit(external_ip(self.proxy), local_interface_hint())


class PostProcessWorker(QThread):
    log = Signal(str)
    done = Signal(bool, str, str)
    progress = Signal(int)

    def __init__(self, action: str, **kwargs):
        super().__init__()
        self.action = action
        self.kwargs = kwargs

    def run(self):
        try:
            if self.action == "aac":
                ffmpeg = Path(self.kwargs["ffmpeg"])
                inp = Path(self.kwargs["input"])
                out = Path(self.kwargs["output"])
                cmd = [
                    str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(inp),
                    "-map", "0:a:0",
                    "-c:a", "copy",
                    "-f", "adts",
                    str(out),
                ]
                cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                ok = cp.returncode == 0 and out.exists()
                self.done.emit(ok, str(out), cp.stderr.decode("utf-8", "replace"))
                return

            if self.action == "fragment":
                ffmpeg = Path(self.kwargs["ffmpeg"])
                inp = Path(self.kwargs["input"])
                out = Path(self.kwargs["output"])
                start = self.kwargs["start"]
                duration = self.kwargs["duration"]
                cmd = [
                    str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", f"{start:.3f}",
                    "-i", str(inp),
                    "-t", f"{duration:.3f}",
                    "-map", "0",
                    "-c", "copy",
                    str(out),
                ]
                cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                ok = cp.returncode == 0 and out.exists()
                self.done.emit(ok, str(out), cp.stderr.decode("utf-8", "replace"))
                return

            if self.action == "embed_chapters":
                ffmpeg = Path(self.kwargs["ffmpeg"])
                inp = Path(self.kwargs["input"])
                chapters = self.kwargs["chapters"]
                ok, err = embed_chapters_copy(ffmpeg, inp, chapters)
                self.done.emit(ok, str(inp), err)
                return

            if self.action == "split":
                ffmpeg = Path(self.kwargs["ffmpeg"])
                inp = Path(self.kwargs["input"])
                chapters = self.kwargs["chapters"]

                def cb(i, total, out):
                    self.log.emit(f"Разделение: {i:02d}/{total:02d} — {out.name}")
                    self.progress.emit(int(i / total * 100))

                ok, err, created = split_audio_copy(ffmpeg, inp, chapters, cb)
                self.done.emit(ok, str(inp), err)
                return

            self.done.emit(False, "", f"Unknown postprocess action: {self.action}")
        except Exception as exc:
            self.done.emit(False, "", str(exc))


class ManualChaptersDialog(QDialog):
    def __init__(self, parent, text: str, lang: str):
        super().__init__(parent)
        self.setWindowTitle("Manual chapters" if lang == "EN" else "Главы вручную")
        self.resize(570, 430)
        layout = QVBoxLayout(self)
        label = QLabel(
            "Paste timestamps, one chapter per line (00:00 Intro)"
            if lang == "EN"
            else "Вставь таймкоды: одна глава на строку (00:00 Вступление)"
        )
        layout.addWidget(label)
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(text)
        self.editor.setPlaceholderText("00:00 Вступление\n01:32 Глава 1\n05:10 Глава 2")
        layout.addWidget(self.editor, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel" if lang == "EN" else "Отмена")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)


class OstrovEqualizer(QWidget):
    """Small silent animation, active only while the easter egg is visible."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(76)
        self.levels = [0.2] * 24
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.tick)

    def tick(self):
        self.levels = [random.uniform(0.12, 1.0) for _ in self.levels]
        self.update()

    def showEvent(self, event):
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#090e0b"))
        step = self.width() / len(self.levels)
        for i, level in enumerate(self.levels):
            count = max(1, int(level * 12))
            for row in range(count):
                painter.fillRect(int(i * step + 2), self.height() - 5 - row * 5,
                                 max(2, int(step - 4)), 3,
                                 QColor("#ffb43b" if row > 8 else "#a4ff36" if row > 5 else "#3cd75f"))


class NetworkDialog(QDialog):
    def __init__(self, parent, settings: dict):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Подключение к YouTube")
        self.resize(700, 810)

        layout = QVBoxLayout(self)
        self.lang = getattr(parent, "lang", "RU")
        self.question = QLabel("Как yt-dlp должен выходить в интернет?" if self.lang == "RU" else "How should yt-dlp connect to the internet?")
        self.question.setObjectName("networkQuestion")
        self.question.setWordWrap(True)
        layout.addWidget(self.question)
        self.route_title = QLabel("МАРШРУТ ПОДКЛЮЧЕНИЯ" if self.lang == "RU" else "CONNECTION ROUTE")
        self.route_title.setObjectName("networkSection")
        layout.addWidget(self.route_title)

        system_proxy = get_system_proxy()
        detected = (
            f"Обнаружен системный proxy: {system_proxy}"
            if system_proxy
            else "Системный proxy не обнаружен"
        )
        detected_label = QLabel(detected)
        detected_label.setProperty("muted", True)
        layout.addWidget(detected_label)

        self.group = QButtonGroup(self)
        self.auto = QRadioButton("Автоматически")
        self.direct = QRadioButton("Напрямую / TUN")
        self.incy = QRadioButton("INCY — использовать системный proxy")
        self.happ = QRadioButton("Happ — использовать системный proxy")
        self.manual = QRadioButton("Ручной proxy")
        for button, mode in [
            (self.auto, "Auto"), (self.direct, "Direct"), (self.incy, "INCY"),
            (self.happ, "Happ"), (self.manual, "Manual"),
        ]:
            self.group.addButton(button)
            button.setProperty("mode", mode)
            layout.addWidget(button)

        hint = QLabel("Auto: System Proxy → иначе Direct / TUN")
        hint.setProperty("muted", True)
        layout.addWidget(hint)

        self.proxy_edit = QLineEdit(settings.get("manual_proxy", ""))
        self.proxy_edit.setPlaceholderText(
            "http://127.0.0.1:10808  или  socks5h://user:pass@127.0.0.1:10808"
        )
        layout.addWidget(self.proxy_edit)

        cert_title = QLabel("HTTPS-сертификаты")
        cert_title.setObjectName("networkSection")
        layout.addWidget(cert_title)

        self.cert_mode = ChevronComboBox()
        self.cert_mode.addItem("Автоматически (рекомендуется)", "Auto")
        if platform.system() == "Darwin":
            self.cert_mode.addItem("macOS Keychain + публичные CA", "MacKeychain")
        self.cert_mode.addItem("Системные сертификаты OpenSSL", "System")
        self.cert_mode.addItem("Встроенный certifi", "Certifi")
        self.cert_mode.addItem("Не проверять сертификаты (небезопасно)", "Insecure")

        saved_cert = settings.get("certificate_mode", "Auto")
        cert_index = self.cert_mode.findData(saved_cert)
        self.cert_mode.setCurrentIndex(cert_index if cert_index >= 0 else 0)
        layout.addWidget(self.cert_mode)

        cert_hint = QLabel(
            "Auto: Windows → certifi; macOS → Keychain + публичные CA; "
            "Linux → системный CA bundle. Отключение проверки SSL — только "
            "после явного подтверждения и как последний вариант."
        )
        cert_hint.setWordWrap(True)
        cert_hint.setProperty("muted", True)
        layout.addWidget(cert_hint)

        lang = getattr(parent, "lang", "RU")
        en = lang == "EN"
        cookies_title = QLabel("YouTube cookies (optional)" if en else "Cookies YouTube (по необходимости)")
        cookies_title.setObjectName("networkSection")
        layout.addWidget(cookies_title)
        self.cookies_mode = ChevronComboBox()
        for label, value in [("Disabled" if en else "Не использовать", "None"),
                             ("From browser" if en else "Из браузера", "Browser"),
                             ("From cookies.txt" if en else "Из файла cookies.txt", "File")]:
            self.cookies_mode.addItem(label, value)
        idx = self.cookies_mode.findData(settings.get("cookies_mode", "None"))
        self.cookies_mode.setCurrentIndex(max(0, idx))
        layout.addWidget(self.cookies_mode)
        self.cookies_browser = ChevronComboBox()
        for browser in BROWSERS:
            if browser != "safari" or platform.system() == "Darwin":
                self.cookies_browser.addItem(("Яндекс Браузер (cookies.txt)" if not en else "Yandex Browser (cookies.txt)") if browser == "yandex" else browser.capitalize(), browser)
        idx = self.cookies_browser.findData(settings.get("cookies_browser", "chrome"))
        self.cookies_browser.setCurrentIndex(max(0, idx))
        layout.addWidget(self.cookies_browser)
        file_row = QHBoxLayout()
        self.cookies_file = QLineEdit(settings.get("cookies_file", ""))
        self.cookies_file.setPlaceholderText("cookies.txt (Netscape)")
        self.cookies_browse = QPushButton("Browse…" if en else "Обзор…")
        self.cookies_browse.clicked.connect(self.browse_cookies)
        file_row.addWidget(self.cookies_file, 1)
        file_row.addWidget(self.cookies_browse)
        layout.addLayout(file_row)
        cookie_hint = QLabel(
            "Open the video in this browser using the same VPN/proxy. Cookies are read only when you select this mode. macOS may ask for Keychain or file access. Do not share cookies: they may grant account access."
            if en else
            "Открой видео в выбранном браузере через тот же VPN/proxy. Cookies читаются только при выборе этого режима. macOS может запросить доступ к связке ключей или файлам. Не передавай cookies другим: они могут дать доступ к аккаунту."
        )
        cookie_hint.setWordWrap(True)
        cookie_hint.setProperty("muted", True)
        layout.addWidget(cookie_hint)
        self.cookies_browser.currentIndexChanged.connect(self.update_cookie_state)
        self.cookies_mode.currentIndexChanged.connect(self.update_cookie_state)
        self.update_cookie_state()

        current = settings.get("network_mode", "Auto")
        for button in self.group.buttons():
            if button.property("mode") == current:
                button.setChecked(True)
                break
        else:
            self.auto.setChecked(True)

        result_title = QLabel("РЕЗУЛЬТАТ ПРОВЕРКИ" if self.lang == "RU" else "TEST RESULT")
        result_title.setObjectName("networkSection")
        layout.addWidget(result_title)
        self.result = QPlainTextEdit()
        self.result.setObjectName("networkResult")
        self.result.setReadOnly(True)
        self.result.setMaximumHeight(90)
        layout.addWidget(self.result)

        buttons = QHBoxLayout()
        self.test_btn = QPushButton("Проверить соединение")
        self.test_btn.setObjectName("primaryButton")
        ok = QPushButton("Продолжить")
        cancel = QPushButton("Отмена")
        self.test_btn.clicked.connect(self.test_connection)
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(self.test_btn)
        buttons.addStretch(1)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

        self.network_help_buttons = []
        for label, target, russian, english in (
            (self.route_title, self.proxy_edit, "Auto берёт системный proxy; Direct/TUN работает без явного proxy.", "Auto uses the system proxy; Direct/TUN uses no explicit proxy."),
            (cert_title, self.cert_mode, "Auto: macOS Keychain, Windows certifi, Linux системные CA. Отключение проверки снижает безопасность.", "Auto: macOS Keychain, Windows certifi, Linux system CA. Disabling verification reduces security."),
            (cookies_title, self.cookies_mode, "Cookies нужны при проверке YouTube или доступе по аккаунту. Яндекс — через cookies.txt.", "Cookies help with YouTube verification or account access. Yandex requires cookies.txt."),
            (result_title, self.result, "Результат проверки выбранного маршрута; ошибки показывают причину.", "Result for the selected route; errors explain the cause."),
        ):
            target.setToolTip(russian if self.lang == "RU" else english)
            button = attach_label_help(label, target)
            if button:
                button.setToolTip(target.toolTip())
                self.network_help_buttons.append(button)
        self.cookies_browser.setToolTip("Выбери браузер с открытой сессией YouTube." if self.lang == "RU" else "Choose the browser with your YouTube session.")
        self.cookies_file.setToolTip("Экспортированный файл cookies в формате Netscape." if self.lang == "RU" else "An exported Netscape cookie file.")
        self.worker: Optional[CaptureWorker] = None
        self.update_manual_state()
        for button in self.group.buttons():
            button.toggled.connect(self.update_manual_state)

    def cookie_settings(self) -> dict:
        return {"cookies_mode": self.cookies_mode.currentData() or "None",
                "cookies_browser": self.cookies_browser.currentData() or "chrome",
                "cookies_file": self.cookies_file.text().strip()}

    def update_cookie_state(self, *_):
        mode = self.cookies_mode.currentData()
        self.cookies_browser.setEnabled(mode == "Browser")
        use_file = mode == "File" or (mode == "Browser" and self.cookies_browser.currentData() == "yandex")
        self.cookies_file.setEnabled(use_file)
        self.cookies_browse.setEnabled(use_file)

    def browse_cookies(self):
        path, _ = QFileDialog.getOpenFileName(self, "cookies.txt", self.cookies_file.text(), "Cookies (*.txt);;All files (*)")
        if path:
            self.cookies_file.setText(path)

    def accept(self):
        try:
            cookie_args(self.cookie_settings())
        except ValueError as exc:
            self.result.setPlainText(str(exc))
            return
        super().accept()

    def mode(self) -> str:
        button = self.group.checkedButton()
        return str(button.property("mode")) if button else "Auto"

    def certificate_mode(self) -> str:
        value = self.cert_mode.currentData()
        return str(value or "Auto")

    def update_manual_state(self):
        self.proxy_edit.setEnabled(self.mode() == "Manual")

    def test_connection(self):
        base = ytdlp_command()
        if not base:
            self.result.setPlainText("✕ yt-dlp не найден.")
            return
        net_args, resolved = proxy_args(self.mode(), self.proxy_edit.text())
        if not resolved.ok:
            self.result.setPlainText("✕ " + resolved.detail)
            return
        try:
            auth_args = cookie_args(self.cookie_settings())
        except ValueError as exc:
            self.result.setPlainText(str(exc))
            return
        cmd = base + auth_args + net_args + ytdlp_common_args(self.certificate_mode()) + [
            "--socket-timeout", "8",
            "--ignore-no-formats-error",
            "--skip-download",
            "--simulate",
            "--print", "%(id)s",
            "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        ]
        self.test_btn.setEnabled(False)
        self.result.setPlainText("Проверка...")
        self.worker = CaptureWorker(
            cmd,
            app_dir(),
            timeout=60 if auth_args else 20,
            extra_env=certificate_process_env(self.certificate_mode()),
        )
        self.worker.completed.connect(self.test_completed)
        self.worker.failed.connect(lambda e: self.test_completed(1, "", e))
        self.worker.start()

    def test_completed(self, code: int, out: str, err: str):
        self.test_btn.setEnabled(True)
        all_text = out + "\n" + err
        if is_youtube_bot_error(all_text):
            self.result.setPlainText(bot_error_help(getattr(self.parent(), "lang", "RU")))
            return
        if is_ssl_certificate_error(all_text):
            self.result.setPlainText(
                "✕ Ошибка проверки HTTPS-сертификата.\n"
                "На macOS попробуй «macOS Keychain + публичные CA». "
                "Если даже Keychain не помогает, сеть/VPN, вероятно, подменяет "
                "HTTPS неизвестным сертификатом."
            )
            return

        network_error = re.search(
            r"failed to resolve|getaddrinfo|connection refused|unable to connect|"
            r"network is unreachable|timed out|proxy.*error|tunnel connection failed|"
            r"authentication methods were rejected|socks5error",
            all_text,
            re.I,
        )
        if network_error:
            self.result.setPlainText("✕ Нет соединения с YouTube.\n" + err[-700:])
            return
        if code == 0 or "jNQXAC9IVRw" in out:
            self.result.setPlainText("✓ YouTube доступен через выбранный маршрут.")
            return
        if re.search(r"\[youtube\]|challenge solving failed|only images|no video formats", all_text, re.I):
            self.result.setPlainText(
                "✓ YouTube доступен. Предупреждение относится к извлечению форматов."
            )
            return
        self.result.setPlainText("✕ Не удалось подтвердить соединение.\n" + all_text[-700:])




class DependencyInstallWorker(QThread):
    progress_changed = Signal(int, str)
    log_line = Signal(str)
    completed_install = Signal(bool, str)

    def __init__(
        self,
        key: str,
        proxy: str = "",
        certificate_mode: str = "Auto",
    ):
        super().__init__()
        self.key = key
        self.proxy = proxy
        self.certificate_mode = certificate_mode

    def run(self):
        try:
            install_dependency(
                self.key,
                proxy=self.proxy,
                progress_cb=lambda value, text: self.progress_changed.emit(value, text),
                log_cb=lambda text: self.log_line.emit(text),
                certificate_mode=self.certificate_mode,
            )
            self.completed_install.emit(True, "")
        except Exception as exc:
            self.completed_install.emit(False, str(exc))




class DependencyStatusWorker(QThread):
    done = Signal(object)

    def run(self):
        try:
            report = dependency_report()

            yt_version = ""
            ffmpeg_version = ""

            if report.get("yt_dlp", {}).get("ok"):
                yt_version = dependency_version(ytdlp_command(), ["--version"])

            ff = report.get("ffmpeg", {})
            if ff.get("ok"):
                ffmpeg_version = dependency_version(
                    [ff["path"]], ["-version"]
                ).replace("ffmpeg version ", "")

            self.done.emit(
                {
                    "yt_ok": bool(report.get("yt_dlp", {}).get("ok")),
                    "yt_version": yt_version,
                    "ffmpeg_ok": bool(ff.get("ok")),
                    "ffmpeg_version": ffmpeg_version,
                }
            )
        except Exception:
            self.done.emit({})


class DependencyUpdateCheckWorker(QThread):
    completed_check = Signal(object)

    def __init__(
        self,
        report: dict,
        proxy: str = "",
        certificate_mode: str = "Auto",
    ):
        super().__init__()
        self.report = report
        self.proxy = proxy
        self.certificate_mode = certificate_mode

    def run(self):
        try:
            self.completed_check.emit(
                check_dependency_updates(
                    self.report,
                    self.proxy,
                    self.certificate_mode,
                )
            )
        except Exception:
            self.completed_check.emit({})


class DependencyDialog(QDialog):
    def __init__(self, parent, lang: str):
        super().__init__(parent)
        self.lang = lang
        self.worker = None
        self.update_check_worker = None
        self.update_info = {}
        self.update_all_queue: list[str] = []
        self.parent_window = parent
        self.setWindowTitle("Dependency check" if lang == "EN" else "Проверка зависимостей")
        self.resize(760, 560)

        layout = QVBoxLayout(self)

        intro = QLabel(
            "The app checks required tools at startup. Missing components can be installed or downloaded."
            if lang == "EN" else
            "При старте приложение проверяет обязательные инструменты. Недостающие компоненты можно установить или скачать."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.summary = QLabel("")
        self.summary.setProperty("muted", True)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.grid = QGridLayout()
        self.grid.setColumnStretch(1, 1)
        layout.addLayout(self.grid)

        self.rows = {}
        row = 0
        for key, title in [
            ("python", "Python runtime"),
            ("yt_dlp", "yt-dlp"),
            ("ffmpeg", "FFmpeg"),
            ("ffprobe", "FFprobe"),
            ("deno", "Deno JS runtime"),
        ]:
            title_label = QLabel(title)
            status_label = QLabel("—")
            status_label.setObjectName("dependencyStatus")
            status_label.setWordWrap(True)
            status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            action_btn = QPushButton()
            action_btn.clicked.connect(lambda _=False, k=key: self.handle_action(k))
            self.grid.addWidget(title_label, row, 0)
            self.grid.addWidget(status_label, row, 1)
            self.grid.addWidget(action_btn, row, 2)
            self.rows[key] = (status_label, action_btn)
            row += 1

        extra = QLabel(
            "Notes: yt-dlp, Deno, FFmpeg and FFprobe are managed here. "
            "Python 3.11+ is recommended by current yt-dlp. A compiled .app/.exe "
            "contains its own Python runtime, so that embedded runtime is upgraded "
            "by rebuilding the app; external modules can be updated directly here."
            if lang == "EN" else
            "Примечание: здесь обновляются yt-dlp, Deno, FFmpeg и FFprobe. "
            "Современный yt-dlp рекомендует Python 3.11+. В собранном .app/.exe "
            "Python встроен внутрь приложения, поэтому его версия меняется при "
            "пересборке; внешние модули обновляются прямо из этого окна."
        )
        extra.setWordWrap(True)
        extra.setProperty("muted", True)
        layout.addWidget(extra)

        self.install_progress = QProgressBar()
        self.install_progress.setRange(0, 100)
        self.install_progress.setValue(0)
        self.install_progress.setVisible(False)
        layout.addWidget(self.install_progress)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(190)
        layout.addWidget(self.log, 1)

        buttons = QHBoxLayout()
        self.recheck_btn = QPushButton("Recheck" if lang == "EN" else "Проверить ещё раз")
        self.update_all_btn = QPushButton(
            "Update all modules" if lang == "EN" else "Обновить все модули"
        )
        self.continue_btn = QPushButton("Continue" if lang == "EN" else "Продолжить")
        self.exit_btn = QPushButton("Exit" if lang == "EN" else "Выход")
        self.recheck_btn.clicked.connect(self.refresh)
        self.update_all_btn.clicked.connect(self.update_all_modules)
        self.continue_btn.clicked.connect(self.accept)
        self.exit_btn.clicked.connect(self.reject)
        buttons.addWidget(self.recheck_btn)
        buttons.addWidget(self.update_all_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.continue_btn)
        buttons.addWidget(self.exit_btn)
        layout.addLayout(buttons)

        self.refresh()

    def append_log(self, text: str):
        if text:
            self.log.appendPlainText(text)

    def dependency_proxy(self) -> str:
        proxy = ""
        try:
            if self.parent_window is not None:
                resolved = resolve_proxy(
                    self.parent_window.settings.get("network_mode", "Auto"),
                    self.parent_window.settings.get("manual_proxy", ""),
                )
                if resolved.ok and str(resolved.proxy).lower().startswith(("http://", "https://")):
                    proxy = str(resolved.proxy)
        except Exception:
            pass
        return proxy

    def dependency_certificate_mode(self) -> str:
        try:
            if self.parent_window is not None:
                return self.parent_window.effective_certificate_mode()
        except Exception:
            pass
        return "Auto"

    def set_status_style(self, label: QLabel, state: str):
        colors = {
            "ok": "#35d07f",
            "missing": "#ff5d68",
            "update": "#f2c94c",
            "optional": "#8da1b3",
        }
        color = colors.get(state, "#c7ccd2")
        label.setStyleSheet(f"color: {color}; font-weight: 650;")

    def refresh(self):
        clear_tool_cache()
        report = dependency_report()
        self.last_report = report

        # For YouTube in 2026, Deno is treated as required because yt-dlp
        # increasingly relies on an external JS runtime for challenge solving.
        all_required_ok = (
            report["yt_dlp"]["ok"]
            and report["yt_dlp"].get("external")
            and report["ffmpeg"]["ok"]
            and report["ffprobe"]["ok"]
            and report["deno"]["ok"]
        )

        missing = []

        # Python runtime is informational inside a compiled app.
        py_status, py_button = self.rows["python"]
        py = report["python"]
        py_ver = py.get("version", "")
        if py.get("recommended"):
            py_status.setText(
                ("✓ Python runtime: " if self.lang == "EN" else "✓ Python runtime: ")
                + py_ver
                + (" • embedded in app" if py.get("frozen") and self.lang == "EN" else
                   " • встроен в приложение" if py.get("frozen") else "")
            )
            self.set_status_style(py_status, "ok")
        else:
            py_status.setText(
                (
                    f"⚠ Python {py_ver}: yt-dlp recommends Python 3.11+. "
                    + ("Rebuild the app with Python 3.12." if py.get("frozen")
                       else "Restart via the launcher; it will upgrade/recreate the environment.")
                )
                if self.lang == "EN"
                else
                (
                    f"⚠ Python {py_ver}: yt-dlp рекомендует Python 3.11+. "
                    + ("Эту сборку нужно пересобрать на Python 3.12." if py.get("frozen")
                       else "Перезапусти через стартовый скрипт — он обновит Python/окружение.")
                )
            )
            self.set_status_style(py_status, "update")
        py_button.setText("Info" if self.lang == "EN" else "Инфо")
        try:
            py_button.clicked.disconnect()
        except Exception:
            pass
        py_button.clicked.connect(self.show_python_info)

        for key, required in [
            ("yt_dlp", True),
            ("ffmpeg", True),
            ("ffprobe", True),
            ("deno", True),
        ]:
            status_label, action_btn = self.rows[key]
            info = report[key]

            if info["ok"]:
                if key == "yt_dlp":
                    ver = dependency_version(ytdlp_command(), ["--version"])
                elif key == "ffmpeg":
                    ver = dependency_version([report[key]["path"]], ["-version"]).replace("ffmpeg version ", "")
                elif key == "ffprobe":
                    ver = dependency_version([report[key]["path"]], ["-version"]).replace("ffprobe version ", "")
                else:
                    ver = dependency_version([report[key]["path"]], ["--version"])

                version_suffix = f" • {ver}" if ver else ""
                update = self.update_info.get(key, {})

                # A Python-module fallback works, but we deliberately replace it
                # with the official platform binary.
                module_fallback = key == "yt_dlp" and info.get("module_fallback")
                if module_fallback:
                    status_label.setText(
                        (
                            "⚠ Python-module fallback is in use. Install the official platform binary"
                            if self.lang == "EN"
                            else
                            "⚠ Используется Python-модуль. Установи официальный бинарник для платформы"
                        )
                        + version_suffix
                    )
                    self.set_status_style(status_label, "update")
                    missing.append("yt_dlp_binary")
                elif update.get("update"):
                    latest = update.get("latest", "")
                    status_label.setText(
                        ("⚠ Update available" if self.lang == "EN" else "⚠ Доступно обновление")
                        + f": {info['path']}{version_suffix}"
                        + (f" → {latest}" if latest else "")
                    )
                    self.set_status_style(status_label, "update")
                else:
                    status_label.setText(
                        ("✓ Found" if self.lang == "EN" else "✓ Найдено")
                        + f": {info['path']}{version_suffix}"
                    )
                    self.set_status_style(status_label, "ok")

                action_btn.setText("Update" if self.lang == "EN" else "Обновить")
            else:
                self.update_info.pop(key, None)
                missing.append(key)
                status_label.setText(
                    "✕ Missing — click Update to download automatically"
                    if self.lang == "EN" else
                    "✕ Не найден — нажми «Обновить», программа скачает автоматически"
                )
                self.set_status_style(status_label, "missing")
                action_btn.setText("Update" if self.lang == "EN" else "Обновить")

        if all_required_ok:
            self.summary.setText(
                "All required dependencies are available. Checking for updates…"
                if self.lang == "EN" else
                "Все обязательные зависимости найдены. Проверяю обновления…"
            )
        else:
            names = ", ".join(missing)
            self.summary.setText(
                f"Missing/recommended dependencies: {names}. The app can install them automatically."
                if self.lang == "EN" else
                f"Не хватает обязательных/рекомендуемых компонентов: {names}. Программа может установить их автоматически."
            )

        self.continue_btn.setEnabled(all_required_ok)
        self.start_update_check(report)


    def start_update_check(self, report: dict):
        if self.update_check_worker and self.update_check_worker.isRunning():
            return
        if not any(report.get(k, {}).get("ok") for k in ("yt_dlp", "ffmpeg", "ffprobe", "deno")):
            return

        self.update_check_worker = DependencyUpdateCheckWorker(
            report,
            self.dependency_proxy(),
            self.dependency_certificate_mode(),
        )
        self.update_check_worker.completed_check.connect(self.update_check_done)
        self.update_check_worker.start()

    def update_check_done(self, info: dict):
        self.update_info = info or {}
        self.update_check_worker = None

        # Repaint locally without immediately starting another web check.
        report = dependency_report()
        updates_found = False

        for key in ("yt_dlp", "ffmpeg", "ffprobe", "deno"):
            status_label, action_btn = self.rows[key]
            dep = report.get(key, {})
            if not dep.get("ok"):
                continue

            if key == "yt_dlp":
                ver = dependency_version(ytdlp_command(), ["--version"])
            elif key == "ffmpeg":
                ver = dependency_version([dep["path"]], ["-version"]).replace("ffmpeg version ", "")
            elif key == "ffprobe":
                ver = dependency_version([dep["path"]], ["-version"]).replace("ffprobe version ", "")
            else:
                ver = dependency_version([dep["path"]], ["--version"])

            version_suffix = f" • {ver}" if ver else ""
            update = self.update_info.get(key, {})
            if update.get("update"):
                updates_found = True
                latest = update.get("latest", "")
                status_label.setText(
                    ("⚠ Update available" if self.lang == "EN" else "⚠ Доступно обновление")
                    + f": {dep['path']}{version_suffix}"
                    + (f" → {latest}" if latest else "")
                )
                self.set_status_style(status_label, "update")
            else:
                status_label.setText(
                    ("✓ Found" if self.lang == "EN" else "✓ Найдено")
                    + f": {dep['path']}{version_suffix}"
                )
                self.set_status_style(status_label, "ok")

        required_ok = (
            report["yt_dlp"]["ok"]
            and report["yt_dlp"].get("external")
            and report["ffmpeg"]["ok"]
            and report["ffprobe"]["ok"]
            and report["deno"]["ok"]
        )
        if required_ok:
            if updates_found:
                self.summary.setText(
                    "Dependencies are ready. Updates are available for items marked in yellow."
                    if self.lang == "EN" else
                    "Зависимости готовы. Для пунктов, отмеченных жёлтым, доступны обновления."
                )
            else:
                self.summary.setText(
                    "All required dependencies are available and up to date."
                    if self.lang == "EN" else
                    "Все обязательные зависимости найдены и актуальны."
                )
        self.continue_btn.setEnabled(required_ok)


    def show_python_info(self):
        report = dependency_report()
        py = report["python"]
        version = py.get("version", "?")

        if py.get("frozen"):
            text = (
                f"Текущая сборка содержит встроенный Python {version}.\n\n"
                "Встроенный Python нельзя безопасно заменить внутри уже собранного .app/.exe. "
                "Зато yt-dlp теперь устанавливается как отдельный официальный бинарник и не "
                "зависит от Python приложения.\n\n"
                "Чтобы обновить именно runtime приложения, пересобери его новым BUILD-скриптом: "
                "он теперь требует Python 3.11+ и предпочитает Python 3.12."
                if self.lang != "EN"
                else
                f"This build contains embedded Python {version}.\n\n"
                "An embedded Python runtime cannot be safely replaced inside an already-built app. "
                "yt-dlp is now installed as a separate official binary and no longer depends on the "
                "app's Python runtime.\n\nRebuild with the new BUILD script to upgrade the app runtime; "
                "it now requires Python 3.11+ and prefers Python 3.12."
            )
        else:
            text = (
                f"Текущий Python: {version}.\n\n"
                "Source-версия обновляет/пересоздаёт .venv через START_* launcher. "
                "Закрой приложение и запусти его через START_MAC.command / START_WINDOWS.bat / start_linux.sh."
                if self.lang != "EN"
                else
                f"Current Python: {version}.\n\n"
                "The source build upgrades/recreates its .venv through the START_* launcher. "
                "Close the app and start it through the platform launcher."
            )

        QMessageBox.information(
            self,
            "Python runtime",
            text,
        )

    def update_all_modules(self):
        if self.worker and self.worker.isRunning():
            return

        # FFmpeg and FFprobe are one installation job.
        self.update_all_queue = ["yt_dlp", "deno", "ffmpeg"]
        self.append_log(
            "Updating all external modules..."
            if self.lang == "EN"
            else "Обновляю все внешние модули..."
        )
        self.run_next_update_all()

    def run_next_update_all(self):
        if not self.update_all_queue:
            clear_tool_cache()
            self.append_log(
                "All module updates completed."
                if self.lang == "EN"
                else "Обновление всех модулей завершено."
            )
            self.refresh()
            return

        key = self.update_all_queue.pop(0)
        self.handle_action(key, from_update_all=True)

    def handle_action(self, key: str, from_update_all: bool = False):
        if key == "python":
            self.show_python_info()
            return

        if self.worker and self.worker.isRunning():
            return

        if not from_update_all:
            self.update_all_queue = []

        label = {
            "yt_dlp": "yt-dlp",
            "ffmpeg": "FFmpeg + FFprobe",
            "ffprobe": "FFmpeg + FFprobe",
            "deno": "Deno",
        }.get(key, key)

        self.append_log(
            f"Updating {label}..." if self.lang == "EN" else f"Обновляю {label}..."
        )

        proxy = self.dependency_proxy()

        self.install_progress.setValue(0)
        self.install_progress.setFormat("%p%")
        self.install_progress.setVisible(True)
        self.set_buttons_enabled(False)

        self.worker = DependencyInstallWorker(
            key,
            proxy,
            self.dependency_certificate_mode(),
        )
        self.worker.log_line.connect(self.append_log)
        self.worker.progress_changed.connect(self.install_progress_changed)
        self.worker.completed_install.connect(
            lambda ok, error, k=key: self.install_finished(k, ok, error)
        )
        self.worker.start()

    def set_buttons_enabled(self, enabled: bool):
        self.recheck_btn.setEnabled(enabled)
        self.update_all_btn.setEnabled(enabled)
        for _, button in self.rows.values():
            button.setEnabled(enabled)
        if not enabled:
            self.continue_btn.setEnabled(False)

    def install_progress_changed(self, value: int, text: str):
        self.install_progress.setValue(value)
        if text:
            self.install_progress.setFormat(f"{value}% • {text}")
        else:
            self.install_progress.setFormat(f"{value}%")

    def install_finished(self, key: str, ok: bool, error: str):
        self.set_buttons_enabled(True)
        if ok:
            self.install_progress.setValue(100)
            self.append_log(
                "Update completed. Re-checking dependencies."
                if self.lang == "EN" else
                "Обновление завершено. Повторно проверяю зависимости."
            )
        else:
            self.append_log(
                ("Update failed: " if self.lang == "EN" else "Ошибка обновления: ") + error
            )
            if is_ssl_certificate_error(error):
                message = (
                    "Не удалось безопасно скачать модуль из-за HTTPS-сертификата.\n\n"
                    "Обновлятор теперь использует тот же macOS Keychain, что и yt-dlp. "
                    "Если ошибка повторяется даже в этой версии, проверь, что сертификат "
                    "VPN/proxy действительно добавлен в Keychain macOS.\n\n"
                    "Проверку сертификатов для загрузки исполняемых модулей программа "
                    "автоматически не отключает — это сделано специально для безопасности."
                    if self.lang != "EN"
                    else
                    "The module could not be downloaded safely because of an HTTPS "
                    "certificate error.\n\nThe updater now uses the same macOS Keychain "
                    "bundle as yt-dlp. If this still fails, verify that the VPN/proxy CA "
                    "is trusted in macOS Keychain.\n\nCertificate verification is not "
                    "silently disabled for executable dependency downloads."
                )
            else:
                message = (
                    ("Could not update dependency:\n" if self.lang == "EN"
                     else "Не удалось обновить зависимость:\n")
                    + error
                )

            QMessageBox.critical(
                self,
                APP_NAME,
                message,
            )

        self.worker = None
        clear_tool_cache()

        if ok and self.update_all_queue:
            self.run_next_update_all()
            return

        if not ok:
            self.update_all_queue = []

        self.refresh()
        if self.parent_window is not None:
            self.parent_window.refresh_dependency_labels()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.lang = self.settings.get("language", "RU")

        saved_skin = self.settings.get("skin", "")
        if saved_skin not in SKIN_ORDER:
            saved_skin = "Graphite Core" if self.settings.get("theme", "Dark") == "Dark" else "Classic Light"
        self.skin = saved_skin
        self.theme = "Light" if self.skin in {"Classic Light", "Windows 98 Light"} else "Dark"

        self.current_info: dict = {}
        self.audio_formats: list[AudioFormat] = []
        self.video_formats = []
        self.audio_map: list[Optional[tuple[AudioFormat, str]]] = []
        self.video_map: list[Optional[object]] = []
        self.filtered_video_audio: list[AudioFormat] = []
        self.manual_chapters_text = ""

        self.analyze_worker: Optional[CaptureWorker] = None
        self.stream_worker: Optional[StreamWorker] = None
        self.post_worker: Optional[PostProcessWorker] = None
        self.network_worker: Optional[NetworkWorker] = None
        self.preview_worker: Optional[PreviewWorker] = None
        self.preview_workers = []
        self.preview_generation = 0
        self.dependency_status_worker: Optional[DependencyStatusWorker] = None
        self.session_certificate_override: Optional[str] = None
        self.pending_ssl_retry_url: Optional[str] = None
        self.stream_error_tail: list[str] = []
        self.active_download_context: dict = {}

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1180, 900)
        self.setMinimumSize(980, 700)

        self.build_ui()
        self.success_toast = SuccessToast(self)
        self.apply_language()
        self.apply_theme()
        self.update_connection_label()

        # Let Qt paint the window first. Version subprocesses and network I/O
        # start only after the event loop is alive, so startup feels immediate.
        QTimer.singleShot(0, self.refresh_dependency_labels)
        QTimer.singleShot(120, self.startup_dependency_check)
        QTimer.singleShot(260, self.refresh_network_info)

    def tr(self, key: str) -> str:
        return TEXT.get(self.lang, TEXT["RU"]).get(key, key)

    def build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.setCentralWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        root = QVBoxLayout(content)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        # HEADER: compact toolbar based on the supplied mockup.
        header = QFrame()
        header.setObjectName("appHeader")
        header_outer = QVBoxLayout(header)
        header_outer.setContentsMargins(10, 7, 10, 7)
        header_outer.setSpacing(5)
        header_layout = QHBoxLayout()
        header_outer.addLayout(header_layout)
        controls_row = QHBoxLayout()
        controls_row.setSpacing(9)
        header_outer.addLayout(controls_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(9)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        self.title = QLabel(f"▶  {APP_NAME}")
        self.title.setObjectName("title")
        self.subtitle = QLabel("")
        self.subtitle.setProperty("muted", True)
        self.subtitle.setWordWrap(True)
        title_box.addWidget(self.title)
        title_box.addWidget(self.subtitle)
        header_layout.addLayout(title_box, 1)

        self.deps_header_btn = QPushButton()
        self.deps_header_btn.setObjectName("headerButton")
        self.deps_header_btn.setMinimumWidth(190)
        self.deps_header_btn.clicked.connect(self.check_ffmpeg)

        self.language_title = QLabel("Language:")
        self.language_title.setProperty("muted", True)
        self.language = ChevronComboBox()
        self.language.addItems(["RU", "EN"])
        self.language.setCurrentText(self.lang)
        self.language.setMinimumWidth(72)
        self.language.currentTextChanged.connect(self.change_language)

        self.skin_label = QLabel()
        self.skin_label.setProperty("muted", True)
        self.skin_combo = ChevronComboBox()
        self.skin_combo.addItems(SKIN_ORDER)
        self.skin_combo.setCurrentText(self.skin)
        self.skin_combo.setMinimumWidth(160)
        self.skin_combo.currentTextChanged.connect(self.change_skin)

        self.connection_btn = QPushButton()
        self.connection_btn.setObjectName("headerButton")
        self.connection_btn.setIcon(QIcon(str(Path(getattr(sys, "_MEIPASS", app_dir())) / "resources" / "network_settings.svg")))
        self.connection_btn.setIconSize(QSize(20, 20))
        self.connection_btn.clicked.connect(self.show_network_settings)
        self.info_btn = QToolButton()
        self.info_btn.setText("?")
        self.info_btn.setStyleSheet("padding: 2px; font-size: 16px; font-weight: 700;")
        self.info_btn.setFixedSize(30, 30)
        self.info_btn.clicked.connect(self.show_app_info)
        self.deps_header_btn.setMinimumWidth(0)
        self.language.setMinimumWidth(58)
        self.skin_combo.setMinimumWidth(128)
        self.skin_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.skin_combo.setMinimumContentsLength(12)
        self.skin_combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        controls_row.setSpacing(6)
        controls_row.addStretch(1)
        controls_row.addWidget(self.deps_header_btn)
        controls_row.addWidget(self.connection_btn)
        controls_row.addWidget(self.language_title)
        controls_row.addWidget(self.language)
        controls_row.addWidget(self.skin_label)
        controls_row.addWidget(self.skin_combo)
        controls_row.addWidget(self.info_btn)
        root.addWidget(header)

        # Shared source / analysis card. Output folder sits opposite the URL.
        source_card = QFrame()
        source_card.setObjectName("sourceCard")
        source_layout = QGridLayout(source_card)
        source_layout.setContentsMargins(12, 8, 12, 9)
        source_layout.setHorizontalSpacing(8)
        source_layout.setVerticalSpacing(5)
        source_layout.setColumnStretch(0, 5)
        source_layout.setColumnStretch(2, 4)

        self.url_label = QLabel()
        self.url_label.setObjectName("keyLabel")
        self.output_label = QLabel()
        self.output_label.setObjectName("keyLabel")

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://www.youtube.com/watch?v=...")

        self.analyze_btn = QPushButton()
        self.analyze_btn.setObjectName("primaryButton")
        self.analyze_btn.setMinimumWidth(176)
        self.analyze_btn.clicked.connect(self.analyze)

        output_inline = QWidget()
        output_inline.setObjectName("outputInline")
        output_row = QHBoxLayout(output_inline)
        output_row.setContentsMargins(0, 0, 0, 0)
        output_row.setSpacing(6)

        self.output_edit = QLineEdit(
            self.settings.get("output_folder", str(Path.home() / "Downloads"))
        )
        self.output_browse = QPushButton()
        self.output_open = QPushButton()
        self.output_browse.clicked.connect(self.browse_output)
        self.output_open.clicked.connect(self.open_output)
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(self.output_browse)
        output_row.addWidget(self.output_open)

        source_layout.addWidget(self.url_label, 0, 0, 1, 2)
        source_layout.addWidget(self.output_label, 0, 2)
        source_layout.addWidget(self.url_edit, 1, 0)
        source_layout.addWidget(self.analyze_btn, 1, 1)
        source_layout.addWidget(output_inline, 1, 2)

        result_row = QHBoxLayout()
        result_row.setSpacing(10)
        self.preview_label = QLabel("▶")
        self.preview_label.setObjectName("videoPreview")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedSize(112, 63)
        self.preview_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.preview_label.customContextMenuRequested.connect(
            self.show_preview_context_menu
        )

        self.video_title = QLabel()
        self.video_title.setWordWrap(True)
        self.video_title.setObjectName("videoTitle")
        result_row.addWidget(self.preview_label)
        result_row.addWidget(self.video_title, 1)
        source_layout.addLayout(result_row, 2, 0, 1, 3)
        root.addWidget(source_card)

        # Two independent, top-aligned columns.
        # Folding Video must make Fragment move directly under it; the right
        # column must not inherit the height of Audio/Remux rows on the left.
        workspace = QHBoxLayout()
        workspace.setSpacing(8)

        left_col = QVBoxLayout()
        left_col.setSpacing(8)
        left_col.setAlignment(Qt.AlignTop)

        right_col = QVBoxLayout()
        right_col.setSpacing(8)
        right_col.setAlignment(Qt.AlignTop)

        workspace.addLayout(left_col, 5)
        workspace.addLayout(right_col, 7)
        root.addLayout(workspace)

        # 1. AUDIO
        self.audio_group = CollapsibleGroup()
        self.audio_group.setObjectName("sectionAudio")
        a = QVBoxLayout(self.audio_group)
        a.setContentsMargins(14, 13, 14, 12)
        a.setSpacing(8)

        self.audio_stream_label = QLabel()
        self.audio_stream_label.setObjectName("keyLabel")
        a.addWidget(self.audio_stream_label)
        self.audio_track_combo = ChevronComboBox()
        self.audio_track_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.audio_track_combo.setMinimumWidth(150)
        self.audio_track_combo.currentIndexChanged.connect(self.update_audio_containers)
        a.addWidget(self.audio_track_combo)
        audio_labels = QHBoxLayout()
        self.audio_format_label = QLabel()
        self.audio_variant_label = QLabel()
        audio_labels.addWidget(self.audio_format_label, 2)
        audio_labels.addWidget(self.audio_variant_label, 5)
        a.addLayout(audio_labels)
        audio_row = QHBoxLayout()
        self.audio_container_combo = ChevronComboBox()
        self.audio_container_combo.setMinimumWidth(92)
        self.audio_container_combo.currentIndexChanged.connect(self.update_audio_variants)
        self.audio_combo = ChevronComboBox()
        self.audio_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.audio_combo.setMinimumWidth(150)
        self.audio_combo.currentIndexChanged.connect(self.audio_selection_changed)
        audio_row.addWidget(self.audio_container_combo, 2)
        audio_row.addWidget(self.audio_combo, 5)
        a.addLayout(audio_row)

        checks = QVBoxLayout()
        checks.setSpacing(4)
        self.audio_meta = QCheckBox()
        self.audio_thumb = QCheckBox()
        self.audio_raw_aac_active = False
        self.audio_saved_options = (True, True)
        self.audio_chapter_preference = "none"
        self.audio_meta.setChecked(True)
        self.audio_thumb.setChecked(True)
        checks.addWidget(self.audio_meta)
        checks.addWidget(self.audio_thumb)
        a.addLayout(checks)

        self.audio_chapter_label = QLabel()
        self.audio_chapter_label.setObjectName("keyLabel")
        a.addWidget(self.audio_chapter_label)
        chapters_row = QHBoxLayout()
        chapters_row.setSpacing(10)
        self.ch_none = QRadioButton()
        self.ch_embed = QRadioButton()
        self.ch_split = QRadioButton()
        self.ch_none.setChecked(True)
        self.chapter_group = QButtonGroup(self)
        for rb in [self.ch_none, self.ch_embed, self.ch_split]:
            self.chapter_group.addButton(rb)
            rb.toggled.connect(self.audio_chapter_changed)
            chapters_row.addWidget(rb)
        chapters_row.addStretch(1)
        a.addLayout(chapters_row)

        manual_row = QHBoxLayout()
        manual_row.addWidget(QLabel("↳"))
        self.audio_manual_btn = QPushButton()
        self.audio_manual_btn.setObjectName("compactAction")
        self.audio_manual_btn.setMaximumWidth(235)
        self.audio_manual_btn.clicked.connect(self.edit_manual_chapters)
        manual_row.addWidget(self.audio_manual_btn)
        manual_row.addStretch(1)
        a.addLayout(manual_row)

        self.download_audio_btn = QPushButton()
        self.download_audio_btn.setObjectName("downloadButton")
        self.download_audio_btn.setEnabled(False)
        self.download_audio_btn.clicked.connect(self.download_audio)
        a.addWidget(self.download_audio_btn)
        left_col.addWidget(self.audio_group)

        # REMUX
        self.remux_group = CollapsibleGroup()
        self.remux_group.setObjectName("sectionRemux")
        remux_layout = QVBoxLayout(self.remux_group)
        remux_layout.setContentsMargins(14, 13, 14, 12)
        remux_layout.setSpacing(8)

        self.remux_drop = RemuxDropArea()
        self.remux_drop.setMinimumHeight(68)
        self.remux_drop.fileDropped.connect(self.set_remux_file)
        self.remux_drop.clicked.connect(self.choose_remux)
        remux_layout.addWidget(self.remux_drop)

        self.remux_input = QLineEdit()
        self.remux_input.setReadOnly(True)
        remux_layout.addWidget(self.remux_input)

        self.remux_info = QLabel()
        self.remux_info.setObjectName("remuxInfo")
        self.remux_info.setWordWrap(True)
        self.remux_info.setProperty("muted", True)
        remux_layout.addWidget(self.remux_info)

        remux_controls = QHBoxLayout()

        self.remux_choose = QPushButton()
        self.remux_choose.clicked.connect(self.choose_remux)

        self.remux_ext = ChevronComboBox()
        self.remux_targets = ["MKV", "MP4", "WebM", "OGG", "M4A"]
        self.remux_ext.addItems(self.remux_targets)
        self.remux_ext.setMinimumWidth(118)

        self.remux_button = QPushButton()
        self.remux_button.setObjectName("remuxActionButton")
        self.remux_button.setEnabled(False)
        self.remux_button.clicked.connect(self.remux)

        remux_controls.addWidget(self.remux_choose, 1)
        remux_controls.addWidget(self.remux_ext)
        remux_layout.addLayout(remux_controls)
        remux_layout.addWidget(self.remux_button)

        left_col.addWidget(self.remux_group)

        # VIDEO
        self.video_group = CollapsibleGroup()
        self.video_group.setObjectName("sectionVideo")
        v = QVBoxLayout(self.video_group)
        v.setContentsMargins(14, 13, 14, 12)
        v.setSpacing(8)

        self.container_label = QLabel()
        self.container_label.setObjectName("keyLabel")
        v.addWidget(self.container_label)
        container_row = QHBoxLayout()
        container_row.setSpacing(12)

        self.mp4 = QPushButton("MP4")
        self.mkv = QPushButton("MKV")
        self.webm = QPushButton("WebM")
        for button in (self.mp4, self.mkv, self.webm):
            button.setCheckable(True)
        self.mp4.setChecked(True)
        self.container_badges = {}

        self.video_container_group = QButtonGroup(self)
        for rb in [self.mp4, self.mkv, self.webm]:
            rb.setProperty("containerOption", True)
            rb.setMinimumWidth(78)
            rb.setMinimumHeight(28)
            self.video_container_group.addButton(rb)
            rb.toggled.connect(self.update_video_choices)
            column = QVBoxLayout()
            column.setSpacing(2)
            badge = QLabel("")
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedHeight(15)
            badge.setStyleSheet("color: #d9ad48; font-size: 11px; font-weight: 800;")
            self.container_badges[rb.text()] = badge
            column.addWidget(badge)
            column.addWidget(rb)
            container_row.addLayout(column)

        container_row.addStretch(1)
        v.addLayout(container_row)

        self.video_stream_label = QLabel()
        self.video_stream_label.setObjectName("keyLabel")
        v.addWidget(self.video_stream_label)
        quality_labels = QHBoxLayout()
        self.resolution_label = QLabel()
        self.variant_label = QLabel()
        quality_labels.addWidget(self.resolution_label, 2)
        quality_labels.addWidget(self.variant_label, 5)
        v.addLayout(quality_labels)
        quality_row = QHBoxLayout()
        self.resolution_combo = ChevronComboBox()
        self.resolution_combo.setMinimumWidth(110)
        self.resolution_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.resolution_combo.currentIndexChanged.connect(self.update_video_variants)
        self.video_combo = ChevronComboBox()
        self.video_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.video_combo.setMinimumWidth(150)
        self.video_combo.currentIndexChanged.connect(self.update_video_details)
        quality_row.addWidget(self.resolution_combo, 2)
        quality_row.addWidget(self.video_combo, 5)
        v.addLayout(quality_row)
        self.video_details = QLabel()
        self.video_details.setWordWrap(True)
        self.video_details.setProperty("muted", True)
        v.addWidget(self.video_details)

        self.video_audio_label = QLabel()
        self.video_audio_label.setObjectName("keyLabel")
        v.addWidget(self.video_audio_label)
        self.video_audio_combo = ChevronComboBox()
        self.video_audio_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.video_audio_combo.setMinimumWidth(150)
        v.addWidget(self.video_audio_combo)

        video_checks = QGridLayout()
        video_checks.setHorizontalSpacing(18)
        video_checks.setVerticalSpacing(4)
        self.video_meta = QCheckBox()
        self.video_thumb = QCheckBox()
        self.video_chapters = QCheckBox()
        self.video_meta.setChecked(True)
        self.video_thumb.setChecked(True)
        self.video_chapters.setChecked(True)
        video_checks.addWidget(self.video_meta, 0, 0)

        thumbnail_row = QHBoxLayout()
        thumbnail_row.setSpacing(7)
        thumbnail_row.addWidget(self.video_thumb)

        thumbnail_row.addStretch(1)

        video_checks.addLayout(thumbnail_row, 0, 1)
        video_checks.addWidget(self.video_chapters, 1, 0)
        v.addLayout(video_checks)

        manual_video_row = QHBoxLayout()
        manual_video_row.addWidget(QLabel("↳"))
        self.video_manual_btn = QPushButton()
        self.video_manual_btn.setObjectName("compactAction")
        self.video_manual_btn.setMaximumWidth(235)
        self.video_manual_btn.clicked.connect(self.edit_manual_chapters)
        manual_video_row.addWidget(self.video_manual_btn)
        manual_video_row.addStretch(1)
        v.addLayout(manual_video_row)

        self.download_video_btn = QPushButton()
        self.download_video_btn.setObjectName("downloadButton")
        self.download_video_btn.setEnabled(False)
        self.download_video_btn.clicked.connect(self.download_video)
        v.addWidget(self.download_video_btn)
        right_col.addWidget(self.video_group)

        # Fragment stays opposite Remux in the second grid row.
        self.fragment_group = CollapsibleGroup()
        self.fragment_group.setObjectName("sectionFragment")
        frag = QGridLayout(self.fragment_group)
        frag.setContentsMargins(12, 12, 12, 10)
        frag.setHorizontalSpacing(6)
        frag.setVerticalSpacing(6)
        self.fragment_enable = QCheckBox()
        self.fragment_from_label = QLabel()
        self.fragment_to_label = QLabel()

        def make_time_spin(maximum: int, value: int = 0):
            spin = QSpinBox()
            spin.setRange(0, maximum)
            spin.setValue(value)
            spin.setAlignment(Qt.AlignCenter)
            spin.setButtonSymbols(QSpinBox.NoButtons)
            spin.setFixedWidth(64)
            return spin

        self.fragment_from_h = make_time_spin(999, 0)
        self.fragment_from_m = make_time_spin(59, 0)
        self.fragment_from_s = make_time_spin(59, 0)
        self.fragment_to_h = make_time_spin(999, 0)
        self.fragment_to_m = make_time_spin(59, 20)
        self.fragment_to_s = make_time_spin(59, 0)

        frag.addWidget(self.fragment_enable, 0, 0, 1, 4)
        frag.addWidget(self.fragment_from_label, 1, 0)
        frag.addWidget(self.fragment_from_h, 1, 1)
        frag.addWidget(self.fragment_from_m, 1, 2)
        frag.addWidget(self.fragment_from_s, 1, 3)
        frag.addWidget(self.fragment_to_label, 2, 0)
        frag.addWidget(self.fragment_to_h, 2, 1)
        frag.addWidget(self.fragment_to_m, 2, 2)
        frag.addWidget(self.fragment_to_s, 2, 3)

        right_col.addWidget(self.fragment_group)

        # Overall progress is outside both columns. It stays global and
        # always starts below whichever column is currently taller.

        progress_card = QFrame()
        progress_card.setObjectName("commonProgressCard")
        progress_outer = QVBoxLayout(progress_card)
        progress_outer.setContentsMargins(11, 8, 11, 9)
        progress_outer.setSpacing(5)

        self.progress_title = QLabel()
        self.progress_title.setObjectName("commonProgressTitle")
        progress_outer.addWidget(self.progress_title)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(9)

        self.progress = OverallProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setMinimumHeight(34)

        progress_row.addWidget(self.progress, 1)
        progress_outer.addLayout(progress_row)

        root.addWidget(progress_card)

        # Journal card.
        self.log_group = CollapsibleGroup()
        self.log_group.setObjectName("journalCard")
        log_layout = QVBoxLayout(self.log_group)
        log_layout.setContentsMargins(12, 12, 12, 10)
        log_layout.setSpacing(6)
        log_header = QHBoxLayout()
        self.log_title = QLabel("Журнал")
        self.log_title.setObjectName("journalTitle")
        self.status_label = QLabel()
        self.status_label.setProperty("muted", True)
        log_header.addWidget(self.log_title)
        log_header.addStretch(1)
        log_header.addWidget(self.status_label)
        log_layout.addLayout(log_header)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(4000)
        self.log.setMinimumHeight(92)
        self.log.setMaximumHeight(112)
        log_layout.addWidget(self.log)
        root.addWidget(self.log_group)

        # Information lives in a modeless dialog; labels stay live while hidden.
        self.info_dialog = QDialog(self)
        self.info_dialog.resize(610, 270)
        info_layout = QVBoxLayout(self.info_dialog)
        self.app_version_label = QLabel(f"{APP_NAME} v{APP_VERSION}")
        self.connection_label = QLabel("Connection: —")
        self.external_label = QLabel("External IP: —")
        self.interface_label = QLabel("Interface: —")
        self.ytdlp_version = QLabel("yt-dlp: —")
        self.ffmpeg_version = QLabel("FFmpeg: —")
        self.credit = QLabel("GUI concept by VJ Ostrov • powered by yt-dlp + FFmpeg")
        for label in (self.app_version_label, self.connection_label, self.external_label,
                      self.interface_label, self.ytdlp_version, self.ffmpeg_version, self.credit):
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            info_layout.addWidget(label)
        self.credit.installEventFilter(self)
        self.credit_clicks = 0
        self.credit_click_time = 0.0
        self.easter_dialog = None
        self.refresh_net = QPushButton()
        self.refresh_net.clicked.connect(self.refresh_network_info)
        info_layout.addWidget(self.refresh_net)
        for button, mode in ((self.ch_none, "none"), (self.ch_embed, "embed"), (self.ch_split, "split")):
            button.clicked.connect(lambda _checked=False, m=mode: setattr(self, "audio_chapter_preference", m))
        self.help_buttons = []
        for label, target in (
            (self.url_label, self.analyze_btn), (self.output_label, self.output_edit),
            (self.audio_stream_label, self.audio_track_combo),
            (self.audio_format_label, self.audio_container_combo),
            (self.audio_variant_label, self.audio_combo),
            (self.audio_chapter_label, self.ch_embed),
            (self.audio_meta, self.audio_meta), (self.audio_thumb, self.audio_thumb),
            (self.container_label, self.mp4), (self.video_stream_label, self.resolution_combo),
            (self.resolution_label, self.resolution_combo), (self.variant_label, self.video_combo),
            (self.video_audio_label, self.video_audio_combo),
        ):
            button = attach_label_help(label, target)
            if button:
                self.help_buttons.append(button)
        for group, target in ((self.remux_group, self.remux_ext),):
            group.section_help = help_indicator(target, group)
            self.help_buttons.append(group.section_help)
        self.video_audio_combo.currentIndexChanged.connect(self.refresh_context_help)
        root.setAlignment(Qt.AlignTop)

    def apply_language(self):
        self.subtitle.setText(self.tr("subtitle"))
        self.skin_label.setText(self.tr("skin"))
        self.url_label.setText(self.tr("url"))
        self.analyze_btn.setText(self.tr("cancel") if self.analyze_worker else self.tr("analyze"))
        self.language_title.setText("Language:")
        if not self.current_info:
            self.video_title.setText(self.tr("not_analyzed"))

        self.audio_group.setTitle(
            "🎵  СКАЧАТЬ АУДИО" if self.lang == "RU" else "🎵  DOWNLOAD AUDIO"
        )
        self.audio_stream_label.setText("1. Аудиодорожка" if self.lang == "RU" else "1. Audio track")
        self.audio_format_label.setText("Формат файла" if self.lang == "RU" else "File format")
        self.audio_variant_label.setText("Вариант потока" if self.lang == "RU" else "Stream variant")
        self.audio_meta.setText(self.tr("metadata"))
        self.audio_thumb.setText(self.tr("thumbnail"))
        self.audio_chapter_label.setText(self.tr("chapters"))
        self.ch_none.setText(self.tr("chapters_none"))
        self.ch_embed.setText(self.tr("chapters_embed"))
        self.ch_split.setText(self.tr("chapters_split"))
        self.audio_manual_btn.setText(self.tr("manual_chapters"))
        self.download_audio_btn.setText(self.tr("download_audio"))

        self.video_group.setTitle(
            "🎬  СКАЧАТЬ ВИДЕО" if self.lang == "RU" else "🎬  DOWNLOAD VIDEO"
        )
        self.container_label.setText(self.tr("container"))
        self.video_stream_label.setText("2. Качество" if self.lang == "RU" else "2. Quality")
        self.resolution_label.setText("Разрешение" if self.lang == "RU" else "Resolution")
        self.variant_label.setText("Вариант потока" if self.lang == "RU" else "Stream variant")
        self.connection_btn.setText("Настройки маршрута подключения" if self.lang == "RU" else "Connection route settings")
        self.video_audio_label.setText(self.tr("video_audio"))
        self.video_meta.setText(self.tr("metadata"))
        self.video_thumb.setText(self.tr("thumbnail"))
        self.video_chapters.setText(self.tr("embed_chapters"))
        self.video_manual_btn.setText(self.tr("manual_chapters"))
        self.download_video_btn.setText(self.tr("download_video"))

        self.remux_group.setTitle(
            "📦  ПЕРЕПАКОВКА КОНТЕЙНЕРА"
            if self.lang == "RU"
            else "📦  CONTAINER REMUX"
        )
        self.remux_drop.set_texts(
            "Перетащи медиафайл сюда" if self.lang == "RU" else "Drop a media file here",
            "или нажми на область, чтобы выбрать файл"
            if self.lang == "RU"
            else "or click the area to choose a file",
        )
        self.remux_choose.setText(self.tr("choose"))
        self.remux_button.setText(self.tr("remux_btn"))
        if not self.remux_input.text().strip():
            self.remux_info.setText(
                "FFprobe определит кодеки и оставит только совместимые контейнеры."
                if self.lang == "RU"
                else "FFprobe will detect codecs and enable only compatible containers."
            )

        self.fragment_group.setTitle(
            "✂  СОХРАНИТЬ ФРАГМЕНТ"
            if self.lang == "RU"
            else "✂  SAVE FRAGMENT"
        )
        self.fragment_enable.setText(self.tr("use_range"))
        self.fragment_from_label.setText(self.tr("from"))
        self.fragment_to_label.setText(self.tr("to"))
        self.update_fragment_unit_suffixes()

        self.output_label.setText("📁  " + self.tr("output"))
        self.output_browse.setText(self.tr("browse"))
        self.output_open.setText(self.tr("open"))

        self.log_group.setTitle("ЖУРНАЛ СОБЫТИЙ" if self.lang == "RU" else "EVENT LOG")
        self.log_title.setText("Журнал" if self.lang == "RU" else "Journal")
        self.status_label.setText(self.tr("ready"))
        self.deps_header_btn.setText(
            "Зависимости / Обновления модулей" if self.lang == "RU"
            else "Dependencies / Module updates"
        )
        self.progress_title.setText(
            "⬇  ОБЩИЙ ПРОГРЕСС СКАЧИВАНИЯ"
            if self.lang == "RU"
            else "⬇  OVERALL DOWNLOAD PROGRESS"
        )

        self.info_dialog.setWindowTitle("Информация о программе" if self.lang == "RU" else "Application information")
        self.info_btn.setToolTip("Информация, версии модулей и сеть" if self.lang == "RU" else "Information, module versions and network")
        self.refresh_net.setText("↻ Обновить сетевую информацию" if self.lang == "RU" else "↻ Refresh network information")
        self.update_tooltips()

        if self.current_info:
            self.update_audio_choices()
            self.update_video_choices()

    def update_tooltips(self):
        ru = self.lang == "RU"

        def tip(widget, ru_text: str, en_text: str):
            widget.setToolTip(ru_text if ru else en_text)

        tip(
            self.url_edit,
            "Вставь ссылку на ролик YouTube для анализа доступных оригинальных потоков.",
            "Paste a YouTube URL to analyze the available original streams.",
        )
        tip(
            self.analyze_btn,
            "Получить название, превью и список доступных аудио/видеопотоков.",
            "Fetch the title, preview and available audio/video streams.",
        )
        tip(
            self.preview_label,
            "Превью ролика. Нажми правой кнопкой мыши → «Сохранить обложку».",
            "Video preview. Right-click → “Save thumbnail”.",
        )
        tip(
            self.output_edit,
            "Общая папка, куда будут сохраняться аудио, видео и обложки.",
            "Common folder for downloaded audio, video and thumbnails.",
        )
        tip(
            self.output_browse,
            "Выбрать папку сохранения.",
            "Choose the output folder.",
        )
        tip(
            self.output_open,
            "Открыть текущую папку сохранения в файловом менеджере.",
            "Open the current output folder in the file manager.",
        )
        tip(
            self.deps_header_btn,
            "Проверка и обновление yt-dlp, Deno, FFmpeg/FFprobe и состояния Python runtime.",
            "Check/update yt-dlp, Deno, FFmpeg/FFprobe and inspect the Python runtime.",
        )
        tip(
            self.language,
            "Язык интерфейса приложения.",
            "Application interface language.",
        )
        tip(
            self.skin_combo,
            "Выбрать оформление интерфейса.",
            "Choose the interface skin.",
        )

        tip(
            self.audio_combo,
            "Выбери исходный аудиопоток и контейнер. Перекодирование не выполняется.",
            "Choose the original audio stream and output container. No transcoding is used.",
        )
        tip(
            self.audio_meta,
            "Добавить метаданные ролика в аудиофайл.",
            "Embed video metadata into the audio file.",
        )
        tip(
            self.audio_thumb,
            "Добавить обложку ролика внутрь файла, если контейнер это поддерживает.",
            "Embed the video thumbnail when the selected container supports it.",
        )
        tip(
            self.ch_none,
            "Не использовать главы.",
            "Do not use chapters.",
        )
        tip(
            self.ch_embed,
            "Записать главы внутрь файла без разделения на отдельные треки.",
            "Embed chapters into the file without splitting it.",
        )
        tip(
            self.ch_split,
            "Разрезать скачанный аудиофайл на отдельные треки по главам.",
            "Split the downloaded audio into separate tracks by chapters.",
        )
        tip(
            self.audio_manual_btn,
            "Ввести собственные таймкоды глав вручную.",
            "Enter custom chapter timestamps manually.",
        )
        tip(
            self.download_audio_btn,
            "Скачать выбранный оригинальный аудиопоток.",
            "Download the selected original audio stream.",
        )

        for radio, ru_name, en_name in [
            (self.mp4, "MP4", "MP4"),
            (self.mkv, "MKV", "MKV"),
            (self.webm, "WebM", "WebM"),
        ]:
            tip(
                radio,
                f"Контейнер {ru_name}. Список потоков ниже автоматически фильтруется по совместимости.",
                f"{en_name} container. The stream list below is filtered for compatibility.",
            )

        tip(
            self.video_combo,
            "Выбери оригинальный видеопоток. Кодек и разрешение берутся напрямую с YouTube.",
            "Choose the original video stream. Codec and resolution come directly from YouTube.",
        )
        tip(
            self.video_audio_combo,
            "Выбери совместимый аудиопоток для объединения с видео.",
            "Choose a compatible audio stream to mux with the video.",
        )
        tip(
            self.video_meta,
            "Добавить метаданные YouTube в готовый видеофайл.",
            "Embed YouTube metadata into the final video file.",
        )
        tip(
            self.video_thumb,
            "Встроить thumbnail внутрь видеофайла.",
            "Embed the thumbnail into the video file.",
        )
        tip(
            self.video_chapters,
            "Встроить главы YouTube или введённые вручную главы.",
            "Embed YouTube chapters or manually entered chapters.",
        )
        tip(
            self.video_manual_btn,
            "Ввести собственные главы для видео.",
            "Enter custom chapters for the video.",
        )
        tip(
            self.download_video_btn,
            "Скачать выбранные видео+аудио потоки и объединить их без перекодирования.",
            "Download the selected video+audio streams and mux them without transcoding.",
        )

        tip(
            self.fragment_enable,
            "Сохранить только указанный временной диапазон. Потоки не перекодируются.",
            "Keep only the selected time range. Streams are not transcoded.",
        )
        for widget in (
            self.fragment_from_h, self.fragment_from_m, self.fragment_from_s,
            self.fragment_to_h, self.fragment_to_m, self.fragment_to_s,
        ):
            tip(
                widget,
                "Время начала/окончания фрагмента: часы, минуты или секунды.",
                "Fragment start/end time: hours, minutes or seconds.",
            )

        tip(
            self.remux_drop,
            "Перетащи сюда медиафайл. FFprobe определит кодеки и покажет только совместимые контейнеры.",
            "Drop a media file here. FFprobe detects its codecs and enables only compatible containers.",
        )
        tip(
            self.remux_ext,
            "Целевой контейнер. Несовместимые варианты отключаются автоматически.",
            "Target container. Incompatible options are disabled automatically.",
        )
        tip(
            self.remux_button,
            "Перепаковать файл через FFmpeg с -c copy, без перекодирования.",
            "Remux with FFmpeg using -c copy, without transcoding.",
        )

        tip(
            self.connection_btn,
            "Настройки маршрута подключения: Auto, Direct/TUN, System Proxy или ручной proxy.",
            "Connection route settings: Auto, Direct/TUN, System Proxy or manual proxy.",
        )
        tip(
            self.refresh_net,
            "Обновить внешний IP и сетевую информацию.",
            "Refresh external IP and network information.",
        )

        for group in (
            self.audio_group,
            self.video_group,
            self.remux_group,
            self.fragment_group,
            self.log_group,
        ):
            group.collapse_button.setToolTip(
                "Свернуть / развернуть раздел"
                if ru
                else "Collapse / expand section"
            )

        self.refresh_context_help()

    def refresh_context_help(self, *_):
        if not hasattr(self, "help_buttons"):
            return
        ru = self.lang == "RU"
        def tip(widget, russian, english):
            widget.setToolTip(russian if ru else english)
        entry = self.selected_audio_entry()
        ext = entry[1] if entry else ""
        raw = ext == ".aac"
        tip(self.audio_track_combo, "Выбери оригинал или дубляж по языку.", "Choose the original track or a dub by language.")
        tip(self.audio_container_combo, "OPUS → .opus / .ogg; AAC → .m4a / .aac. Без перекодирования.", "OPUS → .opus / .ogg; AAC → .m4a / .aac. No transcoding.")
        tip(self.audio_combo, "Битрейт и частота исходного потока. DRC — сжатый динамический диапазон.", "Source bitrate and sample rate. DRC means compressed dynamic range.")
        tip(self.audio_meta, "В .aac/ADTS метаданные не встраиваются; выбери M4A." if raw else "Добавить название, автора и другие метаданные.", "AAC/ADTS cannot embed tags; choose M4A." if raw else "Add title, author and other metadata.")
        tip(self.audio_thumb, "В .aac/ADTS обложка не встраивается; выбери M4A." if raw else "Встроить обложку в аудиофайл.", "AAC/ADTS cannot embed a cover; choose M4A." if raw else "Embed the cover in the audio file.")
        tip(self.ch_embed, "Встроенные главы доступны только в M4A. Для Opus/OGG/AAC используй разделение на треки.", "Embedded chapters require M4A. For Opus/OGG/AAC, split into tracks.")
        tip(self.audio_manual_btn, "Сначала выбери встраивание глав или разделение на треки." if self.ch_none.isChecked() else "Введи таймкоды: 00:00 Название.", "First select chapter embedding or track splitting." if self.ch_none.isChecked() else "Enter timestamps: 00:00 Title.")
        tip(self.download_audio_btn, "Сначала проанализируй ссылку и выбери аудиопоток." if not entry else "Скачать выбранную дорожку без перекодирования.", "Analyze a link and select an audio stream first." if not entry else "Download the selected track without transcoding.")
        tip(self.mp4, "MP4: H.264/AV1 + AAC. Другие потоки доступны в MKV/WebM.", "MP4: H.264/AV1 + AAC. Other streams are available in MKV/WebM.")
        tip(self.mkv, "MKV: H.264/VP9/AV1 + AAC/Opus.", "MKV: H.264/VP9/AV1 + AAC/Opus.")
        tip(self.webm, "WebM: VP9/AV1 + Opus. H.264/AAC несовместимы.", "WebM: VP9/AV1 + Opus. H.264/AAC are incompatible.")
        tip(self.resolution_combo, "Показаны разрешения, совместимые с выбранным контейнером." if self.video_formats else "Сначала проанализируй ссылку.", "Resolutions compatible with the selected container." if self.video_formats else "Analyze a link first.")
        tip(self.video_combo, "Варианты выбранного разрешения: кодек, FPS, битрейт и размер.", "Variants for this resolution: codec, FPS, bitrate and size.")
        original_blocked = bool(self.filtered_video_audio) and self.selected_video_audio() is None
        tip(self.video_audio_combo, "Оригинал несовместим с контейнером: смени контейнер или явно выбери дубляж." if original_blocked else "Только совместимое аудио; оригинал имеет приоритет.", "Original audio is incompatible: change container or explicitly choose a dub." if original_blocked else "Compatible audio only; original audio is preferred.")
        missing = not self.selected_video_entry() or not self.selected_video_audio()
        tip(self.download_video_btn, "Нужны совместимые видео и аудио: проанализируй ссылку и проверь контейнер." if missing else "Скачать выбранные видео и аудио без перекодирования.", "Compatible video and audio required: analyze a link and check the container." if missing else "Download the selected video and audio without transcoding.")
        tip(self.remux_ext, "✓ — совместимо без перекодирования; отключённые варианты не поддерживают исходные кодеки.", "✓ means compatible without transcoding; disabled containers do not support the source codecs.")
        tip(self.remux_button, "Выбери файл и совместимый контейнер; перепаковка сохраняет исходные кодеки.", "Select a file and compatible container; remuxing keeps the source codecs.")
        tip(self.log, "Ход операции и причины ошибок.", "Operation progress and error details.")
        for button in self.help_buttons:
            button.setToolTip(button.help_target.toolTip())

    def startup_dependency_check(self):
        report = dependency_report()
        required_ok = (
            report["yt_dlp"]["ok"]
            and report["yt_dlp"].get("external")
            and report["ffmpeg"]["ok"]
            and report["ffprobe"]["ok"]
            and report["deno"]["ok"]
        )
        if required_ok:
            return
        dlg = DependencyDialog(self, self.lang)
        self.apply_theme()
        result = dlg.exec()
        self.refresh_dependency_labels()
        if result != QDialog.Accepted:
            self.close()

    def change_language(self, lang: str):
        self.lang = lang
        self.settings["language"] = lang
        self.save_settings()
        self.apply_language()

    def change_skin(self, skin: str):
        if skin not in SKIN_ORDER:
            return
        self.skin = skin
        self.theme = "Light" if skin in {"Classic Light", "Windows 98 Light"} else "Dark"
        self.settings["skin"] = self.skin
        self.settings["theme"] = self.theme
        self.save_settings()
        self.apply_theme()

    def toggle_theme(self):
        # Compatibility helper for older code/settings.
        target = "Graphite Core" if self.theme != "Dark" else "Classic Light"
        self.skin_combo.setCurrentText(target)


    def apply_theme(self):
        skin = get_skin(self.skin)
        app = QApplication.instance()
        palette = QPalette()

        palette.setColor(QPalette.Window, QColor(skin["window"]))
        palette.setColor(QPalette.WindowText, QColor(skin["text"]))
        palette.setColor(QPalette.Base, QColor(skin["field"]))
        palette.setColor(QPalette.AlternateBase, QColor(skin["group"]))
        palette.setColor(QPalette.Text, QColor(skin["text"]))
        palette.setColor(QPalette.Button, QColor(skin["button"]))
        palette.setColor(QPalette.ButtonText, QColor(skin["text"]))
        palette.setColor(QPalette.Highlight, QColor(skin["accent"]))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        app.setPalette(palette)

        radius = int(skin["radius"])
        radius_small = max(0, radius - 2)

        stylesheet = f"""
            QWidget {{
                color: {skin["text"]};
            }}

            QMainWindow, QDialog, QScrollArea > QWidget > QWidget {{
                background-color: {skin["window"]};
            }}

            QLabel#title {{
                color: {skin["accent_alt"]};
                font-size: 19px;
                font-weight: 700;
            }}
            QLabel#videoTitle {{
                color: {skin["text"]};
                font-size: 13px;
                font-weight: 700;
                padding: 6px 2px;
            }}
            QLabel#keyLabel {{
                color: {skin["text"]};
                font-size: 12px;
                font-weight: 750;
                padding-top: 2px;
                padding-bottom: 1px;
            }}

            QFrame#appHeader {{
                background-color: {skin["field"]};
                border: 1px solid {skin["border"]};
                border-radius: {radius}px;
            }}
            QFrame#sourceCard,
            QToolButton#helpIndicator {{
                color: {skin["muted"]};
                background: transparent;
                border: 1px solid {skin["muted"]};
                border-radius: 9px;
                padding: 0;
                font-size: 12px;
                font-weight: 600;
            }}
            QToolButton#helpIndicator:hover {{
                color: {skin["accent_alt"]};
                border: 1px solid {skin["accent_alt"]};
            }}
            QLabel#networkQuestion {{
                font-size: 20px;
                font-weight: 800;
                color: {skin["accent_alt"]};
                padding: 4px 0 10px 0;
            }}
            QLabel#networkSection {{
                font-size: 12px;
                font-weight: 800;
                color: {skin["accent_alt"]};
                border-bottom: 1px solid {skin["border"]};
                padding: 6px 0 5px 0;
            }}
            QPlainTextEdit#networkResult {{
                border: 1px solid {skin["accent"]};
                padding: 6px;
            }}
            QFrame#footerBar {{
                background-color: {skin["group"]};
                border: 1px solid {skin["border"]};
                border-radius: {radius}px;
            }}
            QFrame#commonProgressCard {{
                background-color: {skin["field"]};
                border: 2px solid {skin["accent"]};
                border-radius: {radius}px;
            }}
            QLabel#commonProgressTitle {{
                color: {skin["accent_alt"]};
                font-size: 11px;
                font-weight: 800;
            }}

            QLabel[muted="true"] {{
                color: {skin["muted"]};
            }}
            QLabel#dependencyStatus {{
                padding: 3px 0px;
            }}

            QGroupBox {{
                background-color: {skin["group"]};
                font-weight: 700;
                border: 2px solid {skin["border"]};
                border-radius: {radius}px;
                margin-top: 13px;
                padding: 13px 10px 10px 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 7px;
                color: {skin["accent_alt"]};
                background-color: {skin["group"]};
            }}
            QGroupBox[collapsible="true"]::title {{
                left: 42px;
            }}

            QGroupBox#sectionAudio::title,
            QGroupBox#sectionVideo::title {{
                color: {skin["text"]};
                font-size: 13px;
                font-weight: 750;
            }}
            QGroupBox#sectionRemux::title {{
                color: #c67cff;
                font-size: 13px;
                font-weight: 750;
            }}
            QLabel#journalTitle {{
                color: {skin["text"]};
                font-size: 12px;
                font-weight: 700;
            }}
            QLabel#remuxInfo {{
                color: {skin["muted"]};
                padding: 2px 1px;
            }}

            QLineEdit,
            QPlainTextEdit,
            QComboBox,
            QSpinBox,
            QAbstractItemView {{
                background-color: {skin["field"]};
                color: {skin["text"]};
                border: 1px solid {skin["border"]};
                border-radius: {radius_small}px;
                padding: 4px 6px;
                selection-background-color: {skin["accent"]};
                selection-color: #ffffff;
            }}
            QLineEdit:focus,
            QPlainTextEdit:focus,
            QComboBox:focus,
            QSpinBox:focus {{
                border: 1px solid {skin["accent"]};
            }}
            QComboBox::drop-down {{
                border-left: 1px solid {skin["border"]};
                min-width: 27px;
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}
            QLabel#comboChevron {{
                color: {skin["accent_alt"]};
                background: transparent;
                border: none;
                font-weight: 800;
                font-size: 15px;
            }}

            QPushButton,
            QToolButton {{
                background-color: {skin["button"]};
                color: {skin["text"]};
                border: 1px solid {skin["accent"]};
                border-radius: {radius_small}px;
                padding: 6px 11px;
                font-weight: 600;
            }}
            QPushButton:hover,
            QToolButton:hover {{
                background-color: {skin["button_hover"]};
                border: 1px solid {skin["accent_alt"]};
            }}
            QPushButton:pressed,
            QToolButton:pressed {{
                background-color: {skin["field"]};
            }}
            QPushButton:disabled,
            QToolButton:disabled {{
                color: {skin["disabled"]};
                border-color: {skin["border"]};
                background-color: {skin["group"]};
            }}

            QPushButton#primaryButton {{
                background-color: {skin["accent"]};
                color: #ffffff;
                border: 1px solid {skin["accent_alt"]};
                font-weight: 700;
                padding: 7px 14px;
            }}
            QPushButton#primaryButton:hover {{
                background-color: {skin["accent_alt"]};
                border: 1px solid {skin["accent_alt"]};
            }}
            QPushButton#primaryButton:pressed {{
                background-color: {skin["button_hover"]};
            }}

            QPushButton#downloadButton {{
                background-color: #238a55;
                color: #ffffff;
                border: 1px solid #4fd18a;
                font-weight: 750;
                padding: 8px 13px;
            }}
            QPushButton#downloadButton:hover {{
                background-color: #2cab69;
                border-color: #77e6aa;
            }}
            QPushButton#downloadButton:pressed {{
                background-color: #1b7045;
                border-color: #41b979;
            }}
            QPushButton#downloadButton:disabled {{
                background-color: {skin["group"]};
                color: {skin["disabled"]};
                border-color: {skin["border"]};
            }}
            QPushButton#remuxActionButton {{
                background-color: #7540a8;
                color: #ffffff;
                border: 1px solid #b36de5;
                font-weight: 750;
                padding: 8px 13px;
            }}
            QPushButton#remuxActionButton:hover {{
                background-color: #8d4fc2;
                border-color: #cf8cff;
            }}
            QPushButton#remuxActionButton:disabled {{
                background-color: {skin["group"]};
                color: {skin["disabled"]};
                border-color: {skin["border"]};
            }}
            QPushButton#headerButton {{
                font-size: 11px;
                padding: 6px 7px;
                font-weight: 600;
            }}

            QFrame#remuxDropArea {{
                background-color: {skin["field"]};
                border: 2px dashed {skin["border"]};
                border-radius: {radius}px;
            }}
            QFrame#remuxDropArea:hover {{
                border: 2px dashed {skin["accent"]};
                background-color: {skin["group"]};
            }}
            QFrame#remuxDropArea[dragActive="true"] {{
                border: 2px solid {skin["accent_alt"]};
                background-color: {skin["button_hover"]};
            }}
            QLabel#remuxDropTitle {{
                color: {skin["accent_alt"]};
                font-weight: 700;
                font-size: 12px;
            }}
            QLabel#remuxDropHint {{
                color: {skin["muted"]};
                font-size: 10px;
            }}

            QLabel#videoPreview {{
                background-color: {skin["field"]};
                color: {skin["accent_alt"]};
                border: 1px solid {skin["border"]};
                border-radius: {radius_small}px;
                font-size: 20px;
                font-weight: 700;
            }}
            QLabel#videoPreview:hover {{
                border: 1px solid {skin["accent"]};
            }}
            QToolButton#sectionCollapseButton {{
                background-color: {skin["group"]};
                color: {skin["text"]};
                border: none;
                padding: 0px;
                font-size: 20px;
                font-weight: 800;
            }}
            QToolButton#sectionCollapseButton:hover {{
                color: {skin["accent_alt"]};
                background-color: {skin["group"]};
                border: none;
            }}

            QProgressBar {{
                color: {skin["text"]};
                border: 1px solid {skin["border"]};
                border-radius: {radius_small}px;
                background-color: {skin["field"]};
                text-align: center;
                min-height: 28px;
            }}
            QProgressBar::chunk {{
                background-color: {skin["accent"]};
                border-radius: {radius_small}px;
            }}
            QLabel#progressSpeedLabel {{
                color: {skin["text"]};
                background: transparent;
                border: none;
                padding: 0px;
                font-size: 10px;
                font-weight: 700;
            }}
            QFrame#successToast {{
                background-color: #1f7a4c;
                border: 1px solid #55d494;
                border-radius: 7px;
            }}
            QLabel#successToastIcon {{
                color: #ffffff;
                font-size: 18px;
                font-weight: 900;
            }}
            QLabel#successToastText {{
                color: #ffffff;
                font-size: 11px;
                font-weight: 650;
            }}

            QRadioButton,
            QCheckBox {{
                spacing: 6px;
            }}
            QPushButton[containerOption="true"] {{
                font-size: 12px;
                font-weight: 700;
                padding: 4px 7px;
            }}
            QPushButton[containerOption="true"]:checked {{
                color: {skin["accent_alt"]};
                background-color: {skin["field"]};
                border: 2px solid {skin["accent_alt"]};
            }}

            QPushButton#compactAction {{
                padding: 4px 9px;
                font-weight: 600;
            }}
            QRadioButton:checked,
            QCheckBox:checked {{
                color: {skin["accent_alt"]};
            }}

            QScrollBar:vertical {{
                background: {skin["field"]};
                width: 13px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {skin["border"]};
                min-height: 28px;
                border-radius: {radius_small}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {skin["accent"]};
            }}
        """

        # Application-level style makes modal dependency/network dialogs use
        # the same skin as the main window.
        app.setStyleSheet(stylesheet)


    def save_settings(self):
        self.settings["language"] = self.lang
        self.settings["theme"] = self.theme
        self.settings["skin"] = self.skin
        self.settings["output_folder"] = self.output_edit.text().strip()
        save_settings(self.settings)

    def append_log(self, text: str):
        if not text:
            return
        # Suppress the spammiest raw percentage lines after parsing them.
        pct, _ = parse_progress(text)
        if pct is not None and text.startswith("[download]"):
            return
        self.log.appendPlainText(text)

    def show_error(self, message: str):
        if is_youtube_bot_error(message):
            message = bot_error_help(self.lang)
        QMessageBox.critical(self, APP_NAME, message)

    def show_info(self, message: str):
        QMessageBox.information(self, APP_NAME, message)

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("output"), self.output_edit.text().strip() or str(Path.home())
        )
        if folder:
            self.output_edit.setText(folder)
            self.save_settings()

    def open_output(self):
        try:
            open_folder(Path(self.output_edit.text().strip()))
        except Exception as exc:
            self.show_error(str(exc))

    def edit_manual_chapters(self):
        dlg = ManualChaptersDialog(self, self.manual_chapters_text, self.lang)
        if dlg.exec() == QDialog.Accepted:
            self.manual_chapters_text = dlg.editor.toPlainText().strip()

    def update_fragment_unit_suffixes(self):
        hour = " " + self.tr("hour_short")
        minute = " " + self.tr("minute_short")
        second = " " + self.tr("second_short")

        for spin in (self.fragment_from_h, self.fragment_to_h):
            spin.setSuffix(hour)
        for spin in (self.fragment_from_m, self.fragment_to_m):
            spin.setSuffix(minute)
        for spin in (self.fragment_from_s, self.fragment_to_s):
            spin.setSuffix(second)

    def fragment_timecode(self, prefix: str) -> str:
        if prefix == "from":
            h, m, s = (
                self.fragment_from_h.value(),
                self.fragment_from_m.value(),
                self.fragment_from_s.value(),
            )
        else:
            h, m, s = (
                self.fragment_to_h.value(),
                self.fragment_to_m.value(),
                self.fragment_to_s.value(),
            )
        return f"{h:02d}:{m:02d}:{s:02d}"

    def fragment_filename_stamp(self) -> str:
        # ':' is not allowed in Windows filenames.
        a = self.fragment_timecode("from").replace(":", "-")
        b = self.fragment_timecode("to").replace(":", "-")
        return f"{a}_{b}"

    def fragment_range(self):
        if not self.fragment_enable.isChecked():
            return None

        a_seconds = (
            self.fragment_from_h.value() * 3600
            + self.fragment_from_m.value() * 60
            + self.fragment_from_s.value()
        )
        b_seconds = (
            self.fragment_to_h.value() * 3600
            + self.fragment_to_m.value() * 60
            + self.fragment_to_s.value()
        )

        if b_seconds <= a_seconds:
            self.show_error(
                "Значение «До» должно быть больше значения «С»."
                if self.lang == "RU"
                else '"To" must be greater than "From".'
            )
            return False

        return a_seconds * 1000, b_seconds * 1000

    def show_preview_context_menu(self, pos):
        if not self.current_info:
            return

        menu = QMenu(self)
        save_action = menu.addAction(
            "💾  Сохранить обложку"
            if self.lang == "RU"
            else "💾  Save thumbnail"
        )
        chosen = menu.exec(self.preview_label.mapToGlobal(pos))
        if chosen == save_action:
            self.download_thumbnail()

    def clear_video_preview(self):
        self.preview_generation += 1
        for worker in self.preview_workers:
            worker.requestInterruption()
        if hasattr(self, "preview_label"):
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("▶")

    def load_video_preview(self, info: dict):
        self.clear_video_preview()
        primary = str(info.get("thumbnail") or "").strip()
        items = [t for t in (info.get("thumbnails") or []) if isinstance(t, dict) and t.get("url")]
        # JPEG first: portable decoding, then other formats. Retain fallback URLs.
        items.sort(key=lambda t: (".jpg" not in str(t["url"]).lower() and ".jpeg" not in str(t["url"]).lower(), -float(t.get("width") or 0)))
        urls = []
        for url in [primary] + [str(t["url"]) for t in items]:
            if url.startswith(("https://", "http://")) and url not in urls:
                urls.append(url)
        if not urls:
            return
        resolved = resolve_proxy(self.settings.get("network_mode", "Auto"), self.settings.get("manual_proxy", ""))
        if not resolved.ok:
            self.preview_failed(resolved.detail)
            return
        self.preview_label.setText("…")
        generation = self.preview_generation
        worker = PreviewWorker(urls, resolved.proxy, self.effective_certificate_mode(), self)
        self.preview_worker = worker
        self.preview_workers.append(worker)
        worker.loaded.connect(lambda data, g=generation: self.preview_loaded(data) if g == self.preview_generation else None)
        worker.failed.connect(lambda error, g=generation: self.preview_failed(error) if g == self.preview_generation else None)
        worker.finished.connect(lambda w=worker: self.preview_worker_finished(w))
        worker.start()

    def preview_worker_finished(self, worker):
        if worker in self.preview_workers:
            self.preview_workers.remove(worker)
        if self.preview_worker is worker:
            self.preview_worker = None
        worker.deleteLater()

    def preview_loaded(self, data: bytes):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            pixmap = pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setText("")
            self.preview_label.setPixmap(pixmap)
        else:
            self.preview_failed("unsupported image format")

    def preview_failed(self, error: str):
        self.clear_video_preview()
        message = "Превью обложки: " if self.lang == "RU" else "Thumbnail preview: "
        self.append_log(message + str(error)[-600:])

    def update_connection_label(self):
        resolved = resolve_proxy(
            self.settings.get("network_mode", "Auto"),
            self.settings.get("manual_proxy", ""),
        )
        cert_suffix = ""
        if self.session_certificate_override == "Insecure":
            cert_suffix = " • TLS verification OFF"

        if resolved.proxy:
            self.connection_label.setText(
                f"Connection: {resolved.name} • {resolved.detail}{cert_suffix}"
            )
        else:
            self.connection_label.setText(
                f"Connection: {resolved.name}{cert_suffix}"
            )

    def eventFilter(self, watched, event):
        if watched is getattr(self, "credit", None) and event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            now = time.monotonic()
            self.credit_clicks = self.credit_clicks + 1 if now - self.credit_click_time < 1.5 else 1
            self.credit_click_time = now
            if self.credit_clicks >= 3:
                self.credit_clicks = 0
                self.show_ostrov_easter_egg()
        return super().eventFilter(watched, event)

    def show_ostrov_easter_egg(self):
        if self.easter_dialog is None:
            self.easter_dialog = QDialog(self.info_dialog)
            self.easter_dialog.setWindowTitle("VJ OSTROV — ORIGINAL MIX")
            self.easter_dialog.setFixedSize(350, 180)
            self.easter_dialog.setStyleSheet("QDialog { background: #171b1a; border: 2px solid #687868; } QLabel { color: #a4ff36; background: transparent; font-family: monospace; font-weight: bold; }")
            layout = QVBoxLayout(self.easter_dialog)
            title = QLabel("VJ OSTROV  //  ORIGINAL MIX")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
            self.easter_equalizer = OstrovEqualizer()
            layout.addWidget(self.easter_equalizer)
            status = QLabel("100% COPY          0% TRANSCODE")
            status.setAlignment(Qt.AlignCenter)
            layout.addWidget(status)
        self.easter_dialog.show()
        self.easter_dialog.raise_()
        self.easter_dialog.activateWindow()

    def show_app_info(self):
        self.info_dialog.setStyleSheet(self.styleSheet())
        self.info_dialog.show()
        self.info_dialog.raise_()
        self.info_dialog.activateWindow()

    def show_network_settings(self):
        dlg = NetworkDialog(self, self.settings)
        self.apply_theme()
        if dlg.exec() == QDialog.Accepted:
            self.settings["network_mode"] = dlg.mode()
            self.settings["manual_proxy"] = dlg.proxy_edit.text().strip()
            self.settings["certificate_mode"] = dlg.certificate_mode()
            self.settings.update(dlg.cookie_settings())
            self.session_certificate_override = None
            self.save_settings()
            self.update_connection_label()
            self.refresh_network_info()

    def refresh_network_info(self):
        if self.network_worker and self.network_worker.isRunning():
            return
        resolved = resolve_proxy(
            self.settings.get("network_mode", "Auto"),
            self.settings.get("manual_proxy", ""),
        )
        self.external_label.setText("External IP: …")
        self.interface_label.setText("Interface: …")
        self.network_worker = NetworkWorker(resolved.proxy if resolved.ok else "")
        self.network_worker.done.connect(self.network_info_done)
        self.network_worker.start()

    def network_info_done(self, ip: str, interface: str):
        self.external_label.setText(f"External IP: {ip}")
        self.interface_label.setText(f"Interface: {interface}")

    def ytdlp_base(self) -> list[str]:
        cmd = ytdlp_command()
        if not cmd:
            self.show_error(
                "yt-dlp не найден.\n\nЗапусти START-скрипт ещё раз или выполни:\n"
                "python -m pip install -U yt-dlp"
            )
        if cmd:
            try:
                cmd += cookie_args(self.settings)
            except ValueError as exc:
                self.show_error(str(exc))
                return []
        return cmd

    def effective_certificate_mode(self) -> str:
        return str(
            self.session_certificate_override
            or self.settings.get("certificate_mode", "Auto")
            or "Auto"
        )

    def current_certificate_env(self) -> dict[str, str]:
        return certificate_process_env(self.effective_certificate_mode())

    def offer_insecure_ssl_retry(self, *, analysis_url: str = "") -> bool:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(
            "Проблема HTTPS-сертификата"
            if self.lang == "RU"
            else "HTTPS certificate problem"
        )
        box.setText(
            (
                "Не удалось проверить сертификат YouTube даже через доступные "
                "хранилища сертификатов.\n\n"
                "Это часто бывает при VPN, HTTPS-фильтрации или локальном proxy.\n\n"
                "Повторить БЕЗ проверки сертификата только до закрытия программы?\n"
                "Соединение будет зашифровано, но подлинность сервера проверяться не будет."
            )
            if self.lang == "RU"
            else (
                "The YouTube certificate could not be validated using the available "
                "certificate stores.\n\n"
                "This often happens with VPNs, HTTPS filtering or local proxies.\n\n"
                "Retry WITHOUT certificate verification for this app session only?\n"
                "Traffic remains encrypted, but server authenticity will not be verified."
            )
        )

        retry_btn = box.addButton(
            "Повторить без проверки SSL"
            if self.lang == "RU"
            else "Retry without SSL verification",
            QMessageBox.AcceptRole,
        )
        cancel_btn = box.addButton(
            self.tr("cancel"),
            QMessageBox.RejectRole,
        )
        box.setDefaultButton(cancel_btn)
        box.exec()

        if box.clickedButton() == retry_btn:
            self.session_certificate_override = "Insecure"
            self.update_connection_label()
            if analysis_url:
                self.pending_ssl_retry_url = analysis_url
            return True

        return False

    def network_args(self) -> list[str]:
        args, resolved = proxy_args(
            self.settings.get("network_mode", "Auto"),
            self.settings.get("manual_proxy", ""),
        )
        if not resolved.ok:
            self.show_error(resolved.detail)
            return []
        return args

    def analyze(self):
        if self.analyze_worker and self.analyze_worker.isRunning():
            self.analyze_worker.cancel()
            return

        url = self.url_edit.text().strip()
        if not is_valid_youtube_url(url):
            self.show_error("Укажи корректную ссылку YouTube.")
            return

        base = self.ytdlp_base()
        if not base:
            return

        net_args, resolved = proxy_args(
            self.settings.get("network_mode", "Auto"),
            self.settings.get("manual_proxy", ""),
        )
        if not resolved.ok:
            self.show_error(resolved.detail)
            return

        cert_mode = self.effective_certificate_mode()
        cmd = base + net_args + ytdlp_common_args(cert_mode) + [
            "--socket-timeout", "6",
            "--extractor-retries", "1",
            "-J",
            url,
        ]

        self.log.clear()
        self.clear_video_preview()
        self.append_log("> " + " ".join(f'"{x}"' if " " in x else x for x in cmd))
        for badge in self.container_badges.values():
            badge.setText("")
        self.video_title.setText("Анализирую..." if self.lang == "RU" else "Analyzing...")
        self.analyze_btn.setText(self.tr("cancel"))
        self.download_audio_btn.setEnabled(False)
        self.download_video_btn.setEnabled(False)

        self.analyze_worker = CaptureWorker(
            cmd,
            app_dir(),
            timeout=60 if self.settings.get("cookies_mode", "None") != "None" else 20,
            extra_env=certificate_process_env(cert_mode),
        )
        self.analyze_worker.completed.connect(self.analyze_completed)
        self.analyze_worker.failed.connect(self.analyze_failed)
        self.analyze_worker.finished.connect(self.analyze_finished)
        self.analyze_worker.start()

    def analyze_finished(self):
        self.analyze_worker = None
        self.analyze_btn.setText(self.tr("analyze"))

        if self.pending_ssl_retry_url:
            retry_url = self.pending_ssl_retry_url
            self.pending_ssl_retry_url = None
            self.url_edit.setText(retry_url)
            QTimer.singleShot(0, self.analyze)

    def analyze_failed(self, error: str):
        self.show_error(error)
        self.clear_video_preview()
        self.video_title.setText(self.tr("not_analyzed"))

    def analyze_completed(self, code: int, out: str, err: str):
        if err.strip():
            for line in err.splitlines():
                self.append_log(line)

        if code == 124:
            self.show_error(
                "Анализ превысил время ожидания. Проверь VPN/DNS/Proxy и доступ к cookies браузера, затем попробуй ещё раз."
            )
            self.video_title.setText(self.tr("not_analyzed"))
            return
        if code != 0:
            all_text = (err or "") + "\n" + (out or "")
            if is_ssl_certificate_error(all_text):
                current_mode = self.effective_certificate_mode()

                if current_mode != "Insecure":
                    self.append_log(
                        "SSL verify failed. Keychain/system CA could not validate the connection."
                    )
                    self.offer_insecure_ssl_retry(
                        analysis_url=self.url_edit.text().strip()
                    )
                else:
                    self.show_error(
                        "Соединение не удалось даже с отключённой проверкой сертификата. "
                        "Проверь VPN / proxy / интернет-соединение."
                        if self.lang == "RU"
                        else
                        "Connection failed even with certificate verification disabled. "
                        "Check VPN / proxy / network connectivity."
                    )
            else:
                self.show_error((err or out or "yt-dlp error")[-1600:])
            self.video_title.setText(self.tr("not_analyzed"))
            return

        try:
            info = json.loads(out)
        except Exception as exc:
            self.show_error(f"Не удалось разобрать JSON yt-dlp:\n{exc}")
            self.video_title.setText(self.tr("not_analyzed"))
            return

        self.current_info = info
        self.audio_map = []
        self.audio_formats, self.video_formats = parse_formats(info)
        self.resolution_combo.setCurrentIndex(-1)
        self.video_map = []
        title = str(info.get("title") or "YouTube")
        uploader = str(info.get("uploader") or "")
        duration = info.get("duration")
        suffix = []
        if uploader:
            suffix.append(uploader)
        if duration:
            try:
                seconds = int(duration)
                suffix.append(f"{seconds//60}:{seconds%60:02d}")
            except Exception:
                pass
        self.video_title.setText(title + (f"  •  {' • '.join(suffix)}" if suffix else ""))
        self.load_video_preview(info)

        self.update_audio_choices()
        self.update_video_choices()
        self.download_audio_btn.setEnabled(bool(self.audio_formats))
        self.download_video_btn.setEnabled(bool(self.video_formats and self.audio_formats))
        self.status_label.setText(self.tr("ready"))

    def set_combo_rows(self, combo: QComboBox, rows: list[tuple[str, bool]]):
        combo.clear()
        model = QStandardItemModel(combo)
        for text, selectable in rows:
            from PySide6.QtGui import QStandardItem
            item = QStandardItem(text)
            if not selectable:
                item.setEnabled(False)
                item.setSelectable(False)
                if not text.strip().startswith("─"):
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
            model.appendRow(item)
        combo.setModel(model)

    def update_audio_choices(self):
        previous = self.selected_audio_entry()
        self.audio_track_combo.blockSignals(True)
        self.audio_track_combo.clear()
        self.audio_track_groups = {}
        ordered = sorted(self.audio_formats, key=audio_preference_key)
        for fmt in ordered:
            key = (fmt.language, fmt.is_original, fmt.is_dubbed)
            self.audio_track_groups.setdefault(key, []).append(fmt)
        for key in self.audio_track_groups:
            language, original, dubbed = key
            name = ("Оригинал" if self.lang == "RU" else "Original") if original else ("Дубляж" if self.lang == "RU" else "Dubbed") if dubbed else ("Аудиодорожка" if self.lang == "RU" else "Audio track")
            self.audio_track_combo.addItem(name + (" · " + language.upper() if language else ""), key)
        key = (previous[0].language, previous[0].is_original, previous[0].is_dubbed) if previous else None
        selected = next((i for i in range(self.audio_track_combo.count()) if self.audio_track_combo.itemData(i) == key), 0)
        self.audio_track_combo.setCurrentIndex(selected if ordered else -1)
        self.audio_track_combo.blockSignals(False)
        self.update_audio_containers(preferred_id=previous[0].id if previous else None, preferred_ext=previous[1] if previous else None)

    def update_audio_containers(self, *_args, preferred_id=None, preferred_ext=None):
        if not hasattr(self, "audio_combo"):
            return
        group = getattr(self, "audio_track_groups", {}).get(self.audio_track_combo.currentData(), [])
        if preferred_ext is None:
            preferred_ext = self.audio_container_combo.currentData()
        self.audio_container_combo.blockSignals(True)
        self.audio_container_combo.clear()
        first_selectable = -1
        for heading, codec, choices in (
            ("OPUS", "Opus", [("    ├ .opus", ".opus"), ("    └ .ogg", ".ogg")]),
            ("AAC", "AAC", [("    ├ .m4a", ".m4a"), ("    └ .aac", ".aac")]),
        ):
            if not any(f.codec == codec for f in group):
                continue
            self.audio_container_combo.addItem(heading, None)
            header = self.audio_container_combo.model().item(self.audio_container_combo.count()-1)
            header.setFlags(Qt.NoItemFlags)
            for name, ext in choices:
                if first_selectable < 0:
                    first_selectable = self.audio_container_combo.count()
                self.audio_container_combo.addItem(name, ext)
                hint = {".opus": "Opus в контейнере Ogg.", ".ogg": "Opus в контейнере Ogg, расширение .ogg.", ".m4a": "AAC в MP4: метаданные, обложка и главы.", ".aac": "AAC/ADTS: без метаданных, обложки и встроенных глав."} if self.lang == "RU" else {".opus": "Opus in an Ogg container.", ".ogg": "Opus in Ogg, with the .ogg extension.", ".m4a": "AAC in MP4: tags, cover and chapters.", ".aac": "AAC/ADTS: no tags, cover or embedded chapters."}
                self.audio_container_combo.setItemData(self.audio_container_combo.count()-1, hint[ext], Qt.ToolTipRole)
        index = self.audio_container_combo.findData(preferred_ext) if preferred_ext else -1
        self.audio_container_combo.setCurrentIndex(index if index >= 0 else first_selectable)
        self.audio_container_combo.blockSignals(False)
        self.update_audio_variants(preferred_id=preferred_id)

    def update_audio_variants(self, *_args, preferred_id=None):
        if not hasattr(self, "audio_meta"):
            return
        ext = self.audio_container_combo.currentData()
        group = getattr(self, "audio_track_groups", {}).get(self.audio_track_combo.currentData(), [])
        codec = "Opus" if ext in {".opus", ".ogg"} else "AAC"
        streams = sorted([f for f in group if f.codec == codec], key=audio_preference_key)
        self.audio_combo.blockSignals(True)
        self.audio_combo.clear()
        self.audio_map = [(fmt, ext) for fmt in streams]
        for fmt in streams:
            rate = f"~{fmt.abr:g} kbps" if fmt.abr else fmt.codec
            sample = f"{fmt.asr / 1000:g} kHz" if fmt.asr else ""
            size = "≈" + format_bytes(fmt.size) if fmt.size else ""
            self.audio_combo.addItem(" · ".join(x for x in (rate, sample, size, "DRC" if fmt.is_drc else "") if x))
            self.audio_combo.setItemData(self.audio_combo.count()-1, audio_display_label(fmt, self.lang) + f" • id {fmt.id}", Qt.ToolTipRole)
        index = next((i for i,fmt in enumerate(streams) if fmt.id == preferred_id), 0)
        self.audio_combo.setCurrentIndex(index if streams else -1)
        self.audio_combo.blockSignals(False)
        self.audio_selection_changed()

    def audio_selection_changed(self):
        idx = self.audio_combo.currentIndex()
        if idx < 0 or idx >= len(self.audio_map) or self.audio_map[idx] is None:
            return
        fmt, ext = self.audio_map[idx]
        self.ch_embed.setEnabled(ext == ".m4a")
        preference = self.audio_chapter_preference
        if preference == "embed":
            (self.ch_embed if ext == ".m4a" else self.ch_none).setChecked(True)
        elif preference == "split":
            self.ch_split.setChecked(True)
        else:
            self.ch_none.setChecked(True)
        raw_aac = ext == ".aac"
        if raw_aac and not self.audio_raw_aac_active:
            self.audio_saved_options = (self.audio_meta.isChecked(), self.audio_thumb.isChecked())
        self.audio_meta.setEnabled(not raw_aac)
        self.audio_thumb.setEnabled(not raw_aac)
        if raw_aac:
            self.audio_meta.setChecked(False)
            self.audio_thumb.setChecked(False)
        elif self.audio_raw_aac_active:
            self.audio_meta.setChecked(self.audio_saved_options[0])
            self.audio_thumb.setChecked(self.audio_saved_options[1])
        self.audio_raw_aac_active = raw_aac
        self.audio_chapter_changed()
        self.refresh_context_help()

    def audio_chapter_changed(self):
        self.audio_manual_btn.setEnabled(not self.ch_none.isChecked())
        self.refresh_context_help()

    def selected_container(self) -> str:
        if self.mkv.isChecked():
            return "MKV"
        if self.webm.isChecked():
            return "WebM"
        return "MP4"

    def update_video_choices(self):
        if not hasattr(self, "video_combo"):
            return
        container = self.selected_container()

        for name, badge in self.container_badges.items():
            available = container_has_4k(self.video_formats, self.audio_formats, name)
            badge.setText("4K" if available else "")
            badge.setToolTip(("Доступен совместимый поток 4K" if self.lang == "RU" else "Compatible 4K stream available") if available else "")

        vids = [v for v in self.video_formats if video_container_compatible(v, container)]
        auds = sorted(
            [a for a in self.audio_formats if audio_container_compatible(a, container)],
            key=audio_preference_key,
        )
        self.filtered_video_audio = auds

        previous = self.selected_video_entry()
        previous_id = previous.id if previous else None
        previous_resolution = self.resolution_combo.currentData()
        self.compatible_video_formats = vids
        resolutions = sorted({(v.width, v.height) for v in vids},
                             key=lambda size: (min(size) if all(size) else size[1], size[0] * size[1], size[1]), reverse=True)
        self.resolution_combo.blockSignals(True)
        self.resolution_combo.clear()
        for width, height in resolutions:
            pixels = min(width, height) if width and height else height
            suffix = " · 8K" if pixels >= 4320 else " · 4K" if pixels >= 2160 else " · Full HD" if pixels == 1080 else " · HD" if pixels == 720 else ""
            self.resolution_combo.addItem(f"{pixels}p{suffix}", (width, height))
            self.resolution_combo.setItemData(self.resolution_combo.count()-1, f"{width}×{height}", Qt.ToolTipRole)
        index = next((i for i in range(self.resolution_combo.count()) if self.resolution_combo.itemData(i) == previous_resolution), -1)
        self.resolution_combo.setCurrentIndex(index if index >= 0 else 0)
        self.resolution_combo.blockSignals(False)
        self.update_video_variants(preferred_id=previous_id)

        self.video_audio_combo.clear()
        original_known = any(a.is_original for a in self.audio_formats)
        original_compatible = any(a.is_original for a in auds)
        auto_label = ("Оригинальная дорожка (авто)" if self.lang == "RU" else "Original audio (auto)") if original_compatible else self.tr("best")
        if original_known and not original_compatible:
            auto_label = "Оригинал несовместим — выбери другой контейнер" if self.lang == "RU" else "Original incompatible — choose another container"
        self.video_audio_combo.addItem(auto_label)
        for a in auds:
            self.video_audio_combo.addItem(audio_display_label(a, self.lang))

    def update_video_variants(self, *_args, preferred_id=None):
        if not hasattr(self, "video_details"):
            return
        resolution = self.resolution_combo.currentData()
        formats = [v for v in getattr(self, "compatible_video_formats", []) if (v.width, v.height) == resolution]
        formats.sort(key=lambda v: (-v.fps, -v.tbr, v.codec, v.id))
        self.video_combo.blockSignals(True)
        self.video_combo.clear()
        self.video_map = formats
        for fmt in formats:
            fps = f"{fmt.fps:g} fps" if fmt.fps else ""
            rate = f"~{fmt.tbr / 1000:.1f} Mbps" if fmt.tbr else ""
            size = "≈" + format_bytes(fmt.size) if fmt.size else ""
            self.video_combo.addItem(" · ".join(x for x in (fmt.codec, fps, rate, size) if x))
            self.video_combo.setItemData(self.video_combo.count()-1, fmt.label + f" • id {fmt.id}", Qt.ToolTipRole)
        selected = next((i for i, fmt in enumerate(formats) if fmt.id == preferred_id), 0)
        self.video_combo.setCurrentIndex(selected if formats else -1)
        self.video_combo.blockSignals(False)
        self.update_video_details()
        self.refresh_context_help()

    def update_video_details(self, *_):
        if not hasattr(self, "video_details"):
            return
        fmt = self.selected_video_entry()
        if fmt:
            size = ("Примерный размер: " if self.lang == "RU" else "Estimated size: ") + format_bytes(fmt.size) if fmt.size else ""
            self.video_details.setText(" · ".join(x for x in (f"{fmt.width}×{fmt.height}", size) if x))
            self.video_details.setToolTip(fmt.label)
        else:
            self.video_details.setText("")
            self.video_details.setToolTip("")

    def selected_audio_entry(self):
        idx = self.audio_combo.currentIndex()
        if idx < 0 or idx >= len(self.audio_map):
            return None
        return self.audio_map[idx]

    def selected_video_entry(self):
        idx = self.video_combo.currentIndex()
        if idx < 0 or idx >= len(self.video_map):
            return None
        return self.video_map[idx]

    def selected_video_audio(self):
        if not self.filtered_video_audio:
            return None
        idx = self.video_audio_combo.currentIndex()
        if idx <= 0:
            if any(a.is_original for a in self.audio_formats) and not self.filtered_video_audio[0].is_original:
                return None
            return self.filtered_video_audio[0]
        if idx - 1 < len(self.filtered_video_audio):
            return self.filtered_video_audio[idx - 1]
        return None

    def ensure_output(self) -> Optional[Path]:
        text = self.output_edit.text().strip()
        if not text:
            self.show_error("Выбери папку сохранения.")
            return None
        p = Path(text)
        p.mkdir(parents=True, exist_ok=True)
        self.save_settings()
        return p

    def common_download_prefix(self) -> Optional[list[str]]:
        base = self.ytdlp_base()
        if not base:
            return None
        net_args, resolved = proxy_args(
            self.settings.get("network_mode", "Auto"),
            self.settings.get("manual_proxy", ""),
        )
        if not resolved.ok:
            self.show_error(resolved.detail)
            return None
        return base + net_args + ytdlp_common_args(
            self.effective_certificate_mode()
        )

    def show_completion_signal(self, kind: str, folder: str = ""):
        if kind == "audio":
            title = "Аудио скачано" if self.lang == "RU" else "Audio downloaded"
        elif kind == "video":
            title = "Видео скачано" if self.lang == "RU" else "Video downloaded"
        elif kind == "thumbnail":
            title = "Обложка сохранена" if self.lang == "RU" else "Thumbnail saved"
        elif kind == "remux":
            title = "Перепаковка завершена" if self.lang == "RU" else "Remux completed"
        else:
            title = "Готово" if self.lang == "RU" else "Done"

        if folder:
            detail = (
                f"\nСохранено в: {folder}"
                if self.lang == "RU"
                else f"\nSaved to: {folder}"
            )
        else:
            detail = ""

        self.success_toast.show_message(title + detail)

    def start_stream(self, cmd: list[str], context: dict):
        self.log.clear()
        self.progress.setValue(0)
        self.progress.set_speed("—")
        self.active_download_context = context
        self.stream_error_tail = []
        self.append_log("> " + " ".join(f'"{x}"' if " " in x else x for x in cmd))

        extra_env = {}
        if context.get("kind") in {"audio", "video", "thumbnail"}:
            extra_env = self.current_certificate_env()

        self.stream_worker = StreamWorker(
            cmd,
            app_dir(),
            extra_env=extra_env,
        )
        self.stream_worker.line.connect(self.stream_line)
        self.stream_worker.completed.connect(self.stream_done)
        self.stream_worker.failed.connect(self.stream_failed)
        self.stream_worker.start()

    def stream_line(self, line: str):
        pct, speed = parse_progress(line)
        if pct is not None:
            self.progress.setValue(pct)
            self.progress.set_speed(speed)

        self.stream_error_tail.append(line)
        if len(self.stream_error_tail) > 60:
            del self.stream_error_tail[:-60]

        self.append_log(line)

    def stream_failed(self, error: str):
        self.show_error(error)
        self.active_download_context = {}

    def stream_done(self, code: int):
        context = self.active_download_context
        self.stream_worker = None
        if code != 0:
            tail_text = "\n".join(self.stream_error_tail)

            if (
                context.get("kind") in {"audio", "video", "thumbnail"}
                and is_ssl_certificate_error(tail_text)
                and self.effective_certificate_mode() != "Insecure"
            ):
                if self.offer_insecure_ssl_retry():
                    self.show_error(
                        "Проверка SSL отключена до закрытия программы. "
                        "Нажми «Скачать» ещё раз."
                        if self.lang == "RU"
                        else
                        "SSL verification is disabled until the app is closed. "
                        "Click Download again."
                    )
                self.active_download_context = {}
                return

            self.show_error("yt-dlp завершился с ошибкой. Смотри журнал событий.")
            self.active_download_context = {}
            return

        kind = context.get("kind")
        folder = Path(context["download_dir"])
        after = float(context["started"])

        if kind == "audio":
            self.finish_audio_download(context, folder, after)
        elif kind == "video":
            self.finish_video_download(context, folder, after)
        elif kind == "thumbnail":
            self.progress.setValue(100)
            self.progress.set_speed("—")
            self.status_label.setText(self.tr("ready"))
            self.append_log("Готово: обложка сохранена.")
            self.show_completion_signal("thumbnail", context.get("output_dir", ""))
            self.active_download_context = {}
        elif kind == "remux":
            self.progress.setValue(100)
            self.progress.set_speed("—")
            self.status_label.setText(self.tr("ready"))
            self.append_log("Готово: перепаковка завершена.")
            self.show_completion_signal("remux", context.get("output_dir", ""))
            self.active_download_context = {}
        else:
            self.progress.setValue(100)
            self.progress.set_speed("—")
            self.refresh_dependency_labels()
            self.active_download_context = {}

    def existing_download_target(
        self,
        output_dir: Path,
        final_ext: str,
        fragment,
    ) -> Optional[Path]:
        """
        Find the unsuffixed target produced by our standard template.

        Matching by YouTube ID is deliberate: the title may change between
        downloads, but [video_id] remains stable.
        """
        media_id = str(self.current_info.get("id") or "").strip()
        if not media_id:
            return None

        ext = final_ext.lower()
        if not ext.startswith("."):
            ext = "." + ext

        tail = f"[{media_id}]"
        if fragment:
            tail += f" [{self.fragment_filename_stamp()}]"

        try:
            for path in output_dir.iterdir():
                if (
                    path.is_file()
                    and path.suffix.lower() == ext
                    and path.stem.endswith(tail)
                ):
                    return path
        except Exception:
            pass

        return None

    def next_download_copy_suffix(
        self,
        output_dir: Path,
        final_ext: str,
        fragment,
    ) -> str:
        """Return _1, _2, ... without colliding with previous copies."""
        media_id = str(self.current_info.get("id") or "").strip()
        if not media_id:
            return "_1"

        ext = final_ext.lower()
        if not ext.startswith("."):
            ext = "." + ext

        base = f"[{media_id}]"
        fragment_tail = (
            f" [{self.fragment_filename_stamp()}]"
            if fragment
            else ""
        )

        pattern = re.compile(
            re.escape(base)
            + r"_(\d+)"
            + re.escape(fragment_tail)
            + r"$"
        )

        used = set()
        try:
            for path in output_dir.iterdir():
                if not path.is_file() or path.suffix.lower() != ext:
                    continue
                match = pattern.search(path.stem)
                if match:
                    try:
                        used.add(int(match.group(1)))
                    except Exception:
                        pass
        except Exception:
            pass

        number = 1
        while number in used:
            number += 1
        return f"_{number}"

    def resolve_duplicate_download(
        self,
        output_dir: Path,
        final_ext: str,
        fragment,
    ) -> Optional[dict]:
        """
        Ask what to do when the final target already exists.

        Returns:
            {"overwrite": bool, "suffix": str}
        or None when the user cancels.
        """
        existing = self.existing_download_target(
            output_dir,
            final_ext,
            fragment,
        )
        if existing is None:
            return {"overwrite": False, "suffix": ""}

        copy_suffix = self.next_download_copy_suffix(
            output_dir,
            final_ext,
            fragment,
        )

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(
            "Файл уже существует"
            if self.lang == "RU"
            else "File already exists"
        )
        box.setText(
            (
                "Такой файл уже есть:\n\n"
                f"{existing.name}\n\n"
                "Что сделать?"
            )
            if self.lang == "RU"
            else (
                "This file already exists:\n\n"
                f"{existing.name}\n\n"
                "What should be done?"
            )
        )

        overwrite_btn = box.addButton(
            "Перезаписать"
            if self.lang == "RU"
            else "Overwrite",
            QMessageBox.AcceptRole,
        )
        copy_btn = box.addButton(
            (
                f"Сохранить копию ({copy_suffix})"
                if self.lang == "RU"
                else f"Save a copy ({copy_suffix})"
            ),
            QMessageBox.ActionRole,
        )
        cancel_btn = box.addButton(
            self.tr("cancel"),
            QMessageBox.RejectRole,
        )

        box.setDefaultButton(copy_btn)
        box.exec()
        clicked = box.clickedButton()

        if clicked == overwrite_btn:
            return {"overwrite": True, "suffix": ""}
        if clicked == copy_btn:
            return {"overwrite": False, "suffix": copy_suffix}

        return None

    def download_audio(self):
        entry = self.selected_audio_entry()
        if not entry:
            self.show_error("Выбери аудиопоток, а не разделитель.")
            return
        fmt, ext = entry
        out = self.ensure_output()
        if not out:
            return
        prefix = self.common_download_prefix()
        if prefix is None:
            return

        fragment = self.fragment_range()
        if fragment is False:
            return

        duplicate = self.resolve_duplicate_download(out, ext, fragment)
        if duplicate is None:
            return

        name_suffix = duplicate["suffix"]
        overwrite = bool(duplicate["overwrite"])

        # OGG/AAC need an intermediate file with a different extension.
        # Keep that intermediate in a private temp folder so an existing M4A
        # or Opus file can never be mistaken for the new download.
        download_dir = out
        temp_dir = None
        if fragment or ext in {".ogg", ".aac"}:
            temp_dir = Path(tempfile.mkdtemp(prefix="ymd_audio_"))
            download_dir = temp_dir

        template = str(
            download_dir
            / f"%(title)s [%(id)s]{name_suffix}.%(ext)s"
        )
        cmd = prefix + [
            "--newline", "--progress",
            "-f", fmt.id,
            "-o", template,
        ]
        if overwrite:
            cmd += ["--force-overwrites"]

        # Keep the original selected stream. yt-dlp/ffmpeg only remux where required.
        if ext in {".opus", ".ogg"}:
            cmd += ["-x", "--audio-format", "opus"]
        elif ext == ".m4a":
            cmd += ["-x", "--audio-format", "m4a"]

        if ext != ".aac":
            if self.audio_meta.isChecked():
                cmd += ["--embed-metadata"]
            if self.audio_thumb.isChecked():
                cmd += ["--embed-thumbnail"]

        chapter_mode = "none"
        if self.ch_embed.isChecked():
            chapter_mode = "embed"
        elif self.ch_split.isChecked():
            chapter_mode = "split"

        if chapter_mode == "embed" and not self.manual_chapters_text and ext == ".m4a":
            cmd += ["--embed-chapters"]

        cmd += [self.url_edit.text().strip()]

        self.status_label.setText("Скачивание аудио..." if self.lang == "RU" else "Downloading audio...")
        if fragment:
            self.append_log(
                "Быстрый фрагмент: сначала скачивается полный аудиопоток, затем сохраняется локальный фрагмент."
            )
        self.start_stream(
            cmd,
            {
                "kind": "audio",
                "output_dir": str(out),
                "download_dir": str(download_dir),
                "temp_dir": str(temp_dir) if temp_dir else "",
                "started": time.time(),
                "format": fmt,
                "ext": ext,
                "fragment": fragment,
                "chapter_mode": chapter_mode,
                "name_suffix": name_suffix,
                "overwrite": overwrite,
            },
        )

    def finish_audio_download(self, ctx: dict, folder: Path, after: float):
        ext = ctx["ext"]
        # Intermediate extension produced by yt-dlp.
        candidates = [".m4a"] if ext in {".m4a", ".aac"} else [".opus", ".webm", ".ogg"]
        downloaded = find_latest_file(folder, candidates, after)
        if not downloaded:
            self.show_error("Не найден скачанный аудиофайл.")
            self.cleanup_temp(ctx)
            return

        target_out = Path(ctx["output_dir"])
        fragment = ctx.get("fragment")
        if fragment:
            ff = ffmpeg_path()
            if not ff:
                self.show_error("Для локального фрагмента нужен FFmpeg.")
                self.cleanup_temp(ctx)
                return
            start_ms, to_ms = fragment
            suffix = downloaded.suffix
            dest = folder / (
                downloaded.stem
                + f" [{self.fragment_filename_stamp()}]"
                + suffix
            )
            self.run_post(
                "fragment",
                {
                    "ffmpeg": str(ff),
                    "input": str(downloaded),
                    "output": str(dest),
                    "start": start_ms / 1000,
                    "duration": (to_ms - start_ms) / 1000,
                },
                next_step=("audio_after_fragment", ctx),
            )
            return

        dest = downloaded
        self.audio_after_fragment(ctx, dest)

    def move_audio_to_output(self, ctx: dict, downloaded: Path) -> Path:
        target_out = Path(ctx["output_dir"])
        if downloaded.parent == target_out:
            return downloaded

        final = target_out / downloaded.name
        if final.exists():
            final.unlink()

        shutil.move(str(downloaded), str(final))
        return final

    def audio_after_fragment(self, ctx: dict, downloaded: Path):
        ext = ctx["ext"]

        # Rename/convert in the private temp directory first. Only the final
        # file is moved to Downloads, avoiding collisions with other formats.
        if ext == ".ogg" and downloaded.suffix.lower() != ".ogg":
            local_final = downloaded.with_suffix(".ogg")
            if local_final.exists():
                local_final.unlink()
            downloaded.replace(local_final)
            downloaded = local_final

        if ext == ".aac":
            ff = ffmpeg_path()
            if not ff:
                self.show_error("Для .aac нужен FFmpeg.")
                self.cleanup_temp(ctx)
                return

            local_final = downloaded.with_suffix(".aac")
            self.run_post(
                "aac",
                {
                    "ffmpeg": str(ff),
                    "input": str(downloaded),
                    "output": str(local_final),
                },
                next_step=(
                    "audio_after_aac",
                    {**ctx, "source_to_remove": str(downloaded)},
                ),
            )
            return

        downloaded = self.move_audio_to_output(ctx, downloaded)
        self.audio_chapter_post(ctx, downloaded)

    def audio_after_aac(self, ctx: dict, output: Path):
        src = Path(ctx.get("source_to_remove", ""))
        if src.exists() and src != output:
            try:
                src.unlink()
            except Exception:
                pass

        output = self.move_audio_to_output(ctx, output)
        self.audio_chapter_post(ctx, output)


    def chapter_rows_for_file(self, path: Path, fragment):
        probe = ffprobe_path()
        duration_ms = media_duration_ms(probe, path) if probe else int((self.current_info.get("duration") or 86400) * 1000)
        if self.manual_chapters_text:
            # Manual timestamps refer to the original source.
            source_duration = int((self.current_info.get("duration") or duration_ms / 1000) * 1000)
            rows = parse_manual_chapters(self.manual_chapters_text, source_duration)
        else:
            source_duration = int((self.current_info.get("duration") or duration_ms / 1000) * 1000)
            rows = chapters_from_info(self.current_info, source_duration)
        if fragment:
            rows = clip_chapters(rows, fragment[0], fragment[1])
        return rows

    def audio_chapter_post(self, ctx: dict, downloaded: Path):
        mode = ctx.get("chapter_mode")
        if mode == "none":
            self.complete_success(ctx)
            return

        chapters = self.chapter_rows_for_file(downloaded, ctx.get("fragment"))
        if not chapters:
            self.append_log("Главы не найдены — оставляю файл как есть.")
            self.complete_success(ctx)
            return

        ff = ffmpeg_path()
        if not ff:
            self.show_error("Для обработки глав нужен FFmpeg.")
            self.cleanup_temp(ctx)
            return

        if mode == "embed":
            if downloaded.suffix.lower() != ".m4a":
                self.append_log("Встраивание глав доступно только для M4A.")
                self.complete_success(ctx)
                return
            self.run_post(
                "embed_chapters",
                {"ffmpeg": str(ff), "input": str(downloaded), "chapters": chapters},
                next_step=("complete", ctx),
            )
            return

        if mode == "split":
            self.run_post(
                "split",
                {"ffmpeg": str(ff), "input": str(downloaded), "chapters": chapters},
                next_step=("split_complete", {**ctx, "source": str(downloaded)}),
            )
            return

        self.complete_success(ctx)

    def download_video(self):
        video = self.selected_video_entry()
        audio = self.selected_video_audio()
        if not video or not audio:
            self.show_error("Сначала проанализируй ролик и выбери совместимые видео и аудио.")
            return
        out = self.ensure_output()
        if not out:
            return
        ff = ffmpeg_path()
        if not ff:
            self.show_error("Для объединения видео и аудио нужен FFmpeg.")
            return
        prefix = self.common_download_prefix()
        if prefix is None:
            return

        fragment = self.fragment_range()
        if fragment is False:
            return

        container = self.selected_container()
        merge_ext = {"MP4": "mp4", "MKV": "mkv", "WebM": "webm"}[container]

        duplicate = self.resolve_duplicate_download(
            out,
            "." + merge_ext,
            fragment,
        )
        if duplicate is None:
            return

        name_suffix = duplicate["suffix"]
        overwrite = bool(duplicate["overwrite"])

        download_dir = out
        temp_dir = None
        if fragment:
            temp_dir = Path(tempfile.mkdtemp(prefix="ymd_fragment_"))
            download_dir = temp_dir

        cmd = prefix + [
            "--newline", "--progress",
            "-f", f"{video.id}+{audio.id}",
            "--merge-output-format", merge_ext,
            "-o",
            str(
                download_dir
                / f"%(title)s [%(id)s]{name_suffix}.%(ext)s"
            ),
        ]
        if overwrite:
            cmd += ["--force-overwrites"]
        if self.video_meta.isChecked():
            cmd += ["--embed-metadata"]
        if self.video_thumb.isChecked():
            cmd += ["--embed-thumbnail"]
        if self.video_chapters.isChecked() and not self.manual_chapters_text:
            cmd += ["--embed-chapters"]
        cmd += [self.url_edit.text().strip()]

        self.status_label.setText("Скачивание видео..." if self.lang == "RU" else "Downloading video...")
        self.start_stream(
            cmd,
            {
                "kind": "video",
                "output_dir": str(out),
                "download_dir": str(download_dir),
                "temp_dir": str(temp_dir) if temp_dir else "",
                "started": time.time(),
                "merge_ext": merge_ext,
                "fragment": fragment,
                "name_suffix": name_suffix,
                "overwrite": overwrite,
            },
        )

    def finish_video_download(self, ctx: dict, folder: Path, after: float):
        downloaded = find_latest_file(folder, ["." + ctx["merge_ext"]], after)
        if not downloaded:
            self.show_error("Не найден скачанный видеофайл.")
            self.cleanup_temp(ctx)
            return

        out = Path(ctx["output_dir"])
        fragment = ctx.get("fragment")
        if fragment:
            ff = ffmpeg_path()
            assert ff
            start_ms, to_ms = fragment
            dest = out / (
                downloaded.stem + f" [{self.fragment_filename_stamp()}]" + downloaded.suffix
            )
            self.run_post(
                "fragment",
                {
                    "ffmpeg": str(ff),
                    "input": str(downloaded),
                    "output": str(dest),
                    "start": start_ms / 1000,
                    "duration": (to_ms - start_ms) / 1000,
                },
                next_step=("video_after_fragment", ctx),
            )
            return

        dest = downloaded
        self.video_after_fragment(ctx, dest)

    def video_after_fragment(self, ctx: dict, downloaded: Path):
        out = Path(ctx["output_dir"])
        if downloaded.parent != out:
            final = out / downloaded.name
            if final.exists():
                final.unlink()
            shutil.move(str(downloaded), str(final))
            downloaded = final

        if self.video_chapters.isChecked() and self.manual_chapters_text:
            ff = ffmpeg_path()
            if ff:
                chapters = self.chapter_rows_for_file(downloaded, ctx.get("fragment"))
                if chapters:
                    self.run_post(
                        "embed_chapters",
                        {"ffmpeg": str(ff), "input": str(downloaded), "chapters": chapters},
                        next_step=("complete", ctx),
                    )
                    return

        self.complete_success(ctx)

    def run_post(self, action: str, kwargs: dict, next_step):
        self.active_download_context["next_step"] = next_step
        self.post_worker = PostProcessWorker(action, **kwargs)
        self.post_worker.log.connect(self.append_log)
        self.post_worker.progress.connect(self.progress.setValue)
        self.post_worker.done.connect(self.post_done)
        self.post_worker.start()

    def post_done(self, ok: bool, path: str, error: str):
        if not ok:
            self.show_error("FFmpeg завершился с ошибкой:\n" + error[-1600:])
            self.cleanup_temp(self.active_download_context)
            return

        next_step = self.active_download_context.pop("next_step", None)
        self.post_worker = None
        if not next_step:
            self.complete_success(self.active_download_context)
            return

        name, ctx = next_step
        p = Path(path)
        if name == "audio_after_fragment":
            self.audio_after_fragment(ctx, p)
        elif name == "audio_after_aac":
            self.audio_after_aac(ctx, p)
        elif name == "video_after_fragment":
            self.video_after_fragment(ctx, p)
        elif name == "split_complete":
            src = Path(ctx.get("source", ""))
            if src.exists():
                try:
                    src.unlink()
                except Exception:
                    pass
            self.complete_success(ctx)
        else:
            self.complete_success(ctx)

    def complete_success(self, ctx: dict):
        self.progress.setValue(100)
        self.progress.set_speed("—")
        self.status_label.setText(self.tr("ready"))
        self.append_log("Готово.")

        kind = str(ctx.get("kind") or "")
        if kind in {"audio", "video"}:
            self.show_completion_signal(kind, ctx.get("output_dir", ""))

        self.cleanup_temp(ctx)
        self.active_download_context = {}

    def cleanup_temp(self, ctx: dict):
        td = ctx.get("temp_dir") if ctx else ""
        if td:
            shutil.rmtree(td, ignore_errors=True)

    def download_thumbnail(self):
        out = self.ensure_output()
        if not out:
            return
        prefix = self.common_download_prefix()
        if prefix is None:
            return
        cmd = prefix + [
            "--write-thumbnail",
            "--skip-download",
            "-o", str(out / "%(title)s.%(ext)s"),
            self.url_edit.text().strip(),
        ]
        self.start_stream(
            cmd,
            {
                "kind": "thumbnail",
                "output_dir": str(out),
                "download_dir": str(out),
                "started": time.time(),
            },
        )

    def probe_remux_streams(self, path: Path) -> dict:
        probe = ffprobe_path()
        if not probe:
            return {"video": [], "audio": [], "subtitle": [], "error": "FFprobe not found"}

        cmd = [
            str(probe),
            "-v", "error",
            "-show_entries", "stream=codec_type,codec_name",
            "-of", "json",
            str(path),
        ]

        try:
            kwargs = {}
            if platform.system() == "Windows":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

            cp = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=15,
                **kwargs,
            )

            if cp.returncode != 0:
                return {
                    "video": [],
                    "audio": [],
                    "subtitle": [],
                    "error": cp.stderr.decode("utf-8", "replace").strip(),
                }

            data = json.loads(cp.stdout.decode("utf-8", "replace") or "{}")
            result = {"video": [], "audio": [], "subtitle": [], "error": ""}

            for stream in data.get("streams") or []:
                kind = str(stream.get("codec_type") or "").lower()
                codec = str(stream.get("codec_name") or "unknown").lower()
                if kind in result:
                    result[kind].append(codec)

            return result
        except Exception as exc:
            return {"video": [], "audio": [], "subtitle": [], "error": str(exc)}

    def remux_compatibility(self, path: Path, streams: dict) -> dict:
        videos = set(streams.get("video") or [])
        audios = set(streams.get("audio") or [])
        has_media = bool(videos or audios)

        # Conservative -c copy compatibility. It is intentionally stricter
        # than FFmpeg's theoretical limits so the GUI does not offer fragile
        # combinations.
        mp4_video = {"h264", "hevc", "av1", "mpeg4", "mjpeg"}
        mp4_audio = {"aac", "alac", "mp3", "ac3", "eac3"}

        webm_video = {"vp8", "vp9", "av1"}
        webm_audio = {"opus", "vorbis"}

        ogg_audio = {"opus", "vorbis", "flac", "speex"}
        m4a_audio = {"aac", "alac"}

        compatible = {
            "MKV": has_media,
            "MP4": (
                has_media
                and (not videos or videos.issubset(mp4_video))
                and (not audios or audios.issubset(mp4_audio))
            ),
            "WebM": (
                has_media
                and (not videos or videos.issubset(webm_video))
                and (not audios or audios.issubset(webm_audio))
            ),
            "OGG": (
                not videos
                and bool(audios)
                and audios.issubset(ogg_audio)
            ),
            "M4A": (
                not videos
                and bool(audios)
                and audios.issubset(m4a_audio)
            ),
        }

        # Extension fallback if probing did not succeed.
        if not has_media:
            ext = path.suffix.lower()
            fallback = {
                ".mp4": {"MKV", "MP4"},
                ".m4v": {"MKV", "MP4"},
                ".mov": {"MKV", "MP4"},
                ".webm": {"MKV", "WebM"},
                ".mkv": {"MKV"},
                ".opus": {"MKV", "WebM", "OGG"},
                ".ogg": {"MKV", "OGG"},
                ".aac": {"MKV", "MP4", "M4A"},
                ".m4a": {"MKV", "MP4", "M4A"},
                ".flac": {"MKV", "OGG"},
                ".wav": {"MKV"},
            }.get(ext, {"MKV"})

            compatible = {
                target: target in fallback
                for target in self.remux_targets
            }

        return compatible

    def update_remux_target_model(self, compatible: dict):
        model = QStandardItemModel(self.remux_ext)
        first_enabled = -1

        for index, target in enumerate(self.remux_targets):
            ok = bool(compatible.get(target))
            item = QStandardItem(target)

            if ok:
                item.setText(f"{target}   ✓")
                if first_enabled < 0:
                    first_enabled = index
            else:
                item.setText(f"{target}   —   ✕")
                item.setEnabled(False)
                item.setSelectable(False)
                item.setToolTip(
                    "Несовместимо с кодеками выбранного файла"
                    if self.lang == "RU"
                    else "Not compatible with the selected file codecs"
                )

            model.appendRow(item)

        self.remux_ext.setModel(model)

        if first_enabled >= 0:
            self.remux_ext.setCurrentIndex(first_enabled)
            self.remux_button.setEnabled(True)
        else:
            self.remux_ext.setCurrentIndex(-1)
            self.remux_button.setEnabled(False)

    def set_remux_file(self, path: str):
        file_path = Path(path)
        if not file_path.exists() or not file_path.is_file():
            return

        self.remux_input.setText(str(file_path))
        self.append_log(
            ("Файл для перепаковки: " if self.lang == "RU" else "Remux file: ")
            + str(file_path)
        )

        streams = self.probe_remux_streams(file_path)
        compatible = self.remux_compatibility(file_path, streams)
        self.update_remux_target_model(compatible)

        video_text = ", ".join(streams.get("video") or []) or "—"
        audio_text = ", ".join(streams.get("audio") or []) or "—"
        allowed = [
            target for target in self.remux_targets
            if compatible.get(target)
        ]

        if streams.get("error"):
            description = (
                "FFprobe не смог полностью определить потоки; использовано расширение файла."
                if self.lang == "RU"
                else "FFprobe could not fully detect streams; extension fallback was used."
            )
        else:
            description = (
                f"Видео: {video_text}  •  Аудио: {audio_text}"
                if self.lang == "RU"
                else f"Video: {video_text}  •  Audio: {audio_text}"
            )

        allowed_text = ", ".join(allowed) if allowed else "—"
        self.remux_info.setText(
            description
            + (
                f"\nСовместимо без перекодирования: {allowed_text}"
                if self.lang == "RU"
                else f"\nCompatible without re-encoding: {allowed_text}"
            )
        )

    def choose_remux(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("choose"),
            "",
            "Media files (*.opus *.ogg *.aac *.webm *.m4a *.mp4 *.mkv *.mov *.m4v *.avi *.ts *.m2ts *.flac *.wav);;All files (*)",
        )
        if path:
            self.set_remux_file(path)

    def remux(self):
        inp = Path(self.remux_input.text().strip())
        if not inp.exists():
            self.show_error(
                "Выбери существующий файл."
                if self.lang == "RU"
                else "Choose an existing file."
            )
            return

        ff = ffmpeg_path()
        if not ff:
            self.show_error("FFmpeg не найден." if self.lang == "RU" else "FFmpeg not found.")
            return

        index = self.remux_ext.currentIndex()
        if index < 0 or index >= len(self.remux_targets):
            self.show_error(
                "Для этого файла нет совместимого контейнера."
                if self.lang == "RU"
                else "No compatible target container is available for this file."
            )
            return

        target = self.remux_targets[index]

        streams = self.probe_remux_streams(inp)
        compatible = self.remux_compatibility(inp, streams)
        if not compatible.get(target):
            self.show_error(
                f"Нельзя перепаковать этот файл в {target} без перекодирования."
                if self.lang == "RU"
                else f"This file cannot be remuxed to {target} without re-encoding."
            )
            return

        ext_map = {
            "MKV": ".mkv",
            "MP4": ".mp4",
            "WebM": ".webm",
            "OGG": ".ogg",
            "M4A": ".m4a",
        }
        ext = ext_map[target]
        out = inp.with_name(inp.stem + "_remux" + ext)

        # .opus is already Ogg-framed.
        if inp.suffix.lower() == ".opus" and target == "OGG":
            shutil.copy2(inp, out)
            self.append_log(f"Готово: {out}")
            return

        cmd = [
            str(ff),
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", str(inp),
        ]

        if target == "MKV":
            cmd += ["-map", "0", "-c", "copy"]
        elif target in {"OGG", "M4A"}:
            cmd += ["-map", "0:a:0", "-c:a", "copy"]
        else:
            if streams.get("video"):
                cmd += ["-map", "0:v:0"]
            if streams.get("audio"):
                cmd += ["-map", "0:a:0"]
            cmd += ["-c", "copy"]

        cmd += [str(out)]

        self.append_log(
            (
                f"Перепаковка без перекодирования: {inp.suffix or '?'} → {ext}"
                if self.lang == "RU"
                else f"Remux without re-encoding: {inp.suffix or '?'} → {ext}"
            )
        )

        self.start_stream(
            cmd,
            {
                "kind": "remux",
                "output_dir": str(inp.parent),
                "download_dir": str(inp.parent),
                "started": time.time(),
            },
        )

    def refresh_dependency_labels(self):
        if self.dependency_status_worker and self.dependency_status_worker.isRunning():
            return

        self.dependency_status_worker = DependencyStatusWorker()
        self.dependency_status_worker.done.connect(self.dependency_labels_done)
        self.dependency_status_worker.finished.connect(
            lambda: setattr(self, "dependency_status_worker", None)
        )
        self.dependency_status_worker.start()

    def dependency_labels_done(self, info: dict):
        if info.get("yt_ok"):
            self.ytdlp_version.setText(
                "yt-dlp: " + (info.get("yt_version") or "found")
            )
        else:
            self.ytdlp_version.setText("yt-dlp: not found")

        if info.get("ffmpeg_ok"):
            self.ffmpeg_version.setText(
                "FFmpeg: " + (info.get("ffmpeg_version") or "found")
            )
        else:
            self.ffmpeg_version.setText("FFmpeg: not found")


    def update_ytdlp(self):
        if getattr(sys, "frozen", False):
            open_url("https://github.com/yt-dlp/yt-dlp/releases")
            return
        cmd = [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"]
        self.start_stream(
            cmd,
            {"kind": "generic", "output_dir": str(app_dir()), "download_dir": str(app_dir()), "started": time.time()},
        )

    def check_ffmpeg(self):
        dlg = DependencyDialog(self, self.lang)
        self.apply_theme()
        dlg.exec()
        self.refresh_dependency_labels()

    def closeEvent(self, event):
        self.save_settings()

        for worker in [self.analyze_worker, self.stream_worker]:
            if worker and worker.isRunning():
                worker.cancel()

        active_previews = [worker for worker in self.preview_workers if worker.isRunning()]
        if active_previews:
            for worker in active_previews:
                worker.requestInterruption()
            event.ignore()
            QTimer.singleShot(150, self.close)
            return

        # Short background probes should be allowed to finish cleanly.
        for worker in [self.network_worker, self.dependency_status_worker, self.preview_worker]:
            if worker and worker.isRunning():
                worker.wait(250)

        event.accept()
