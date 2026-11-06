// Debug builds only: a loopback socket host for a running app. Never ship it in a release build.
// On Android add it with debugImplementation so release variants cannot see it.
plugins { kotlin("jvm") }
layout.buildDirectory.set(rootProject.layout.buildDirectory.dir("reflex-socket"))
kotlin { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) } }
java { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
dependencies { api(project(":reflex-kit")) }
