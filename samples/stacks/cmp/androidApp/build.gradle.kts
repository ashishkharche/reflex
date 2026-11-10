plugins { id("com.android.application"); kotlin("plugin.compose") }
android {
    namespace = "counter.cmp.app"
    compileSdk = 37
    buildToolsVersion = "36.0.0"
    defaultConfig { applicationId = "com.ashishkharche.reflex.counter.cmp"; minSdk = 26; targetSdk = 36; versionCode = 1; versionName = "1.0" }
    buildFeatures { compose = true }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
}
kotlin { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) } }
dependencies {
    implementation(project(":composeApp"))
    implementation("androidx.activity:activity-compose:1.13.0")
}
