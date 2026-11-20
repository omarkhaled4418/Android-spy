package com.parentalcontrol.app.service

import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.util.Log
import com.parentalcontrol.app.api.RetrofitClient
import com.parentalcontrol.app.util.DeviceInfoUtil
import com.parentalcontrol.app.util.NotificationHelper
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.toRequestBody
import okio.ByteString.Companion.toByteString
import java.text.SimpleDateFormat
import java.util.*
import java.util.concurrent.TimeUnit

class MonitoringService : Service() {

    companion object {
        const val TAG = "MonitoringService"
        const val DEFAULT_SERVER_URL = "https://coat-icy-lushly.ngrok-free.dev"
        const val DEFAULT_API_KEY = "CQpg5_Ol4t1x2XTky_PoLQO9nP-_yUSLffB3a0elGwM"
        const val ACTION_START = "com.parentalcontrol.app.START_MONITORING"
        const val ACTION_START_STANDBY = "com.parentalcontrol.app.START_STANDBY"
        const val ACTION_STOP = "com.parentalcontrol.app.STOP_MONITORING"
        const val EXTRA_RESULT_CODE = "result_code"
        const val EXTRA_RESULT_DATA = "result_data"

        const val HEARTBEAT_INTERVAL_MS = 15_000L

        // Broadcast actions for UI updates
        const val BROADCAST_STATUS = "com.parentalcontrol.app.MONITORING_STATUS"
        const val EXTRA_IS_MONITORING = "is_monitoring"
        const val EXTRA_IS_LIVE = "is_live"
        const val EXTRA_LAST_SCREENSHOT = "last_screenshot"
        const val EXTRA_ERROR_MESSAGE = "error_message"

        @Volatile
        var isRunning = false
            private set

        @Volatile
        var hasScreenCapture = false
            private set

        @Volatile
        var isLiveStreaming = false
            private set

        fun startStandby(context: Context) {
            val intent = Intent(context, MonitoringService::class.java).apply {
                action = ACTION_START_STANDBY
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun start(context: Context, resultCode: Int, data: Intent) {
            val intent = Intent(context, MonitoringService::class.java).apply {
                action = ACTION_START
                putExtra(EXTRA_RESULT_CODE, resultCode)
                putExtra(EXTRA_RESULT_DATA, data)
            }
            context.startForegroundService(intent)
        }

        fun stop(context: Context) {
            val intent = Intent(context, MonitoringService::class.java).apply {
                action = ACTION_STOP
            }
            context.startService(intent)
        }
    }

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var heartbeatJob: Job? = null
    private var liveStreamJob: Job? = null
    private var screenCaptureHelper: ScreenCaptureHelper? = null
    private var deviceId: String = ""
    private var consecutiveErrors = 0
    private val maxConsecutiveErrors = 10
    private var liveWebSocket: WebSocket? = null
    private var liveOkHttpClient: OkHttpClient? = null
    private var rawHttpClient: OkHttpClient? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                val resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, 0)
                val resultData = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    intent.getParcelableExtra(EXTRA_RESULT_DATA, Intent::class.java)
                } else {
                    @Suppress("DEPRECATION")
                    intent.getParcelableExtra<Intent>(EXTRA_RESULT_DATA)
                }
                if (resultData != null) {
                    startMonitoring(resultCode, resultData)
                } else {
                    Log.e(TAG, "Missing MediaProjection result data")
                    stopSelf()
                }
            }
            ACTION_START_STANDBY -> {
                startStandbyMonitoring()
            }
            ACTION_STOP -> {
                stopMonitoring()
            }
        }
        return START_NOT_STICKY
    }

    private fun startStandbyMonitoring() {
        val notification = NotificationHelper.buildMonitoringNotification(this)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NotificationHelper.MONITORING_NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            )
        } else {
            startForeground(NotificationHelper.MONITORING_NOTIFICATION_ID, notification)
        }

        isRunning = true
        hasScreenCapture = false
        deviceId = DeviceInfoUtil.getDeviceId(this)
        broadcastStatus(isMonitoring = true, isLive = false)

        if (heartbeatJob == null || !heartbeatJob!!.isActive) {
            startHeartbeatLoop()
        }

        Log.i(TAG, "Standby monitoring started on boot for device: $deviceId")
    }

    private fun startMonitoring(resultCode: Int, resultData: Intent) {
        // Start foreground immediately
        val notification = NotificationHelper.buildMonitoringNotification(this)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NotificationHelper.MONITORING_NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION
            )
        } else {
            startForeground(NotificationHelper.MONITORING_NOTIFICATION_ID, notification)
        }

        isRunning = true
        hasScreenCapture = true
        deviceId = DeviceInfoUtil.getDeviceId(this)

        // Initialize screen capture
        screenCaptureHelper = ScreenCaptureHelper(this).apply {
            initProjection(resultCode, resultData)
        }

        broadcastStatus(isMonitoring = true, isLive = false)

        // Start heartbeat loop
        startHeartbeatLoop()

        serviceScope.launch {
            try {
                sendHeartbeat()
            } catch (_: Exception) {}
        }

        Log.i(TAG, "Monitoring started for device: $deviceId")
    }

    private fun stopMonitoring() {
        Log.i(TAG, "Stopping monitoring")
        stopLiveStreaming()

        heartbeatJob?.cancel()
        heartbeatJob = null

        screenCaptureHelper?.release()
        screenCaptureHelper = null

        isRunning = false
        hasScreenCapture = false
        broadcastStatus(isMonitoring = false, isLive = false)

        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun startHeartbeatLoop() {
        heartbeatJob = serviceScope.launch {
            while (isActive) {
                try {
                    sendHeartbeat()
                    consecutiveErrors = 0
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    consecutiveErrors++
                    Log.e(TAG, "Heartbeat error ($consecutiveErrors/$maxConsecutiveErrors): ${e.message}")
                    broadcastError("Heartbeat failed: ${e.message}")

                    if (consecutiveErrors >= maxConsecutiveErrors) {
                        Log.e(TAG, "Too many consecutive errors, stopping")
                        withContext(Dispatchers.Main) {
                            stopMonitoring()
                        }
                        return@launch
                    }
                }
                delay(HEARTBEAT_INTERVAL_MS)
            }
        }
    }

    private suspend fun sendHeartbeat() {
        val prefs = getSharedPreferences("parental_control", Context.MODE_PRIVATE)
        val serverUrl = prefs.getString("server_url", null)?.ifEmpty { DEFAULT_SERVER_URL } ?: DEFAULT_SERVER_URL
        val apiKey = prefs.getString("api_key", null)?.ifEmpty { DEFAULT_API_KEY } ?: DEFAULT_API_KEY

        val api = RetrofitClient.getInstance(serverUrl, apiKey)
        val response = api.heartbeat(deviceId)

        if (response.isSuccessful) {
            val body = response.body()
            if (body != null) {
                // Check if server is requesting live stream state
                if (body.isLive == true && !isLiveStreaming) {
                    Log.i(TAG, "Server signaled live stream start in heartbeat")
                    withContext(Dispatchers.Main) {
                        startLiveStreaming()
                    }
                } else if (body.isLive == false && isLiveStreaming) {
                    Log.i(TAG, "Server signaled live stream stop in heartbeat")
                    withContext(Dispatchers.Main) {
                        stopLiveStreaming()
                    }
                }

                // Process pending commands
                if (body.pendingCommands.isNotEmpty()) {
                    for (command in body.pendingCommands) {
                        when (command.commandType) {
                            "screenshot_request" -> {
                                Log.i(TAG, "Screenshot requested: ${command.commandId}")
                                handleScreenshotRequest(command.commandId)
                            }
                            "start_live", "start_live_monitoring" -> {
                                Log.i(TAG, "Live streaming requested: ${command.commandId}")
                                withContext(Dispatchers.Main) {
                                    startLiveStreaming()
                                }
                            }
                            "stop_live", "stop_live_monitoring" -> {
                                Log.i(TAG, "Live streaming stop requested: ${command.commandId}")
                                withContext(Dispatchers.Main) {
                                    stopLiveStreaming()
                                }
                            }
                        }
                    }
                }
            }
        } else {
            throw Exception("HTTP ${response.code()}: ${response.errorBody()?.string()}")
        }
    }

    // ── Live Streaming Mode ──────────────────────────────────────────────────

    private fun startLiveStreaming() {
        if (isLiveStreaming) return
        val helper = screenCaptureHelper ?: run {
            Log.w(TAG, "No MediaProjection available — requesting MainActivity to prompt")
            val launchIntent = Intent(this, com.parentalcontrol.app.MainActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                putExtra(com.parentalcontrol.app.MainActivity.EXTRA_AUTO_START, true)
            }
            try { startActivity(launchIntent) } catch (_: Exception) {}
            return
        }
        if (!helper.hasProjection()) {
            Log.w(TAG, "Cannot start live streaming: No MediaProjection — requesting MainActivity to prompt")
            val launchIntent = Intent(this, com.parentalcontrol.app.MainActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                putExtra(com.parentalcontrol.app.MainActivity.EXTRA_AUTO_START, true)
            }
            try { startActivity(launchIntent) } catch (_: Exception) {}
            return
        }

        isLiveStreaming = true
        Log.i(TAG, "Activating live screen streaming mode...")

        broadcastStatus(isMonitoring = true, isLive = true)

        val prefs = getSharedPreferences("parental_control", Context.MODE_PRIVATE)
        val serverUrl = prefs.getString("server_url", null)?.ifEmpty { DEFAULT_SERVER_URL } ?: DEFAULT_SERVER_URL
        connectLiveWebSocket(serverUrl)

        val initialized = helper.startLiveCapture(maxWidth = 420)
        if (!initialized) {
            Log.e(TAG, "Failed to initialize live capture display")
            stopLiveStreaming()
            return
        }

        liveStreamJob = serviceScope.launch {
            var consecutiveLiveErrors = 0
            var lastSentTime = 0L

            while (isActive && isLiveStreaming) {
                val cycleStart = System.currentTimeMillis()
                try {
                    val frameBytes = helper.captureLiveJpeg(quality = 48)
                    val now = System.currentTimeMillis()

                    // Send frame when changed, or keep-alive frame every 1000ms
                    val bytesToSend = frameBytes ?: if (now - lastSentTime >= 1000L) helper.getLastLiveJpeg() else null

                    if (bytesToSend != null && bytesToSend.isNotEmpty()) {
                        val sentWs = sendLiveFrameWs(bytesToSend)
                        if (!sentWs) {
                            uploadLiveFrameRaw(bytesToSend)
                        }
                        lastSentTime = now
                        consecutiveLiveErrors = 0
                    }
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    consecutiveLiveErrors++
                    Log.e(TAG, "Live streaming error ($consecutiveLiveErrors): ${e.message}")
                    if (consecutiveLiveErrors >= 15) {
                        Log.w(TAG, "Too many live streaming errors, stopping")
                        break
                    }
                }

                // Target ~12-14 FPS: 75ms per cycle
                val elapsed = System.currentTimeMillis() - cycleStart
                val delayTime = maxOf(10L, 75L - elapsed)
                delay(delayTime)
            }

            withContext(Dispatchers.Main) {
                stopLiveStreaming()
            }
        }
    }

    private fun stopLiveStreaming() {
        if (!isLiveStreaming && liveStreamJob == null) return
        Log.i(TAG, "Deactivating live streaming mode...")
        isLiveStreaming = false
        liveStreamJob?.cancel()
        liveStreamJob = null

        disconnectLiveWebSocket()

        screenCaptureHelper?.stopLiveCapture()
        broadcastStatus(isMonitoring = true, isLive = false)
    }

    private fun connectLiveWebSocket(serverUrl: String) {
        disconnectLiveWebSocket()
        val cleanUrl = serverUrl.trimEnd('/')
        val wsUrl = cleanUrl
            .replaceFirst("^http://".toRegex(), "ws://")
            .replaceFirst("^https://".toRegex(), "wss://") + "/api/live/push/$deviceId"

        val client = OkHttpClient.Builder()
            .readTimeout(0, TimeUnit.MILLISECONDS)
            .pingInterval(10, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .build()
        liveOkHttpClient = client

        val request = Request.Builder()
            .url(wsUrl)
            .header("ngrok-skip-browser-warning", "true")
            .build()

        liveWebSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.i(TAG, "Live WebSocket opened: $wsUrl")
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.w(TAG, "Live WebSocket error (${t.message}), fallback will stream frames")
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.i(TAG, "Live WebSocket closed ($code): $reason")
            }
        })
    }

    private fun disconnectLiveWebSocket() {
        try {
            liveWebSocket?.close(1000, "Live streaming stopped")
        } catch (_: Exception) {}
        liveWebSocket = null
        liveOkHttpClient = null
    }

    private fun sendLiveFrameWs(bytes: ByteArray): Boolean {
        val ws = liveWebSocket ?: return false
        // Prevent queue accumulation if network stalls
        if (ws.queueSize() > 64 * 1024) {
            Log.d(TAG, "Dropping frame: WS queueSize=${ws.queueSize()}")
            return true // Dropped intentionally to prevent lag buildup
        }
        val byteString = bytes.toByteString(0, bytes.size)
        return ws.send(byteString)
    }

    private fun uploadLiveFrameRaw(jpegBytes: ByteArray): Boolean {
        return try {
            val prefs = getSharedPreferences("parental_control", Context.MODE_PRIVATE)
            val serverUrl = prefs.getString("server_url", null)?.ifEmpty { DEFAULT_SERVER_URL } ?: DEFAULT_SERVER_URL
            val apiKey = prefs.getString("api_key", null)?.ifEmpty { DEFAULT_API_KEY } ?: DEFAULT_API_KEY

            val client = rawHttpClient ?: OkHttpClient.Builder()
                .connectTimeout(2, TimeUnit.SECONDS)
                .writeTimeout(2, TimeUnit.SECONDS)
                .readTimeout(2, TimeUnit.SECONDS)
                .build().also { rawHttpClient = it }

            val requestBody = jpegBytes.toRequestBody("image/jpeg".toMediaTypeOrNull())
            val cleanUrl = serverUrl.trimEnd('/')
            val request = Request.Builder()
                .url("$cleanUrl/api/live/frame_raw/$deviceId")
                .header("X-API-Key", apiKey)
                .header("ngrok-skip-browser-warning", "true")
                .post(requestBody)
                .build()

            client.newCall(request).execute().use { response ->
                response.isSuccessful
            }
        } catch (e: Exception) {
            Log.e(TAG, "uploadLiveFrameRaw error: ${e.message}")
            false
        }
    }

    // ── Manual Screenshot Request ────────────────────────────────────────────

    private suspend fun handleScreenshotRequest(commandId: String) {
        val helper = screenCaptureHelper
        if (helper == null || !helper.hasProjection()) {
            Log.w(TAG, "No MediaProjection available for screenshot — requesting MainActivity to prompt")
            val launchIntent = Intent(this, com.parentalcontrol.app.MainActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                putExtra(com.parentalcontrol.app.MainActivity.EXTRA_AUTO_START, true)
            }
            try { startActivity(launchIntent) } catch (_: Exception) {}
            return
        }

        // If live stream is active, we can take the current live JPEG directly, or full capture
        val imageBytes = withContext(Dispatchers.Main) {
            suspendCancellableCoroutine<ByteArray?> { continuation ->
                helper.captureScreen { bytes ->
                    if (continuation.isActive) {
                        continuation.resume(bytes) {}
                    }
                }
            }
        }

        if (imageBytes != null) {
            uploadScreenshot(commandId, imageBytes)
        } else {
            Log.e(TAG, "Failed to capture screenshot")
        }
    }

    private suspend fun uploadScreenshot(commandId: String, imageBytes: ByteArray) {
        try {
            val prefs = getSharedPreferences("parental_control", Context.MODE_PRIVATE)
            val serverUrl = prefs.getString("server_url", null)?.ifEmpty { DEFAULT_SERVER_URL } ?: DEFAULT_SERVER_URL
            val apiKey = prefs.getString("api_key", null)?.ifEmpty { DEFAULT_API_KEY } ?: DEFAULT_API_KEY

            val api = RetrofitClient.getInstance(serverUrl, apiKey)

            val deviceIdBody = deviceId.toRequestBody("text/plain".toMediaTypeOrNull())
            val commandIdBody = commandId.toRequestBody("text/plain".toMediaTypeOrNull())
            val imageBody = imageBytes.toRequestBody("image/png".toMediaTypeOrNull())
            val imagePart = MultipartBody.Part.createFormData(
                "image",
                "screenshot_${System.currentTimeMillis()}.png",
                imageBody
            )

            val response = api.uploadScreenshot(deviceIdBody, commandIdBody, imagePart)

            if (response.isSuccessful) {
                Log.i(TAG, "Screenshot uploaded: ${response.body()?.screenshotId}")
                val timestamp = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
                broadcastScreenshotTime(timestamp)
            } else {
                Log.e(TAG, "Screenshot upload failed: ${response.code()}")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Screenshot upload error: ${e.message}")
        }
    }

    // ── Broadcast Helpers ────────────────────────────────────────────────────

    private fun broadcastStatus(isMonitoring: Boolean, isLive: Boolean) {
        val intent = Intent(BROADCAST_STATUS).apply {
            putExtra(EXTRA_IS_MONITORING, isMonitoring)
            putExtra(EXTRA_IS_LIVE, isLive)
            setPackage(packageName)
        }
        sendBroadcast(intent)
    }

    private fun broadcastScreenshotTime(timestamp: String) {
        val intent = Intent(BROADCAST_STATUS).apply {
            putExtra(EXTRA_IS_MONITORING, true)
            putExtra(EXTRA_IS_LIVE, isLiveStreaming)
            putExtra(EXTRA_LAST_SCREENSHOT, timestamp)
            setPackage(packageName)
        }
        sendBroadcast(intent)
    }

    private fun broadcastError(message: String) {
        val intent = Intent(BROADCAST_STATUS).apply {
            putExtra(EXTRA_IS_MONITORING, true)
            putExtra(EXTRA_IS_LIVE, isLiveStreaming)
            putExtra(EXTRA_ERROR_MESSAGE, message)
            setPackage(packageName)
        }
        sendBroadcast(intent)
    }

    override fun onDestroy() {
        super.onDestroy()
        stopLiveStreaming()
        heartbeatJob?.cancel()
        screenCaptureHelper?.release()
        isRunning = false
        serviceScope.cancel()
        Log.i(TAG, "MonitoringService destroyed")
    }
}
