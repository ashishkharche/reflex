package counter.java.cli

import counter.java.CounterViewModel
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

/** Kotlin adapter over the Java ViewModel. It only calls send. */
class CounterNode(private val vm: CounterViewModel) : Node {
    override val name = "Counter"
    override val state: JsonValue get() = jsonObject("count" to vm.state.count.json)
    override val actions get() = mapOf(
        "Decrement" to NodeAction { vm.send(CounterViewModel.Decrement()) },
        "Increment" to NodeAction { vm.send(CounterViewModel.Increment()) },
        "Reset" to NodeAction { vm.send(CounterViewModel.Reset()) },
        "Set" to NodeAction(setInput) { vm.send(CounterViewModel.SetValue(it.int64("value"))) })
}

fun main() {
    val vm = CounterViewModel()
    Session("counter", { CounterNode(vm) }).serveStandardIO()
}
