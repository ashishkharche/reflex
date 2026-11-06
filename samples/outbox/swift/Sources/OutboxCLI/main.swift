import Foundation
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

// One lock serialises every request and every background change, so a reply is never a torn state.
let lock = NSLock()

/// `advanceLater`: replies at once, then a background thread advances the fake clock after a real
/// delay. Journeys use it to exercise `eventually`, which polls `ls` until the change lands.
var ops = OutboxOps.make(vm: outbox, clock: clock, network: network)
ops["advanceLater"] = Session.Op(input: Schema([.required("ms", .int64(min: 0, max: OutboxOps.maxAdvanceMs)),
                                                .required("afterMs", .int64(min: 0, max: 5_000))])) { args in
    let ms = args.int64("ms"), afterMs = args.int64("afterMs")
    Thread.detachNewThread {
        Thread.sleep(forTimeInterval: Double(afterMs) / 1000)
        lock.lock()
        clock.advance(by: ms, waking: outbox)
        lock.unlock()
    }
}
let session = Session(sample: "outbox", root: { OutboxNode(vm: outbox) }, ops: ops, extras: { OutboxOps.server(network) })

// Same loop as Session.serveStandardIO, with each request handled under the lock.
var framer = LineFramer()
var buffer = [UInt8](repeating: 0, count: 65_536)
func answer(_ line: [UInt8]) {
    lock.lock()
    let reply = session.handle(bytes: line).wire + "\n"
    lock.unlock()
    fputs(reply, stdout)
    fflush(stdout)
}
while true {
    let count = read(0, &buffer, buffer.count)
    if count < 0 && errno == EINTR { continue }
    if count <= 0 { break }
    for line in framer.push(buffer[0..<count]) { answer(line) }
}
if let last = framer.finish() { answer(last) }
