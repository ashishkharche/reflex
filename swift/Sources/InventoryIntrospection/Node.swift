import InventoryCore
import ReflexKit

// Adapters have no UI rules or state writes. Every closure dispatches through send.
private let quantityInput = Schema([.required("quantity", .int64)])
private let productInput = Schema([.required("id", .string)])

private extension Product {
    var json: JSONValue { ["id": .string(id), "title": .string(title), "quantity": JSONValue(quantity)] }
}

public struct DetailNode: Node {
    let vm: InventoryDetailViewModel
    public var name: String { "InventoryDetail" }
    public var state: JSONValue {
        var fields: [String: JSONValue] = ["product": vm.state.product.json, "saved": .bool(vm.state.saved)]
        if let error = vm.state.error { fields["error"] = .string(error) }
        return .object(fields)
    }
    public var actions: [String: NodeAction] { [
        "SetQuantity": NodeAction(input: quantityInput) { args in
            guard let quantity = Int(exactly: args.int64("quantity")) else {
                throw WireError(WireCode.intRange, "$.input.quantity")
            }
            vm.send(.setQuantity(quantity))
        },
        "Decrement": NodeAction { _ in vm.send(.decrement) },
        "Save": NodeAction { _ in vm.send(.save) }
    ] }
}

public struct ListNode: Node {
    let vm: InventoryListViewModel
    public var name: String { "InventoryList" }
    public var state: JSONValue { ["products": .array(vm.state.products.map(\.json))] }
    public var actions: [String: NodeAction] { ["Refresh": NodeAction { _ in vm.send(.refresh) }] }
}

public struct NavigatorNode: Node {
    let nav: InventoryNavigator
    public var name: String { "InventoryNavigator" }
    public var state: JSONValue { ["depth": nav.state.detail == nil ? 1 : 2] }
    private var open: NodeAction { NodeAction(input: productInput) { nav.send(.openProduct($0.string("id"))) } }
    public var actions: [String: NodeAction] { ["OpenProduct": open] }
    public var lentActions: [String: NodeAction] { ["OpenProduct": open, "goBack": NodeAction { _ in nav.send(.goBack) }] }
    public var child: (any Node)? {
        if let detail = nav.state.detail { return DetailNode(vm: detail) }
        return ListNode(vm: nav.list)
    }
}

public struct AppNode: Node {
    let app: InventoryApp
    public init(app: InventoryApp) { self.app = app }
    public var name: String { "InventoryApp" }
    public var state: JSONValue { [:] }
    public var actions: [String: NodeAction] { [:] }
    public var child: (any Node)? { NavigatorNode(nav: app.navigator) }
}
