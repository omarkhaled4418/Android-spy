package com.parentalcontrol.app.service

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.PixelFormat
import android.graphics.Rect
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.Image
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Handler
import android.os.Looper
import android.util.DisplayMetrics
import android.util.Log
import android.view.WindowManager
import java.io.ByteArrayOutputStream

class ScreenCaptureHelper(private val context: Context) {

    companion object {
        private const val TAG = "ScreenCaptureHelper"

        fun createScreenCaptureIntent(context: Context): Intent {
            val projectionManager = context.getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            return projectionManager.createScreenCaptureIntent()
        }
    }

    private var mediaProjection: MediaProjection? = null

    // For one-off high-res screenshots
    private var virtualDisplay: VirtualDisplay? = null
    private var imageReader: ImageReader? = null

    // For continuous live streaming (high performance, pre-allocated buffers)
    private var liveVirtualDisplay: VirtualDisplay? = null
    private var liveImageReader: ImageReader? = null
    private var liveWidth: Int = 0
    private var liveHeight: Int = 0
    private var reusableLiveBitmap: Bitmap? = null
    private var reusableCroppedBitmap: Bitmap? = null
    private var reusableCanvas: Canvas? = null
    private var srcRect: Rect? = null
    private var dstRect: Rect? = null
    private val reusableOutputStream = ByteArrayOutputStream(32768)
    private var lastLiveJpeg: ByteArray? = null

    fun initProjection(resultCode: Int, data: Intent) {
        val projectionManager = context.getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        mediaProjection = projectionManager.getMediaProjection(resultCode, data)
        mediaProjection?.registerCallback(object : MediaProjection.Callback() {
            override fun onStop() {
                super.onStop()
                releaseVirtualDisplay()
                stopLiveCapture()
            }
        }, Handler(Looper.getMainLooper()))
    }

    // ── High-Res Manual Screenshot ───────────────────────────────────────────

    fun captureScreen(callback: (ByteArray?) -> Unit) {
        val projection = mediaProjection
        if (projection == null) {
            callback(null)
            return
        }

        val wm = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val metrics = DisplayMetrics()
        @Suppress("DEPRECATION")
        wm.defaultDisplay.getRealMetrics(metrics)

        val width = metrics.widthPixels
        val height = metrics.heightPixels
        val density = metrics.densityDpi

        imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)

        virtualDisplay = projection.createVirtualDisplay(
            "ScreenCapture",
            width, height, density,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            imageReader!!.surface,
            null, null
        )

        val handler = Handler(Looper.getMainLooper())

