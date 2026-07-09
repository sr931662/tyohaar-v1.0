import org.jetbrains.kotlin.gradle.dsl.JvmTarget

allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
subprojects {
    project.evaluationDependsOn(":app")
}

subprojects {
    val configureProject: () -> Unit = {
        if (project.extensions.findByName("android") != null) {
            val android = project.extensions.getByName<com.android.build.gradle.BaseExtension>("android")
            try {
                android.apply {
                    compileOptions {
                        sourceCompatibility = JavaVersion.VERSION_17
                        targetCompatibility = JavaVersion.VERSION_17
                    }
                }
            } catch (e: Exception) {
                // Skip if properties are already finalized
            }
        }

        tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
            try {
                compilerOptions {
                    jvmTarget.set(JvmTarget.JVM_17)
                }
            } catch (e: Exception) {
                // Skip if properties are already finalized
            }
        }
    }

    if (project.state.executed) {
        configureProject()
    } else {
        project.afterEvaluate { configureProject() }
    }
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
