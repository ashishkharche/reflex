pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositories { google(); mavenCentral() } }
rootProject.name = "counter-cmp"
include(":shared", ":cli", ":reflex-kit")
project(":reflex-kit").projectDir = file("../../../kit/kotlin")
// Compose UI, the Android target and the Android app need an SDK. Headless builds never configure them.
if (providers.gradleProperty("mobile").orNull == "true") {
    include(":composeApp", ":androidApp")
}
