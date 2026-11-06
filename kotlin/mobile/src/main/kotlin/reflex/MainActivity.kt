package reflex
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import androidx.compose.ui.unit.dp

/** Owns the real Core for the screen. In debug builds the socket host drives this same object. */
class InventoryModel {
    val network = NetworkGuard()
    val app = InventoryApp(FixtureInventoryService(guardrail = network))
    var revision by mutableIntStateOf(0)
    fun dispatch(block: () -> Unit) { block(); revision++ }
}

class MainActivity : ComponentActivity() {
    private val model = InventoryModel()
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Debug: starts the loopback socket host when launched with --ei reflexPort PORT. Release: does nothing.
        DebugSocket.startIfRequested(intent.getIntExtra("reflexPort", -1), model)
        setContent { MaterialTheme { InventoryScreen(model) } }
    }
}
@Composable private fun InventoryScreen(model: InventoryModel) {
    fun dispatch(block: () -> Unit) = model.dispatch(block)
    // Core is synchronous. This revision bridge re-reads immutable state after send.
    key(model.revision) {
        val nav = model.app.navigator
        val detail = nav.state.detail
        Column(
            Modifier
                .padding(24.dp)
                .semantics { testTagsAsResourceId = true },
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text("Inventory", style = MaterialTheme.typography.headlineMedium, modifier = Modifier.testTag("inventory.title"))
            if (detail == null) {
                nav.list.state.products.forEach { product ->
                    Button(
                        onClick = { dispatch { nav.send(InventoryNavigator.Action.OpenProduct(product.id)) } },
                        modifier = Modifier.testTag("list.product.${product.id}")
                    ) {
                        Text("${product.title}: ${product.quantity}")
                    }
                }
            } else {
                Text(detail.state.product.title, modifier = Modifier.testTag("detail.title"))
                Text("Quantity: ${detail.state.product.quantity}", modifier = Modifier.testTag("detail.quantity"))
                var input by remember { mutableStateOf(detail.state.product.quantity.toString()) }
                OutlinedTextField(
                    input,
                    { input = it },
                    label = { Text("Quantity") },
                    modifier = Modifier.testTag("detail.quantityField")
                )
                Button(
                    onClick = { input.toLongOrNull()?.let { value -> dispatch { detail.send(InventoryDetailViewModel.Action.SetQuantity(value)) } } },
                    modifier = Modifier.testTag("detail.setQuantity")
                ) { Text("Set quantity") }
                Button(
                    onClick = { dispatch { detail.send(InventoryDetailViewModel.Action.Decrement) } },
                    modifier = Modifier.testTag("detail.decrement")
                ) { Text("Decrement") }
                Button(
                    onClick = { dispatch { detail.send(InventoryDetailViewModel.Action.Save) } },
                    modifier = Modifier.testTag("detail.save")
                ) { Text("Save") }
                detail.state.error?.let { Text(it, modifier = Modifier.testTag("detail.error")) }
                if (detail.state.saved) Text("Stock saved", modifier = Modifier.testTag("detail.saved"))
                Button(
                    onClick = { dispatch { nav.send(InventoryNavigator.Action.GoBack) } },
                    modifier = Modifier.testTag("detail.back")
                ) { Text("Back") }
            }
        }
    }
}
