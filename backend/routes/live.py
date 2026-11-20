"""Live screen monitoring routes: start/stop streaming, upload frames, WebSocket & MJPEG feeds."""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import Response, StreamingResponse

from ..auth import verify_api_key
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/live", tags=["live"])


class LiveSession:
    """Tracks live monitoring state and subscribers for a single device."""

    def __init__(self, device_id: str):
        self.device_id: str = device_id
        self.is_active: bool = False
        self.last_frame: Optional[bytes] = None
        self.last_frame_time: float = 0.0
        self.fps: float = 0.0
        self._frame_times: List[float] = []
        self.ws_subscribers: Set[WebSocket] = set()
        self.queue_subscribers: Set[asyncio.Queue] = set()
        self.started_at: float = 0.0

    def update_frame(self, frame_bytes: bytes) -> None:
        now = time.time()
        self.last_frame = frame_bytes
        self.last_frame_time = now
        self._frame_times.append(now)

        # Calculate rolling FPS over last 2 seconds for responsive metric
        self._frame_times = [t for t in self._frame_times if now - t <= 2.0]
        if len(self._frame_times) > 1:
            duration = self._frame_times[-1] - self._frame_times[0]
            if duration > 0:
                self.fps = round((len(self._frame_times) - 1) / duration, 1)
        else:
            self.fps = 1.0 if self._frame_times else 0.0

    async def broadcast(self, frame_bytes: bytes) -> None:
        self.update_frame(frame_bytes)

        if not self.ws_subscribers and not self.queue_subscribers:
            return

        # Broadcast binary frame to all viewer WebSockets concurrently
        if self.ws_subscribers:
            async def _send(ws: WebSocket):
                try:
                    await ws.send_bytes(frame_bytes)
                    return None
                except Exception:
                    return ws

            results = await asyncio.gather(*[_send(ws) for ws in list(self.ws_subscribers)])
            dead = {ws for ws in results if ws is not None}
            if dead:
                self.ws_subscribers.difference_update(dead)

        # Broadcast frame to MJPEG streaming queues
        for q in list(self.queue_subscribers):
            try:
                if q.full():
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(frame_bytes)
            except Exception:
                pass


# In-memory sessions mapped by device_id
_sessions: Dict[str, LiveSession] = {}


def get_session(device_id: str) -> LiveSession:
    """Get or create the live session for a device."""
    if device_id not in _sessions:
        _sessions[device_id] = LiveSession(device_id)
    return _sessions[device_id]


@router.post("/start/{device_id}")
async def start_live_stream(
    device_id: str,
    _key: str = Depends(verify_api_key),
):
    """Start live monitoring stream for a device."""
    db = await get_db()
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

    session = get_session(device_id)
    session.is_active = True
    session.started_at = time.time()

    # Clear prior pending live commands and insert a start command
    now = datetime.now(timezone.utc).isoformat()
    cmd_id = str(uuid.uuid4())
    await db.execute(
        "DELETE FROM commands WHERE device_id = ? AND command_type IN ('start_live', 'stop_live') AND status = 'pending'",
        (device_id,),
    )
    await db.execute(
        """INSERT INTO commands (id, device_id, command_type, status, created_at)
           VALUES (?, ?, 'start_live', 'pending', ?)""",
        (cmd_id, device_id, now),
    )
    await db.commit()

    logger.info("Live stream started for device %s (cmd=%s)", device_id, cmd_id)
    return {
        "success": True,
        "message": "Live monitoring requested",
        "command_id": cmd_id,
        "is_live": True,
    }


@router.post("/stop/{device_id}")
async def stop_live_stream(
    device_id: str,
    _key: str = Depends(verify_api_key),
):
    """Stop live monitoring stream for a device."""
    session = get_session(device_id)
    session.is_active = False

    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()
    cmd_id = str(uuid.uuid4())
    await db.execute(
        "DELETE FROM commands WHERE device_id = ? AND command_type IN ('start_live', 'stop_live') AND status = 'pending'",
        (device_id,),
    )
    await db.execute(
        """INSERT INTO commands (id, device_id, command_type, status, created_at)
           VALUES (?, ?, 'stop_live', 'pending', ?)""",
        (cmd_id, device_id, now),
    )
    await db.commit()

    logger.info("Live stream stopped for device %s", device_id)
    return {
        "success": True,
        "message": "Live monitoring stopped",
        "is_live": False,
    }


