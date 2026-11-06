package reflex

import android.os.Handler
import android.os.Looper
import android.util.Log
import java.util.concurrent.FutureTask
import reflex.kit.Session
import reflex.kit.json
import reflex.kit.socket.SocketHost

/** Debug builds only. Starts the Reflex socket host on 127.0.0.1 when the launch intent has
 *  `reflexPort`. Each request runs on the main thread through the real Core, then the screen redraws. */
object DebugSocket {
    private var host: SocketHost? = null

    fun startIfRequested(port: Int, model: InventoryModel) {
        if (host != null || port !in 1..65535) return
        val session = Session("inventory", { AppNode(model.app) }, extras = { mapOf("networkAttempts" to model.network.attempts.json) })
        val main = Handler(Looper.getMainLooper())
        Thread {
            val socket = try {
                SocketHost(session, port) { work ->
                    val task = FutureTask { work().also { model.revision++ } }
                    main.post(task)
                    task.get()
                }
            } catch (error: java.io.IOException) {
                Log.e("Reflex", "socket host failed: $error")
                return@Thread
            }
            host = socket
            Log.i("Reflex", "LISTENING 127.0.0.1:${socket.port}")
            socket.serve()
        }.apply { isDaemon = true; name = "reflex-socket-host" }.start()
    }
}
