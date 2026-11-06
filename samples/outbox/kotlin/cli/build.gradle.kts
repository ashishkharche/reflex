plugins { kotlin("jvm"); application }
kotlin { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) } }
java { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
dependencies { implementation(project(":introspection")); implementation(project(":reflex-socket")) }
application { mainClass.set("reflex.outbox.MainKt"); applicationDefaultJvmArgs = listOf("-Xmx96m") }
