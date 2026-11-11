#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif
import Dispatch
#if canImport(Darwin)
import CoreFoundation
#endif

/// Reflex NDJSON protocol v1 for one host process. See docs/protocol/v1.md.
public final class Session {
    public static let protocolVersion: Int64 = 1
    public static let supportedVersions: [Int64] = [1]
    public static let kitVersion = "1.0.1"

    /// A host-specific operation, such as advancing a fake clock. Its input is decoded strictly.
    public struct Op {
        public let input: Schema?
        public let run: (Args) throws -> Void
        public init(input: Schema? = nil, _ run: @escaping (Args) throws -> Void) {
            self.input = input
            self.run = run
        }
    }

    public let sample: String
    public private(set) var negotiated: Int64?
    private let root: () -> any Node
    private let ops: [String: Op]
    private let extras: () -> [String: JSONValue]

    /// - Parameters:
    ///   - sample: name reported by `hello`.
    ///   - root: builds the root node for each response, so focus follows navigation.
    ///   - ops: extra operations next to `hello`, `ls` and `do`.
    ///   - extras: fields merged into every response, such as a network attempt counter.
    public init(sample: String, root: @escaping () -> any Node, ops: [String: Op] = [:],
                extras: @escaping () -> [String: JSONValue] = { [:] }) {
        precondition(Set(ops.keys).isDisjoint(with: ["hello", "ls", "do"]), "ReflexKit: reserved op name")
        self.sample = sample
        self.root = root
        self.ops = ops
        self.extras = extras
    }

    /// Handles one request line given as text.
    public func handle(_ line: String) -> JSONValue {
        respond { try dispatch(WireJSON.parseTree(line)) }
    }

    /// Handles one request line given as raw bytes without its LF. Bytes that are not strict
    /// UTF-8 are `json.malformed` at `$` and are never decoded or echoed.
    public func handle(bytes line: [UInt8]) -> JSONValue {
        respond {
            guard let text = StrictUTF8.decode(line) else { throw WireError(WireCode.malformed, "$") }
            return try dispatch(WireJSON.parseTree(text))
        }
    }

    private func respond(_ body: () throws -> [String: JSONValue]) -> JSONValue {
        snapshot(outcome(body))
    }

    private func outcome(_ body: () throws -> [String: JSONValue]) -> [String: JSONValue] {
        var response: [String: JSONValue]
        do {
            response = try body()
            response["ok"] = true
        } catch let error as WireError {
            response = ["ok": false, "error": error.json]
            if error.code == WireCode.unsupportedProtocol {
                response["supported"] = .array(Session.supportedVersions.map { .int($0) })
            }
        } catch {
            preconditionFailure("ReflexKit: actions and ops may only throw WireError, got \(error)")
        }
        return response
    }

    private func snapshot(_ outcome: [String: JSONValue]) -> JSONValue {
        var response = outcome
        response["node"] = Focus(root: root()).snapshot
        for (key, value) in extras() { response[key] = value }
        return .object(response)
    }

    /// Request keys, op names and action titles compare by exact UTF-16 code units.
    private func dispatch(_ tree: WireNode) throws -> [String: JSONValue] {
        guard case .object(let request) = tree else {
            throw WireError(WireCode.requestNotObject, "$")
        }
        guard let opValue = request["op"] else { throw WireError(WireCode.missing, "$.op") }
        guard case .scalar(.string(let op)) = opValue else { throw WireError(WireCode.type, "$.op") }
        let custom = ops.first { exactlyEqual($0.key, op) }?.value
        let builtIn = ["hello", "ls", "do"].first { exactlyEqual($0, op) }
        guard builtIn != nil || custom != nil else { throw WireError(WireCode.unknownOp, "$.op") }
        if builtIn != "hello" && negotiated == nil { throw WireError(WireCode.handshakeRequired, "$.op") }
        switch builtIn {
        case "hello":
            try only(request, ["op", "protocol"])
            guard let raw = request["protocol"] else { throw WireError(WireCode.missing, "$.protocol") }
            let version = try FieldType.int64.decode(raw, at: "$.protocol")
            guard case .int(let number) = version, Session.supportedVersions.contains(number) else {
                throw WireError(WireCode.unsupportedProtocol, "$.protocol")
            }
            negotiated = number
            return ["protocol": .int(number), "sample": .string(sample), "kit": .string(Session.kitVersion)]
        case "ls":
            try only(request, ["op"])
        case "do":
            try only(request, ["op", "action", "input"])
            guard let actionValue = request["action"] else { throw WireError(WireCode.missing, "$.action") }
            guard case .scalar(.string(let title)) = actionValue else { throw WireError(WireCode.type, "$.action") }
            guard let action = Focus(root: root()).actions.first(where: { exactlyEqual($0.key, title) })?.value else {
                throw WireError(WireCode.unknownAction, "$.action")
            }
            try action.run(try Session.decodeInput(request["input"], action.input))
        default:
            try only(request, ["op", "input"])
            try custom!.run(try Session.decodeInput(request["input"], custom!.input))
        }
        return [:]
    }

