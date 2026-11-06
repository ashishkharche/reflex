import XCTest
@testable import InventoryCore
final class CoreTests: XCTestCase {
    func testClampAndValidation() {
        let guardrail = NetworkGuard()
        let app = InventoryApp(service: FixtureInventoryService(guardrail: guardrail))
        app.navigator.send(.openProduct("mug"))
        let vm = app.navigator.state.detail!
        vm.send(.decrement)
        XCTAssertEqual(vm.state.product.quantity, 0)
        vm.send(.setQuantity(-1))
        XCTAssertEqual(vm.state.product.quantity, 0)
        XCTAssertNotNil(vm.state.error)
    }
    func testStickyNetworkGuard() {
        let guardrail = NetworkGuard()
        try? guardrail.request("https://inventory.invalid")
        XCTAssertEqual(guardrail.attempts, 1)
    }
}

import ReflexKit
import InventoryIntrospection

final class IntrospectionTests: XCTestCase {
    func testSessionUsesStrictKit() {
        let app = InventoryApp(service: FixtureInventoryService(guardrail: NetworkGuard()))
        let session = Session(sample: "inventory", root: { AppNode(app: app) })
        XCTAssertEqual(session.handle(#"{"op":"ls"}"#)["error"], ["code": "protocol.handshake_required", "path": "$.op"])
        XCTAssertEqual(session.handle(#"{"op":"hello","protocol":1}"#)["ok"], true)
        XCTAssertEqual(session.handle(#"{"op":"do","action":"OpenProduct","input":{"id":"shirt"}}"#)["node"]?["name"], "InventoryDetail")
        let fraction = session.handle(#"{"op":"do","action":"SetQuantity","input":{"quantity":5.0}}"#)
        XCTAssertEqual(fraction["error"], ["code": "int.syntax", "path": "$.input.quantity"])
        let wide = session.handle(#"{"op":"do","action":"SetQuantity","input":{"quantity":2147483648}}"#)
        XCTAssertTrue(Expect.matches(wide, ["ok": true, "node": ["state": ["error": "Quantity must be between 0 and 999999."]]]))
    }
}
