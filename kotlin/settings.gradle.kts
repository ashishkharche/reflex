pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositories { google(); mavenCentral() } }
rootProject.name = "inventory"
include(":core", ":introspection", ":cli", ":reflex-kit")
// Shared strict decoder and Introspection Kit, also used by samples/outbox.
project(":reflex-kit").projectDir = file("../kit/kotlin")
// Headless work must not resolve or configure Android plugins or require an SDK.
if (providers.gradleProperty("mobile").orNull == "true") include(":mobile")
