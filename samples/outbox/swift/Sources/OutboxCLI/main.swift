import OutboxCore
import OutboxIntrospection
import ReflexKit
#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif

/// `http` fixture: every delivery first tries a real loopback TCP connect, then uses the fake.
/// Under the runner’s DYLD guard that connect is denied and the journey must report it.
final class LoopbackTripwire: Transport {
    let inner: FlakyNetwork
    init(_ inner: FlakyNetwork) { self.inner = inner }
    func deliver(key: String, body: String) -> DeliveryResult {
        let fd = socket(AF_INET, SOCK_STREAM, 0)
        if fd >= 0 {
            var address = sockaddr_in()
            address.sin_family = sa_family_t(AF_INET)
            address.sin_port = in_port_t(9).bigEndian
            address.sin_addr.s_addr = inet_addr("127.0.0.1")
            _ = withUnsafePointer(to: &address) {
                $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { connect(fd, $0, socklen_t(MemoryLayout<sockaddr_in>.size)) }
            }
            close(fd)
        }
        return inner.deliver(key: key, body: body)
    }
}

let fixture = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "fake"
guard ["fake", "http"].contains(fixture) else { fputs("Unknown fixture\n", stderr); exit(64) }
let clock = FakeClock(now: 1_800_000_000_000)
let network = FlakyNetwork()
let transport: Transport = fixture == "http" ? LoopbackTripwire(network) : network
let outbox = OutboxViewModel(clock: clock, transport: transport)
let session = Session(sample: "outbox", root: { OutboxNode(vm: outbox) },
                      ops: OutboxOps.make(vm: outbox, clock: clock, network: network),
                      extras: { OutboxOps.server(network) })
session.serveStandardIO()
