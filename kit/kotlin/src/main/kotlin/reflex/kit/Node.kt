package reflex.kit

/** One public action. [run] receives input already decoded against [input].
 *  Keep it an unconditional closure over the ViewModel’s `send`: no business rules here. */
class NodeAction(val input: Schema? = null, val run: (Args) -> Unit)

/** Introspection adapter for one ViewModel. [state] is the ViewModel’s state as JSON. */
interface Node {
    val name: String
    val state: JsonValue
    val actions: Map<String, NodeAction>
    /** Actions a parent lends to the focused descendant, such as navigation. */
    val lentActions: Map<String, NodeAction> get() = emptyMap()
    val child: Node? get() = null
}

/** The deepest node in the child chain plus every lent action above it. */
class Focus(root: Node) {
    val node: Node
    val actions: Map<String, NodeAction>

    init {
        var current = root
        var inherited = emptyMap<String, NodeAction>()
        while (true) {
            val next = current.child ?: break
            inherited = inherited + current.lentActions
            current = next
        }
        node = current
        actions = inherited + current.actions
    }

    val snapshot: JsonValue get() = jsonObject(
        "name" to node.name.json,
        "state" to node.state,
        "actions" to JsonArray(actions.keys.sorted().map { it.json }),
        "inputs" to JsonObject(actions.mapNotNull { (k, v) -> v.input?.let { k to it.jsonSchema } }.toMap()))
}
