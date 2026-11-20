# Android-spy / Parental Control System

A transparent, consent-based remote parental control and device monitoring system that enables parents to monitor their child's Android device by requesting on-demand screenshots and managing active sessions via a modern Web Dashboard or a native Windows Desktop GUI.

---

## 🌟 Key Features

- **📱 Android Client (Foreground Service)**:
  - Persistent Android foreground service with transparent notification.
  - Native screen capture using Android's `MediaProjection` API.
  - Periodic heartbeat (every 15 seconds) with automatic offline status detection.
  - Resilient network communication with retry policies.

- **⚡ FastAPI Backend**:
  - High-performance asynchronous REST API powered by FastAPI & `aiosqlite`.
  - Built-in interactive **Web Dashboard** at `http://localhost:8080/`.
  - Token-based API authentication (`Bearer <API_KEY>`).
  - Command queue system for dispatching capture requests.
  - Support for public tunnels (e.g., **ngrok**) to connect across cellular and external networks.

- **🖥️ Desktop Dashboard (PySide6 / Qt)**:
  - Native cross-platform desktop application.
  - Live device status indicator (Online / Offline).
  - One-click screenshot capture requests.
  - Screenshot gallery viewer with timestamp and metadata inspection.

- **🔒 Local-First & Privacy-Focused**:
  - All screenshots and SQLite databases are stored locally on the host machine.
  - No third-party cloud database or tracking services required.

---

## 🏗️ Architecture

```
┌───────────────────────────────────────┐         HTTPS (ngrok / direct)         ┌────────────────────────┐
│             Host PC / Server          │◄──────────────────────────────────────►│     Android Device     │
│                                       │                                        │                        │
│  ┌─────────────────┐  ┌────────────┐  │             ┌──────────────┐           │   ┌─────────────────┐  │
│  │  Web Dashboard  │  │  Desktop   │  │             │    ngrok     │           │   │   Android App   │  │
│  │ (FastAPI / HTML)│  │ Dashboard  │  │             │   (Tunnel)   │           │   │  (Foreground    │  │
│  └────────┬────────┘  └─────┬──────┘  │             └──────┬───────┘           │   │    Service)     │  │
│           │                 │         │                    │                   │   └────────┬────────┘  │
│           └────────┬────────┘         │                    │                   │            │           │
│                    ▼                  │                    │                   │            ▼           │
│           ┌─────────────────┐         │                    │                   │   ┌─────────────────┐  │
│           │ FastAPI Backend │◄────────┼────────────────────┘                   │   │ MediaProjection │  │
│           │  (Port 8080)    │         │                                        │   │ (Screen Capture)│  │
│           └────────┬────────┘         │                                        │   └─────────────────┘  │
│                    │                  │                                        │                        │
│           ┌────────▼────────┐         │                                        │                        │
│           │   SQLite DB     │         │                                        │                        │
│           │  + Screenshots  │         │                                        │                        │
│           └─────────────────┘         │                                        │                        │
└───────────────────────────────────────┘                                        └────────────────────────┘
```

---

## ⚙️ Configuration & Environment Variables

The project supports configuration through environment variables, a root `.env` file, or a `config.json` file.

Copy `.env.example` to `.env` or edit `.env` directly:

```bash
cp .env.example .env
```

### Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `SERVER_HOST` | `0.0.0.0` | Host IP address the backend binds to. |
| `SERVER_PORT` | `8080` | Port on which the backend server listens. |
| `API_KEY` | *(Auto-generated)* | Shared Bearer token used to authenticate API requests. |
| `NGROK_URL` | `""` | Public HTTPS tunnel URL (if using ngrok to expose backend). |
| `SCREENSHOT_DIR` | `./screenshots` | Directory where uploaded screenshots are saved. |
| `HEARTBEAT_TIMEOUT_SECONDS` | `45` | Seconds of missed heartbeats before a device is marked offline. |

