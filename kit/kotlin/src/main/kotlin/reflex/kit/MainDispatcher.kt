package reflex.kit

import java.lang.reflect.InvocationTargetException

/** Checks for a JVM host with kotlinx.coroutines but no `Dispatchers.Main`. Work a ViewModel
 *  starts in `viewModelScope` then never runs, so its state stays at the first value with no error.
 *  Uses reflection, so the kit itself still needs no coroutines dependency. */
object MainDispatcher {
    const val WARNING = "ReflexKit warning: Dispatchers.Main is missing, so viewModelScope work never runs " +
        "and state stays at its first value. Call Dispatchers.setMain(UnconfinedTestDispatcher()) " +
        "from kotlinx-coroutines-test before you build the ViewModel. See docs/add-to-your-app.md."

    /** [WARNING] when coroutines are on the classpath and Main is missing, else null. */
    fun problem(loader: ClassLoader = MainDispatcher::class.java.classLoader): String? {
        val dispatchers = try {
            Class.forName("kotlinx.coroutines.Dispatchers", true, loader)
        } catch (_: ClassNotFoundException) {
            return null
        }
        return try {
            val main = dispatchers.getMethod("getMain").invoke(null)
            val context = Class.forName("kotlin.coroutines.CoroutineContext", true, loader)
            val empty = Class.forName("kotlin.coroutines.EmptyCoroutineContext", true, loader).getField("INSTANCE").get(null)
            // The missing dispatcher is an internal class, so call through the public base class.
            Class.forName("kotlinx.coroutines.CoroutineDispatcher", true, loader)
                .getMethod("isDispatchNeeded", context).invoke(main, empty)
            null
        } catch (error: InvocationTargetException) {
            if (error.cause is IllegalStateException) WARNING else null
        } catch (_: ReflectiveOperationException) {
            null
        }
    }
}
