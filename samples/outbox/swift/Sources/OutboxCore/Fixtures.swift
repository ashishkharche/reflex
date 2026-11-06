/// Test fixtures passed in at construction. No production endpoint exists in this sample.

public final class FakeClock: Clock {
    public private(set) var now: Int64
    public init(now: Int64) { self.now = now }

    /// Moves time forward by `ms`, firing the outbox timer at every wake time on the way,
    /// the way a host’s scheduler would.
    public func advance(by ms: Int64, waking outbox: OutboxViewModel) {
        precondition(ms >= 0, "time only moves forward")
        let target = now + ms
        var fired = 0
        while let wake = outbox.nextWakeAt, wake <= target, fired < 10_000 {
            now = max(now, wake)
            outbox.send(.wake)
            fired += 1
        }
        now = target
    }
}

/// A scripted flaky network in front of a fake server that dedups by idempotency key.
/// Each delivery consumes one scripted outcome; an empty script means `ok`.
public final class FlakyNetwork: Transport {
    public enum Outcome: String, CaseIterable {
        /// Server stores the message (or already has it) and the reply arrives.
        case ok
        /// Server stores the message but the reply is lost: the client sees a timeout.
        case lost
        /// The request never reaches the server.
        case timeout
        case error500 = "500"
        /// Another writer already created this key: the server answers 409.
        case conflict409 = "409"
        case rejected422 = "422"
    }

    public private(set) var stored: [String] = []
    public private(set) var requests = 0
    private var script: [Outcome] = []

    public init() {}

    public var scripted: Int { script.count }

    public func enqueue(_ outcomes: [Outcome]) { script.append(contentsOf: outcomes) }

    public func deliver(key: String, body: String) -> DeliveryResult {
        requests += 1
        let outcome = script.isEmpty ? .ok : script.removeFirst()
        switch outcome {
        case .ok:
            if stored.contains(key) { return .duplicate }
            stored.append(key)
            return .created
        case .lost:
            if !stored.contains(key) { stored.append(key) }
            return .timeout
        case .timeout: return .timeout
        case .error500: return .serverError(500)
        case .conflict409:
            if !stored.contains(key) { stored.append(key) }
            return .duplicate
        case .rejected422: return .rejected(422)
        }
    }
}
