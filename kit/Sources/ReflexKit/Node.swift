/// One public action. `run` receives input already decoded against `input`.
/// Keep it an unconditional closure over the ViewModel’s `send`: no business rules here.
public struct NodeAction {
    public let input: Schema?
    public let run: (Args) throws -> Void
    public init(input: Schema? = nil, _ run: @escaping (Args) throws -> Void) {
        self.input = input
        self.run = run
    }
}

/// Introspection adapter for one ViewModel. `state` is the ViewModel’s state as JSON.
public protocol Node {
    var name: String { get }
    var state: JSONValue { get }
    var actions: [String: NodeAction] { get }
    /// Actions a parent lends to the focused descendant, such as navigation.
    var lentActions: [String: NodeAction] { get }
    var child: (any Node)? { get }
}

public extension Node {
    var lentActions: [String: NodeAction] { [:] }
    var child: (any Node)? { nil }
}

/// The deepest node in the child chain plus every lent action above it.
public struct Focus {
    public let node: any Node
    public let actions: [String: NodeAction]

    public init(root: any Node) {
        var current = root
        var inherited: [String: NodeAction] = [:]
        while let next = current.child {
            inherited.merge(current.lentActions) { _, new in new }
            current = next
        }
        node = current
        actions = inherited.merging(current.actions) { _, new in new }
    }

    public var snapshot: JSONValue {
        var inputs: [String: JSONValue] = [:]
        for (title, action) in actions { if let schema = action.input { inputs[title] = schema.jsonSchema } }
        return ["name": .string(node.name), "state": node.state,
                "actions": .array(JSONValue.sortedKeys(actions.keys).map { .string($0) }),
                "inputs": .object(inputs)]
    }
}
