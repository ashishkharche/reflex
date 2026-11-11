import XCTest
import ReflexKit

// A main actor ViewModel that does its work in a Task, as many SwiftUI ViewModels do.
@MainActor
private final class TaskCounter {
    private(set) var count = 0
    func increment() { Task { count += 1 } }
}

@MainActor
private struct TaskCounterNode: Node {
    let vm: TaskCounter
    var name: String { "Counter" }
    var state: JSONValue { ["count": .int(Int64(vm.count))] }
    var actions: [String: NodeAction] { ["Increment": NodeAction { _ in vm.increment() }] }
}

final class MainActorTests: XCTestCase {
    @MainActor
    func testSettledReplyShowsWorkTheActionStarted() async {
        let vm = TaskCounter()
        let session = Session(sample: "counter", root: { TaskCounterNode(vm: vm) })
        _ = session.handle(#"{"op":"hello","protocol":1}"#)
        let line = Array(#"{"op":"do","action":"Increment"}"#.utf8)
        let reply = await session.handle(bytes: line, settle: Session.yieldThrice)
        XCTAssertEqual(reply.wire, #"{"node":{"actions":["Increment"],"inputs":{},"name":"Counter","state":{"count":1}},"ok":true}"#)
    }

    @MainActor
    func testPlainReplyIsTakenBeforeTheTaskRuns() async {
        let vm = TaskCounter()
        let session = Session(sample: "counter", root: { TaskCounterNode(vm: vm) })
        _ = session.handle(#"{"op":"hello","protocol":1}"#)
        let reply = session.handle(#"{"op":"do","action":"Increment"}"#)
        XCTAssertTrue(reply.wire.contains(#""count":0"#), reply.wire)
    }

    @MainActor
    func testErrorsStillReplyAfterSettling() async {
        let vm = TaskCounter()
        let session = Session(sample: "counter", root: { TaskCounterNode(vm: vm) })
        let reply = await session.handle(bytes: Array(#"{"op":"ls"}"#.utf8), settle: Session.yieldThrice)
        XCTAssertTrue(reply.wire.contains(#""code":"protocol.handshake_required""#), reply.wire)
    }
}