Example `.env`:
```env
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
API_KEY=CQpg5_Ol4t1x2XTky_PoLQO9nP-_yUSLffB3a0elGwM
NGROK_URL=https://your-domain.ngrok-free.dev
SCREENSHOT_DIR=./screenshots
HEARTBEAT_TIMEOUT_SECONDS=45
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python**: 3.9 or higher
- **Android Studio**: Arctic Fox or newer (with Android SDK 26+)
- **ngrok** *(Optional, for remote connections)*: [Download ngrok](https://ngrok.com/)

---

### 2. Backend Setup

1. Install Python dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

2. Start the FastAPI backend:
   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
   ```

3. Open the **Web Dashboard** in your browser:
   ```
   http://localhost:8080/
   ```

4. *(Optional)* Expose the server via ngrok:
   ```bash
   ngrok http 8080
   ```
   Copy the `https://...ngrok-free.dev` forwarding URL and update `NGROK_URL` in `.env`.

---

### 3. Desktop Dashboard Setup

1. Install desktop dependencies:
   ```bash
   pip install -r desktop/requirements.txt
   ```

2. Launch the desktop GUI:
   ```bash
   python -m desktop.main
   ```

---

### 4. Android App Setup

1. Open the `android/` directory in **Android Studio**.
2. Build and run the app on an Android device or emulator.
3. In the app settings screen:
   - Enter the **Server URL** (e.g. `http://<PC_LOCAL_IP>:8080` for local Wi-Fi, or your `https://...ngrok-free.dev` URL).
   - Enter your **API Key** (from `.env` or `config.json`).
4. Tap **Connect**, approve the `MediaProjection` screen recording permission prompt, and tap **Start Monitoring**.

---

## 📁 Project Structure

```
Android-spy/
├── android/              # Native Android application (Kotlin / Gradle)
│   ├── app/              # Main app source code & UI
│   └── build.gradle      # Android project build definitions
├── backend/              # FastAPI server & async services
│   ├── routes/           # API routes (devices, screenshots, live stream)
│   ├── auth.py           # Bearer token verification
│   ├── config.py         # Multi-source config loader (.env / config.json)
│   ├── database.py       # SQLite connection & schema management
│   ├── main.py           # FastAPI entry point & background maintenance loop
│   ├── models.py         # Pydantic schema models
│   ├── web_dashboard.py  # Embedded web dashboard UI
│   └── requirements.txt  # Backend Python dependencies
├── desktop/              # PySide6 (Qt) desktop application
│   ├── api_client.py     # Desktop HTTP client
│   ├── config_manager.py # Settings management
│   ├── dashboard.py      # Main UI window & screenshot viewer
│   ├── main.py           # Desktop launcher
│   └── requirements.txt  # Desktop dependencies
├── docs/                 # Detailed documentation
│   ├── api.md            # Complete API documentation & curl samples
│   ├── security.md       # Threat model & security principles
│   ├── setup.md          # Comprehensive step-by-step setup guide
│   └── troubleshooting.md# Common issues & fixes
├── screenshots/          # Local directory storing captured screenshots
├── .env                  # Environment configuration file
├── .env.example          # Template environment configuration file
├── .gitignore            # Git exclusion rules
├── API_CONTRACT.md       # Machine-readable API specifications
└── README.md             # Project documentation
```

---

## 📚 Documentation Links

- [Setup & Installation Walkthrough](docs/setup.md)
- [API Reference & Endpoint Documentation](docs/api.md)
- [Security Model & Consent Principles](docs/security.md)
- [Troubleshooting & FAQs](docs/troubleshooting.md)
- [API Contract Specification](API_CONTRACT.md)

---

## 🛡️ Security & Consent Principles

This project is built around **visible and consensual monitoring**:

- **Always Visible**: The Android application operates with a persistent foreground service notification.
- **Explicit System Consent**: Requires user permission through the official Android `MediaProjection` prompt.
- **Zero Hidden Modules**: Contains no background keyloggers, hidden location tracking, or mic recording.
- **Local Storage**: All captured data stays on the user's private computer.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
