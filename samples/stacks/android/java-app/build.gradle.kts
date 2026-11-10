plugins { id("com.android.application") }
android {
    namespace = "counter.java.app"
    compileSdk = 36
    buildToolsVersion = "36.0.0"
    defaultConfig { applicationId = "com.ashishkharche.reflex.counter.java"; minSdk = 26; targetSdk = 36; versionCode = 1; versionName = "1.0" }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
}
dependencies { implementation(project(":java-core")) }
