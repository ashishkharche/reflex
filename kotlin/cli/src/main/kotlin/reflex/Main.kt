package reflex

import reflex.kit.Session
import reflex.kit.json
import kotlin.system.exitProcess

fun main(args: Array<String>) {
    val fixture = args.firstOrNull() ?: "happy"
    if (fixture !in listOf("happy", "save-failure", "network", "network-caught", "http-caught")) {
        System.err.println("Unknown fixture"); exitProcess(64)
    }
    val network = NetworkGuard()
    val app = InventoryApp(FixtureInventoryService(fixture, network))
    val session = Session("inventory", { AppNode(app) }, extras = { mapOf("networkAttempts" to network.attempts.json) })
    // Any service guard attempt is sticky: answer, then exit 70.
    session.serveStandardIO { if (network.attempts > 0) 70 else null }
}
