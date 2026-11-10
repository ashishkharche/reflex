import CounterCore
import ReflexKit

private let setInput = Schema([.required("value", .int64(min: 0, max: 99))])

/// Adapter: name, state and actions. It only calls send on the real ViewModel.
public struct CounterNode: Node {
    let vm: CounterViewModel
    public init(vm: CounterViewModel) { self.vm = vm }
    public var name: String { "Counter" }
    public var state: JSONValue { ["count": JSONValue(vm.state.count)] }
    public var actions: [String: NodeAction] { [
        "Decrement": NodeAction { _ in vm.send(.decrement) },
        "Increment": NodeAction { _ in vm.send(.increment) },
        "Reset": NodeAction { _ in vm.send(.reset) },
        "Set": NodeAction(input: setInput) { args in vm.send(.set(Int(args.int64("value")))) }
    ] }
}
