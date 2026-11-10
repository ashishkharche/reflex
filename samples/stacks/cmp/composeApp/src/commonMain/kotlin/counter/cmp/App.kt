package counter.cmp

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.text.BasicText
import androidx.compose.foundation.clickable
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import counter.shared.CounterViewModel
import counter.shared.CounterViewModel.Action

/** One Compose Multiplatform screen for Android and iOS over the commonMain ViewModel.
 *  `shown` only mirrors vm.state so Compose redraws. The ViewModel owns the count. */
@Composable
fun App(vm: CounterViewModel = remember { CounterViewModel() }) {
    var shown by remember { mutableStateOf(vm.state) }
    fun send(action: Action) { vm.send(action); shown = vm.state }
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        BasicText("${shown.count}")
        BasicText("−", Modifier.clickable { send(Action.Decrement) })
        BasicText("+", Modifier.clickable { send(Action.Increment) })
        BasicText("Reset", Modifier.clickable { send(Action.Reset) })
    }
}