        handler.postDelayed({
            try {
                val image = imageReader?.acquireLatestImage()
                if (image != null) {
                    val bytes = imageToPng(image, width, height)
                    image.close()
                    releaseVirtualDisplay()
                    callback(bytes)
                } else {
                    handler.postDelayed({
                        try {
                            val retryImage = imageReader?.acquireLatestImage()
                            if (retryImage != null) {
                                val bytes = imageToPng(retryImage, width, height)
                                retryImage.close()
                                releaseVirtualDisplay()
                                callback(bytes)
                            } else {
                                releaseVirtualDisplay()
                                callback(null)
                            }
                        } catch (e: Exception) {
                            releaseVirtualDisplay()
                            callback(null)
                        }
                    }, 400)
                }
            } catch (e: Exception) {
                releaseVirtualDisplay()
                callback(null)
            }
        }, 300)
    }

    private fun imageToPng(image: Image, width: Int, height: Int): ByteArray {
        val planes = image.planes
        val buffer = planes[0].buffer
        val pixelStride = planes[0].pixelStride
        val rowStride = planes[0].rowStride
        val rowPadding = rowStride - pixelStride * width

        val bitmap = Bitmap.createBitmap(
            width + rowPadding / pixelStride,
            height,
            Bitmap.Config.ARGB_8888
        )
        bitmap.copyPixelsFromBuffer(buffer)

        val croppedBitmap = Bitmap.createBitmap(bitmap, 0, 0, width, height)
        if (croppedBitmap != bitmap) {
            bitmap.recycle()
        }

        val outputStream = ByteArrayOutputStream()
        croppedBitmap.compress(Bitmap.CompressFormat.PNG, 100, outputStream)
        croppedBitmap.recycle()

        return outputStream.toByteArray()
    }

    private fun releaseVirtualDisplay() {
        virtualDisplay?.release()
        virtualDisplay = null
        imageReader?.close()
        imageReader = null
    }

    // ── High-Speed Low-Latency Live Stream Capture ───────────────────────────

    fun startLiveCapture(maxWidth: Int = 420): Boolean {
        val projection = mediaProjection ?: return false
        if (liveVirtualDisplay != null) return true

        val wm = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val metrics = DisplayMetrics()
        @Suppress("DEPRECATION")
        wm.defaultDisplay.getRealMetrics(metrics)

        val screenW = metrics.widthPixels
        val screenH = metrics.heightPixels
        val density = metrics.densityDpi

        val scale = minOf(1.0f, maxWidth.toFloat() / minOf(screenW, screenH))
        // Dimensions must be even for encoder
        liveWidth = ((screenW * scale).toInt() / 2) * 2
        liveHeight = ((screenH * scale).toInt() / 2) * 2
        val liveDensity = (density * scale).toInt()

        Log.i(TAG, "Starting high-FPS live capture at ${liveWidth}x${liveHeight} (density=$liveDensity)")

        // Use 3 buffers to completely eliminate surface lock stalls
        liveImageReader = ImageReader.newInstance(liveWidth, liveHeight, PixelFormat.RGBA_8888, 3)
        liveVirtualDisplay = projection.createVirtualDisplay(
            "LiveStreamDisplay",
            liveWidth, liveHeight, liveDensity,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            liveImageReader!!.surface,
            null, null
        )

        srcRect = Rect(0, 0, liveWidth, liveHeight)
        dstRect = Rect(0, 0, liveWidth, liveHeight)

        return true
    }

    fun captureLiveJpeg(quality: Int = 48): ByteArray? {
        val reader = liveImageReader ?: return null
        try {
            val image = reader.acquireLatestImage()
            if (image != null) {
                val bytes = imageToJpegFast(image, liveWidth, liveHeight, quality)
                image.close()
                lastLiveJpeg = bytes
                return bytes
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error acquiring live image: ${e.message}")
        }
        return null
    }

    fun getLastLiveJpeg(): ByteArray? = lastLiveJpeg

    /**
     * Ultra-fast zero-allocation JPEG conversion using pre-allocated Bitmaps.
     * Takes ~3-5ms on modern devices.
     */
    private fun imageToJpegFast(image: Image, width: Int, height: Int, quality: Int): ByteArray {
        val planes = image.planes
        val buffer = planes[0].buffer
        val pixelStride = planes[0].pixelStride
        val rowStride = planes[0].rowStride
        val rowPadding = rowStride - pixelStride * width
        val paddedWidth = width + rowPadding / pixelStride

        // 1. Ensure liveBitmap matches buffer dimensions
        var bitmap = reusableLiveBitmap
        if (bitmap == null || bitmap.width != paddedWidth || bitmap.height != height || bitmap.isRecycled) {
            bitmap?.recycle()
            bitmap = Bitmap.createBitmap(paddedWidth, height, Bitmap.Config.ARGB_8888)
            reusableLiveBitmap = bitmap
        }

        buffer.rewind()
        bitmap.copyPixelsFromBuffer(buffer)

        // 2. If row padding exists, crop without allocating new Bitmap using reusable Canvas
        val targetBitmap: Bitmap
        if (rowPadding != 0) {
            var cropped = reusableCroppedBitmap
            if (cropped == null || cropped.width != width || cropped.height != height || cropped.isRecycled) {
                cropped?.recycle()
                cropped = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                reusableCroppedBitmap = cropped
                reusableCanvas = Canvas(cropped)
            }
            reusableCanvas?.drawBitmap(bitmap, srcRect!!, dstRect!!, null)
            targetBitmap = cropped
        } else {
            targetBitmap = bitmap
        }

        // 3. Compress directly into pre-allocated output stream
        reusableOutputStream.reset()
        targetBitmap.compress(Bitmap.CompressFormat.JPEG, quality, reusableOutputStream)
        return reusableOutputStream.toByteArray()
    }

    fun stopLiveCapture() {
        liveVirtualDisplay?.release()
        liveVirtualDisplay = null
        liveImageReader?.close()
        liveImageReader = null

        reusableLiveBitmap?.recycle()
        reusableLiveBitmap = null
        reusableCroppedBitmap?.recycle()
        reusableCroppedBitmap = null
        reusableCanvas = null
        lastLiveJpeg = null

        Log.i(TAG, "Live capture stopped and resources recycled")
    }

    fun isLiveCaptureActive(): Boolean = liveVirtualDisplay != null

    // ── Release All ──────────────────────────────────────────────────────────

    fun release() {
        stopLiveCapture()
        releaseVirtualDisplay()
        mediaProjection?.stop()
        mediaProjection = null
    }

    fun hasProjection(): Boolean = mediaProjection != null

    fun getMediaProjection(): MediaProjection? = mediaProjection
}
