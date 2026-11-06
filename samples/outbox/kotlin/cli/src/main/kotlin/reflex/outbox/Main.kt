package reflex.outbox

import reflex.kit.Field
import reflex.kit.FieldType
import reflex.kit.LineFramer
import reflex.kit.Schema
import reflex.kit.Session
import reflex.kit.socket.SocketHost
import java.io.FileDescriptor
import java.io.FileOutputStream
import java.io.PrintStream
import java.net.InetSocketAddress
import java.net.Socket
import kotlin.system.exitProcess

/** `http` fixture: every delivery first tries a real loopback TCP connect, then uses the fake.
 *  Under the runner’s DYLD guard that connect is denied and the journey must report it. */
class LoopbackTripwire(private val inner: FlakyNetwork) : Transport {
    override fun deliver(key: String, body: String): DeliveryResult {
        runCatching { Socket().use { it.connect(InetSocketAddress("127.0.0.1", 9), 500) } }
        return inner.deliver(key, body)
    }
}

fun main(args: Array<String>) {
    val fixture = args.firstOrNull() ?: "fake"
    if (fixture !in listOf("fake", "http")) { System.err.println("Unknown fixture"); exitProcess(64) }
    val clock = FakeClock(1_800_000_000_000L)
    val network = FlakyNetwork()
    val transport: Transport = if (fixture == "http") LoopbackTripwire(network) else network
    val outbox = OutboxViewModel(clock, transport)
    // One lock serialises every request and every background change, so a reply is never a torn state.
    val lock = Any()
    // `advanceLater`: replies at once, then a background thread advances the fake clock after a real
    // delay. Journeys use it to exercise `eventually`, which polls `ls` until the change lands.
    val advanceLater = Session.Op(Schema(Field.required("ms", FieldType.int64(min = 0, max = OutboxOps.MAX_ADVANCE_MS)),
        Field.required("afterMs", FieldType.int64(min = 0, max = 5_000)))) { args ->
        val ms = args.int64("ms")
        val afterMs = args.int64("afterMs")
        Thread {
            Thread.sleep(afterMs)
            synchronized(lock) { clock.advance(ms, outbox) }
        }.apply { isDaemon = true }.start()
    }
    val ops = OutboxOps.make(outbox, clock, network) + ("advanceLater" to advanceLater)
    val session = Session("outbox", { OutboxNode(outbox) }, ops, { OutboxOps.server(network) })

    // `--listen PORT` serves the same session over a loopback socket instead of stdin (debug host demo).
    val flag = args.indexOf("--listen")
    if (flag >= 0) {
        val port = args.getOrNull(flag + 1)?.toIntOrNull()
        if (port == null || port !in 0..65535) { System.err.println("--listen needs a port"); exitProcess(64) }
        val host = try { SocketHost(session, port) { work -> synchronized(lock) { work() } } }
            catch (e: java.io.IOException) { System.err.println(e.toString()); exitProcess(69) }
        System.err.println("LISTENING 127.0.0.1:${host.port}")
        host.serve()
        return
    }

    // Same loop as Session.serveStandardIO, with each request handled under the lock.
    val out = PrintStream(FileOutputStream(FileDescriptor.out), false, Charsets.UTF_8)
    val framer = LineFramer()
    val buffer = ByteArray(65_536)
    fun answer(line: ByteArray) {
        val reply = synchronized(lock) { session.handle(line).wire }
        out.print(reply + "\n")
        out.flush()
    }
    while (true) {
        val count = System.`in`.read(buffer)
        if (count < 0) break
        for (line in framer.push(buffer, count)) answer(line)
    }
    framer.finish()?.let { answer(it) }
    out.flush()
}
