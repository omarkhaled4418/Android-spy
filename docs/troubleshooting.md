# Troubleshooting

Common problems and their solutions when running the Parental Control System.

---

## Connection Issues

### "Connection refused" when accessing the server

**Symptoms:** `curl` or the app cannot reach `http://localhost:8000`.

**Solutions:**

1. **Is the server running?** Check that the backend process is active:
   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```
2. **Correct port?** Ensure you're connecting to port `8000` (or whatever port is set in `config.json`).
3. **Firewall blocking the port?** See ["Firewall blocking port 8000"](#firewall-blocking-port-8000) below.
4. **Bound to `127.0.0.1` instead of `0.0.0.0`?** The `--host 0.0.0.0` flag is required for ngrok to reach the server.

---

### "401 Unauthorized"

**Symptoms:** API calls return `{"detail": "Invalid or missing API key"}`.

**Solutions:**

1. **Missing `Bearer` prefix** — The header must be `Authorization: Bearer <API_KEY>`, not just `Authorization: <API_KEY>`.
2. **Wrong API key** — Check `f:\parental-app\config.json` for the correct `api_key` value.
3. **Extra whitespace** — Ensure there are no leading/trailing spaces in the API key.
4. **Regenerated key** — If you deleted and regenerated `config.json`, the key has changed. Update it in both the desktop dashboard and the Android app.

---

### Device shows as "Offline"

**Symptoms:** The desktop dashboard shows the device as offline even though the Android app is running.

**Solutions:**

1. **Heartbeat not reaching the server** — The device must send a heartbeat every 15 seconds. It is considered offline after 45 seconds of no heartbeat.
2. **Wrong ngrok URL** — If you restarted ngrok, the URL changed. Update the URL in the Android app.
3. **ngrok tunnel not running** — Make sure `ngrok http 8000` is still running.
4. **Network connectivity** — Ensure the Android device has an internet connection (Wi-Fi or mobile data).
5. **App not in foreground** — Some Android devices aggressively kill background services. See ["Android app crashes"](#android-app-crashes-or-stops-in-background) below.

---

### Screenshot request times out

**Symptoms:** You click "Request Screenshot" but nothing appears.

**Solutions:**

1. **MediaProjection permission not granted** — The Android app must have screen capture permission. If you denied the system dialog, restart the app and tap **Start Monitoring** again, then approve the permission.
2. **App in background/killed** — Some Android manufacturers (Xiaomi, Huawei, Samsung) aggressively kill background apps. See [Android app crashes](#android-app-crashes-or-stops-in-background).
3. **Device offline** — Check the device status in the dashboard. If offline, the screenshot request returns a `503` error.
4. **Command expired** — Check the request status via the API; the command may have expired before the device picked it up.

---

### ngrok URL changed

**Symptoms:** Everything was working, but after restarting ngrok, the app can't connect.

**Cause:** The free tier of ngrok generates a **new URL on every restart**.

**Solutions:**

1. After restarting ngrok, **copy the new HTTPS URL** from the ngrok terminal.
2. Update the URL in the **Android app** settings.
3. Update the URL in the **desktop dashboard** settings.
4. **Permanent fix:** Upgrade to a [paid ngrok plan](https://ngrok.com/pricing) for a static domain that doesn't change.

---

## Android Issues

### Android app crashes or stops in background

**Symptoms:** The app stops sending heartbeats or crashes after a while.

**Solutions:**

1. **Check logcat** for crash details:
   ```bash
   adb logcat -s ParentalControl
   ```
2. **Battery optimization** — Go to **Settings → Battery → App Battery Management** and set the Parental Control app to **Unrestricted** or **Don't optimize**.
3. **Manufacturer-specific settings:**
   - **Xiaomi/MIUI:** Settings → Apps → Manage Apps → Parental Control → enable Autostart; disable battery saver for the app.
   - **Huawei/EMUI:** Settings → Battery → App Launch → set to Manual and enable all three toggles.
   - **Samsung/OneUI:** Settings → Device Care → Battery → Background usage limits → add to "Never sleeping apps."
4. **Lock the app in recent apps** — Open the app switcher, long-press the app card, and tap the lock/pin icon.

### Android emulator can't reach localhost

**Symptoms:** The emulator can't connect to `http://localhost:8000`.

**Solution:** The Android emulator runs in a virtual network. To reach the host machine's `localhost`:

- Use `http://10.0.2.2:8000` instead of `http://localhost:8000`.
- **Better:** Use the **ngrok URL** even during emulator testing. This avoids the issue entirely and tests the same path the real device will use.

