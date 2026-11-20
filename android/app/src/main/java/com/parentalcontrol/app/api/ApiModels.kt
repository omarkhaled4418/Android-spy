package com.parentalcontrol.app.api

import com.google.gson.annotations.SerializedName

// ── Device Registration ──

data class DeviceRegistrationRequest(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("device_name") val deviceName: String,
    @SerializedName("device_model") val deviceModel: String,
    @SerializedName("android_version") val androidVersion: String,
    @SerializedName("app_version") val appVersion: String
)

data class DeviceRegistrationResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("message") val message: String
)

// ── Heartbeat ──

data class HeartbeatResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("pending_commands") val pendingCommands: List<PendingCommand>,
    @SerializedName("is_live") val isLive: Boolean? = false
)

// ── Live Monitoring ──

data class LiveFrameResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("is_live") val isLive: Boolean
)

data class LiveStatusResponse(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("is_live") val isLive: Boolean,
    @SerializedName("fps") val fps: Float,
    @SerializedName("viewers") val viewers: Int
)

data class PendingCommand(
    @SerializedName("command_id") val commandId: String,
    @SerializedName("command_type") val commandType: String,
    @SerializedName("created_at") val createdAt: String
)

// ── Screenshot Upload ──

data class ScreenshotUploadResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("screenshot_id") val screenshotId: String,
    @SerializedName("message") val message: String
)

// ── Health ──

data class HealthResponse(
    @SerializedName("status") val status: String,
    @SerializedName("timestamp") val timestamp: String
)

// ── Devices List ──

data class DevicesListResponse(
    @SerializedName("devices") val devices: List<DeviceInfo>
)

data class DeviceInfo(
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("device_name") val deviceName: String,
    @SerializedName("device_model") val deviceModel: String,
    @SerializedName("android_version") val androidVersion: String,
    @SerializedName("app_version") val appVersion: String,
    @SerializedName("is_online") val isOnline: Boolean,
    @SerializedName("last_seen") val lastSeen: String,
    @SerializedName("registered_at") val registeredAt: String
)

// ── Screenshot List ──

data class ScreenshotListResponse(
    @SerializedName("screenshots") val screenshots: List<ScreenshotInfo>,
    @SerializedName("total") val total: Int
)

data class ScreenshotInfo(
    @SerializedName("screenshot_id") val screenshotId: String,
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("command_id") val commandId: String,
    @SerializedName("filename") val filename: String,
    @SerializedName("file_size") val fileSize: Long,
    @SerializedName("created_at") val createdAt: String
)

// ── Screenshot Status ──

data class ScreenshotStatusResponse(
    @SerializedName("command_id") val commandId: String,
    @SerializedName("status") val status: String,
    @SerializedName("screenshot_id") val screenshotId: String?,
    @SerializedName("created_at") val createdAt: String
)

// ── Error ──

data class ErrorResponse(
    @SerializedName("detail") val detail: String
)
