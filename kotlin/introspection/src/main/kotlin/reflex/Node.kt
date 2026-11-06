package reflex

import reflex.kit.Field
import reflex.kit.FieldType
import reflex.kit.JsonValue
import reflex.kit.Node
import reflex.kit.NodeAction
import reflex.kit.Schema
import reflex.kit.json
import reflex.kit.jsonObject

// Adapters have no UI rules or state writes. Every closure dispatches through send.
private val quantityInput = Schema(Field.required("quantity", FieldType.int64))
private val productInput = Schema(Field.required("id", FieldType.string))

private fun Product.json() = jsonObject("id" to id.json, "title" to title.json, "quantity" to quantity.json)

class DetailNode(private val vm: InventoryDetailViewModel) : Node {
    override val name = "InventoryDetail"
    override val state: JsonValue get() = jsonObject(
        "product" to vm.state.product.json(), "saved" to vm.state.saved.json, "error" to vm.state.error?.json)
    override val actions get() = mapOf(
        "SetQuantity" to NodeAction(quantityInput) { vm.send(InventoryDetailViewModel.Action.SetQuantity(it.int64("quantity"))) },
        "Decrement" to NodeAction { vm.send(InventoryDetailViewModel.Action.Decrement) },
        "Save" to NodeAction { vm.send(InventoryDetailViewModel.Action.Save) })
}

class ListNode(private val vm: InventoryListViewModel) : Node {
    override val name = "InventoryList"
    override val state: JsonValue get() = jsonObject("products" to vm.state.products.map { it.json() }.json())
    override val actions get() = mapOf("Refresh" to NodeAction { vm.send(InventoryListViewModel.Action.Refresh) })
}

class NavigatorNode(private val nav: InventoryNavigator) : Node {
    override val name = "InventoryNavigator"
    override val state: JsonValue get() = jsonObject("depth" to (if (nav.state.detail == null) 1 else 2).json)
    private val open = NodeAction(productInput) { nav.send(InventoryNavigator.Action.OpenProduct(it.string("id"))) }
    override val actions get() = mapOf("OpenProduct" to open)
    override val lentActions get() = mapOf(
        "OpenProduct" to open,
        "goBack" to NodeAction { nav.send(InventoryNavigator.Action.GoBack) })
    override val child: Node get() = nav.state.detail?.let { DetailNode(it) } ?: ListNode(nav.list)
}

class AppNode(private val app: InventoryApp) : Node {
    override val name = "InventoryApp"
    override val state: JsonValue = jsonObject()
    override val actions = emptyMap<String, NodeAction>()
    override val child: Node get() = NavigatorNode(app.navigator)
}
