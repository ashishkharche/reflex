// swift-tools-version:6.0
// UI-free Core for the iOS-only SwiftUI stack check. It imports UIKit, so it builds for iOS and not for the Mac.
import PackageDescription

let package = Package(
    name: "CounterCore",
    platforms: [.iOS(.v17)],
    products: [.library(name: "CounterCore", targets: ["CounterCore"])],
    targets: [.target(name: "CounterCore")],
    swiftLanguageModes: [.v5]
)
