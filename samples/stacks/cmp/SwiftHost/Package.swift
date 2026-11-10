// swift-tools-version:6.0
// Swift host for the Compose Multiplatform stack check: Swift ReflexKit over the commonMain ViewModel compiled by Kotlin/Native.
// Build the framework first: kotlin/gradlew -p samples/stacks/cmp :shared:assembleSharedXCFramework
import PackageDescription

let package = Package(
    name: "SwiftHost",
    platforms: [.macOS(.v13)],
    dependencies: [.package(path: "../../../../kit")],
    targets: [
        .binaryTarget(name: "Shared", path: "../shared/build/XCFrameworks/debug/Shared.xcframework"),
        .executableTarget(name: "cmp-swift-cli", dependencies: ["Shared", .product(name: "ReflexKit", package: "kit")])
    ]
)
