"""
API client — wraps every backend endpoint with typed helpers.
All calls include the Bearer token and handle connection errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests


# ------------------------------------------------------------------ #
# Lightweight result wrapper
# ------------------------------------------------------------------ #


@dataclass
class ApiResult:
    """Uniform result for every API call."""

    ok: bool
    status_code: int = 0
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    raw_bytes: Optional[bytes] = None


# ------------------------------------------------------------------ #
# Client
# ------------------------------------------------------------------ #


class ApiClient:
    """HTTP client for the parental-control backend."""

    def __init__(self, base_url: str, api_key: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    # -- helpers ---------------------------------------------------- #

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[dict] = None,
        params: Optional[dict] = None,
        files: Optional[dict] = None,
        data: Optional[dict] = None,
        stream: bool = False,
    ) -> ApiResult:
        try:
            resp = requests.request(
                method,
                self._url(path),
                headers=self._headers(),
                json=json_body,
                params=params,
                files=files,
                data=data,
                timeout=self.timeout,
                stream=stream,
            )
            if stream and resp.status_code == 200:
                return ApiResult(
                    ok=True,
                    status_code=resp.status_code,
                    raw_bytes=resp.content,
                )
            try:
                body = resp.json()
            except ValueError:
                body = {}
            if resp.status_code >= 400:
                detail = body.get("detail", resp.text)
                return ApiResult(
                    ok=False,
                    status_code=resp.status_code,
                    data=body,
                    error=str(detail),
                )
            return ApiResult(ok=True, status_code=resp.status_code, data=body)
        except requests.ConnectionError:
            return ApiResult(ok=False, error="Connection refused — is the server running?")
        except requests.Timeout:
            return ApiResult(ok=False, error="Request timed out")
        except requests.RequestException as exc:
            return ApiResult(ok=False, error=str(exc))

    # ------------------------------------------------------------------ #
    # Health
    # ------------------------------------------------------------------ #

    def health(self) -> ApiResult:
        """GET /api/health (no auth required)."""
        try:
            resp = requests.get(
                self._url("/api/health"), timeout=self.timeout
            )
            return ApiResult(ok=True, status_code=resp.status_code, data=resp.json())
        except Exception:
            return ApiResult(ok=False, error="Server unreachable")

    # ------------------------------------------------------------------ #
    # Devices
    # ------------------------------------------------------------------ #

    def register_device(
        self,
        device_id: str,
        device_name: str,
        device_model: str,
        android_version: str,
        app_version: str,
    ) -> ApiResult:
        """POST /api/devices/register"""
        return self._request(
            "POST",
            "/api/devices/register",
            json_body={
                "device_id": device_id,
                "device_name": device_name,
                "device_model": device_model,
                "android_version": android_version,
                "app_version": app_version,
            },
        )

    def list_devices(self) -> ApiResult:
        """GET /api/devices"""
        return self._request("GET", "/api/devices")

    def device_heartbeat(self, device_id: str) -> ApiResult:
        """POST /api/devices/{device_id}/heartbeat"""
        return self._request("POST", f"/api/devices/{device_id}/heartbeat")

    # ------------------------------------------------------------------ #
    # Screenshots
    # ------------------------------------------------------------------ #

    def request_screenshot(self, device_id: str) -> ApiResult:
        """POST /api/screenshots/request/{device_id}"""
        return self._request("POST", f"/api/screenshots/request/{device_id}")

    def get_screenshot_status(self, command_id: str) -> ApiResult:
        """GET /api/screenshots/status/{command_id}"""
        return self._request("GET", f"/api/screenshots/status/{command_id}")

    def get_screenshot_image(self, screenshot_id: str) -> ApiResult:
        """GET /api/screenshots/{screenshot_id}/image — returns raw bytes."""
        return self._request(
            "GET", f"/api/screenshots/{screenshot_id}/image", stream=True
        )

    def list_screenshots(
        self,
        device_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ApiResult:
        """GET /api/screenshots"""
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if device_id:
            params["device_id"] = device_id
        return self._request("GET", "/api/screenshots", params=params)

    def upload_screenshot(
        self,
        device_id: str,
        command_id: str,
        image_path: str,
    ) -> ApiResult:
        """POST /api/screenshots/upload (multipart)."""
        with open(image_path, "rb") as img:
            return self._request(
                "POST",
                "/api/screenshots/upload",
                data={"device_id": device_id, "command_id": command_id},
                files={"image": ("screenshot.png", img, "image/png")},
            )

    # ------------------------------------------------------------------ #
    # Live Monitoring
    # ------------------------------------------------------------------ #

    def start_live_monitoring(self, device_id: str) -> ApiResult:
        """POST /api/live/start/{device_id}"""
        return self._request("POST", f"/api/live/start/{device_id}")

    def stop_live_monitoring(self, device_id: str) -> ApiResult:
        """POST /api/live/stop/{device_id}"""
        return self._request("POST", f"/api/live/stop/{device_id}")

    def get_live_status(self, device_id: str) -> ApiResult:
        """GET /api/live/status/{device_id}"""
        return self._request("GET", f"/api/live/status/{device_id}")

    def get_latest_live_frame(self, device_id: str) -> ApiResult:
        """GET /api/live/latest/{device_id} — returns raw JPEG bytes."""
        return self._request("GET", f"/api/live/latest/{device_id}", stream=True)
