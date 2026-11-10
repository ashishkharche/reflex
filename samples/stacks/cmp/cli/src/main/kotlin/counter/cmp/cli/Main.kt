package counter.cmp.cli

import counter.shared.CounterViewModel
import counter.shared.CounterViewModel.Action
import reflex.kit.Field
import reflex.kit.FieldType
import reflex.kit.JsonValue
import reflex.kit.Node
import reflex.kit.NodeAction
import reflex.kit.Schema
import reflex.kit.Session
import reflex.kit.json
import reflex.kit.jsonObject

private val setInput = Schema(Field.required("value", FieldType.int64(min = 0, max = 99)))

/** Adapter: it only calls send on the shared commonMain ViewModel. */
class CounterNode(private val vm: CounterViewModel) : Node {
    override val name = "Counter"
    override val state: JsonValue get() = jsonObject("count" to vm.state.count.json)
    override val actions get() = mapOf(
        "Decrement" to NodeAction { vm.send(Action.Decrement) },
        "Increment" to NodeAction { vm.send(Action.Increment) },
        "Reset" to NodeAction { vm.send(Action.Reset) },
        "Set" to NodeAction(setInput) { vm.send(Action.Set(it.int64("value"))) })
}

fun main() {
    val vm = CounterViewModel()
    Session("counter", { CounterNode(vm) }).serveStandardIO()
}
