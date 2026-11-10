// ReflexKit for Kotlin/JVM. Included by each sample’s Gradle build as :reflex-kit.
// Outputs go under the including build so two samples never share one build directory.
plugins { kotlin("jvm") }
layout.buildDirectory.set(isolated.rootProject.projectDirectory.dir("build/reflex-kit"))
kotlin { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) } }
java { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
// Coroutines only for MainDispatcherTest, loaded in its own class loader so the kit stays dependency-free.
val coroutinesProbe = configurations.create("coroutinesProbe")
dependencies {
    testImplementation("junit:junit:4.13.2")
    coroutinesProbe("org.jetbrains.kotlinx:kotlinx-coroutines-core-jvm:1.10.2")
}
tasks.test {
    useJUnit()
    val probe = coroutinesProbe.incoming.files
    inputs.files(probe)
    jvmArgumentProviders.add(CommandLineArgumentProvider { listOf("-Dreflex.coroutines=" + probe.files.joinToString(File.pathSeparator)) })
    systemProperty("reflex.conformance", projectDir.resolve("../conformance/strict-decoder.json").canonicalPath)
    System.getenv("REFLEX_CONFORMANCE_REPORT")?.let { environment("REFLEX_CONFORMANCE_REPORT", it) }
    testLogging { events("passed", "failed"); showStandardStreams = false; exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL }
}
