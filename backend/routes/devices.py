"""Device-related routes: register, heartbeat, list."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import verify_api_key
from ..database import get_db
from .live import get_session
from ..models import (
    DeviceInfo,
    DeviceListResponse,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    HeartbeatResponse,
    PendingCommand,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.post("/register", response_model=DeviceRegisterResponse)
async def register_device(
    body: DeviceRegisterRequest,
    _key: str = Depends(verify_api_key),
):
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Check for duplicate
    row = await db.execute(
        "SELECT device_id FROM devices WHERE device_id = ?", (body.device_id,)
    )
    existing = await row.fetchone()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device already registered",
        )

    await db.execute(
        """INSERT INTO devices
           (device_id, device_name, device_model, android_version, app_version, is_online, last_seen, registered_at)
           VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
        (
            body.device_id,
            body.device_name,
            body.device_model,
            body.android_version,
            body.app_version,
            now,
            now,
        ),
    )
    await db.commit()
    logger.info("Device registered: %s (%s)", body.device_id, body.device_name)

    return DeviceRegisterResponse(
        success=True,
        device_id=body.device_id,
        message="Device registered successfully",
    )


@router.post("/{device_id}/heartbeat", response_model=HeartbeatResponse)
async def device_heartbeat(
    device_id: str,
    _key: str = Depends(verify_api_key),
):
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Verify device exists
    row = await db.execute(
        "SELECT device_id FROM devices WHERE device_id = ?", (device_id,)
    )
    device = await row.fetchone()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    # Update last_seen and mark online
    await db.execute(
        "UPDATE devices SET last_seen = ?, is_online = 1 WHERE device_id = ?",
        (now, device_id),
    )
    await db.commit()

    # Fetch pending commands for this device
    cursor = await db.execute(
        "SELECT id, command_type, created_at FROM commands WHERE device_id = ? AND status = 'pending'",
        (device_id,),
    )
    rows = await cursor.fetchall()
    pending = [
        PendingCommand(
            command_id=r["id"],
            command_type=r["command_type"],
            created_at=r["created_at"],
        )
        for r in rows
    ]

    session = get_session(device_id)
    logger.debug("Heartbeat from %s — %d pending command(s), is_live=%s", device_id, len(pending), session.is_active)
    return HeartbeatResponse(success=True, pending_commands=pending, is_live=session.is_active)


@router.get("", response_model=DeviceListResponse)
async def list_devices(
    _key: str = Depends(verify_api_key),
):
    db = await get_db()
    cursor = await db.execute("SELECT * FROM devices ORDER BY registered_at DESC")
    rows = await cursor.fetchall()
    devices = [
        DeviceInfo(
            device_id=r["device_id"],
            device_name=r["device_name"],
            device_model=r["device_model"],
            android_version=r["android_version"],
            app_version=r["app_version"],
            is_online=bool(r["is_online"]),
            last_seen=r["last_seen"],
            registered_at=r["registered_at"],
        )
        for r in rows
    ]
    return DeviceListResponse(devices=devices)
