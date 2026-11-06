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

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme { InventoryScreen() } }
    }
}
@Composable private fun InventoryScreen() {
    val app = remember { InventoryApp(FixtureInventoryService(guardrail = NetworkGuard())) }
    var revision by remember { mutableIntStateOf(0) }
    fun dispatch(block: () -> Unit) { block(); revision++ }
    // Core is synchronous. This revision bridge re-reads immutable state after send.
    key(revision) {
        val nav = app.navigator
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
