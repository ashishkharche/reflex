// ReflexKit for Kotlin/JVM. Included by each sample’s Gradle build as :reflex-kit.
// Outputs go under the including build so two samples never share one build directory.
plugins { kotlin("jvm") }
layout.buildDirectory.set(rootProject.layout.buildDirectory.dir("reflex-kit"))
kotlin { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) } }
java { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
dependencies { testImplementation("junit:junit:4.13.2") }
tasks.test {
    useJUnit()
    systemProperty("reflex.conformance", projectDir.resolve("../conformance/strict-decoder.json").canonicalPath)
    System.getenv("REFLEX_CONFORMANCE_REPORT")?.let { environment("REFLEX_CONFORMANCE_REPORT", it) }
    testLogging { events("passed", "failed"); showStandardStreams = false; exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL }
}
