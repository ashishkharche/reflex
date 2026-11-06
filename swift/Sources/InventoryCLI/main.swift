import InventoryCore
import InventoryIntrospection
import ReflexKit
#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif

let arguments = CommandLine.arguments
let fixture = arguments.count > 1 ? arguments[1] : "happy"
guard ["happy", "save-failure", "network", "network-caught", "http-caught"].contains(fixture) else {
    fputs("Unknown fixture\n", stderr); exit(64)
}
let network = NetworkGuard()
let app = InventoryApp(service: FixtureInventoryService(fixture: fixture, guardrail: network))
let session = Session(sample: "inventory", root: { AppNode(app: app) },
                      extras: { ["networkAttempts": JSONValue(network.attempts)] })
// Any service guard attempt is sticky: answer, then exit 70.
session.serveStandardIO { network.attempts > 0 ? 70 : nil }
