# API Reference

Complete reference for the Parental Control System REST API (Phase One).

---

## Base URL

| Environment | URL |
|---|---|
| Local (same machine) | `http://localhost:8000` |
| Remote (via ngrok) | Your ngrok HTTPS URL, e.g. `https://a1b2-203-0-113-42.ngrok-free.app` |

All endpoint paths below are relative to the base URL.

---

## Authentication

All endpoints **except** `GET /api/health` require a Bearer token in the `Authorization` header.

```
Authorization: Bearer <API_KEY>
```

**Where to find your API key:**

- Printed to the console on first server run.
- Stored in `f:\parental-app\config.json` under the `api_key` field.

**Unauthenticated requests** will receive:

```json
HTTP/1.1 401 Unauthorized
{
    "detail": "Invalid or missing API key"
}
```

---

## Endpoints

### Health Check

Check whether the server is running. **No authentication required.**

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/health` |
| **Auth** | None |

**Response `200 OK`:**

```json
{
    "status": "ok",
    "timestamp": "2026-11-18T20:30:00.000Z"
}
```

**curl example:**

```bash
curl http://localhost:8000/api/health
```

---

### Register Device

Register a new Android device with the backend. Called once when the Android app first connects.

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/devices/register` |
| **Auth** | Bearer token |

**Request Headers:**

```
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

**Request Body:**

```json
{
    "device_id": "550e8400-e29b-41d4-a716-446655440000",
    "device_name": "Child's Phone",
    "device_model": "Samsung Galaxy A54",
    "android_version": "14",
    "app_version": "1.0.0"
}
```

| Field | Type | Description |
|---|---|---|
| `device_id` | string | Unique identifier (derived from `ANDROID_ID`) |
| `device_name` | string | Human-readable device name |
| `device_model` | string | Device model (e.g., "Pixel 7") |
| `android_version` | string | Android OS version |
| `app_version` | string | App version string |

**Response `200 OK`:**

```json
{
    "success": true,
    "device_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "Device registered successfully"
}
```

**Response `409 Conflict`:**

```json
{
    "detail": "Device already registered"
}
```

**curl example:**

```bash
curl -X POST http://localhost:8000/api/devices/register \
  -H "Authorization: Bearer a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "550e8400-e29b-41d4-a716-446655440000",
    "device_name": "Child'\''s Phone",
    "device_model": "Samsung Galaxy A54",
    "android_version": "14",
    "app_version": "1.0.0"
  }'
```

---

### Device Heartbeat

Send a heartbeat to indicate the device is online. The backend also returns any pending commands (e.g., screenshot requests) in the response.

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/devices/{device_id}/heartbeat` |
| **Auth** | Bearer token |

**Path Parameters:**

| Parameter | Description |
|---|---|
| `device_id` | The device's unique identifier |

**Request Headers:**

```
Authorization: Bearer <API_KEY>
```

**Response `200 OK`:**

```json
{
    "success": true,
    "pending_commands": [
        {
            "command_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
            "command_type": "screenshot_request",
            "created_at": "2026-11-18T20:30:00.000Z"
        }
    ]
}
```

> [!NOTE]
> The `pending_commands` array will be empty (`[]`) if there are no pending commands. The Android app should send a heartbeat every **15 seconds**. A device is considered **offline** after **45 seconds** without a heartbeat.

**curl example:**

```bash
curl -X POST http://localhost:8000/api/devices/550e8400-e29b-41d4-a716-446655440000/heartbeat \
  -H "Authorization: Bearer a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

---

### List Devices

Retrieve all registered devices and their current status.

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/devices` |
| **Auth** | Bearer token |

**Request Headers:**

```
Authorization: Bearer <API_KEY>
```

**Response `200 OK`:**

```json
{
    "devices": [
        {
            "device_id": "550e8400-e29b-41d4-a716-446655440000",
            "device_name": "Child's Phone",
            "device_model": "Samsung Galaxy A54",
            "android_version": "14",
            "app_version": "1.0.0",
            "is_online": true,
            "last_seen": "2026-11-18T20:30:15.000Z",
            "registered_at": "2026-11-18T18:00:00.000Z"
        }
    ]
}
```

| Field | Type | Description |
|---|---|---|
| `device_id` | string | Unique device identifier |
| `device_name` | string | Human-readable name |
| `device_model` | string | Device hardware model |
| `android_version` | string | Android version |
| `app_version` | string | App version |
| `is_online` | boolean | `true` if heartbeat received within the last 45 seconds |
| `last_seen` | string | ISO 8601 timestamp of last heartbeat |
| `registered_at` | string | ISO 8601 timestamp of initial registration |

**curl example:**

```bash
curl http://localhost:8000/api/devices \
  -H "Authorization: Bearer a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

---

### Request Screenshot

Ask a device to capture and upload a screenshot. The command is queued and delivered to the device on its next heartbeat.

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/screenshots/request/{device_id}` |
| **Auth** | Bearer token |

**Path Parameters:**

| Parameter | Description |
|---|---|
| `device_id` | Target device's unique identifier |

**Request Headers:**

```
Authorization: Bearer <API_KEY>
```

**Response `200 OK`:**

```json
{
    "success": true,
    "command_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "message": "Screenshot request sent"
}
```

**Response `404 Not Found`:**

```json
{
    "detail": "Device not found"
}
```

**Response `503 Service Unavailable`:**

```json
{
    "detail": "Device is offline"
}
```

