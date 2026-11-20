"""
Configuration manager — reads config.json for api_key, server_port, ngrok_url.
"""

import json
import os
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


class ConfigManager:
    """Reads and writes the shared config.json."""

    def __init__(self):
        self.api_key: str = ""
        self.server_host: str = "0.0.0.0"
        self.server_port: int = 8080
        self.ngrok_url: str = "https://coat-icy-lushly.ngrok-free.dev"
        self.screenshot_dir: str = str(
            Path(__file__).resolve().parent.parent / "screenshots"
        )
        self.heartbeat_timeout_seconds: int = 45
        self.load()

    # ------------------------------------------------------------------ #
    # Public helpers
    # ------------------------------------------------------------------ #

    @property
    def base_url(self) -> str:
        """Return the ngrok URL if set, otherwise localhost."""
        if self.ngrok_url:
            return self.ngrok_url.rstrip("/")
        return f"http://localhost:{self.server_port}"

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def load(self):
        """Load values from config.json (if it exists)."""
        if not CONFIG_PATH.exists():
            return
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.api_key = data.get("api_key", self.api_key)
            self.server_host = data.get("server_host", self.server_host)
            self.server_port = data.get("server_port", self.server_port)
            self.ngrok_url = data.get("ngrok_url", self.ngrok_url)
            self.screenshot_dir = data.get("screenshot_dir", self.screenshot_dir)
            self.heartbeat_timeout_seconds = data.get(
                "heartbeat_timeout_seconds", self.heartbeat_timeout_seconds
            )
        except (json.JSONDecodeError, OSError):
            pass

    def save(self):
        """Persist current values back to config.json."""
        data: dict = {}
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except (json.JSONDecodeError, OSError):
                pass
        data.update(
            {
                "api_key": self.api_key,
                "server_host": self.server_host,
                "server_port": self.server_port,
                "ngrok_url": self.ngrok_url,
                "screenshot_dir": self.screenshot_dir,
                "heartbeat_timeout_seconds": self.heartbeat_timeout_seconds,
            }
        )
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=4)
