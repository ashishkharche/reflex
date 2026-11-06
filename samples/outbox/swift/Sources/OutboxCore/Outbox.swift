/// Offline outbox: messages queue locally and deliver through a Transport with retry,
/// exponential backoff and an idempotency key per message. UI-free and platform-free.

public protocol Clock: AnyObject {
    /// Milliseconds since the Unix epoch.
    var now: Int64 { get }
}

public enum DeliveryResult: Equatable {
    case created
    case duplicate
    case timeout
    case serverError(Int)
    case rejected(Int)
}

public protocol Transport: AnyObject {
    func deliver(key: String, body: String) -> DeliveryResult
}

public enum Backoff {
    public static let baseMs: Int64 = 1_000
    public static let capMs: Int64 = 30_000
    public static let maxAttempts = 7

    /// Delay after failed attempt `attempt` (1-based): 1 s, 2 s, 4 s … capped at 30 s. No jitter.
    public static func delay(afterAttempt attempt: Int) -> Int64 {
        var delay = baseMs
        for _ in 1..<max(attempt, 1) {
            delay *= 2
            if delay >= capMs { return capMs }
        }
        return min(delay, capMs)
    }
}

public final class OutboxViewModel {
    public enum Status: String { case pending, retrying, sent, failed }

    public struct Item: Equatable {
        public let key: String
        public let body: String
        public var status: Status
        public var attempts: Int
        public var nextAttemptAt: Int64?
        public var lastError: String?
        public var ack: String?
    }

    public struct State: Equatable {
        public var items: [Item] = []
        public var online = true
        public var deduped = 0
        public var error: String?
    }

    public enum Action: Equatable {
        case enqueue(key: String, body: String)
        case syncNow
        case setOnline(Bool)
        case retry(key: String)
        case purgeSent
        /// The host’s timer fired at or after `nextWakeAt`.
        case wake
    }

    private enum Message {
        case viewAction(Action)
        case attempting(key: String)
        case delivered(key: String, DeliveryResult)
    }

    public static let maxBodyScalars = 280
    public static let keyError = "Key must be 1 to 64 letters, digits, dots, dashes or underscores."
    public static let bodyError = "Message must be 280 characters or fewer."
    public static let offlineError = "You’re offline. Messages will send when you’re back online."
    public static let retryError = "Only failed messages can be retried."

    public private(set) var state = State()
    private let clock: Clock
    private let transport: Transport

    public init(clock: Clock, transport: Transport) {
        self.clock = clock
        self.transport = transport
    }

    public var now: Int64 { clock.now }

    /// When the host should call `send(.wake)` next, or nil when nothing is waiting.
    public var nextWakeAt: Int64? {
        guard state.online else { return nil }
        return state.items.filter { $0.status == .pending || $0.status == .retrying }.compactMap(\.nextAttemptAt).min()
    }

    public func send(_ action: Action) { update(.viewAction(action)) }

    private func update(_ message: Message) {
        switch message {
        case .viewAction(.enqueue(let key, let body)):
            guard OutboxViewModel.isValidKey(key) else { state.error = OutboxViewModel.keyError; return }
            guard body.unicodeScalars.count <= OutboxViewModel.maxBodyScalars else {
                state.error = OutboxViewModel.bodyError; return
            }
            state.error = nil
            if state.items.contains(where: { $0.key == key }) { state.deduped += 1; return }
            state.items.append(Item(key: key, body: body, status: .pending, attempts: 0,
                                    nextAttemptAt: clock.now, lastError: nil, ack: nil))
        case .viewAction(.syncNow):
            guard state.online else { state.error = OutboxViewModel.offlineError; return }
            state.error = nil
            deliver(force: true)
        case .viewAction(.setOnline(let online)):
            state.online = online
            state.error = nil
            if online { deliver(force: false) }
        case .viewAction(.retry(let key)):
            // Always offered. Only a failed message can be retried; anything else sets retryError.
            guard let index = state.items.firstIndex(where: { $0.key == key && $0.status == .failed }) else {
                state.error = OutboxViewModel.retryError; return
            }
            state.error = nil
            state.items[index].status = .pending
            state.items[index].attempts = 0
            state.items[index].nextAttemptAt = clock.now
            state.items[index].lastError = nil
            if state.online { deliver(force: false) }
        case .viewAction(.purgeSent):
            // Always offered. With nothing sent this is a no-op.
            state.items.removeAll { $0.status == .sent }
        case .viewAction(.wake):
            deliver(force: false)
        case .attempting(let key):
            guard let index = state.items.firstIndex(where: { $0.key == key }) else { return }
            state.items[index].attempts += 1
        case .delivered(let key, let result):
            guard let index = state.items.firstIndex(where: { $0.key == key }) else { return }
            var item = state.items[index]
            switch result {
            case .created, .duplicate:
                item.status = .sent
                item.ack = result == .created ? "created" : "duplicate"
                item.nextAttemptAt = nil
                item.lastError = nil
            case .rejected(let code):
                item.status = .failed
                item.nextAttemptAt = nil
                item.lastError = "http-\(code)"
            case .timeout, .serverError:
                if case .serverError(let code) = result { item.lastError = "http-\(code)" } else { item.lastError = "timeout" }
                if item.attempts >= Backoff.maxAttempts {
                    item.status = .failed
                    item.nextAttemptAt = nil
                } else {
                    item.status = .retrying
                    item.nextAttemptAt = clock.now + Backoff.delay(afterAttempt: item.attempts)
                }
            }
            state.items[index] = item
        }
    }

    /// One pass in queue order. Each waiting item is attempted at most once per pass.
    /// Reads state only. Every write goes through `update`.
    private func deliver(force: Bool) {
        guard state.online else { return }
        let now = clock.now
        let due = state.items.filter {
            ($0.status == .pending || $0.status == .retrying) && (force || ($0.nextAttemptAt ?? .max) <= now)
        }.map(\.key)
        for key in due {
            update(.attempting(key: key))
            guard let item = state.items.first(where: { $0.key == key }) else { continue }
            update(.delivered(key: key, transport.deliver(key: item.key, body: item.body)))
        }
    }

    static func isValidKey(_ key: String) -> Bool {
        let scalars = key.unicodeScalars
        guard (1...64).contains(scalars.count) else { return false }
        return scalars.allSatisfy { s in
            (97...122).contains(s.value) || (65...90).contains(s.value) || (48...57).contains(s.value) || s == "." || s == "-" || s == "_"
        }
    }
}
