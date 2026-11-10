import Shared
import SwiftUI

/// SwiftUI over the Kotlin commonMain ViewModel. The view holds no counter state of its own.
final class CounterModel: ObservableObject {
    let vm = CounterViewModel()
    @Published private(set) var count: Int32 = 0
    func send(_ action: CounterViewModelAction) { vm.send(action: action); count = vm.state.count }
}

struct CounterView: View {
    @StateObject private var model = CounterModel()
    var body: some View {
        VStack(spacing: 12) {
            Text("\(model.count)").font(.system(size: 48, weight: .semibold)).monospacedDigit()
            Button("−") { model.send(CounterViewModelActionDecrement.shared) }
            Button("+") { model.send(CounterViewModelActionIncrement.shared) }
            Button("Reset") { model.send(CounterViewModelActionReset.shared) }
        }
    }
}

@main struct CounterKMPApp: App {
    var body: some Scene { WindowGroup { CounterView() } }
}
