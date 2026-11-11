// swift-tools-version:6.0
// Reflex harness for the iOS-only SwiftUI stack check. It runs on the iOS simulator. The app never references it.
import PackageDescription

let package = Package(
    name: "Harness",
    platforms: [.iOS(.v17)],
    dependencies: [.package(path: "../CounterCore"), .package(path: "../../../../kit")],
    targets: [
        .executableTarget(name: "counter-ios", dependencies: ["CounterCore", .product(name: "ReflexKit", package: "kit")])
    ],
    swiftLanguageModes: [.v5]
)
