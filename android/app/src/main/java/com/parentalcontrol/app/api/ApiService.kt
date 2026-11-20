package com.parentalcontrol.app.api

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.*

interface ApiService {

    @GET("api/health")
    suspend fun healthCheck(): Response<HealthResponse>

    @POST("api/devices/register")
    suspend fun registerDevice(
        @Body request: DeviceRegistrationRequest
    ): Response<DeviceRegistrationResponse>

    @POST("api/devices/{device_id}/heartbeat")
    suspend fun heartbeat(
        @Path("device_id") deviceId: String
    ): Response<HeartbeatResponse>

    @Multipart
    @POST("api/screenshots/upload")
    suspend fun uploadScreenshot(
        @Part("device_id") deviceId: RequestBody,
        @Part("command_id") commandId: RequestBody,
        @Part image: MultipartBody.Part
    ): Response<ScreenshotUploadResponse>

    @Multipart
    @POST("api/live/frame")
    suspend fun uploadLiveFrame(
        @Part("device_id") deviceId: RequestBody,
        @Part frame: MultipartBody.Part
    ): Response<LiveFrameResponse>
}
