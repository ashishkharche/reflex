import CounterCore
import SwiftUI

/// SwiftUI screen over the shared Core. The view holds no state of its own.
struct CounterView: View {
    @State private var vm = CounterViewModel()

    var body: some View {
        VStack(spacing: 12) {
            Text("\(vm.state.count)").font(.system(size: 48, weight: .semibold).monospacedDigit())
                .accessibilityIdentifier("count")
            Button("−") { vm.send(.decrement) }
            Button("+") { vm.send(.increment) }
            Button("Reset") { vm.send(.reset) }
        }
    }
}

@main
struct CounterSwiftUIApp: App {
    var body: some Scene { WindowGroup { CounterView() } }
}
