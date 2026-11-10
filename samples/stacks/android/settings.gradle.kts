pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositories { google(); mavenCentral() } }
rootProject.name = "counter-android"
include(":views-core", ":views-cli", ":java-core", ":java-cli", ":reflex-kit")
project(":reflex-kit").projectDir = file("../../../kit/kotlin")
// The Android apps need an SDK. Headless CLI builds never configure them.
if (providers.gradleProperty("mobile").orNull == "true") {
    include(":views-app", ":java-app")
}
