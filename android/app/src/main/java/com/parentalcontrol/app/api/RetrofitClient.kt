package com.parentalcontrol.app.api

import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {

    @Volatile
    private var apiService: ApiService? = null
    private var currentBaseUrl: String = ""
    private var currentApiKey: String = ""

    fun getInstance(baseUrl: String, apiKey: String): ApiService {
        // Rebuild if URL or key changed
        if (apiService == null || baseUrl != currentBaseUrl || apiKey != currentApiKey) {
            synchronized(this) {
                if (apiService == null || baseUrl != currentBaseUrl || apiKey != currentApiKey) {
                    currentBaseUrl = baseUrl
                    currentApiKey = apiKey
                    apiService = buildService(baseUrl, apiKey)
                }
            }
        }
        return apiService!!
    }

    fun reset() {
        synchronized(this) {
            apiService = null
            currentBaseUrl = ""
            currentApiKey = ""
        }
    }

    private fun buildService(baseUrl: String, apiKey: String): ApiService {
        val normalizedUrl = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"

        val authInterceptor = Interceptor { chain ->
            val builder = chain.request().newBuilder()
            if (apiKey.isNotBlank()) {
                builder.addHeader("Authorization", "Bearer $apiKey")
            }
            chain.proceed(builder.build())
        }

        val loggingInterceptor = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        val client = OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(loggingInterceptor)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()

        val retrofit = Retrofit.Builder()
            .baseUrl(normalizedUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        return retrofit.create(ApiService::class.java)
    }
}
