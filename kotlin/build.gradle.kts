// Load Android into the same parent classloader only for Mobile builds.
// Headless Core/CLI never resolve Android plugins or require an SDK.
buildscript {
    if (project.findProperty("mobile") == "true") {
        repositories { google(); mavenCentral() }
        dependencies { classpath("com.android.tools.build:gradle:9.5.0") }
    }
}
plugins { kotlin("jvm") version "2.4.21" apply false }
