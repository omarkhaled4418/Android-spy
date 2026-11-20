# Security Documentation

Security model, threat analysis, and privacy principles for the Parental Control System.

---

## Threat Model

### What we protect against

| Threat | Mitigation |
|---|---|
| Unauthorized access to the API | API key authentication on all endpoints (except health check) |
| Man-in-the-middle attacks | HTTPS encryption via ngrok tunnel |
| Data leakage to third parties | All data stored locally — no cloud services, no telemetry |
| Child unaware of monitoring | Persistent Android notification, system-level capture dialog |
| Accidental API key exposure | Key stored in local `config.json`, never transmitted in URLs |

### What we do NOT protect against (Phase One)

| Limitation | Notes |
|---|---|
| Brute-force API key guessing | No rate limiting in Phase One. Mitigated by key length/entropy. |
| Physical access to the PC | Anyone with access to the PC can read `config.json`, the database, and screenshots. Use OS-level user accounts and disk encryption. |
| ngrok account compromise | An attacker with your ngrok credentials could observe tunnel traffic. Use a strong ngrok password and 2FA. |
| Compromised Android device | A rooted or malware-infected device could tamper with the app. |
| Network-level adversaries beyond HTTPS | We rely entirely on TLS via ngrok. No additional encryption layer (e.g., end-to-end encryption) exists in Phase One. |

---

## Authentication

### API Key

- **Generation:** A cryptographically random API key is generated automatically on the server's first run and stored in `f:\parental-app\config.json`.
- **Transmission:** Sent as a `Bearer` token in the `Authorization` HTTP header over HTTPS.
- **Scope:** A single shared secret used by both the desktop dashboard and the Android app.
- **Storage locations:**
  - Backend: `config.json` on the parent's PC.
  - Android: Stored in the app's local preferences (sandboxed by Android).
  - Desktop: Stored in the dashboard's local configuration.

> [!IMPORTANT]
> **Rotate your API key periodically.** To rotate: stop the server, edit the `api_key` field in `config.json` (use a long random string), restart the server, and update the key in both the desktop and Android apps.

### No Authentication on Health Check

The `GET /api/health` endpoint is intentionally unauthenticated. It returns only `{"status": "ok", "timestamp": "..."}` and exposes no sensitive information. This allows monitoring tools and load balancers to check server availability without credentials.

---

## HTTPS via ngrok

### How it works

1. The FastAPI backend listens on `http://localhost:8000` (plain HTTP, local only).
2. ngrok creates an encrypted TLS tunnel from a public HTTPS URL to `localhost:8000`.
3. All traffic between the Android device and the backend travels through this HTTPS tunnel.
4. The connection between ngrok's local agent and `localhost:8000` is unencrypted but never leaves the machine.

### Diagram

```
Android Device                    ngrok Cloud                 Parent's PC
     │                               │                            │
     │── HTTPS (TLS 1.2+) ──────────►│                            │
     │                               │── local TCP ──────────────►│
     │                               │   (localhost:8000)         │
     │◄── HTTPS (TLS 1.2+) ─────────│                            │
     │                               │◄── local TCP ──────────────│
```

### Free tier limitations

| Limitation | Impact | Recommendation |
|---|---|---|
| URL changes on restart | Must update URL in all clients | Use ngrok paid tier for a static domain |
| Rate limits | May throttle high-frequency requests | Acceptable for Phase One usage patterns |
| Inspection dashboard | ngrok's web UI at `localhost:4040` shows request/response data | Only accessible locally; be aware if sharing the PC |
| Traffic passes through ngrok servers | ngrok can theoretically inspect traffic | Use a paid tier with IP restrictions, or consider alternatives like Cloudflare Tunnel for production |

---

## Data Storage

All data is stored **locally on the parent's PC**. Nothing is transmitted to any cloud service beyond the ngrok tunnel itself.

