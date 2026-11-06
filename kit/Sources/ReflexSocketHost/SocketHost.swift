#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif
import ReflexKit

/// Debug-only host: serves one `Session` over a loopback TCP socket with protocol v1 framing.
/// Link it from debug builds only. Release builds must not include this product.
/// It binds 127.0.0.1, accepts one client at a time and never listens on another interface.
/// See docs/real-build.md.
public final class SocketHost {
    public struct Failure: Error, CustomStringConvertible {
        public let description: String
    }

    /// Runs one request. The default serialises requests with a lock. An app passes a closure
    /// that runs `work` on its main thread, so actions reach the real Core and the live UI.
    public typealias Perform = (_ work: () -> JSONValue) -> JSONValue

    public let port: UInt16
    private let listener: Int32
    private let session: Session
    private let perform: Perform

    public init(session: Session, port: UInt16 = 0, perform: Perform? = nil) throws {
        self.session = session
        let lock = Lock()
        self.perform = perform ?? { work in lock.locked(work) }
        let fd = socket(AF_INET, SOCK_STREAM, 0)
        guard fd >= 0 else { throw Failure(description: "socket failed errno=\(errno)") }
        var yes: Int32 = 1
        setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &yes, socklen_t(MemoryLayout<Int32>.size))
        var address = sockaddr_in()
        address.sin_family = sa_family_t(AF_INET)
        address.sin_port = port.bigEndian
        address.sin_addr.s_addr = inet_addr("127.0.0.1")
        let bound = withUnsafePointer(to: &address) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { bind(fd, $0, socklen_t(MemoryLayout<sockaddr_in>.size)) }
        }
        guard bound == 0, listen(fd, 1) == 0 else {
            let code = errno
            close(fd)
            throw Failure(description: "bind 127.0.0.1:\(port) failed errno=\(code)")
        }
        var actual = sockaddr_in()
        var length = socklen_t(MemoryLayout<sockaddr_in>.size)
        _ = withUnsafeMutablePointer(to: &actual) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { getsockname(fd, $0, &length) }
        }
        listener = fd
        self.port = UInt16(bigEndian: actual.sin_port)
    }

    /// Accepts clients one after another until the process ends. Blocks the calling thread.
    public func serve() {
        while true {
            let client = accept(listener, nil, nil)
            if client < 0 {
                if errno == EINTR { continue }
                return
            }
            #if canImport(Darwin)
            var yes: Int32 = 1
            setsockopt(client, SOL_SOCKET, SO_NOSIGPIPE, &yes, socklen_t(MemoryLayout<Int32>.size))
            #endif
            handle(client)
            close(client)
        }
    }

    /// Serves on a background thread and returns at once.
    public func start() {
        #if canImport(Darwin)
        var thread = pthread_t?.none
        #else
        var thread = pthread_t()
        #endif
        let box = Unmanaged.passRetained(self)
        pthread_create(&thread, nil, { raw in
            #if canImport(Darwin)
            let host = Unmanaged<SocketHost>.fromOpaque(raw).takeRetainedValue()
            #else
            let host = Unmanaged<SocketHost>.fromOpaque(raw!).takeRetainedValue()
            #endif
            host.serve()
            return nil
        }, box.toOpaque())
    }

    private func handle(_ client: Int32) {
        var framer = LineFramer()
        var buffer = [UInt8](repeating: 0, count: 65_536)
        func answer(_ line: [UInt8]) -> Bool {
            let reply = Array((perform { session.handle(bytes: line) }.wire + "\n").utf8)
            var sent = 0
            while sent < reply.count {
                #if canImport(Darwin)
                let flags: Int32 = 0
                #else
                let flags = Int32(MSG_NOSIGNAL)
                #endif
                let count = reply[sent...].withUnsafeBytes { send(client, $0.baseAddress, $0.count, flags) }
                if count < 0 && errno == EINTR { continue }
                if count <= 0 { return false }
                sent += count
            }
            return true
        }
        while true {
            let count = read(client, &buffer, buffer.count)
            if count < 0 && errno == EINTR { continue }
            if count <= 0 { break }
            for line in framer.push(buffer[0..<count]) where !answer(line) { return }
        }
        if let last = framer.finish() { _ = answer(last) }
    }
}

private final class Lock {
    private var mutex = pthread_mutex_t()
    init() { pthread_mutex_init(&mutex, nil) }
    func locked<T>(_ work: () -> T) -> T {
        pthread_mutex_lock(&mutex)
        defer { pthread_mutex_unlock(&mutex) }
        return work()
    }
}