@router.get("/status/{device_id}")
async def get_live_status(
    device_id: str,
    _key: str = Depends(verify_api_key),
):
    """Get current live stream status and performance metrics."""
    session = get_session(device_id)

    # Auto-stop if no frame uploaded for > 45 seconds while active
    now = time.time()
    if session.is_active and session.last_frame_time > 0 and (now - session.last_frame_time > 45):
        session.is_active = False
        logger.info("Live session auto-stopped for %s due to inactivity", device_id)

    return {
        "device_id": device_id,
        "is_live": session.is_active,
        "fps": session.fps,
        "viewers": len(session.ws_subscribers) + len(session.queue_subscribers),
        "last_frame_time": session.last_frame_time,
        "has_frame": session.last_frame is not None,
    }


@router.websocket("/push/{device_id}")
async def websocket_device_push(
    websocket: WebSocket,
    device_id: str,
):
    """Ultra-low-latency WebSocket endpoint for the Android phone to stream raw binary frames."""
    await websocket.accept()
    session = get_session(device_id)
    session.is_active = True
    logger.info("Device %s connected to WebSocket high-speed video feed", device_id)
    try:
        while True:
            frame_data = await websocket.receive_bytes()
            if frame_data:
                await session.broadcast(frame_data)
    except WebSocketDisconnect:
        logger.info("Device %s WebSocket feed disconnected", device_id)
    except Exception as exc:
        logger.debug("Device %s push error: %s", device_id, exc)


@router.post("/frame_raw/{device_id}")
async def upload_live_frame_raw(
    device_id: str,
    request: Request,
    _key: str = Depends(verify_api_key),
):
    """Direct binary JPEG upload without multipart parsing overhead."""
    session = get_session(device_id)
    content = await request.body()
    if content:
        await session.broadcast(content)

    return {
        "success": True,
        "is_live": session.is_active,
    }


@router.post("/frame")
async def upload_live_frame(
    device_id: str = Form(...),
    frame: UploadFile = File(...),
    _key: str = Depends(verify_api_key),
):
    """Multipart upload (legacy / fallback)."""
    session = get_session(device_id)
    content = await frame.read()

    if content:
        await session.broadcast(content)

    return {
        "success": True,
        "is_live": session.is_active,
    }


@router.get("/latest/{device_id}")
async def get_latest_frame(
    device_id: str,
    _key: str = Depends(verify_api_key),
):
    """Get the most recent live frame as a JPEG image."""
    session = get_session(device_id)
    if not session.last_frame:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No live frame available yet",
        )
    return Response(
        content=session.last_frame,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@router.get("/mjpeg/{device_id}")
async def get_mjpeg_stream(
    device_id: str,
    _token: Optional[str] = Query(None),
):
    """Continuous MJPEG multipart live stream for browsers and media players."""
    session = get_session(device_id)

    async def stream():
        queue: asyncio.Queue = asyncio.Queue(maxsize=5)
        session.queue_subscribers.add(queue)
        try:
            if session.last_frame:
                yield (
                    b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                    + session.last_frame
                    + b"\r\n"
                )
            while True:
                frame_data = await queue.get()
                yield (
                    b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                    + frame_data
                    + b"\r\n"
                )
        except asyncio.CancelledError:
            pass
        finally:
            session.queue_subscribers.discard(queue)

    return StreamingResponse(
        stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@router.websocket("/ws/{device_id}")
async def websocket_live_stream(
    websocket: WebSocket,
    device_id: str,
):
    """WebSocket endpoint to receive real-time binary JPEG frames."""
    await websocket.accept()
    session = get_session(device_id)
    session.ws_subscribers.add(websocket)

    try:
        # Deliver latest frame immediately if available
        if session.last_frame:
            await websocket.send_bytes(session.last_frame)

        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("WebSocket error on device %s: %s", device_id, exc)
    finally:
        session.ws_subscribers.discard(websocket)

