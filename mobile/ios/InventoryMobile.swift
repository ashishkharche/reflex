import SwiftUI
import InventoryCore

/// Owns the real Core for the screen. In Debug builds the socket host drives this same object.
final class InventoryModel: ObservableObject {
    let network = NetworkGuard()
    let app: InventoryApp
    @Published var revision = 0
    init() { app = InventoryApp(service: FixtureInventoryService(guardrail: network)) }
    func dispatch(_ action: () -> Void) { action(); revision += 1 }
}

@main struct InventoryMobile: App {
    @StateObject private var model = InventoryModel()
    var body: some Scene {
        WindowGroup {
            InventoryScreen(model: model)
            #if DEBUG
                .onAppear { DebugSocket.startIfRequested(model) }
            #endif
        }
    }
}

private struct InventoryScreen: View {
    @ObservedObject var model: InventoryModel
    @State private var quantity = ""
    private func dispatch(_ action: () -> Void) { model.dispatch(action) }
    var body: some View {
        let nav = model.app.navigator
        let _ = model.revision
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
