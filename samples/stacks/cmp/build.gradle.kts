buildscript {
    if (project.findProperty("mobile") == "true") {
        repositories { google(); mavenCentral() }
        dependencies { classpath("com.android.tools.build:gradle:9.5.0") }
    }
}
plugins {
    kotlin("jvm") version "2.4.21" apply false
    kotlin("multiplatform") version "2.4.21" apply false
    kotlin("plugin.compose") version "2.4.21" apply false
    id("org.jetbrains.compose") version "1.12.2" apply false
}
