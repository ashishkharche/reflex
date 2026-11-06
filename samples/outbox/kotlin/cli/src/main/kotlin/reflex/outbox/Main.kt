package reflex.outbox

import reflex.kit.Session
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
    Session("outbox", { OutboxNode(outbox) }, OutboxOps.make(outbox, clock, network), { OutboxOps.server(network) })
        .serveStandardIO()
}
