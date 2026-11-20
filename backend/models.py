"""Pydantic models for all request/response schemas."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


# ── Device models ──────────────────────────────────────────────────────────

class DeviceRegisterRequest(BaseModel):
    device_id: str
    device_name: str
    device_model: str
    android_version: str
    app_version: str


class DeviceRegisterResponse(BaseModel):
    success: bool
    device_id: str
    message: str


class PendingCommand(BaseModel):
    command_id: str
    command_type: str
    created_at: str


class HeartbeatResponse(BaseModel):
    success: bool
    pending_commands: List[PendingCommand]
    is_live: Optional[bool] = False


class DeviceInfo(BaseModel):
    device_id: str
    device_name: str
    device_model: str
    android_version: str
    app_version: str
    is_online: bool
    last_seen: str
    registered_at: str


class DeviceListResponse(BaseModel):
    devices: List[DeviceInfo]


# ── Screenshot models ─────────────────────────────────────────────────────

class ScreenshotRequestResponse(BaseModel):
    success: bool
    command_id: str
    message: str


class ScreenshotUploadResponse(BaseModel):
    success: bool
    screenshot_id: str
    message: str


class ScreenshotInfo(BaseModel):
    screenshot_id: str
    device_id: str
    command_id: str
    filename: str
    file_size: int
    created_at: str


class ScreenshotListResponse(BaseModel):
    screenshots: List[ScreenshotInfo]
    total: int


class ScreenshotStatusResponse(BaseModel):
    command_id: str
    status: str
    screenshot_id: Optional[str]
    created_at: str


# ── Health ─────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    timestamp: str
