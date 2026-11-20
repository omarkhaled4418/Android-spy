"""
DashboardWindow — PySide6 main window for the parental-control desktop app.
"""

from __future__ import annotations

import datetime
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import (
    QObject,
    QThread,
    QTimer,
    Signal,
    Slot,
    Qt,
)
from PySide6.QtGui import QClipboard, QFont, QPixmap, QIcon, QPainter, QColor
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QGroupBox,
    QFormLayout,
    QSizePolicy,
    QScrollArea,
)

from api_client import ApiClient, ApiResult
from config_manager import ConfigManager

# ------------------------------------------------------------------ #
# Style sheet
# ------------------------------------------------------------------ #

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #2b2b2b;
    color: #e0e0e0;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #555;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 14px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QPushButton {
    background-color: #3c3c3c;
    color: #e0e0e0;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 6px 14px;
    min-height: 24px;
}
QPushButton:hover { background-color: #505050; }
QPushButton:pressed { background-color: #606060; }
QPushButton:disabled { color: #777; background-color: #333; }
QPushButton#startBtn { background-color: #2e7d32; }
QPushButton#startBtn:hover { background-color: #388e3c; }
QPushButton#stopBtn  { background-color: #c62828; }
QPushButton#stopBtn:hover { background-color: #d32f2f; }
QPushButton#screenshotBtn { background-color: #1565c0; }
QPushButton#screenshotBtn:hover { background-color: #1976d2; }
QPushButton#screenshotBtn:disabled { background-color: #333; }
QPushButton#liveBtn { background-color: #e11d48; }
QPushButton#liveBtn:hover { background-color: #be123c; }
QPushButton#liveBtn:disabled { background-color: #333; }
QListWidget {
    background-color: #333;
    border: 1px solid #555;
    border-radius: 4px;
}
QListWidget::item { padding: 4px; }
QListWidget::item:selected { background-color: #1565c0; }
QTextEdit {
    background-color: #1e1e1e;
    border: 1px solid #555;
    border-radius: 4px;
    font-family: Consolas, monospace;
    font-size: 12px;
}
QLineEdit {
    background-color: #333;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 4px;
}
QLabel#placeholder {
    color: #888;
    font-size: 15px;
}
"""

# ------------------------------------------------------------------ #
# Worker — runs a callable in a QThread, emits results via signals
# ------------------------------------------------------------------ #


class _WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)


class Worker(QThread):
    """Generic worker that runs *fn* in a background thread."""

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = _WorkerSignals()

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception as exc:
            self.signals.error.emit(str(exc))


# ------------------------------------------------------------------ #
# Dashboard window
# ------------------------------------------------------------------ #


class DashboardWindow(QMainWindow):
    def __init__(self, config: ConfigManager):
        super().__init__()
        self.config = config
        self.api = ApiClient(config.base_url, config.api_key)
        self._server_proc: Optional[subprocess.Popen] = None
        self._devices: List[Dict[str, Any]] = []
        self._selected_device: Optional[Dict[str, Any]] = None
        self._current_pixmap: Optional[QPixmap] = None
        self._workers: List[Worker] = []  # prevent GC
        self._is_live_monitoring: bool = False
        self._live_timer: Optional[QTimer] = None
        self._live_frame_count: int = 0
        self._live_fetching: bool = False

        self.setWindowTitle("Parental Control Dashboard")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

        self._build_ui()
        self.setStyleSheet(DARK_STYLE)

        # -- timers ------------------------------------------------- #
        self._device_timer = QTimer(self)
        self._device_timer.timeout.connect(self._refresh_devices)
        self._device_timer.start(15_000)

        self._server_status_timer = QTimer(self)
        self._server_status_timer.timeout.connect(self._check_server_status)
        self._server_status_timer.start(5_000)

        # -- initial data ------------------------------------------- #
        self._check_server_status()
        self._refresh_devices()

    # ================================================================ #
    #  UI construction
    # ================================================================ #

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        # ---- top bar ---------------------------------------------- #
        top_bar = self._build_top_bar()
        root_layout.addLayout(top_bar)

        # ---- main splitter (left | center) ------------------------ #
        splitter = QSplitter(Qt.Horizontal)

        left_widget = self._build_left_panel()
        left_widget.setMinimumWidth(300)
        left_widget.setMaximumWidth(400)
        splitter.addWidget(left_widget)

        center_widget = self._build_center_panel()
        splitter.addWidget(center_widget)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root_layout.addWidget(splitter, stretch=1)

        # ---- bottom panel (logs) ---------------------------------- #
        bottom = self._build_bottom_panel()
        root_layout.addWidget(bottom)

    # ---- top bar -------------------------------------------------- #

    def _build_top_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()

        title = QLabel("Parental Control Dashboard")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        layout.addStretch()

        self._status_indicator = QLabel("●")
        self._status_indicator.setStyleSheet("font-size: 18px; color: #f44336;")
        layout.addWidget(self._status_indicator)

        self._status_text = QLabel("Server: unknown")
        layout.addWidget(self._status_text)

        layout.addSpacing(16)

        self._start_btn = QPushButton("Start Server")
        self._start_btn.setObjectName("startBtn")
        self._start_btn.clicked.connect(self._start_server)
        layout.addWidget(self._start_btn)

        self._stop_btn = QPushButton("Stop Server")
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_server)
        layout.addWidget(self._stop_btn)

        return layout

    # ---- left panel ----------------------------------------------- #

    def _build_left_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Device list
        grp_devices = QGroupBox("Devices")
        grp_layout = QVBoxLayout(grp_devices)

        self._device_list = QListWidget()
        self._device_list.currentItemChanged.connect(self._on_device_selected)
        grp_layout.addWidget(self._device_list)

        layout.addWidget(grp_devices)

        # Device details
        grp_details = QGroupBox("Device Details")
        form = QFormLayout(grp_details)

        self._detail_id = QLabel("-")
        self._detail_id.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow("ID:", self._detail_id)

        self._detail_name = QLabel("-")
        form.addRow("Name:", self._detail_name)

        self._detail_model = QLabel("-")
        form.addRow("Model:", self._detail_model)

        self._detail_android = QLabel("-")
        form.addRow("Android:", self._detail_android)

        self._detail_app = QLabel("-")
        form.addRow("App ver:", self._detail_app)

        self._detail_status = QLabel("-")
        form.addRow("Status:", self._detail_status)

        self._detail_last_seen = QLabel("-")
        form.addRow("Last seen:", self._detail_last_seen)

        self._detail_registered = QLabel("-")
        form.addRow("Registered:", self._detail_registered)

        layout.addWidget(grp_details)

        # API key + server URL
        grp_config = QGroupBox("Configuration")
        cfg_layout = QVBoxLayout(grp_config)

        # API key row
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("API Key:"))
        self._api_key_label = QLabel(self._masked_key())
        self._api_key_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        key_layout.addWidget(self._api_key_label, stretch=1)
        copy_btn = QPushButton("Copy")
        copy_btn.setMaximumWidth(60)
        copy_btn.clicked.connect(self._copy_api_key)
        key_layout.addWidget(copy_btn)
        cfg_layout.addLayout(key_layout)

        # Server URL row
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Server URL:"))
        self._url_edit = QLineEdit(self.config.ngrok_url or "")
        self._url_edit.setPlaceholderText("Leave empty for localhost")
        url_layout.addWidget(self._url_edit, stretch=1)
        save_url_btn = QPushButton("Save")
        save_url_btn.setMaximumWidth(60)
        save_url_btn.clicked.connect(self._save_server_url)
        url_layout.addWidget(save_url_btn)
        cfg_layout.addLayout(url_layout)

        layout.addWidget(grp_config)
        layout.addStretch()
        return widget

    # ---- center panel --------------------------------------------- #

    def _build_center_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 0, 0, 0)

        # Screenshot and live controls
        ctrl_layout = QHBoxLayout()
        self._live_btn = QPushButton("🔴  Live Monitor")
        self._live_btn.setObjectName("liveBtn")
        self._live_btn.setEnabled(False)
        self._live_btn.clicked.connect(self._toggle_live_monitoring)
        ctrl_layout.addWidget(self._live_btn)

        self._screenshot_btn = QPushButton("📷  Request Screenshot")
        self._screenshot_btn.setObjectName("screenshotBtn")
        self._screenshot_btn.setEnabled(False)
        self._screenshot_btn.clicked.connect(self._request_screenshot)
        ctrl_layout.addWidget(self._screenshot_btn)

        self._screenshot_status = QLabel("")
        ctrl_layout.addWidget(self._screenshot_status, stretch=1)
        layout.addLayout(ctrl_layout)

        # Screenshot preview area
        self._screenshot_label = QLabel("No screenshot yet")
        self._screenshot_label.setObjectName("placeholder")
        self._screenshot_label.setAlignment(Qt.AlignCenter)
        self._screenshot_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        self._screenshot_label.setMinimumHeight(300)
        self._screenshot_label.setStyleSheet(
            "background-color: #1e1e1e; border: 1px solid #555; border-radius: 4px;"
        )
        layout.addWidget(self._screenshot_label, stretch=1)

        # Timestamp + Save
        bottom_row = QHBoxLayout()
        self._screenshot_ts = QLabel("")
        bottom_row.addWidget(self._screenshot_ts)
        bottom_row.addStretch()

        self._save_btn = QPushButton("Save Screenshot")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_screenshot)
        bottom_row.addWidget(self._save_btn)
        layout.addLayout(bottom_row)

        return widget

    # ---- bottom panel (logs) -------------------------------------- #

    def _build_bottom_panel(self) -> QGroupBox:
        grp = QGroupBox("Logs")
        layout = QVBoxLayout(grp)

        self._log_edit = QTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setMaximumHeight(160)
        layout.addWidget(self._log_edit)

        clear_btn = QPushButton("Clear Logs")
        clear_btn.setMaximumWidth(100)
        clear_btn.clicked.connect(self._log_edit.clear)
        layout.addWidget(clear_btn, alignment=Qt.AlignRight)

        return grp

    # ================================================================ #
    #  Logging
    # ================================================================ #

    def _log(self, msg: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._log_edit.append(f"[{ts}] {msg}")

    # ================================================================ #
    #  Server management
    # ================================================================ #

    def _start_server(self):
        if self._server_proc and self._server_proc.poll() is None:
            self._log("Server already running.")
            return

        project_root = str(Path(__file__).resolve().parent.parent)
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(self.config.server_port),
        ]
        try:
            self._server_proc = subprocess.Popen(
                cmd,
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
                if sys.platform == "win32"
                else 0,
            )
            self._log(f"Server started (PID {self._server_proc.pid})")
            self._start_btn.setEnabled(False)
            self._stop_btn.setEnabled(True)

            # Read stdout in a thread
            self._start_log_reader()

            # Reload config after a moment (backend generates api_key)
            QTimer.singleShot(3000, self._reload_config)

        except Exception as exc:
            self._log(f"Failed to start server: {exc}")

    def _stop_server(self):
        if self._server_proc and self._server_proc.poll() is None:
            self._server_proc.terminate()
            try:
                self._server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._server_proc.kill()
            self._log("Server stopped.")
        self._server_proc = None
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._set_server_status(False)

    def _start_log_reader(self):
        """Read server stdout in a background thread."""

        def _read():
            proc = self._server_proc
            if proc and proc.stdout:
                for line in proc.stdout:
                    stripped = line.rstrip("\n")
                    if stripped:
                        return stripped  # one line at a time
            return None

        def _loop():
            if self._server_proc is None or self._server_proc.poll() is not None:
                return
            w = Worker(_read)
            self._workers.append(w)
            w.signals.finished.connect(lambda text: self._on_server_line(text, _loop))
            w.start()

        _loop()

    def _on_server_line(self, text, loop_fn):
        if text:
            self._log(f"[server] {text}")
        loop_fn()

    def _reload_config(self):
        self.config.load()
        self.api.api_key = self.config.api_key
        self.api.base_url = self.config.base_url
        self._api_key_label.setText(self._masked_key())
        self._log("Config reloaded.")

    # ================================================================ #
    #  Server status check
    # ================================================================ #

    def _check_server_status(self):
        w = Worker(self.api.health)
        self._workers.append(w)
        w.signals.finished.connect(self._on_health_result)
        w.start()

    @Slot(object)
    def _on_health_result(self, result: ApiResult):
        self._set_server_status(result.ok)

    def _set_server_status(self, online: bool):
        if online:
            self._status_indicator.setStyleSheet("font-size: 18px; color: #4CAF50;")
            self._status_text.setText("Server: online")
        else:
            self._status_indicator.setStyleSheet("font-size: 18px; color: #f44336;")
            self._status_text.setText("Server: offline")

    # ================================================================ #
    #  Device list
    # ================================================================ #

    def _refresh_devices(self):
        w = Worker(self.api.list_devices)
        self._workers.append(w)
        w.signals.finished.connect(self._on_devices_result)
        w.signals.error.connect(lambda e: self._log(f"Device refresh error: {e}"))
        w.start()

    @Slot(object)
    def _on_devices_result(self, result: ApiResult):
        if not result.ok:
            return
        self._devices = result.data.get("devices", [])
        current_id = None
        if self._selected_device:
            current_id = self._selected_device.get("device_id")

        self._device_list.blockSignals(True)
        self._device_list.clear()
        select_idx = -1
        for i, dev in enumerate(self._devices):
            online = dev.get("is_online", False)
            indicator = "🟢" if online else "🔴"
            status_word = "Online" if online else "Offline"
            text = f"{indicator}  {dev.get('device_name', 'Unknown')}  ({dev.get('device_model', '')})"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, i)
            self._device_list.addItem(item)
            if dev.get("device_id") == current_id:
                select_idx = i

        self._device_list.blockSignals(False)

        if select_idx >= 0:
            self._device_list.setCurrentRow(select_idx)
        elif self._device_list.count() > 0:
            pass  # don't auto-select

        self._update_screenshot_btn()

    def _on_device_selected(self, current: Optional[QListWidgetItem], _prev):
        if current is None:
            self._selected_device = None
            self._clear_device_details()
            self._update_screenshot_btn()
            return
        idx = current.data(Qt.UserRole)
        if idx is not None and 0 <= idx < len(self._devices):
            self._selected_device = self._devices[idx]
            self._show_device_details(self._selected_device)
        self._update_screenshot_btn()

    def _show_device_details(self, dev: Dict[str, Any]):
        self._detail_id.setText(dev.get("device_id", "-"))
        self._detail_name.setText(dev.get("device_name", "-"))
        self._detail_model.setText(dev.get("device_model", "-"))
        self._detail_android.setText(dev.get("android_version", "-"))
        self._detail_app.setText(dev.get("app_version", "-"))
        online = dev.get("is_online", False)
        if online:
            self._detail_status.setText("Online")
            self._detail_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self._detail_status.setText("Offline")
            self._detail_status.setStyleSheet("color: #f44336; font-weight: bold;")
        self._detail_last_seen.setText(dev.get("last_seen", "-"))
        self._detail_registered.setText(dev.get("registered_at", "-"))

    def _clear_device_details(self):
        for lbl in (
            self._detail_id,
            self._detail_name,
            self._detail_model,
            self._detail_android,
            self._detail_app,
            self._detail_last_seen,
            self._detail_registered,
        ):
            lbl.setText("-")
        self._detail_status.setText("-")
        self._detail_status.setStyleSheet("")

    def _update_screenshot_btn(self):
        enabled = (
            self._selected_device is not None
            and self._selected_device.get("is_online", False)
        )
        self._screenshot_btn.setEnabled(enabled and not self._is_live_monitoring)
        self._live_btn.setEnabled(enabled or self._is_live_monitoring)

    def _toggle_live_monitoring(self):
        if self._is_live_monitoring:
            self._stop_live_monitoring()
        else:
            self._start_live_monitoring()

    def _start_live_monitoring(self):
        if not self._selected_device:
            return
        device_id = self._selected_device["device_id"]
        self._is_live_monitoring = True
        self._live_frame_count = 0
        self._live_btn.setText("⏹️  Stop Live Monitor")
        self._live_btn.setStyleSheet("background-color: #991b1b;")
        self._screenshot_btn.setEnabled(False)
        self._screenshot_status.setText("🔴 LIVE MONITORING — Initializing...")
        self._screenshot_status.setStyleSheet("color: #ff4d6d; font-weight: bold;")
        self._log(f"Starting live monitoring for device {device_id}...")

        w = Worker(self.api.start_live_monitoring, device_id)
        self._workers.append(w)
        w.start()

        if self._live_timer is None:
            self._live_timer = QTimer(self)
            self._live_timer.timeout.connect(self._poll_live_frame)
        self._live_timer.start(100)

    def _stop_live_monitoring(self):
        if not self._is_live_monitoring:
            return
        self._is_live_monitoring = False
        if self._live_timer:
            self._live_timer.stop()
        self._live_btn.setText("🔴  Live Monitor")
        self._live_btn.setStyleSheet("")
        self._screenshot_status.setText("Live monitoring stopped.")
        self._screenshot_status.setStyleSheet("color: #e0e0e0;")
        self._update_screenshot_btn()
        self._log("Stopping live monitoring...")

        if self._selected_device:
            device_id = self._selected_device["device_id"]
            w = Worker(self.api.stop_live_monitoring, device_id)
            self._workers.append(w)
            w.start()

    def _poll_live_frame(self):
        if not self._is_live_monitoring or not self._selected_device or self._live_fetching:
            return
        self._live_fetching = True
        device_id = self._selected_device["device_id"]
        w = Worker(self.api.get_latest_live_frame, device_id)
        self._workers.append(w)
        w.signals.finished.connect(self._on_live_frame_fetched)
        w.signals.error.connect(lambda _err: self._on_live_frame_error())
        w.start()

    @Slot(object)
    def _on_live_frame_fetched(self, result: ApiResult):
        self._live_fetching = False
        if not self._is_live_monitoring:
            return
        if result.ok and result.raw_bytes:
            pixmap = QPixmap()
            if pixmap.loadFromData(result.raw_bytes):
                self._current_pixmap = pixmap
                self._display_pixmap(pixmap)
                self._live_frame_count += 1
                self._save_btn.setEnabled(True)
                self._screenshot_ts.setText(f"Live Frame #{self._live_frame_count}")
                self._screenshot_status.setText(f"🔴 LIVE MONITORING — #{self._live_frame_count}")
                self._screenshot_status.setStyleSheet("color: #ff4d6d; font-weight: bold;")

    def _on_live_frame_error(self):
        self._live_fetching = False

    # ================================================================ #
    #  Configuration helpers
    # ================================================================ #

    def _masked_key(self) -> str:
        key = self.config.api_key
        if not key:
            return "(not set)"
        if len(key) <= 8:
            return "●" * len(key)
        return key[:4] + "●" * (len(key) - 8) + key[-4:]

    def _copy_api_key(self):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.config.api_key)
            self._log("API key copied to clipboard.")

    def _save_server_url(self):
        url = self._url_edit.text().strip()
        self.config.ngrok_url = url
        self.config.save()
        self.api.base_url = self.config.base_url
        self._log(f"Server URL updated → {self.config.base_url}")

    # ================================================================ #
    #  Screenshot workflow
    # ================================================================ #

    def _request_screenshot(self):
        if not self._selected_device:
            return
        device_id = self._selected_device["device_id"]
        self._screenshot_btn.setEnabled(False)
        self._screenshot_status.setText("Requesting...")
        self._screenshot_status.setStyleSheet("color: #FFC107;")
        self._log(f"Requesting screenshot from device {device_id}")

        w = Worker(self.api.request_screenshot, device_id)
        self._workers.append(w)
        w.signals.finished.connect(self._on_screenshot_requested)
        w.signals.error.connect(self._on_screenshot_error)
        w.start()

    @Slot(object)
    def _on_screenshot_requested(self, result: ApiResult):
        if not result.ok:
            self._screenshot_status.setText(f"Error: {result.error}")
            self._screenshot_status.setStyleSheet("color: #f44336;")
            self._log(f"Screenshot request failed: {result.error}")
            self._update_screenshot_btn()
            return

        command_id = result.data.get("command_id", "")
        self._log(f"Screenshot command created: {command_id}")
        self._screenshot_status.setText("Waiting for device...")
        self._screenshot_status.setStyleSheet("color: #FFC107;")

        # Start polling
        self._poll_screenshot_status(command_id, 0)

    def _poll_screenshot_status(self, command_id: str, attempt: int):
        if attempt >= 15:  # 15 * 2s = 30s
            self._screenshot_status.setText("Request timed out")
            self._screenshot_status.setStyleSheet("color: #f44336;")
            self._log("Screenshot request timed out after 30 seconds.")
            self._update_screenshot_btn()
            return

        def _check():
            import time
            time.sleep(2)
            return self.api.get_screenshot_status(command_id)

        w = Worker(_check)
        self._workers.append(w)
        w.signals.finished.connect(
            lambda r: self._on_poll_result(r, command_id, attempt)
        )
        w.signals.error.connect(self._on_screenshot_error)
        w.start()

    @Slot(object)
    def _on_poll_result(self, result: ApiResult, command_id: str, attempt: int):
        if not result.ok:
            self._log(f"Status poll error: {result.error}")
            self._poll_screenshot_status(command_id, attempt + 1)
            return

        status = result.data.get("status", "pending")
        self._log(f"Command {command_id}: status={status}")

        if status == "completed":
            screenshot_id = result.data.get("screenshot_id", "")
            self._screenshot_status.setText("Screenshot received!")
            self._screenshot_status.setStyleSheet("color: #4CAF50;")
            self._fetch_screenshot_image(screenshot_id)
        elif status == "expired":
            self._screenshot_status.setText("Request expired")
            self._screenshot_status.setStyleSheet("color: #f44336;")
            self._log("Screenshot command expired.")
            self._update_screenshot_btn()
        else:
            self._poll_screenshot_status(command_id, attempt + 1)

    def _fetch_screenshot_image(self, screenshot_id: str):
        self._log(f"Fetching screenshot image {screenshot_id}")
        w = Worker(self.api.get_screenshot_image, screenshot_id)
        self._workers.append(w)
        w.signals.finished.connect(
            lambda r: self._on_image_fetched(r, screenshot_id)
        )
        w.signals.error.connect(self._on_screenshot_error)
        w.start()

    @Slot(object)
    def _on_image_fetched(self, result: ApiResult, screenshot_id: str):
        self._update_screenshot_btn()
        if not result.ok or not result.raw_bytes:
            self._log(f"Failed to fetch image: {result.error}")
            self._screenshot_status.setText("Failed to load image")
            self._screenshot_status.setStyleSheet("color: #f44336;")
            return

        pixmap = QPixmap()
        pixmap.loadFromData(result.raw_bytes)
        if pixmap.isNull():
            self._log("Received invalid image data.")
            return

        self._current_pixmap = pixmap
        self._display_pixmap(pixmap)
        self._screenshot_ts.setText(
            f"Received: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self._save_btn.setEnabled(True)
        self._log("Screenshot displayed.")

    def _display_pixmap(self, pixmap: QPixmap):
        """Scale pixmap to fit the label while keeping aspect ratio."""
        label_size = self._screenshot_label.size()
        scaled = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._screenshot_label.setPixmap(scaled)

    @Slot(str)
    def _on_screenshot_error(self, error: str):
        self._screenshot_status.setText(f"Error: {error}")
        self._screenshot_status.setStyleSheet("color: #f44336;")
        self._log(f"Screenshot error: {error}")
        self._update_screenshot_btn()

    # ---- save ----------------------------------------------------- #

    def _save_screenshot(self):
        if not self._current_pixmap:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Screenshot", "screenshot.png", "Images (*.png *.jpg)"
        )
        if path:
            self._current_pixmap.save(path)
            self._log(f"Screenshot saved to {path}")

    # ================================================================ #
    #  Resize event — rescale screenshot
    # ================================================================ #

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._current_pixmap and not self._current_pixmap.isNull():
            self._display_pixmap(self._current_pixmap)

    # ================================================================ #
    #  Cleanup
    # ================================================================ #

    def closeEvent(self, event):
        if self._is_live_monitoring:
            self._stop_live_monitoring()
        self._device_timer.stop()
        self._server_status_timer.stop()
        if self._server_proc and self._server_proc.poll() is None:
            self._server_proc.terminate()
            try:
                self._server_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._server_proc.kill()
        # Wait for workers
        for w in self._workers:
            if w.isRunning():
                w.quit()
                w.wait(1000)
        super().closeEvent(event)
