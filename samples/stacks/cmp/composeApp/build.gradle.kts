plugins {
    kotlin("multiplatform")
    kotlin("plugin.compose")
    id("org.jetbrains.compose")
}
apply(plugin = "com.android.kotlin.multiplatform.library")

kotlin {
    (this as ExtensionAware).extensions.getByName("android").withGroovyBuilder {
        setProperty("namespace", "counter.cmp")
        setProperty("compileSdk", 37)
        setProperty("minSdk", 26)
    }
    iosSimulatorArm64().binaries.framework { baseName = "ComposeApp"; isStatic = true }
    sourceSets {
        commonMain.dependencies {
            api(project(":shared"))
            implementation("org.jetbrains.compose.runtime:runtime:1.12.2")
            implementation("org.jetbrains.compose.foundation:foundation:1.12.2")
            implementation("org.jetbrains.compose.ui:ui:1.12.2")
        }
    }
}