| Data | Location | Format |
|---|---|---|
| Screenshot images | `f:\parental-app\screenshots\` | PNG files, named `{device_id}_{timestamp}.png` |
| Device metadata & commands | `f:\parental-app\backend\parental_control.db` | SQLite database |
| API key & configuration | `f:\parental-app\config.json` | JSON |

### Data retention

Phase One does **not** automatically delete old screenshots or database records. Screenshots accumulate on disk indefinitely. Manage storage manually by deleting old files from the `screenshots/` directory.

> [!TIP]
> Monitor disk usage if the system runs for extended periods. A single screenshot is typically 100–500 KB (PNG), so 100 screenshots per day would use roughly 25–50 MB.

---

## Android Permissions

The Android app requests the following permissions. Each is explained below.

| Permission | Why it's needed |
|---|---|
| `INTERNET` | Communicate with the backend server via HTTPS |
| `FOREGROUND_SERVICE` | Run the monitoring service with a persistent notification |
| `FOREGROUND_SERVICE_MEDIA_PROJECTION` | Use `MediaProjection` in a foreground service (Android 14+) |
| `POST_NOTIFICATIONS` | Show the persistent "monitoring active" notification (Android 13+) |

### Permissions NOT requested

The app does **not** request and does **not** have access to:

- `ACCESS_FINE_LOCATION` / `ACCESS_COARSE_LOCATION` — No location tracking
- `RECORD_AUDIO` / `CAMERA` — No microphone or camera access
- `READ_CONTACTS` / `READ_CALL_LOG` / `READ_SMS` — No access to contacts, calls, or messages
- `SYSTEM_ALERT_WINDOW` — No overlay/floating windows
- `ACCESSIBILITY_SERVICE` — No keylogging or input monitoring
- `USAGE_STATS_ACCESS` — No app usage tracking (Phase One)

---

## Visible Monitoring Policy

This system is designed around the principle of **transparent, visible monitoring**. At no point should a child be unaware that monitoring is occurring.

### How visibility is enforced

1. **Persistent notification** — Android requires foreground services to display an ongoing notification. The Parental Control notification is always visible in the notification shade and status bar while monitoring is active. It **cannot** be hidden by the app.

2. **MediaProjection consent dialog** — Android's `MediaProjection` API shows a **system-level dialog** every time screen capture starts:
   > "Parental Control will start capturing everything that's displayed on your screen."
   
   The user must explicitly tap **Start now** / **Allow**. The app cannot bypass this dialog.

3. **Screen capture indicator** — On Android 12+, the system shows a persistent status bar icon (a casting/screen-share icon) whenever `MediaProjection` is active.

4. **No stealth mode** — The app has no hidden mode, no way to hide the notification, and no way to suppress the system-level capture indicators.

---

## Explicit Consent Requirement

Screen capture requires **active consent** at two levels:

1. **Installation consent** — The parent and child agree to install the app. It is not sideloaded silently.
2. **Runtime consent** — Every time the monitoring service starts, Android's `MediaProjection` API displays a system dialog that requires the user to approve screen capture. This cannot be suppressed or auto-accepted by the app.

---

## No Hidden Features

The Parental Control System in Phase One includes **only** the following capabilities:

- ✅ On-demand screenshot capture (parent-initiated, one at a time)
- ✅ Device online/offline status monitoring
- ✅ Device registration and identification

The system does **NOT** include, and there is no code for:

- ❌ Keylogging or input monitoring
- ❌ Silent or automatic screenshot capture
- ❌ Location tracking
- ❌ Audio recording or camera access
- ❌ Contact, call log, or SMS access
- ❌ App usage tracking (planned for Phase 2)
- ❌ Website or content filtering (planned for Phase 4)
- ❌ Remote device locking or wiping
- ❌ File browsing or download

---

## Recommendations

### For regular use

1. **Use a paid ngrok plan** for a static HTTPS domain that doesn't change on restart.
2. **Rotate the API key periodically** — edit `config.json`, restart the server, and update both clients.
3. **Enable Windows user accounts** — Ensure the parent's PC account is password-protected so other users can't access `config.json` or the screenshots.
4. **Enable disk encryption** (BitLocker on Windows 10 Pro / 11 Pro) to protect stored screenshots if the PC is lost or stolen.
5. **Keep software updated** — Update Python packages (`pip install --upgrade -r requirements.txt`) and the Android app regularly.

### ADB safety

> [!CAUTION]
> **Never expose ADB (Android Debug Bridge) over the network.** ADB over Wi-Fi/TCP gives full shell access to the device without authentication. If you used `adb tcpip` during development, disable it when done:
> ```bash
> adb usb
> ```
> ADB over USB is safe as it requires physical access.

### Network safety

- Do **not** expose port 8000 directly to the internet (e.g., via port forwarding on your router). Always use ngrok or a similar authenticated tunnel.
- If you must run without ngrok on a local network, ensure the network is trusted and secured with WPA3/WPA2.

---

## Security Checklist

Use this checklist when deploying the system:

- [ ] API key copied securely (not shared via unencrypted email/chat)
- [ ] ngrok HTTPS URL being used (not plain HTTP)
- [ ] Windows user account is password-protected
- [ ] ngrok inspection dashboard (`localhost:4040`) is not exposed
- [ ] ADB is not enabled over Wi-Fi/TCP
- [ ] Port 8000 is not exposed via router port forwarding
- [ ] Child is informed that monitoring is active
- [ ] Child has consented to the MediaProjection dialog
