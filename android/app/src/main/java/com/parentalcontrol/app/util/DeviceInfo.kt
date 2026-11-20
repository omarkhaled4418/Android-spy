package com.parentalcontrol.app.util

import android.content.Context
import android.os.Build
import android.provider.Settings

object DeviceInfoUtil {

    fun getDeviceId(context: Context): String {
        // Try to get from SharedPreferences first for consistency
        val prefs = context.getSharedPreferences("parental_control", Context.MODE_PRIVATE)
        var deviceId = prefs.getString("device_id", null)
        if (deviceId == null) {
            deviceId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
            prefs.edit().putString("device_id", deviceId).apply()
        }
        return deviceId ?: "unknown"
    }

    fun getDeviceName(): String {
        val manufacturer = Build.MANUFACTURER.replaceFirstChar { it.uppercase() }
        val model = Build.MODEL
        return if (model.startsWith(manufacturer, ignoreCase = true)) {
            model
        } else {
            "$manufacturer $model"
        }
    }

    fun getDeviceModel(): String = Build.MODEL

    fun getAndroidVersion(): String = Build.VERSION.RELEASE

    fun getAppVersion(context: Context): String {
        return try {
            context.packageManager.getPackageInfo(context.packageName, 0).versionName ?: "1.0.0"
        } catch (e: Exception) {
            "1.0.0"
        }
    }
}
