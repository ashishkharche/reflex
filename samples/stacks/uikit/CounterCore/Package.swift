// swift-tools-version:6.0
// UI-free Core for the UIKit stack check. No ReflexKit here.
import PackageDescription

let package = Package(
    name: "CounterCore",
    platforms: [.macOS(.v13), .iOS(.v17)],
    products: [.library(name: "CounterCore", targets: ["CounterCore"])],
    targets: [.target(name: "CounterCore")]
)
