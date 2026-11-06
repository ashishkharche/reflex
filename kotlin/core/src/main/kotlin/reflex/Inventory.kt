package reflex

data class Product(val id: String, val title: String, val quantity: Long)
interface InventoryService {
    fun products(): List<Product>
    fun save(product: Product)
}
class NetworkGuard {
    var attempts = 0
        private set
    fun request(url: String): Nothing {
        attempts++
        error("HTTP attempted: fixture missing")
    }
}
class FixtureInventoryService(private val fixture: String = "happy", private val guardrail: NetworkGuard) : InventoryService {
    private var values = listOf(Product("shirt", "Cotton shirt", 3), Product("mug", "Ceramic mug", 0))
    override fun products() = values.toList()
    override fun save(product: Product) {
        if (fixture == "http-caught") runCatching {
            val connection = java.net.URI("http://127.0.0.1:9/reflex-tripwire").toURL().openConnection()
            connection.connectTimeout = 2000
            connection.readTimeout = 2000
            connection.getInputStream().use { it.read() }
        }
        if (fixture == "save-failure") error("Couldn’t save stock. Try again.")
        if (fixture == "network") guardrail.request("https://inventory.invalid/products")
        if (fixture == "network-caught") runCatching { guardrail.request("https://inventory.invalid/products") }
        values = values.map { if (it.id == product.id) product else it }
    }
}
class InventoryListViewModel(private val service: InventoryService) {
    data class State(val products: List<Product>)
    sealed interface Action { data object Refresh : Action }
    private sealed interface Message {
        data class ViewAction(val action: Action) : Message
        data class Loaded(val products: List<Product>) : Message
    }
    var state = State(service.products())
        private set
    fun send(action: Action) = update(Message.ViewAction(action))
    private fun update(message: Message) {
        when (message) {
            is Message.ViewAction -> when (message.action) {
                Action.Refresh -> update(Message.Loaded(service.products()))
            }
            is Message.Loaded -> state = State(message.products)
        }
    }
}
class InventoryDetailViewModel(product: Product, private val service: InventoryService) {
    data class State(val product: Product, val saved: Boolean = false, val error: String? = null)
    sealed interface Action {
        data class SetQuantity(val quantity: Long) : Action
        data object Decrement : Action
        data object Save : Action
    }
    private sealed interface Message {
        data class ViewAction(val action: Action) : Message
        data object Saved : Message
        data class Failed(val error: String) : Message
    }
    var state = State(product)
        private set
    fun send(action: Action) = update(Message.ViewAction(action))
    private fun update(message: Message) {
        when (message) {
            is Message.ViewAction -> when (val action = message.action) {
                is Action.SetQuantity -> {
                    state = if (action.quantity !in 0L..999999L)
                        state.copy(error = "Quantity must be between 0 and 999999.")
                    else state.copy(product = state.product.copy(quantity = action.quantity), saved = false, error = null)
                }
                Action.Decrement -> state = state.copy(product = state.product.copy(quantity = maxOf(0L, state.product.quantity - 1L)), saved = false, error = null)
                Action.Save -> try { service.save(state.product); update(Message.Saved) }
                    catch (e: Exception) { update(Message.Failed(e.message ?: "Save failed")) }
            }
            Message.Saved -> state = state.copy(saved = true, error = null)
            is Message.Failed -> state = state.copy(saved = false, error = message.error)
        }
    }
}
class InventoryNavigator(private val service: InventoryService) {
    data class State(val detail: InventoryDetailViewModel? = null)
    sealed interface Action {
        data class OpenProduct(val id: String) : Action
        data object GoBack : Action
    }
    private sealed interface Message { data class ViewAction(val action: Action) : Message }
    val list = InventoryListViewModel(service)
    var state = State()
        private set
    fun send(action: Action) = update(Message.ViewAction(action))
    private fun update(message: Message) {
        when (message) {
            is Message.ViewAction -> when (val action = message.action) {
                is Action.OpenProduct -> {
                    if (state.detail != null) return
                    val product = list.state.products.find { it.id == action.id } ?: return
                    state = State(InventoryDetailViewModel(product, service))
                }
                Action.GoBack -> { state = State(); list.send(InventoryListViewModel.Action.Refresh) }
            }
        }
    }
}
class InventoryApp(service: InventoryService) { val navigator = InventoryNavigator(service) }
