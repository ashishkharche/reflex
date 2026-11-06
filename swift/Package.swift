// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "Inventory", platforms: [.macOS(.v13), .iOS(.v17)], products: [
    .library(name: "InventoryCore", targets: ["InventoryCore"]),
    .executable(name: "inventory-cli", targets: ["InventoryCLI"])
], dependencies: [
    .package(path: "../kit")
], targets: [
    .target(name: "InventoryCore"),
    .target(name: "InventoryIntrospection", dependencies: ["InventoryCore", .product(name: "ReflexKit", package: "kit")]),
    .executableTarget(name: "InventoryCLI", dependencies: ["InventoryCore", "InventoryIntrospection", .product(name: "ReflexKit", package: "kit")]),
    .testTarget(name: "InventoryCoreTests", dependencies: ["InventoryCore", "InventoryIntrospection", .product(name: "ReflexKit", package: "kit")])
], swiftLanguageModes: [.v5])
