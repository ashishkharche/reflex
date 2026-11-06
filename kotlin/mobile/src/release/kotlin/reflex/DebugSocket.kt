package reflex

/** Release builds have no socket host. This stub keeps MainActivity the same for both variants. */
object DebugSocket {
    @Suppress("UNUSED_PARAMETER")
    fun startIfRequested(port: Int, model: InventoryModel) = Unit
}
