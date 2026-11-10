package reflex.kit

import java.io.File
import java.net.URLClassLoader
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class MainDispatcherTest {
    @Test fun noCoroutinesNoWarning() {
        assertNull(MainDispatcher.problem())
    }

    @Test fun coroutinesWithoutMainWarns() {
        val jars = System.getProperty("reflex.coroutines").split(File.pathSeparator).map { File(it).toURI().toURL() }
        val loader = URLClassLoader(jars.toTypedArray(), MainDispatcher::class.java.classLoader)
        assertEquals(MainDispatcher.WARNING, MainDispatcher.problem(loader))
        assert(MainDispatcher.WARNING.startsWith("ReflexKit warning:"))
    }
}
