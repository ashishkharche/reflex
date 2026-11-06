import OutboxCore
import ReflexKit

// Adapter only: every closure dispatches through send. No delivery rules here.
// The action set never depends on state. The ViewModel’s update decides if an action is valid.
private let enqueueInput = Schema([.required("key", .string), .required("body", .string)])
private let onlineInput = Schema([.required("online", .bool)])
private let keyInput = Schema([.required("key", .string)])

private extension OutboxViewModel.Item {
    var json: JSONValue {
        var fields: [String: JSONValue] = ["key": .string(key), "body": .string(body), "status": .string(status.rawValue),
                                           "attempts": JSONValue(attempts)]
        if let nextAttemptAt { fields["nextAttemptAt"] = .int(nextAttemptAt) }
        if let lastError { fields["lastError"] = .string(lastError) }
        if let ack { fields["ack"] = .string(ack) }
        return .object(fields)
    }
}

public struct OutboxNode: Node {
    let vm: OutboxViewModel
    public init(vm: OutboxViewModel) { self.vm = vm }
    public var name: String { "Outbox" }
    public var state: JSONValue {
        var fields: [String: JSONValue] = ["online": .bool(vm.state.online), "now": .int(vm.now),
                                           "deduped": JSONValue(vm.state.deduped), "items": .array(vm.state.items.map(\.json))]
        if let wake = vm.nextWakeAt { fields["nextWakeAt"] = .int(wake) }
        if let error = vm.state.error { fields["error"] = .string(error) }
        return .object(fields)
    }
    public var actions: [String: NodeAction] {
        [
            "Enqueue": NodeAction(input: enqueueInput) { vm.send(.enqueue(key: $0.string("key"), body: $0.string("body"))) },
            "SyncNow": NodeAction { _ in vm.send(.syncNow) },
            "SetOnline": NodeAction(input: onlineInput) { vm.send(.setOnline($0.bool("online"))) },
            "Retry": NodeAction(input: keyInput) { vm.send(.retry(key: $0.string("key"))) },
            "PurgeSent": NodeAction { _ in vm.send(.purgeSent) }
        ]
    }
}

/// Host operations for behaviour sessions: fake time and the flaky network script.
public enum OutboxOps {
    public static let maxAdvanceMs: Int64 = 86_400_000

    public static func make(vm: OutboxViewModel, clock: FakeClock, network: FlakyNetwork) -> [String: Session.Op] {
        [
            "advance": Session.Op(input: Schema([.required("ms", .int64(min: 0, max: maxAdvanceMs))])) { args in
                clock.advance(by: args.int64("ms"), waking: vm)
            },
            "network": Session.Op(input: Schema([.required("script", .array(.string))])) { args in
                var outcomes: [FlakyNetwork.Outcome] = []
                for (index, name) in args.strings("script").enumerated() {
                    guard let outcome = FlakyNetwork.Outcome(rawValue: name) else {
                        throw WireError(WireCode.valueInvalid, "$.input.script[\(index)]")
                    }
                    outcomes.append(outcome)
                }
                network.enqueue(outcomes)
            }
        ]
    }

    public static func server(_ network: FlakyNetwork) -> [String: JSONValue] {
        ["server": ["requests": JSONValue(network.requests), "stored": .array(network.stored.map { .string($0) }),
                    "scripted": JSONValue(network.scripted)]]
    }
}
