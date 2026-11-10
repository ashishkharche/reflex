import ComposeApp
import SwiftUI

/// Hosts the shared Compose Multiplatform screen on iOS.
struct ComposeScreen: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> UIViewController { MainViewControllerKt.MainViewController() }
    func updateUIViewController(_ controller: UIViewController, context: Context) {}
}

@main struct CounterCMPApp: App {
    var body: some Scene { WindowGroup { ComposeScreen().ignoresSafeArea() } }
}
