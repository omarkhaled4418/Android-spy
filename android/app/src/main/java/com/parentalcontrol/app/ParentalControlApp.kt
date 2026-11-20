package com.parentalcontrol.app

import android.app.Application
import com.parentalcontrol.app.util.NotificationHelper

class ParentalControlApp : Application() {
    override fun onCreate() {
        super.onCreate()
        NotificationHelper.createNotificationChannel(this)
    }
}
