// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "ReflexKit", platforms: [.macOS(.v13), .iOS(.v17)], products: [
    .library(name: "ReflexKit", targets: ["ReflexKit"])
], targets: [
    .target(name: "ReflexKit"),
    .testTarget(name: "ReflexKitTests", dependencies: ["ReflexKit"])
], swiftLanguageModes: [.v5])
