"""Configuration management for the Parental Control System."""

import json
import logging
import os
import secrets
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.json"
ENV_PATH = PROJECT_ROOT / ".env"

DEFAULT_CONFIG = {
    "api_key": "",
    "server_host": "0.0.0.0",
    "server_port": 8080,
    "screenshot_dir": str(PROJECT_ROOT / "screenshots"),
    "heartbeat_timeout_seconds": 45,
    "ngrok_url": "",
}


def _load_env_file(path: Path) -> dict:
    """Parse simple KEY=VALUE pairs from a .env file."""
    values = {}
    if not path.exists():
        return values
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    values[k.strip().lower()] = v.strip().strip('"').strip("'")
    except Exception as e:
        logger.warning("Could not read .env file: %s", e)
    return values


def load_config() -> dict:
    """Load config from disk (.env and config.json), creating it if necessary."""
    env_file_data = _load_env_file(ENV_PATH)

    config_data = DEFAULT_CONFIG.copy()

    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config_data.update(json.load(f))
            logger.info("Loaded configuration from %s", CONFIG_PATH)
        except Exception as e:
            logger.warning("Failed to load %s: %s", CONFIG_PATH, e)
    else:
        # Create default config.json
        config_data["api_key"] = secrets.token_urlsafe(32)
        save_config(config_data)
        logger.info("Created new configuration at %s", CONFIG_PATH)

    # Allow .env and environment variables to override or populate settings
    env_mapping = {
        "api_key": ["API_KEY"],
        "server_host": ["SERVER_HOST", "HOST"],
        "server_port": ["SERVER_PORT", "PORT"],
        "screenshot_dir": ["SCREENSHOT_DIR"],
        "heartbeat_timeout_seconds": ["HEARTBEAT_TIMEOUT_SECONDS"],
        "ngrok_url": ["NGROK_URL"],
    }

    for key, env_vars in env_mapping.items():
        for env_var in env_vars:
            val = os.environ.get(env_var) or env_file_data.get(env_var.lower())
            if val is not None and val != "":
                if key in ("server_port", "heartbeat_timeout_seconds"):
                    try:
                        config_data[key] = int(val)
                    except ValueError:
                        pass
                else:
                    config_data[key] = val
                break

    # Resolve screenshot_dir to absolute path
    if "screenshot_dir" in config_data:
        p = Path(config_data["screenshot_dir"])
        if not p.is_absolute():
            config_data["screenshot_dir"] = str((PROJECT_ROOT / p).resolve())

    # Ensure the API key exists
    if not config_data.get("api_key"):
        config_data["api_key"] = secrets.token_urlsafe(32)
        save_config(config_data)

    return config_data


def save_config(config_data: dict) -> None:
    """Persist config to disk."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)
    logger.info("Saved configuration to %s", CONFIG_PATH)


# Singleton loaded at import time by main.py; other modules import this.
config: dict = {}
