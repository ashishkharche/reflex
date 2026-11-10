pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositories { google(); mavenCentral() } }
rootProject.name = "counter-kmp"
include(":shared", ":cli", ":reflex-kit")
project(":reflex-kit").projectDir = file("../../../kit/kotlin")
// The Android app and the Android target need an SDK. Headless builds never configure them.
if (providers.gradleProperty("mobile").orNull == "true") {
    include(":androidApp")
}
