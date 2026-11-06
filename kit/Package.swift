// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "ReflexKit", platforms: [.macOS(.v13), .iOS(.v17)], products: [
    .library(name: "ReflexKit", targets: ["ReflexKit"]),
    // Debug builds only: a loopback socket host for a running app. Never link it into a release build.
    .library(name: "ReflexSocketHost", targets: ["ReflexSocketHost"])
], targets: [
    .target(name: "ReflexKit"),
    .target(name: "ReflexSocketHost", dependencies: ["ReflexKit"]),
    .testTarget(name: "ReflexKitTests", dependencies: ["ReflexKit"])
], swiftLanguageModes: [.v5])
