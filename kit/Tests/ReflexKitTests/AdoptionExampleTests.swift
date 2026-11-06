import XCTest
import ReflexKit

// Compiles the kit/README.md adoption snippet against stand-in app types.
private final class FakeClock {
    private(set) var now: Int64
    init(now: Int64) { self.now = now }
    func advance(by ms: Int64) { now += ms }
}

private final class OvenTimerViewModel {
    enum Status: String { case idle, running, ended }
    struct State { var status = Status.idle; var remainingSeconds: Int64 = 0; var label: String?; var fanOn = false }
    enum Action { case start(seconds: Int64, label: String?, fanOn: Bool), skip }
    private(set) var state = State()
    let clock: FakeClock
    init(clock: FakeClock) { self.clock = clock }
    func send(_ action: Action) {
        switch action {
        case .start(let seconds, let label, let fanOn):
            state = State(status: .running, remainingSeconds: seconds, label: label, fanOn: fanOn)
        case .skip: state.status = .ended
        }
    }
}

private let startInput = Schema([
    .required("seconds", .int64(min: 1, max: 3_600)),
    .optional("label", .string),
    .optional("fanOn", .bool)
])

private struct OvenTimerNode: Node {
    let vm: OvenTimerViewModel
    var name: String { "OvenTimer" }
    var state: JSONValue {
        var fields: [String: JSONValue] = ["status": .string(vm.state.status.rawValue),
                                           "remainingSeconds": .int(vm.state.remainingSeconds)]
        if let label = vm.state.label { fields["label"] = .string(label) }
        return .object(fields)
    }
    var actions: [String: NodeAction] { [
        "Start": NodeAction(input: startInput) { args in
            vm.send(.start(seconds: args.int64("seconds"), label: args.stringIfPresent("label"),
                           fanOn: args.boolIfPresent("fanOn") ?? false))
        },
        "Skip": NodeAction { _ in vm.send(.skip) }
    ] }
}

final class AdoptionExampleTests: XCTestCase {
    func testReadmeSnippet() {
        let clock = FakeClock(now: 1_800_000_000_000)
        let vm = OvenTimerViewModel(clock: clock)
        let session = Session(sample: "oven-timer", root: { OvenTimerNode(vm: vm) }, ops: [
            "tick": Session.Op(input: Schema([.required("ms", .int64(min: 0, max: 86_400_000))])) { args in
                clock.advance(by: args.int64("ms"))
            }
        ])
        _ = session.handle(#"{"op":"hello","protocol":1}"#)
        XCTAssertEqual(session.handle(#"{"op":"do","action":"Start","input":{"seconds":"90"}}"#)["error"],
                       ["code": "field.type", "path": "$.input.seconds"])
        XCTAssertEqual(session.handle(#"{"op":"do","action":"Start","input":{"seconds":3601}}"#)["error"],
                       ["code": "int.range", "path": "$.input.seconds"])
        let started = session.handle(#"{"op":"do","action":"Start","input":{"seconds":90,"label":"Row"}}"#)
        XCTAssertTrue(Expect.matches(started, ["ok": true, "node": ["state": ["status": "running", "remainingSeconds": 90, "label": "Row"]]]))
        XCTAssertEqual(session.handle(#"{"op":"tick","input":{"ms":1000}}"#)["ok"], true)
        XCTAssertEqual(clock.now, 1_800_000_001_000)
    }
}
