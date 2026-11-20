"""Screenshot-related routes: request, upload, get image, list, status."""

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from ..auth import verify_api_key
from ..config import config
from ..database import get_db
from ..models import (
    ScreenshotInfo,
    ScreenshotListResponse,
    ScreenshotRequestResponse,
    ScreenshotStatusResponse,
    ScreenshotUploadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/screenshots", tags=["screenshots"])


@router.post("/request/{device_id}", response_model=ScreenshotRequestResponse)
async def request_screenshot(
    device_id: str,
    _key: str = Depends(verify_api_key),
):
    db = await get_db()

    # Verify device exists
    row = await db.execute(
        "SELECT device_id, is_online FROM devices WHERE device_id = ?", (device_id,)
    )
    device = await row.fetchone()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
        )
    if not device["is_online"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device is offline",
        )

    command_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        """INSERT INTO commands (id, device_id, command_type, status, created_at)
           VALUES (?, ?, 'screenshot_request', 'pending', ?)""",
        (command_id, device_id, now),
    )
    await db.commit()
    logger.info("Screenshot requested for device %s — command %s", device_id, command_id)

    return ScreenshotRequestResponse(
        success=True,
        command_id=command_id,
        message="Screenshot request sent",
    )


@router.post("/upload", response_model=ScreenshotUploadResponse)
async def upload_screenshot(
    device_id: str = Form(...),
    command_id: str = Form(...),
    image: UploadFile = File(...),
    _key: str = Depends(verify_api_key),
):
    db = await get_db()

    # Verify command exists and is pending
    row = await db.execute("SELECT id, status FROM commands WHERE id = ?", (command_id,))
    cmd = await row.fetchone()
    if not cmd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Command not found"
        )
    if cmd["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Command status is '{cmd['status']}', expected 'pending'",
        )

    # Save image file
    default_screenshots = Path(__file__).resolve().parent.parent.parent / "screenshots"
    screenshot_dir = Path(config.get("screenshot_dir", str(default_screenshots)))
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{device_id}_{timestamp}.png"
    filepath = screenshot_dir / filename

    content = await image.read()
    with open(filepath, "wb") as f:
        f.write(content)

    file_size = len(content)
    screenshot_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Insert screenshot record
    await db.execute(
        """INSERT INTO screenshots (screenshot_id, device_id, command_id, filename, file_size, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (screenshot_id, device_id, command_id, filename, file_size, now),
    )

    # Mark command completed and link screenshot
    await db.execute(
        "UPDATE commands SET status = 'completed', screenshot_id = ? WHERE id = ?",
        (screenshot_id, command_id),
    )
    await db.commit()

    logger.info(
        "Screenshot uploaded: %s (device=%s, command=%s, size=%d bytes)",
        screenshot_id,
        device_id,
        command_id,
        file_size,
    )

    return ScreenshotUploadResponse(
        success=True,
        screenshot_id=screenshot_id,
        message="Screenshot uploaded successfully",
    )


@router.get("/{screenshot_id}/image")
async def get_screenshot_image(
    screenshot_id: str,
    _key: str = Depends(verify_api_key),
):
    db = await get_db()
    row = await db.execute(
        "SELECT filename FROM screenshots WHERE screenshot_id = ?", (screenshot_id,)
    )
    record = await row.fetchone()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Screenshot not found"
        )

    screenshot_dir = Path(config.get("screenshot_dir", r"f:\parental-app\screenshots"))
    filepath = screenshot_dir / record["filename"]

    if not filepath.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Screenshot file not found on disk"
        )

    return FileResponse(str(filepath), media_type="image/png")


@router.get("", response_model=ScreenshotListResponse)
async def list_screenshots(
    device_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
    _key: str = Depends(verify_api_key),
):
    db = await get_db()

    where_clause = ""
    params: list = []
    if device_id:
        where_clause = "WHERE device_id = ?"
        params.append(device_id)

    # Total count
    count_row = await db.execute(
        f"SELECT COUNT(*) as cnt FROM screenshots {where_clause}", params
    )
    total = (await count_row.fetchone())["cnt"]

    # Paginated results
    query = f"""
        SELECT screenshot_id, device_id, command_id, filename, file_size, created_at
        FROM screenshots {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """
    cursor = await db.execute(query, params + [limit, offset])
    rows = await cursor.fetchall()

    screenshots = [
        ScreenshotInfo(
            screenshot_id=r["screenshot_id"],
            device_id=r["device_id"],
            command_id=r["command_id"],
            filename=r["filename"],
            file_size=r["file_size"],
            created_at=r["created_at"],
        )
        for r in rows
    ]

    return ScreenshotListResponse(screenshots=screenshots, total=total)


@router.get("/status/{command_id}", response_model=ScreenshotStatusResponse)
async def get_screenshot_status(
    command_id: str,
    _key: str = Depends(verify_api_key),
):
    db = await get_db()
    row = await db.execute(
        "SELECT id, status, screenshot_id, created_at FROM commands WHERE id = ?",
        (command_id,),
    )
    cmd = await row.fetchone()
    if not cmd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Command not found"
        )

    return ScreenshotStatusResponse(
        command_id=cmd["id"],
        status=cmd["status"],
        screenshot_id=cmd["screenshot_id"],
        created_at=cmd["created_at"],
    )
