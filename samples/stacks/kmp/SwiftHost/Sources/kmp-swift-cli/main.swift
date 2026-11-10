import ReflexKit
import Shared

private let setInput = Schema([.required("value", .int64(min: 0, max: 99))])

/// Swift adapter over the Kotlin commonMain ViewModel, the same object an iOS app would use.
struct CounterNode: Node {
    let vm: CounterViewModel
    var name: String { "Counter" }
    var state: JSONValue { ["count": JSONValue(Int(vm.state.count))] }
    var actions: [String: NodeAction] { [
        "Decrement": NodeAction { _ in vm.send(action: CounterViewModelActionDecrement.shared) },
        "Increment": NodeAction { _ in vm.send(action: CounterViewModelActionIncrement.shared) },
        "Reset": NodeAction { _ in vm.send(action: CounterViewModelActionReset.shared) },
        "Set": NodeAction(input: setInput) { args in vm.send(action: CounterViewModelActionSet(value: args.int64("value"))) }
    ] }
}

let vm = CounterViewModel()
Session(sample: "counter", root: { CounterNode(vm: vm) }).serveStandardIO()
