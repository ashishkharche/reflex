// ReflexKit auto host for Kotlin/JVM: serves one state holder by reflection, so an app needs no
// hand-written adapter for a first run. runner/reflex_init.py puts its jar on the app’s unit test classpath.
// Coroutines are compileOnly: the app brings its own.
plugins { kotlin("jvm") }
layout.buildDirectory.set(isolated.rootProject.projectDirectory.dir("build/reflex-auto"))
kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
        // App classpaths carry their own Kotlin standard library, often older than this build’s.
        apiVersion.set(org.jetbrains.kotlin.gradle.dsl.KotlinVersion.KOTLIN_2_0)
        languageVersion.set(org.jetbrains.kotlin.gradle.dsl.KotlinVersion.KOTLIN_2_0)
    }
    coreLibrariesVersion = "2.0.21"
}
// One jar: the kit sources are compiled here too, for the same older Kotlin API.
sourceSets.main { kotlin.srcDir("../kotlin/src/main/kotlin") }
java { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
dependencies {
    compileOnly("org.jetbrains.kotlinx:kotlinx-coroutines-core-jvm:1.8.1")
    compileOnly("org.jetbrains.kotlinx:kotlinx-coroutines-test-jvm:1.8.1")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-core-jvm:1.8.1")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test-jvm:1.8.1")
}
tasks.test { useJUnit(); testLogging { events("passed", "failed"); exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL } }
