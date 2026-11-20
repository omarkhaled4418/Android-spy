"""Web dashboard HTML interface served at GET /."""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Parental Control — Dashboard</title>
    <style>
        :root {
            --bg-dark: #121316;
            --bg-card: #1c1d22;
            --bg-input: #15161a;
            --text-main: #f0f0f5;
            --text-muted: #9595a5;
            --accent: #3b82f6;
            --accent-hover: #2563eb;
            --online: #10b981;
            --offline: #ef4444;
            --live: #e11d48;
            --live-hover: #be123c;
            --border: #2a2b34;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg-dark);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        header {
            background: var(--bg-card);
            border-bottom: 1px solid var(--border);
            padding: 14px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo-group {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .logo-icon {
            font-size: 24px;
        }
        h1 {
            font-size: 18px;
            font-weight: 600;
        }
        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(16, 185, 129, 0.15);
            color: var(--online);
            padding: 6px 14px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 500;
        }
        .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: currentColor;
        }
        .container {
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 20px;
            padding: 20px;
            flex: 1;
            max-width: 1500px;
            margin: 0 auto;
            width: 100%;
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            flex-direction: column;
        }
        .card h2 {
            font-size: 15px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 16px;
        }
        .device-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            overflow-y: auto;
            flex: 1;
            max-height: 500px;
        }
        .device-item {
            background: var(--bg-input);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px 14px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .device-item:hover {
            border-color: var(--accent);
        }
        .device-item.active {
            border-color: var(--accent);
            background: rgba(59, 130, 246, 0.1);
        }
        .device-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
        }
        .device-name {
            font-weight: 600;
            font-size: 14px;
        }
        .device-meta {
            font-size: 12px;
            color: var(--text-muted);
        }
        .preview-pane {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }
        .btn-group {
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }
        .btn {
            background: var(--accent);
            color: white;
            border: none;
            padding: 9px 18px;
            border-radius: 8px;
            font-size: 13.5px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }
        .btn:hover:not(:disabled) {
            background: var(--accent-hover);
        }
        .btn:disabled {
            opacity: 0.45;
            cursor: not-allowed;
        }
        .btn-secondary {
            background: #2a2b34;
        }
        .btn-secondary:hover:not(:disabled) {
            background: #383946;
        }
        .btn-live {
            background: var(--live);
        }
        .btn-live:hover:not(:disabled) {
            background: var(--live-hover);
        }
        .btn-live.streaming {
            background: #991b1b;
            box-shadow: 0 0 12px rgba(225, 29, 72, 0.5);
        }
        .preview-box {
            background: var(--bg-input);
            border: 2px dashed var(--border);
            border-radius: 12px;
            flex: 1;
            min-height: 480px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }
        .preview-box.streaming-active {
            border: 2px solid var(--live);
            background: #0d0e11;
        }
        .preview-box img, .preview-box canvas {
            max-width: 100%;
            max-height: 620px;
            border-radius: 6px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.6);
            display: none;
            object-fit: contain;
        }
        .live-overlay {
            position: absolute;
            top: 14px;
            left: 14px;
            display: flex;
            align-items: center;
            gap: 12px;
            background: rgba(18, 19, 22, 0.85);
            backdrop-filter: blur(8px);
            padding: 6px 14px;
            border-radius: 999px;
            border: 1px solid rgba(225, 29, 72, 0.4);
            z-index: 10;
        }
        .live-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            color: #ff4d6d;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .live-pulse {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #ff4d6d;
            box-shadow: 0 0 8px #ff4d6d;
            animation: pulse-animation 1.2s infinite ease-in-out;
        }
        @keyframes pulse-animation {
            0% { transform: scale(0.9); opacity: 0.7; }
            50% { transform: scale(1.3); opacity: 1; box-shadow: 0 0 12px #ff4d6d; }
            100% { transform: scale(0.9); opacity: 0.7; }
        }
        .live-stats {
            font-size: 12px;
            color: #d1d5db;
            font-family: monospace;
        }
        .placeholder {
            text-align: center;
            color: var(--text-muted);
        }
        .placeholder-icon {
            font-size: 48px;
            margin-bottom: 12px;
        }
        .log-section {
            grid-column: 1 / -1;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px 20px;
        }
        .log-box {
            background: var(--bg-input);
            border: 1px solid var(--border);
            border-radius: 8px;
            height: 120px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
            padding: 10px 14px;
            color: #d1d5db;
        }
        .log-line {
            margin-bottom: 4px;
        }
        .log-time {
            color: var(--text-muted);
            margin-right: 8px;
        }
        .status-badge {
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 999px;
            font-weight: 600;
        }
        .status-badge.online {
            background: rgba(16, 185, 129, 0.2);
            color: var(--online);
        }
        .status-badge.offline {
            background: rgba(239, 68, 68, 0.2);
            color: var(--offline);
        }
        .spinner {
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <header>
        <div class="logo-group">
            <span class="logo-icon">🛡️</span>
            <h1>Parental Control Dashboard</h1>
        </div>
        <div class="status-pill">
            <span class="dot"></span>
            <span id="server-status">Backend Active</span>
        </div>
    </header>

    <div class="container">
        <!-- Sidebar: Devices -->
        <div class="card">
            <h2>Connected Devices (<span id="device-count">0</span>)</h2>
            <div class="device-list" id="devices-container">
                <div class="placeholder" style="margin-top: 40px;">
                    <div>🔍 Searching for devices…</div>
                    <div style="font-size: 12px; margin-top: 8px;">Ensure Android app is running</div>
                </div>
            </div>
            <div style="margin-top: 16px; font-size: 12px; color: var(--text-muted);">
                Auto-refreshes every 5 seconds
            </div>
        </div>

        <!-- Main Panel: Screen Preview -->
        <div class="card preview-pane">
            <div class="toolbar">
                <div>
                    <h2 style="margin: 0;" id="selected-device-title">No Device Selected</h2>
                    <span id="capture-status" style="font-size: 13px; color: var(--text-muted);">Select a device to view or request screenshots</span>
                </div>
                <div class="btn-group">
                    <button class="btn btn-live" id="btn-live" disabled onclick="toggleLiveMonitoring()">
                        <span id="btn-live-text">🔴 Start Live Stream</span>
                    </button>
                    <button class="btn" id="btn-request" disabled onclick="requestScreenshot()">
                        📸 Request Screenshot
                    </button>
                    <button class="btn btn-secondary" id="btn-download" disabled onclick="downloadScreenshot()">
                        💾 Save
                    </button>
                    <button class="btn btn-secondary" id="btn-fullscreen" disabled onclick="toggleFullscreen()">
                        ⛶ Fullscreen
                    </button>
                </div>
            </div>

            <div class="preview-box" id="preview-box">
                <!-- Live Overlay -->
                <div class="live-overlay" id="live-overlay" style="display: none;">
                    <div class="live-badge">
                        <span class="live-pulse"></span>
                        LIVE
                    </div>
                    <div class="live-stats" id="live-stats">Waiting for frames…</div>
                </div>

                <div class="placeholder" id="preview-placeholder">
                    <div class="placeholder-icon">📱</div>
                    <div>No screen content loaded yet</div>
                    <div style="font-size: 12px; margin-top: 6px;">Click "Start Live Stream" or "Request Screenshot" when an online device is selected</div>
                </div>
                <canvas id="live-canvas"></canvas>
                <img id="screenshot-img" alt="Device Screen">
            </div>
        </div>

        <!-- Logs Section -->
        <div class="log-section">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h2 style="font-size: 13px; color: var(--text-muted); margin: 0;">Activity Log</h2>
                <button onclick="clearLogs()" style="background: none; border: none; color: var(--accent); cursor: pointer; font-size: 12px;">Clear</button>
            </div>
            <div class="log-box" id="log-box"></div>
        </div>
    </div>

    <script>
        let devices = [];
        let selectedDeviceId = null;
        let activeCommandId = null;
        let pollTimer = null;
        let currentScreenshotUrl = null;

        // Live Monitoring State
        let isLive = false;
        let liveWs = null;
        let livePingTimer = null;
        let livePollTimer = null;
        let liveFrameCount = 0;
        let liveStartTime = 0;
        let liveFpsCalcTimer = null;
        let lastFrameArrivedTime = 0;
        let currentObjectUrl = null;

        function log(msg) {
            const box = document.getElementById("log-box");
            const time = new Date().toLocaleTimeString();
            const div = document.createElement("div");
            div.className = "log-line";
            div.innerHTML = `<span class="log-time">[${time}]</span> ${msg}`;
            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
        }

        function clearLogs() {
            document.getElementById("log-box").innerHTML = "";
        }

        let initialDevicesLoaded = false;
        async function fetchDevices() {
            try {
                const res = await fetch("/api/devices");
                if (!res.ok) throw new Error("HTTP " + res.status);
                const data = await res.json();
                devices = data.devices || [];
                if (!initialDevicesLoaded && devices.length > 0) {
                    initialDevicesLoaded = true;
                    log(`Discovered ${devices.length} registered device(s).`);
                }
                renderDevices();
            } catch (e) {
                // Log once if initial fetch encounters an issue
                if (!initialDevicesLoaded) {
                    log("Waiting to reach device API: " + e.message);
                }
            }
        }

        function renderDevices() {
            const container = document.getElementById("devices-container");
            document.getElementById("device-count").textContent = devices.length;

            if (devices.length === 0) {
                container.innerHTML = `
                    <div class="placeholder" style="margin-top: 40px;">
                        <div>🔍 No registered devices</div>
                        <div style="font-size: 12px; margin-top: 8px;">Connect from the Android app</div>
                    </div>`;
                return;
            }

            container.innerHTML = devices.map(d => {
                const isSelected = d.device_id === selectedDeviceId;
                const statusClass = d.is_online ? "online" : "offline";
                const statusText = d.is_online ? "Online" : "Offline";
                return `
                    <div class="device-item ${isSelected ? 'active' : ''}" onclick="selectDevice('${d.device_id}')">
                        <div class="device-top">
                            <span class="device-name">${escapeHtml(d.device_name || d.device_model || 'Android Phone')}</span>
                            <span class="status-badge ${statusClass}">${statusText}</span>
                        </div>
                        <div class="device-meta">Model: ${escapeHtml(d.device_model || 'Unknown')}</div>
                        <div class="device-meta">Android: ${escapeHtml(d.android_version || '11+')}</div>
                    </div>
                `;
            }).join("");

            // Auto-select first device if none is selected
            if (!selectedDeviceId && devices.length > 0) {
                selectDevice(devices[0].device_id);
            }

            // Update action buttons state
            if (selectedDeviceId) {
                const cur = devices.find(d => d.device_id === selectedDeviceId);
                if (cur) {
                    document.getElementById("selected-device-title").textContent = cur.device_name || cur.device_model;
                    document.getElementById("btn-request").disabled = !cur.is_online || isLive;
                    document.getElementById("btn-live").disabled = !cur.is_online;
                }
            }
        }

        function selectDevice(id) {
            if (selectedDeviceId === id) return;
            if (isLive) {
                stopLiveMonitoring();
            }
            selectedDeviceId = id;
            renderDevices();
            const cur = devices.find(d => d.device_id === selectedDeviceId);
            if (cur) {
                log(`Selected device: ${cur.device_name || cur.device_id}`);
                loadLatestScreenshot(id);
            }
        }

        async function loadLatestScreenshot(deviceId) {
            try {
                const res = await fetch(`/api/screenshots?device_id=${encodeURIComponent(deviceId)}&limit=1`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.screenshots && data.screenshots.length > 0) {
                        displayImage(`/api/screenshots/${data.screenshots[0].screenshot_id}/image`);
                    }
                }
            } catch(e) {}
        }

        // ── LIVE MONITORING ────────────────────────────────────────────────────────

        async function toggleLiveMonitoring() {
            if (isLive) {
                await stopLiveMonitoring();
            } else {
                await startLiveMonitoring();
            }
        }

        async function startLiveMonitoring() {
            if (!selectedDeviceId) return;
            const btn = document.getElementById("btn-live");
            const btnText = document.getElementById("btn-live-text");
            const status = document.getElementById("capture-status");

            btn.disabled = true;
            btnText.innerHTML = `<span class="spinner"></span> Connecting Live…`;
            status.textContent = "Requesting live stream from device…";
            log("Sending start live stream command to device…");

            try {
                const res = await fetch(`/api/live/start/${encodeURIComponent(selectedDeviceId)}`, {
                    method: "POST"
                });
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || "Failed to start live stream");
                }

                isLive = true;
                btn.disabled = false;
                btn.classList.add("streaming");
                btnText.textContent = "⏹️ Stop Live Stream";
                document.getElementById("btn-request").disabled = true;
                document.getElementById("preview-box").classList.add("streaming-active");
                document.getElementById("live-overlay").style.display = "flex";
                document.getElementById("btn-fullscreen").disabled = false;

                status.textContent = "Live screen stream active (low-latency feed)";
                log("Live stream session initiated. Connecting real-time video…");

                liveStartTime = Date.now();
                liveFrameCount = 0;
                startLiveFeed(selectedDeviceId);
                startLiveStatsLoop();
            } catch (err) {
                log(`Error starting live stream: ${err.message}`);
                status.textContent = `Failed: ${err.message}`;
                btn.disabled = false;
                btnText.textContent = "🔴 Start Live Stream";
                btn.classList.remove("streaming");
            }
        }

        async function stopLiveMonitoring() {
            const btn = document.getElementById("btn-live");
            const btnText = document.getElementById("btn-live-text");
            const status = document.getElementById("capture-status");

            log("Stopping live stream…");
            isLive = false;

            if (livePingTimer) {
                clearInterval(livePingTimer);
                livePingTimer = null;
            }
            if (liveWs) {
                liveWs.close();
                liveWs = null;
            }
            if (livePollTimer) {
                clearInterval(livePollTimer);
                livePollTimer = null;
            }
            if (liveFpsCalcTimer) {
                clearInterval(liveFpsCalcTimer);
                liveFpsCalcTimer = null;
            }

            btn.classList.remove("streaming");
            btnText.textContent = "🔴 Start Live Stream";
            document.getElementById("btn-request").disabled = false;
            document.getElementById("preview-box").classList.remove("streaming-active");
            document.getElementById("live-overlay").style.display = "none";
            status.textContent = "Live stream stopped.";

            try {
                if (selectedDeviceId) {
                    await fetch(`/api/live/stop/${encodeURIComponent(selectedDeviceId)}`, {
                        method: "POST"
                    });
                }
            } catch(e) {}

            log("Live stream stopped successfully.");
        }

        function startLiveFeed(deviceId) {
            // Prefer WebSocket for instant binary frame delivery
            const protocol = location.protocol === "https:" ? "wss:" : "ws:";
            const wsUrl = `${protocol}//${location.host}/api/live/ws/${encodeURIComponent(deviceId)}`;

            try {
                liveWs = new WebSocket(wsUrl);
                liveWs.binaryType = "blob";

                liveWs.onopen = () => {
                    log("WebSocket live channel established.");
                    if (livePingTimer) clearInterval(livePingTimer);
                    livePingTimer = setInterval(() => {
                        if (liveWs && liveWs.readyState === WebSocket.OPEN) {
                            liveWs.send("ping");
                        }
                    }, 10000);
                };

                liveWs.onmessage = (event) => {
                    if (event.data instanceof Blob) {
                        renderFrameBlob(event.data);
                    }
                };

                liveWs.onerror = () => {
                    log("WebSocket error — activating fast polling fallback…");
                    startHttpLivePolling(deviceId);
                };

                liveWs.onclose = () => {
                    if (livePingTimer) {
                        clearInterval(livePingTimer);
                        livePingTimer = null;
                    }
                    if (isLive) {
                        log("WebSocket disconnected — falling back to polling…");
                        startHttpLivePolling(deviceId);
                    }
                };
            } catch (e) {
                startHttpLivePolling(deviceId);
            }
        }

        function startHttpLivePolling(deviceId) {
            if (livePollTimer) clearInterval(livePollTimer);
            livePollTimer = setInterval(async () => {
                if (!isLive) return;
                try {
                    const res = await fetch(`/api/live/latest/${encodeURIComponent(deviceId)}?_=${Date.now()}`);
                    if (res.ok) {
                        const blob = await res.blob();
                        renderFrameBlob(blob);
                    }
                } catch(e) {}
            }, 100);
        }

        async function renderFrameBlob(blob) {
            liveFrameCount++;
            lastFrameArrivedTime = Date.now();

            const canvas = document.getElementById("live-canvas");
            const img = document.getElementById("screenshot-img");
            const placeholder = document.getElementById("preview-placeholder");

            if (window.createImageBitmap && canvas) {
                try {
                    const bmp = await createImageBitmap(blob);
                    if (canvas.width !== bmp.width || canvas.height !== bmp.height) {
                        canvas.width = bmp.width;
                        canvas.height = bmp.height;
                    }
                    const ctx = canvas.getContext("2d", { alpha: false });
                    ctx.drawImage(bmp, 0, 0);
                    bmp.close();

                    canvas.style.display = "block";
                    img.style.display = "none";
                    placeholder.style.display = "none";
                    document.getElementById("btn-download").disabled = false;
                    return;
                } catch (e) {
                    // Fallback to DOM img
                }
            }

            if (currentObjectUrl) {
                URL.revokeObjectURL(currentObjectUrl);
            }
            currentObjectUrl = URL.createObjectURL(blob);

            img.src = currentObjectUrl;
            img.style.display = "block";
            if (canvas) canvas.style.display = "none";
            placeholder.style.display = "none";
            document.getElementById("btn-download").disabled = false;
        }

        function startLiveStatsLoop() {
            let lastCount = 0;
            if (liveFpsCalcTimer) clearInterval(liveFpsCalcTimer);

            liveFpsCalcTimer = setInterval(() => {
                if (!isLive) return;
                const elapsedSec = Math.floor((Date.now() - liveStartTime) / 1000);
                const currentFps = liveFrameCount - lastCount;
                lastCount = liveFrameCount;

                const minutes = Math.floor(elapsedSec / 60).toString().padStart(2, '0');
                const seconds = (elapsedSec % 60).toString().padStart(2, '0');

                const statsEl = document.getElementById("live-stats");
                if (Date.now() - lastFrameArrivedTime > 3000 && liveFrameCount > 0) {
                    statsEl.textContent = `Screen idle / unchanged • ${minutes}:${seconds}`;
                } else if (liveFrameCount === 0) {
                    statsEl.textContent = `Connecting to stream…`;
                } else {
                    statsEl.textContent = `${currentFps} FPS • Low Latency • ${minutes}:${seconds}`;
                }
            }, 1000);
        }

        function toggleFullscreen() {
            const previewBox = document.getElementById("preview-box");
            if (!document.fullscreenElement) {
                previewBox.requestFullscreen().catch(err => {
                    log(`Fullscreen error: ${err.message}`);
                });
            } else {
                document.exitFullscreen();
            }
        }

        // ── MANUAL SCREENSHOT REQUEST ──────────────────────────────────────────────

        async function requestScreenshot() {
            if (!selectedDeviceId || isLive) return;
            const btn = document.getElementById("btn-request");
            const status = document.getElementById("capture-status");
            btn.disabled = true;
            btn.innerHTML = `<span class="spinner"></span> Requesting…`;
            status.textContent = "Sending request to device…";
            log("Sending screenshot request command…");

            try {
                const res = await fetch(`/api/screenshots/request/${encodeURIComponent(selectedDeviceId)}`, {
                    method: "POST"
                });
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || "Request failed");
                }
                const data = await res.json();
                activeCommandId = data.command_id;
                status.textContent = "Waiting for device to capture and upload (heartbeat interval)…";
                log(`Command queued (ID: ${activeCommandId}). Waiting for Android heartbeat…`);
                startPollingStatus(activeCommandId);
            } catch (err) {
                log(`Error: ${err.message}`);
                status.textContent = `Failed: ${err.message}`;
                btn.disabled = false;
                btn.innerHTML = `📸 Request Screenshot`;
            }
        }

        function startPollingStatus(commandId) {
            let attempts = 0;
            const maxAttempts = 25; // 50 seconds
            if (pollTimer) clearInterval(pollTimer);

            pollTimer = setInterval(async () => {
                attempts++;
                try {
                    const res = await fetch(`/api/screenshots/status/${encodeURIComponent(commandId)}`);
                    if (res.ok) {
                        const data = await res.json();
                        if (data.status === "completed" && data.screenshot_id) {
                            clearInterval(pollTimer);
                            log(`Screenshot received successfully!`);
                            document.getElementById("capture-status").textContent = "Screenshot received!";
                            displayImage(`/api/screenshots/${data.screenshot_id}/image`);
                            resetRequestButton();
                            return;
                        } else if (data.status === "expired") {
                            clearInterval(pollTimer);
                            log("Screenshot command expired on device.");
                            document.getElementById("capture-status").textContent = "Request expired.";
                            resetRequestButton();
                            return;
                        }
                    }
                } catch(e) {}

                if (attempts >= maxAttempts) {
                    clearInterval(pollTimer);
                    log("Screenshot request timed out.");
                    document.getElementById("capture-status").textContent = "Request timed out.";
                    resetRequestButton();
                }
            }, 2000);
        }

        function resetRequestButton() {
            const btn = document.getElementById("btn-request");
            btn.disabled = !devices.find(d => d.device_id === selectedDeviceId)?.is_online || isLive;
            btn.innerHTML = `📸 Request Screenshot`;
        }

        function displayImage(url) {
            currentScreenshotUrl = url;
            const img = document.getElementById("screenshot-img");
            const canvas = document.getElementById("live-canvas");
            const placeholder = document.getElementById("preview-placeholder");
            img.src = url;
            img.onload = () => {
                placeholder.style.display = "none";
                img.style.display = "block";
                if (canvas) canvas.style.display = "none";
                document.getElementById("btn-download").disabled = false;
                document.getElementById("btn-fullscreen").disabled = false;
            };
        }

        function downloadScreenshot() {
            const canvas = document.getElementById("live-canvas");
            if (isLive && canvas && canvas.style.display === "block") {
                const a = document.createElement("a");
                a.href = canvas.toDataURL("image/jpeg", 0.95);
                a.download = `live_stream_${Date.now()}.jpg`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                log("Live frame downloaded.");
                return;
            }
            const img = document.getElementById("screenshot-img");
            if (!img.src) return;
            const a = document.createElement("a");
            a.href = img.src;
            a.download = `screenshot_${Date.now()}.${isLive ? 'jpg' : 'png'}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            log("Screen capture downloaded.");
        }

        function escapeHtml(text) {
            const div = document.createElement("div");
            div.textContent = text;
            return div.innerHTML;
        }

        // Initial setup
        log("Dashboard initialized. Connecting to API…");
        fetchDevices();
        setInterval(fetchDevices, 5000);
    </script>
</body>
</html>
"""