    private func only(_ request: WireObject, _ allowed: Set<String>) throws {
        let exact = Set(allowed.map(ExactKey.init))
        for key in request.sortedKeys where !exact.contains(ExactKey(key)) {
            throw WireError(WireCode.unknown, "$." + key)
        }
    }

    /// Input must be absent or an object. Absent input decodes as `{}`.
    public static func decodeInput(_ value: JSONValue?, _ schema: Schema?) throws -> Args {
        try decodeInput(value.map(WireNode.init), schema)
    }

    static func decodeInput(_ value: WireNode?, _ schema: Schema?) throws -> Args {
        let input = value ?? .object(WireObject())
        guard case .object = input else { throw WireError(WireCode.inputNotObject, "$.input") }
        return try (schema ?? .empty).decode(input, at: "$.input")
    }

    /// Like `handle(bytes:)`, but awaits `settle` after the request runs and before the reply reads state.
    /// Call it on the main actor, so work an action starts there can finish first.
    @MainActor
    public func handle(bytes line: [UInt8], settle: @MainActor () async -> Void) async -> JSONValue {
        let result = outcome {
            guard let text = StrictUTF8.decode(line) else { throw WireError(WireCode.malformed, "$") }
            return try dispatch(WireJSON.parseTree(text))
        }
        await settle()
        return snapshot(result)
    }

    /// Lets queued main actor work run: three turns of `Task.yield()`.
    @MainActor
    public static func yieldThrice() async {
        for _ in 0..<3 { await Task.yield() }
    }

    /// For ViewModels on the main actor, such as `@MainActor @Observable` classes on iOS. Reads stdin on
    /// a background queue and answers each line on the main actor, so Tasks an action starts can run.
    /// Each reply waits for `settle`, which by default yields three times; pass one that awaits the
    /// ViewModel’s own task when its work crosses actors. Call it from the main thread. Exits 0 at EOF.
    public func serveStandardIOOnMain(settle: @escaping @MainActor () async -> Void = Session.yieldThrice) -> Never {
        DispatchQueue.global().async {
            var framer = LineFramer()
            var buffer = [UInt8](repeating: 0, count: 65_536)
            func answer(_ line: [UInt8]) {
                let done = DispatchSemaphore(value: 0)
                Task { @MainActor in
                    let out = await self.handle(bytes: line, settle: settle).wire + "\n"
                    fputs(out, stdout)
                    fflush(stdout)
                    done.signal()
                }
                done.wait()
            }
            while true {
                let count = read(0, &buffer, buffer.count)
                if count < 0 && errno == EINTR { continue }
                if count <= 0 { break }
                for line in framer.push(buffer[0..<count]) { answer(line) }
            }
            if let last = framer.finish() { answer(last) }
            exit(0)
        }
        #if canImport(Darwin)
        // dispatchMain() lets a worker thread drain the main queue, so main actor code would see
        // Thread.isMainThread false and main thread asserts in the app would fire. The run loop keeps it here.
        while true { CFRunLoopRun() }
        #else
        dispatchMain()
        #endif
    }

    /// Reads NDJSON from stdin until EOF with `LineFramer` and answers each line with
    /// `handle(bytes:)`. After each response, `stop` may return an exit code.
    public func serveStandardIO(stop: () -> Int32? = { nil }) {
        var framer = LineFramer()
        var buffer = [UInt8](repeating: 0, count: 65_536)
        func answer(_ line: [UInt8]) {
            let out = handle(bytes: line).wire + "\n"
            fputs(out, stdout)
            fflush(stdout)
            if let code = stop() { exit(code) }
        }
        while true {
            let count = read(0, &buffer, buffer.count)
            if count < 0 && errno == EINTR { continue }
            if count <= 0 { break }
            for line in framer.push(buffer[0..<count]) { answer(line) }
        }
        if let last = framer.finish() { answer(last) }
    }
}
