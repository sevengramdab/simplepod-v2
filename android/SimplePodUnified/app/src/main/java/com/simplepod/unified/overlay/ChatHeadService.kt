package com.simplepod.unified.overlay

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.graphics.PixelFormat
import android.os.Build
import android.os.IBinder
import android.view.*
import android.widget.ImageButton
import android.widget.LinearLayout
import androidx.core.app.NotificationCompat
import com.simplepod.unified.MainActivity
import com.simplepod.unified.R

/**
 * ELI5: This is like a 3-way smart switch that follows you around the room.
 *      Tap the floating circle to open/close the panel, no matter what app you're in.
 */
class ChatHeadService : Service() {

    private lateinit var windowManager: WindowManager
    private lateinit var chatHeadView: View
    private lateinit var params: WindowManager.LayoutParams
    private var isMenuOpen = false
    private var initialX = 0
    private var initialY = 0
    private var initialTouchX = 0f
    private var initialTouchY = 0f

    companion object {
        const val CHANNEL_ID = "simplepod_chathead"
        const val NOTIFICATION_ID = 1
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        startForeground()
        createChatHead()
    }

    private fun startForeground() {
        // ELI5: We have to post a notice on the bulletin board (notification)
        //       so the building inspector knows this service is running.
        val channel = NotificationChannel(
            CHANNEL_ID,
            "SimplePod ChatHead",
            NotificationManager.IMPORTANCE_LOW
        )
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(channel)

        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("SimplePod Unified")
            .setContentText("ChatHead overlay active")
            .setSmallIcon(android.R.drawable.ic_menu_compass)
            .setContentIntent(pendingIntent)
            .build()

        startForeground(NOTIFICATION_ID, notification)
    }

    private fun createChatHead() {
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager

        // ELI5: We're hanging a junction box (overlay) on the outside of the wall.
        //       It floats above everything, like a smart switch panel that follows you.
        chatHeadView = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL

            val icon = ImageButton(context).apply {
                setImageResource(android.R.drawable.ic_menu_compass)
                setBackgroundResource(android.R.drawable.btn_default)
                layoutParams = LinearLayout.LayoutParams(120, 120)
                setOnClickListener { toggleMenu() }
            }

            val menu = LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                visibility = LinearLayout.GONE
                setBackgroundColor(0xCC1E1E2E.toInt())
                setPadding(24, 24, 24, 24)

                addView(menuButton("Analyze", android.R.drawable.ic_menu_search) {
                    launchMain("analysis")
                })
                addView(menuButton("Reply", android.R.drawable.ic_menu_send) {
                    launchMain("reply")
                })
                addView(menuButton("Swarm", android.R.drawable.ic_menu_agenda) {
                    launchMain("swarm")
                })
                addView(menuButton("Close", android.R.drawable.ic_menu_close_clear_cancel) {
                    stopSelf()
                })
            }

            addView(icon)
            addView(menu)

            setOnTouchListener { _, event ->
                when (event.action) {
                    MotionEvent.ACTION_DOWN -> {
                        initialX = params.x
                        initialY = params.y
                        initialTouchX = event.rawX
                        initialTouchY = event.rawY
                        true
                    }
                    MotionEvent.ACTION_MOVE -> {
                        params.x = initialX + (event.rawX - initialTouchX).toInt()
                        params.y = initialY + (event.rawY - initialTouchY).toInt()
                        windowManager.updateViewLayout(this, params)
                        true
                    }
                    else -> false
                }
            }
        }

        params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            else
                WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = 100
            y = 100
        }

        windowManager.addView(chatHeadView, params)
    }

    private fun menuButton(label: String, icon: Int, onClick: () -> Unit): ImageButton {
        return ImageButton(this).apply {
            setImageResource(icon)
            contentDescription = label
            setOnClickListener { onClick() }
            layoutParams = LinearLayout.LayoutParams(100, 100).apply {
                setMargins(0, 8, 0, 8)
            }
        }
    }

    private fun toggleMenu() {
        isMenuOpen = !isMenuOpen
        val menu = (chatHeadView as LinearLayout).getChildAt(1) as LinearLayout
        menu.visibility = if (isMenuOpen) LinearLayout.VISIBLE else LinearLayout.GONE
    }

    private fun launchMain(route: String) {
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
            putExtra("route", route)
        }
        startActivity(intent)
    }

    override fun onDestroy() {
        super.onDestroy()
        if (::chatHeadView.isInitialized) {
            windowManager.removeView(chatHeadView)
        }
    }
}
