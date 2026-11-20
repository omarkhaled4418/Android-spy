"""FastAPI application entry point for the Parental Control System."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .config import config, load_config
from .database import close_db, get_db, init_db
from .models import HealthResponse
from .routes.devices import router as devices_router
from .routes.screenshots import router as screenshots_router
from .routes.live import router as live_router
from .web_dashboard import DASHBOARD_HTML

# ── Logging ───────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


# ── Background task ───────────────────────────────────────────────────────

async def _maintenance_loop() -> None:
    """Periodically mark devices offline and expire stale commands."""
    while True:
        try:
            db = await get_db()
            now = datetime.now(timezone.utc)
            timeout = config.get("heartbeat_timeout_seconds", 45)
            cutoff = (now - timedelta(seconds=timeout)).isoformat()

            # Mark devices offline
            cursor = await db.execute(
                "UPDATE devices SET is_online = 0 WHERE is_online = 1 AND last_seen < ?",
                (cutoff,),
            )
            if cursor.rowcount:
                logger.info("Marked %d device(s) offline (no heartbeat for %ds)", cursor.rowcount, timeout)

            # Expire pending commands older than 60 seconds
            expire_cutoff = (now - timedelta(seconds=60)).isoformat()
            cursor = await db.execute(
                "UPDATE commands SET status = 'expired' WHERE status = 'pending' AND created_at < ?",
                (expire_cutoff,),
            )
            if cursor.rowcount:
                logger.info("Expired %d stale command(s)", cursor.rowcount)

            await db.commit()
        except Exception:
            logger.exception("Error in maintenance loop")

        await asyncio.sleep(10)


# ── Lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    config.update(load_config())
    await init_db()

    logger.info("=" * 60)
    logger.info("  Parental Control System — Backend")
    logger.info("  Server URL : http://%s:%s", config["server_host"], config["server_port"])
    if config.get("ngrok_url"):
        logger.info("  Ngrok URL  : %s", config["ngrok_url"])
    logger.info("  API Key    : %s", config["api_key"])
    logger.info("=" * 60)

    # Print to stdout as well for quick copy-paste
    print(f"\n{'=' * 60}")
    print(f"  API Key    : {config['api_key']}")
    print(f"  Server URL : http://{config['server_host']}:{config['server_port']}")
    print(f"{'=' * 60}\n")

    task = asyncio.create_task(_maintenance_loop())

    yield

    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await close_db()


# ── App ───────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Parental Control System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins (needed for ngrok / various clients)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(devices_router)
app.include_router(screenshots_router)
app.include_router(live_router)


# ── Web UI ───────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def web_ui():
    """Web dashboard interface for managing devices and viewing screenshots."""
    return HTMLResponse(content=DASHBOARD_HTML)


# ── Health (no auth) ──────────────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