---

## Server Issues

### Firewall blocking port 8000

**Symptoms:** ngrok can't reach the backend, or the backend is unreachable from other machines on the LAN.

**Solution:** Add a Windows Firewall exception:

1. Open **Windows Defender Firewall with Advanced Security**.
2. Click **Inbound Rules → New Rule**.
3. Select **Port → TCP → Specific port: 8000**.
4. Select **Allow the connection**.
5. Apply to all profiles (Domain, Private, Public).
6. Name it "Parental Control Backend".

Or via PowerShell (run as administrator):

```powershell
New-NetFirewallRule -DisplayName "Parental Control Backend" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

---

### "Address already in use" (port 8000)

**Symptoms:** Server fails to start with `[Errno 10048]` or `address already in use`.

**Solution:** Another process is using port 8000. Find and kill it:

```powershell
# Find what's using port 8000
netstat -aon | findstr :8000

# Kill the process by PID (replace 12345 with the actual PID)
taskkill /PID 12345 /F
```

Alternatively, use a different port:

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001
ngrok http 8001
```

> [!IMPORTANT]
> If you change the port, update `server_port` in `config.json` and the ngrok command accordingly.

---

### Screenshots not saving

**Symptoms:** Screenshots are captured and uploaded but files don't appear in the `screenshots/` folder.

**Solutions:**

1. **Check directory permissions** — Ensure the `f:\parental-app\screenshots\` directory exists and is writable.
2. **Create the directory manually** if it doesn't exist:
   ```powershell
   mkdir f:\parental-app\screenshots
   ```
3. **Check disk space** — Ensure the drive has free space.
4. **Check `config.json`** — The `screenshot_dir` field should point to `f:\\parental-app\\screenshots`.

---

## Installation Issues

### `pip install` fails

**Symptoms:** Errors during `pip install -r requirements.txt`.

**Solutions:**

1. **Upgrade pip:**
   ```bash
   python -m pip install --upgrade pip
   ```
2. **Use `--user` flag** if you don't have admin permissions:
   ```bash
   pip install --user -r backend/requirements.txt
   ```
3. **Virtual environment** (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r backend/requirements.txt
   ```
4. **Missing C++ build tools** — Some packages need Visual C++ build tools. Install from [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).

---

### PySide6 won't start (desktop dashboard)

**Symptoms:** `ImportError` or the dashboard window doesn't appear.

**Solutions:**

1. **Python version** — PySide6 requires Python 3.9+. Check with `python --version`.
2. **Reinstall PySide6:**
   ```bash
   pip uninstall PySide6 PySide6-Essentials PySide6-Addons
   pip install PySide6>=6.5.0
   ```
3. **Missing system libraries** — On some Windows installs, PySide6 needs the Visual C++ Redistributable. Download from [Microsoft](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).
4. **Display scaling** — If the UI appears blurry, set the `QT_SCALE_FACTOR` environment variable:
   ```bash
   set QT_SCALE_FACTOR=1
   python -m desktop.main
   ```

---

### SSL certificate errors with ngrok

**Symptoms:** `SSL: CERTIFICATE_VERIFY_FAILED` or similar errors.

**Solution:** This can occur with ngrok's free tier. The Android app and desktop client should handle ngrok's certificates correctly by default. If you encounter issues:

1. Ensure you're using the **HTTPS** URL (not HTTP).
2. Update your `certifi` package: `pip install --upgrade certifi`.
3. If testing with `curl`, you can temporarily bypass verification with `-k` (not recommended for production).

---

## Multiple Devices

### Setting up multiple Android devices

Each Android device is identified by a unique `device_id` derived from `ANDROID_ID`. Simply:

1. Install the app on each device.
2. Enter the same ngrok URL and API key.
3. Tap **Connect** — each device registers with its own unique ID.
4. All devices appear separately in the desktop dashboard.

> [!NOTE]
> `ANDROID_ID` is unique per device and per app signing key. Factory resetting a device or reinstalling the app with a different signing key may generate a new `device_id`.

---

## Still Stuck?

1. **Check server logs** — The backend terminal shows all incoming requests and errors.
2. **Check logcat** — Run `adb logcat` to see Android app logs.
3. **Test the API directly** — Use `curl` commands from the [API Reference](api.md) to isolate whether the issue is in the backend, desktop, or Android app.
4. **Restart everything** — Stop all components, then start them in order: backend → ngrok → desktop → Android app.
