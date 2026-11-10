plugins { kotlin("jvm"); application }
kotlin { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) } }
java { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
dependencies { implementation(project(":shared")); implementation(project(":reflex-kit")) }
application { mainClass.set("counter.cmp.cli.MainKt") }