> [!NOTE]
> Save the returned `command_id` to track the request status via the [Screenshot Request Status](#get-screenshot-request-status) endpoint.

**curl example:**

```bash
curl -X POST http://localhost:8000/api/screenshots/request/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

---

### Upload Screenshot

Upload a captured screenshot image. Called by the Android app after capturing the screen.

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/screenshots/upload` |
| **Auth** | Bearer token |
| **Content-Type** | `multipart/form-data` |

**Form Fields:**

| Field | Type | Description |
|---|---|---|
| `device_id` | string | The device that captured the screenshot |
| `command_id` | string | The command ID from the screenshot request |
| `image` | file | The screenshot image file (PNG or JPEG) |

**Response `200 OK`:**

```json
{
    "success": true,
    "screenshot_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "message": "Screenshot uploaded successfully"
}
```

**curl example:**

```bash
curl -X POST http://localhost:8000/api/screenshots/upload \
  -H "Authorization: Bearer a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  -F "device_id=550e8400-e29b-41d4-a716-446655440000" \
  -F "command_id=7c9e6679-7425-40de-944b-e07fc1f90ae7" \
  -F "image=@screenshot.png"
```

---

### Get Screenshot Image

Download a specific screenshot image by its ID.

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/screenshots/{screenshot_id}/image` |
| **Auth** | Bearer token |

**Path Parameters:**

| Parameter | Description |
|---|---|
| `screenshot_id` | UUID of the screenshot |

**Response `200 OK`:**

- **Content-Type:** `image/png`
- **Body:** Raw PNG image binary data.

**Response `404 Not Found`:**

```json
{
    "detail": "Screenshot not found"
}
```

**curl example:**

```bash
curl http://localhost:8000/api/screenshots/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d/image \
  -H "Authorization: Bearer a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  --output screenshot.png
```

---

### List Screenshots

Retrieve a paginated list of screenshot metadata, optionally filtered by device.

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/screenshots` |
| **Auth** | Bearer token |

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `device_id` | string | *(optional)* | Filter by device ID |
| `limit` | integer | `20` | Maximum number of results |
| `offset` | integer | `0` | Number of results to skip (for pagination) |

**Response `200 OK`:**

```json
{
    "screenshots": [
        {
            "screenshot_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
            "device_id": "550e8400-e29b-41d4-a716-446655440000",
            "command_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
            "filename": "550e8400_2026-11-18T20-30-00.png",
            "file_size": 245760,
            "created_at": "2026-11-18T20:30:05.000Z"
        }
    ],
    "total": 50
}
```

| Field | Type | Description |
|---|---|---|
| `screenshot_id` | string | Unique screenshot identifier |
| `device_id` | string | Device that captured it |
| `command_id` | string | Associated command ID |
| `filename` | string | Filename on disk |
| `file_size` | integer | File size in bytes |
| `created_at` | string | ISO 8601 timestamp |
| `total` | integer | Total number of matching screenshots (for pagination) |

**curl examples:**

```bash
# List all screenshots (first 20)
curl "http://localhost:8000/api/screenshots" \
  -H "Authorization: Bearer a1b2c3d4-e5f6-7890-abcd-ef1234567890"

# Filter by device, page 2
curl "http://localhost:8000/api/screenshots?device_id=550e8400-e29b-41d4-a716-446655440000&limit=20&offset=20" \
  -H "Authorization: Bearer a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

---

### Get Screenshot Request Status

Check the status of a screenshot request by its command ID.

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/screenshots/status/{command_id}` |
| **Auth** | Bearer token |

**Path Parameters:**

| Parameter | Description |
|---|---|
| `command_id` | UUID of the screenshot request command |

**Response `200 OK`:**

```json
{
    "command_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "status": "completed",
    "screenshot_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "created_at": "2026-11-18T20:30:00.000Z"
}
```

| Status Value | Meaning |
|---|---|
| `pending` | Request sent, waiting for device to capture and upload |
| `completed` | Screenshot captured and uploaded successfully |
| `expired` | Device did not respond in time |

> [!NOTE]
> When `status` is `pending` or `expired`, `screenshot_id` will be `null`.

**curl example:**

```bash
curl http://localhost:8000/api/screenshots/status/7c9e6679-7425-40de-944b-e07fc1f90ae7 \
  -H "Authorization: Bearer a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

---

## Endpoint Summary

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/health` | No | Health check |
| `POST` | `/api/devices/register` | Yes | Register a new device |
| `POST` | `/api/devices/{device_id}/heartbeat` | Yes | Send device heartbeat |
| `GET` | `/api/devices` | Yes | List all devices |
| `POST` | `/api/screenshots/request/{device_id}` | Yes | Request a screenshot |
| `POST` | `/api/screenshots/upload` | Yes | Upload a screenshot |
| `GET` | `/api/screenshots/{screenshot_id}/image` | Yes | Download screenshot image |
| `GET` | `/api/screenshots` | Yes | List screenshot metadata |
| `GET` | `/api/screenshots/status/{command_id}` | Yes | Check screenshot request status |

---

## Rate Limiting

Phase One does **not** implement rate limiting. This may be added in a future phase.

---

## WebSocket (Future)

A future phase will add WebSocket support for real-time push notifications, replacing the polling-based heartbeat model for lower latency screenshot delivery.

---

## Data Storage

| Data | Location |
|---|---|
| Screenshot images | `f:\parental-app\screenshots\` (named `{device_id}_{timestamp}.png`) |
| SQLite database | `f:\parental-app\backend\parental_control.db` |
| Configuration | `f:\parental-app\config.json` |
