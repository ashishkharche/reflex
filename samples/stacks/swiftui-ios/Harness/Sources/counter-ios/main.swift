import CounterCore
import ReflexKit

private let setInput = Schema([.required("value", .int64(min: 0, max: 99))])

/// Adapter: name, state and actions. It only calls send on the real ViewModel.
@MainActor
struct CounterNode: Node {
    let vm: CounterViewModel
    var name: String { "Counter" }
    var state: JSONValue { ["count": JSONValue(vm.state.count)] }
    var actions: [String: NodeAction] { [
        "Decrement": NodeAction { _ in vm.send(.decrement) },
        "Increment": NodeAction { _ in vm.send(.increment) },
        "Reset": NodeAction { _ in vm.send(.reset) },
        "Set": NodeAction(input: setInput) { args in vm.send(.set(Int(args.int64("value")))) }
    ] }
}

// The ViewModel is main actor isolated, so serve on the main actor: each reply waits for the Task send starts.
MainActor.assumeIsolated {
    let vm = CounterViewModel()
    Session(sample: "counter", root: { CounterNode(vm: vm) }).serveStandardIOOnMain()
}
