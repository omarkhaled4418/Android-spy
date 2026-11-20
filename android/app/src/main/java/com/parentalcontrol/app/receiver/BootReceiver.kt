package com.parentalcontrol.app.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import com.parentalcontrol.app.MainActivity
import com.parentalcontrol.app.service.MonitoringService
import com.parentalcontrol.app.util.NotificationHelper

class BootReceiver : BroadcastReceiver() {

    companion object {
        private const val TAG = "BootReceiver"
        private const val PREFS_NAME = "parental_control"
    }

    override fun onReceive(context: Context, intent: Intent?) {
        val action = intent?.action
        if (action == Intent.ACTION_BOOT_COMPLETED ||
            action == "android.intent.action.QUICKBOOT_POWERON" ||
            action == "com.htc.intent.action.QUICKBOOT_POWERON"
        ) {
            Log.i(TAG, "Device boot received ($action) — starting parental control auto-start sequence")

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                NotificationHelper.createNotificationChannel(context)
            }

            // 1. Immediately start MonitoringService in standby mode (connects & sends heartbeats)
            try {
                MonitoringService.startStandby(context)
                Log.i(TAG, "MonitoringService standby started on boot")
            } catch (e: Exception) {
                Log.e(TAG, "Could not start MonitoringService standby on boot: ${e.message}")
            }

            // 2. Launch MainActivity to acquire/prompt for MediaProjection permission
            try {
                val launchIntent = Intent(context, MainActivity::class.java).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                    putExtra(MainActivity.EXTRA_AUTO_START, true)
                }
                context.startActivity(launchIntent)
                Log.i(TAG, "MainActivity launched on boot for full monitoring auto-start")
            } catch (e: Exception) {
                Log.w(TAG, "Background activity launch restricted on this device: ${e.message}")
            }
        }
    }
}
