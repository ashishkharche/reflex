// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "Outbox", platforms: [.macOS(.v13), .iOS(.v17)], products: [
    .library(name: "OutboxCore", targets: ["OutboxCore"]),
    .executable(name: "outbox-cli", targets: ["OutboxCLI"])
], dependencies: [
    .package(path: "../../../kit")
], targets: [
    .target(name: "OutboxCore"),
    .target(name: "OutboxIntrospection", dependencies: ["OutboxCore", .product(name: "ReflexKit", package: "kit")]),
    .executableTarget(name: "OutboxCLI", dependencies: ["OutboxCore", "OutboxIntrospection", .product(name: "ReflexKit", package: "kit")]),
    .testTarget(name: "OutboxCoreTests", dependencies: ["OutboxCore", "OutboxIntrospection", .product(name: "ReflexKit", package: "kit")])
], swiftLanguageModes: [.v5])
