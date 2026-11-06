plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose") version "2.4.21"
}
android {
    namespace = "reflex.mobile"
    compileSdk = 36
    buildToolsVersion = "36.0.0"
    defaultConfig { applicationId = "com.ashishkharche.reflex.inventory"; minSdk = 26; targetSdk = 36; versionCode = 1; versionName = "1.0" }
    buildFeatures { compose = true }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
}
kotlin { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) } }
dependencies {
    implementation(project(":core"))
    // Debug socket host only. Release variants never see these (scripts/check_release_exclusion.sh).
    debugImplementation(project(":introspection"))
    debugImplementation(project(":reflex-socket"))
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.compose.material3:material3:1.4.0")
}
