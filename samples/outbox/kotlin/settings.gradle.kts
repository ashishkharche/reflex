pluginManagement { repositories { mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositories { mavenCentral() } }
rootProject.name = "outbox"
include(":core", ":introspection", ":cli", ":reflex-kit")
project(":reflex-kit").projectDir = file("../../../kit/kotlin")
