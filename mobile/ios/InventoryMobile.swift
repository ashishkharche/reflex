import SwiftUI
import InventoryCore

@main struct InventoryMobile: App {
    var body: some Scene { WindowGroup { InventoryScreen() } }
}
private struct InventoryScreen: View {
    @State private var app = InventoryApp(service: FixtureInventoryService(guardrail: NetworkGuard()))
    @State private var revision = 0
    @State private var quantity = ""
    private func dispatch(_ action: () -> Void) { action(); revision += 1 }
    var body: some View {
        let nav = app.navigator
        let _ = revision
        VStack(spacing: 16) {
            Text("Inventory").font(.title).accessibilityIdentifier("inventory.title")
            if let detail = nav.state.detail {
                Text(detail.state.product.title).accessibilityIdentifier("detail.title")
                Text("Quantity: \(detail.state.product.quantity)").accessibilityIdentifier("detail.quantity")
                TextField("Quantity", text: $quantity)
                    .keyboardType(.numberPad)
                    .textFieldStyle(.roundedBorder)
                    .accessibilityIdentifier("detail.quantityField")
                Button("Set quantity") {
                    if let value = Int(quantity) { dispatch { detail.send(.setQuantity(value)) } }
                }.accessibilityIdentifier("detail.setQuantity")
                Button("Decrement") { dispatch { detail.send(.decrement) } }
                    .accessibilityIdentifier("detail.decrement")
                Button("Save") { dispatch { detail.send(.save) } }
                    .accessibilityIdentifier("detail.save")
                if let error = detail.state.error {
                    Text(error).accessibilityIdentifier("detail.error")
                }
                if detail.state.saved {
                    Text("Stock saved").accessibilityIdentifier("detail.saved")
                }
                Button("Back") { dispatch { nav.send(.goBack) } }
                    .accessibilityIdentifier("detail.back")
            } else {
                ForEach(nav.list.state.products, id: \.id) { product in
                    Button("\(product.title): \(product.quantity)") {
                        quantity = String(product.quantity)
                        dispatch { nav.send(.openProduct(product.id)) }
                    }.accessibilityIdentifier("list.product.\(product.id)")
                }
            }
        }.padding()
    }
}
