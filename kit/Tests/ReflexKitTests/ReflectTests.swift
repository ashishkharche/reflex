#if canImport(Combine)
import Combine
#endif
import Foundation
import XCTest
@testable import ReflexKit

private enum Phase { case loading, ready(count: Int) }
private struct Item { let id: Int; let title: String }
private final class Model {
    var _items: [Item] = [Item(id: 1, title: "One")]
    var phase: Phase = .ready(count: 1)
    var loading = Phase.loading
    var note: String? = nil
    var onTap: () -> Void = {}
    var clock = Date(timeIntervalSince1970: 5)
    weak var parent: Model?
}

final class ReflectTests: XCTestCase {
    func testStateFromStoredProperties() {
        let model = Model()
        model.parent = model
        let state = Reflect.state(of: model, omit: ["clock"])
        XCTAssertEqual(state, .object([
            "items": .array([.object(["id": .int(1), "title": .string("One")])]),
            "phase": .object(["case": .string("ready"), "value": .object(["count": .int(1)])]),
            "loading": .string("loading"),
            "note": .null,
        ]))
    }

    #if canImport(Combine)
    func testPublishedValues() {
        final class Store: ObservableObject {
            @Published var count = 1
            @Published var names = ["a"]
        }
        let store = Store()
        XCTAssertEqual(Reflect.state(of: store), .object(["count": .int(1), "names": .array([.string("a")])]))
        // A subscriber moves the value into the wrapper’s subject.
        let watch = store.$count.sink { _ in }
        store.count = 2
        XCTAssertEqual(Reflect.state(of: store), .object(["count": .int(2), "names": .array([.string("a")])]))
        watch.cancel()
    }
    #endif
}
