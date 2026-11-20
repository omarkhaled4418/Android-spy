# Setup Guide

Complete step-by-step instructions to get the Parental Control System running on Windows 10 with an Android device.

---

## Prerequisites

### 1. Python 3.9+

1. Download the latest Python 3.x installer from [python.org](https://www.python.org/downloads/).
2. **Important:** Check **"Add Python to PATH"** on the first screen of the installer.
3. Click **Install Now** and complete the installation.
4. Verify:
   ```
   python --version
   pip --version
   ```

### 2. Android Studio

1. Download Android Studio from [developer.android.com](https://developer.android.com/studio).
2. Run the installer and follow the defaults.
3. On first launch, complete the **Setup Wizard** — it will download the Android SDK and other components.
4. Enable **USB debugging** on your Android device:
   - Go to **Settings → About Phone → tap "Build number" 7 times**.
   - Go to **Settings → Developer Options → enable USB Debugging**.

### 3. ngrok

1. Create a free account at [ngrok.com](https://ngrok.com/).
2. Install ngrok using **one** of these methods:
   - **Download:** Get the ZIP from the [ngrok downloads page](https://ngrok.com/download), extract it, and add the folder to your system `PATH`.
   - **Chocolatey:** `choco install ngrok`
3. Authenticate ngrok with your account token (found on the [ngrok dashboard](https://dashboard.ngrok.com/get-started/your-authtoken)):
   ```
   ngrok config add-authtoken <YOUR_TOKEN>
   ```
4. Verify:
   ```
   ngrok version
   ```

---

## Step 1 — Start the Backend Server

Open a terminal in the project root (`f:\parental-app`):

```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Start the FastAPI server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

On **first run**, the server will:

1. Create `config.json` with a randomly generated API key.
2. Print the API key to the console. **Copy and save it** — you will need it for both the desktop dashboard and the Android app.

You should see output similar to:

```
INFO:     API Key: a1b2c3d4-e5f6-7890-abcd-ef1234567890
INFO:     Uvicorn running on http://0.0.0.0:8000
```

> [!TIP]
> You can also find your API key any time in `f:\parental-app\config.json`.

**Verify the server is running:**

```bash
curl http://localhost:8000/api/health
# Expected: {"status":"ok","timestamp":"..."}
```

---

## Step 2 — Start ngrok

Open a **new** terminal (keep the backend running) and start the tunnel:

```bash
ngrok http 8000
```

ngrok will display a forwarding URL like:

```
Forwarding    https://a1b2-203-0-113-42.ngrok-free.app -> http://localhost:8000
```

**Copy the HTTPS URL** (e.g., `https://a1b2-203-0-113-42.ngrok-free.app`). You will enter this URL in both the desktop dashboard and the Android app.

> [!WARNING]
> The free tier of ngrok generates a **new URL every time you restart ngrok**. If you restart ngrok, you must update the URL in both the desktop dashboard and the Android app. Consider the [ngrok paid tier](https://ngrok.com/pricing) for a static domain.

---

## Step 3 — Launch the Desktop Dashboard

Open a **new** terminal:

```bash
# Install desktop dependencies
pip install -r desktop/requirements.txt

# Launch the dashboard
cd f:\parental-app
python -m desktop.main
```

The PySide6 dashboard window will open. Enter:

- **ngrok URL** — the HTTPS URL from Step 2.
- **API Key** — the key from Step 1.

> [!NOTE]
> The desktop dashboard also has a **Start Server** button that can launch the backend for you, so you can skip Step 1 on subsequent runs if you prefer.

---

## Step 4 — Install the Android App

### Build the APK

1. Open Android Studio.
2. Click **File → Open** and select the `f:\parental-app\android\` directory.
3. Wait for **Gradle sync** to complete (may take a few minutes on first open).
4. Connect your Android device via USB, or start an **emulator** from the AVD Manager.
5. Click the green **Run ▶** button (or press `Shift+F10`).
6. Android Studio will build the APK and install it on the device.

### Configure the App

1. Open the **Parental Control** app on the Android device.
2. Enter the **ngrok HTTPS URL** from Step 2.
3. Enter the **API Key** from Step 1.
4. Tap **Connect** — the app will register the device with the backend.
5. Tap **Start Monitoring**.
6. Android will show a **screen capture permission dialog** — tap **Start now** (or **Allow**).

The app will now:

- Send heartbeats every 15 seconds to keep the device marked as online.
- Show a persistent notification indicating that monitoring is active.
- Respond to screenshot requests from the desktop dashboard.

---

## Step 5 — Verify Everything Works

1. In the **desktop dashboard**, you should see your Android device listed as **Online**.
2. Click **Request Screenshot**.
3. Within a few seconds, the screenshot should appear in the dashboard.
4. The screenshot image is saved locally in `f:\parental-app\screenshots\`.

**Congratulations!** The system is running.

---

## Testing with Two Different Networks

To confirm the system works across networks (the real use case):

1. Keep the **PC on your home Wi-Fi**.
2. Disconnect the **phone from Wi-Fi** and use **mobile data** instead.
3. Both the PC and the phone connect through the **ngrok HTTPS URL**, so they don't need to be on the same network.
4. Request a screenshot from the desktop dashboard and confirm it appears.

> [!TIP]
> For initial testing, you can use the **Android emulator** on the same PC. The emulator accesses `localhost` through the special IP `10.0.2.2`, but since you're using ngrok, you can just enter the ngrok URL directly.

---

## Stopping the System

| Component | How to stop |
|---|---|
| Backend server | Press `Ctrl+C` in the terminal |
| ngrok | Press `Ctrl+C` in the terminal |
| Desktop dashboard | Close the window |
| Android app | Tap **Stop Monitoring** in the app, or dismiss the notification |

---

## Next Steps

- Read the [API Reference](api.md) for endpoint details.
- Check [Troubleshooting](troubleshooting.md) if something isn't working.
- Review the [Security Guide](security.md) to understand the security model.
