package reflex

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

class InventoryCoreTest {
    @Test fun clampAndValidation() {
        val app = InventoryApp(FixtureInventoryService(guardrail = NetworkGuard()))
        app.navigator.send(InventoryNavigator.Action.OpenProduct("mug"))
        val vm = app.navigator.state.detail!!
        vm.send(InventoryDetailViewModel.Action.Decrement)
        assertEquals(0L, vm.state.product.quantity)
        vm.send(InventoryDetailViewModel.Action.SetQuantity(-1))
        assertEquals(0L, vm.state.product.quantity)
        assertNotNull(vm.state.error)
        vm.send(InventoryDetailViewModel.Action.SetQuantity(2147483648L))
        assertEquals("Quantity must be between 0 and 999999.", vm.state.error)
    }

    @Test fun stickyNetworkGuard() {
        val guardrail = NetworkGuard()
        runCatching { guardrail.request("https://inventory.invalid") }
        assertEquals(1, guardrail.attempts)
    }
}
