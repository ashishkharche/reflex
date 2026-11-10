// swift-tools-version:6.0
// Reflex harness for the UIKit stack check. The app project never references this package.
import PackageDescription

let package = Package(
    name: "Harness",
    platforms: [.macOS(.v13)],
    dependencies: [.package(path: "../CounterCore"), .package(path: "../../../../kit")],
    targets: [
        .target(name: "CounterIntrospection", dependencies: ["CounterCore", .product(name: "ReflexKit", package: "kit")]),
        .executableTarget(name: "counter-cli", dependencies: ["CounterIntrospection", .product(name: "ReflexKit", package: "kit")])
    ]
)
