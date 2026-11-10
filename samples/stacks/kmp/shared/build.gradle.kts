import org.jetbrains.kotlin.gradle.plugin.mpp.apple.XCFramework

plugins { kotlin("multiplatform") }
val mobile = findProperty("mobile") == "true"
// The Android target needs AGP, which only Mobile builds load.
if (mobile) apply(plugin = "com.android.kotlin.multiplatform.library")

kotlin {
    jvm { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) } }
    // One framework for the iOS app and one for the macOS Swift host, built from the same commonMain.
    val xcf = XCFramework("Shared")
    listOf(iosSimulatorArm64(), macosArm64()).forEach {
        it.binaries.framework { baseName = "Shared"; isStatic = true; xcf.add(this) }
    }
    if (mobile) {
        (this as ExtensionAware).extensions.getByName("android").withGroovyBuilder {
            setProperty("namespace", "counter.shared")
            setProperty("compileSdk", 36)
            setProperty("minSdk", 26)
        }
    }
}
