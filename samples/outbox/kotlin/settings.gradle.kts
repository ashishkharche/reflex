pluginManagement { repositories { mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositories { mavenCentral() } }
rootProject.name = "outbox"
include(":core", ":introspection", ":cli", ":reflex-kit", ":reflex-socket")
project(":reflex-kit").projectDir = file("../../../kit/kotlin")
project(":reflex-socket").projectDir = file("../../../kit/kotlin-socket")
