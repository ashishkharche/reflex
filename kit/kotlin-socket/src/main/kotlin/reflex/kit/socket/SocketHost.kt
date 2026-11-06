package reflex.kit.socket

import reflex.kit.JsonValue
import reflex.kit.LineFramer
import reflex.kit.Session
import java.io.Closeable
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketException

/** Debug-only host: serves one [Session] over a loopback TCP socket with protocol v1 framing.
 *  Add it to debug builds only. Release builds must not include this module.
 *  It binds 127.0.0.1, accepts one client at a time and never listens on another interface.
 *  [perform] runs one request. The default serialises requests with a lock. An Android app passes
 *  a function that runs the work on the main thread, so actions reach the real Core and the live UI.
 *  See docs/real-build.md. */
class SocketHost(
    private val session: Session,
    port: Int = 0,
    private val perform: (() -> JsonValue) -> JsonValue = serial(),
) : Closeable {
    private val server = ServerSocket(port, 1, InetAddress.getLoopbackAddress())
    val port: Int get() = server.localPort

    /** Accepts clients one after another until [close]. Blocks the calling thread. */
    fun serve() {
        while (!server.isClosed) {
            val client = try { server.accept() } catch (e: SocketException) { return }
            client.use { handle(it) }
        }
    }

    /** Serves on a daemon thread and returns at once. */
    fun start(): Thread = Thread(::serve, "reflex-socket-host").apply { isDaemon = true; start() }

    override fun close() = server.close()

    private fun handle(client: Socket) {
        val input = client.getInputStream()
        val output = client.getOutputStream()
        val framer = LineFramer()
        val buffer = ByteArray(65_536)
        fun answer(line: ByteArray) {
            output.write((perform { session.handle(line) }.wire + "\n").toByteArray(Charsets.UTF_8))
            output.flush()
        }
        try {
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                for (line in framer.push(buffer, count)) answer(line)
            }
            framer.finish()?.let { answer(it) }
        } catch (e: SocketException) {
            // The client went away. Wait for the next one.
        }
    }

    companion object {
        fun serial(): (() -> JsonValue) -> JsonValue {
            val lock = Any()
            return { work -> synchronized(lock) { work() } }
        }
    }
}
