# Parental Control System — API Contract (Phase One)

## Base URL
- Local: `http://localhost:8000`
- Public: ngrok HTTPS URL (configured at runtime)

## Authentication
- **Method**: API Key (static shared secret)
- **Header**: `Authorization: Bearer <API_KEY>`
- API_KEY is generated on first run, stored in `config.json`
- Both desktop and Android use the same API key
- All endpoints require authentication except `GET /api/health`

## Endpoints

### Health Check
```
GET /api/health
Response: {"status": "ok", "timestamp": "ISO8601"}
```

### Device Registration
```
POST /api/devices/register
Headers: Authorization: Bearer <API_KEY>
Body: {
    "device_id": "uuid-string",
    "device_name": "string",
    "device_model": "string",
    "android_version": "string",
    "app_version": "string"
}
Response 200: {
    "success": true,
    "device_id": "uuid-string",
    "message": "Device registered successfully"
}
Response 409: {"detail": "Device already registered"}
```

### Device Heartbeat
```
POST /api/devices/{device_id}/heartbeat
Headers: Authorization: Bearer <API_KEY>
Response 200: {
    "success": true,
    "pending_commands": [
        {"command_id": "uuid", "command_type": "screenshot_request", "created_at": "ISO8601"}
    ]
}
```
Heartbeat interval: 15 seconds. Device considered offline after 45 seconds of no heartbeat.

### List Devices
```
GET /api/devices
Headers: Authorization: Bearer <API_KEY>
Response 200: {
    "devices": [
        {
            "device_id": "uuid",
            "device_name": "string",
            "device_model": "string",
            "android_version": "string",
            "app_version": "string",
            "is_online": true,
            "last_seen": "ISO8601",
            "registered_at": "ISO8601"
        }
    ]
}
```

### Request Screenshot
```
POST /api/screenshots/request/{device_id}
Headers: Authorization: Bearer <API_KEY>
Response 200: {
    "success": true,
    "command_id": "uuid",
    "message": "Screenshot request sent"
}
Response 404: {"detail": "Device not found"}
Response 503: {"detail": "Device is offline"}
```

### Upload Screenshot
```
POST /api/screenshots/upload
Headers: Authorization: Bearer <API_KEY>
Content-Type: multipart/form-data
Form fields:
    - device_id: string
    - command_id: string
    - image: file (PNG/JPEG)
Response 200: {
    "success": true,
    "screenshot_id": "uuid",
    "message": "Screenshot uploaded successfully"
}
```

### Get Screenshot Image
```
GET /api/screenshots/{screenshot_id}/image
Headers: Authorization: Bearer <API_KEY>
Response 200: image/png binary
Response 404: {"detail": "Screenshot not found"}
```

### List Screenshots
```
GET /api/screenshots?device_id={device_id}&limit=20&offset=0
Headers: Authorization: Bearer <API_KEY>
Response 200: {
    "screenshots": [
        {
            "screenshot_id": "uuid",
            "device_id": "uuid",
            "command_id": "uuid",
            "filename": "string",
            "file_size": 123456,
            "created_at": "ISO8601"
        }
    ],
    "total": 50
}
```

### Get Screenshot Request Status
```
GET /api/screenshots/status/{command_id}
Headers: Authorization: Bearer <API_KEY>
Response 200: {
    "command_id": "uuid",
    "status": "pending|completed|expired",
    "screenshot_id": "uuid or null",
    "created_at": "ISO8601"
}
```

### Live Monitoring Endpoints

#### Start Live Stream
```
POST /api/live/start/{device_id}
Headers: Authorization: Bearer <API_KEY>
Response 200: {
    "success": true,
    "message": "Live monitoring requested",
    "command_id": "uuid",
    "is_live": true
}
```

#### Stop Live Stream
```
POST /api/live/stop/{device_id}
Headers: Authorization: Bearer <API_KEY>
Response 200: {
    "success": true,
    "message": "Live monitoring stopped",
    "is_live": false
}
```

#### Live Status
```
GET /api/live/status/{device_id}
Response 200: {
    "device_id": "uuid",
    "is_live": true,
    "fps": 1.5,
    "viewers": 1,
    "last_frame_time": 1700000000.0,
    "has_frame": true
}
```

#### Upload Live Frame (Device to Server)
```
POST /api/live/frame
Headers: Authorization: Bearer <API_KEY>
Content-Type: multipart/form-data
Form fields:
    - device_id: string
    - frame: file (JPEG)
Response 200: {
    "success": true,
    "is_live": true
}
```

#### WebSocket Live Binary Feed
```
WS /api/live/ws/{device_id}
Binary frames: Raw JPEG blobs delivered in real time as captured.
```

#### MJPEG Stream
```
GET /api/live/mjpeg/{device_id}
Response 200: multipart/x-mixed-replace continuous stream
```

#### Latest Live Frame
```
GET /api/live/latest/{device_id}
Response 200: image/jpeg binary
```

## Data Storage
- Screenshots saved in: `f:\parental-app\screenshots\` as `{device_id}_{timestamp}.png`
- Database: SQLite at `f:\parental-app\backend\parental_control.db`
- Config: `f:\parental-app\config.json`

## Config File Format
```json
{
    "api_key": "generated-secure-key",
    "server_host": "0.0.0.0",
    "server_port": 8000,
    "screenshot_dir": "f:\\parental-app\\screenshots",
    "heartbeat_timeout_seconds": 45,
    "ngrok_url": ""
}
```
