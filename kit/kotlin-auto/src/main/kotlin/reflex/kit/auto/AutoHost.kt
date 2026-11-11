package reflex.kit.auto

import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.emptyFlow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.test.setMain
import reflex.kit.Args
import reflex.kit.Field
import reflex.kit.FieldType
import reflex.kit.JsonArray
import reflex.kit.JsonBool
import reflex.kit.JsonInt
import reflex.kit.JsonNull
import reflex.kit.JsonNumber
import reflex.kit.JsonObject
import reflex.kit.JsonString
import reflex.kit.JsonValue
import reflex.kit.Node
import reflex.kit.NodeAction
import reflex.kit.Schema
import reflex.kit.Session
import reflex.kit.WireCode
import reflex.kit.WireError
import reflex.kit.WireJson
import java.io.File
import java.lang.reflect.GenericArrayType
import java.lang.reflect.InvocationTargetException
import java.lang.reflect.Method
import java.lang.reflect.Modifier
import java.lang.reflect.ParameterizedType
import java.lang.reflect.Proxy
import java.lang.reflect.Type
import java.lang.reflect.TypeVariable
import java.lang.reflect.WildcardType
import java.util.IdentityHashMap
import kotlin.coroutines.Continuation
import kotlin.coroutines.CoroutineContext
import kotlin.coroutines.intrinsics.suspendCoroutineUninterceptedOrReturn

/** What runner/reflex_init.py found in the source: the class to serve and hints reflection can’t see. */
class AutoConfig(
    val className: String,
    val name: String,
    /** Test doubles in the app, such as `TestUserDataRepository`, tried first for an interface. */
    val fakes: List<String> = emptyList(),
    /** Parameter names by `method/arity`, read from the source. */
    val params: Map<String, List<String>> = emptyMap(),
    /** State keys left out everywhere, such as a clock reading that differs per run. */
    val omit: Set<String> = emptySet(),
) {
    companion object {
        fun read(file: File): AutoConfig {
            val root = WireJson.parse(file.readText()) as JsonObject
            fun strings(key: String) = (root[key] as? JsonArray)?.items?.map { (it as JsonString).value } ?: emptyList()
            val params = (root["params"] as? JsonObject)?.fields?.mapValues { (_, v) ->
                (v as JsonArray).items.map { (it as JsonString).value }
            } ?: emptyMap()
            return AutoConfig(
                className = (root["class"] as JsonString).value,
                name = (root["name"] as? JsonString)?.value ?: (root["class"] as JsonString).value.substringAfterLast('.'),
                fakes = strings("fakes"),
                params = params,
                omit = strings("omit").toSet(),
            )
        }
    }
}

class Unbuildable(message: String) : RuntimeException(message)

private val PREFERRED = listOf("Test", "Fake", "InMemory", "Stub", "Dummy", "Noop", "NoOp")

/** Builds an object graph from constructors: app test doubles first, then Kotlin defaults, then stand-ins. */
class Builder(private val loader: ClassLoader, fakeNames: List<String>, private val main: CoroutineDispatcher) {
    private val fakes: List<Class<*>> = fakeNames.mapNotNull {
        try { Class.forName(it, false, loader) } catch (_: Throwable) { null }
    }.filter { !it.isInterface && !Modifier.isAbstract(it.modifiers) }
        // A fake that records or replays is closer to the app than one that does nothing.
        .sortedBy { c -> PREFERRED.indexOfFirst { c.simpleName.startsWith(it) }.let { if (it < 0) PREFERRED.size else it } }
    private val made = HashMap<Class<*>, Any?>()
    private val building = HashSet<Class<*>>()
    /** One line per choice, written to stderr so a failed first run says what it used. */
    val notes = mutableListOf<String>()

    fun build(type: Type, depth: Int = 0): Any? {
        val raw = raw(type) ?: throw Unbuildable("no class for $type")
        simple(raw, type)?.let { return it.value }
        if (made.containsKey(raw)) return made[raw]
        if (depth > 10) throw Unbuildable("${raw.name} is nested too deeply")
        if (!building.add(raw)) throw Unbuildable("${raw.name} depends on itself")
        try {
            val value = make(raw, type, depth)
            made[raw] = value
            return value
        } finally {
            building.remove(raw)
        }
    }

    private class Box(val value: Any?)

    /** Values that never need a constructor. */
    private fun simple(raw: Class<*>, type: Type): Box? = when {
        raw == java.lang.Boolean.TYPE || raw == java.lang.Boolean::class.java -> Box(false)
        raw == Integer.TYPE || raw == Integer::class.java -> Box(0)
        raw == java.lang.Long.TYPE || raw == java.lang.Long::class.java -> Box(0L)
        raw == java.lang.Short.TYPE || raw == java.lang.Short::class.java -> Box(0.toShort())
        raw == java.lang.Byte.TYPE || raw == java.lang.Byte::class.java -> Box(0.toByte())
        raw == java.lang.Double.TYPE || raw == java.lang.Double::class.java -> Box(0.0)
        raw == java.lang.Float.TYPE || raw == java.lang.Float::class.java -> Box(0f)
        raw == Character.TYPE || raw == Character::class.java -> Box(' ')
        raw == String::class.java || raw == CharSequence::class.java -> Box("")
        raw == Unit::class.java -> Box(Unit)
        raw == List::class.java || raw == Collection::class.java || raw == Iterable::class.java -> Box(emptyList<Any>())
        raw == Set::class.java -> Box(emptySet<Any>())
        raw == Map::class.java -> Box(emptyMap<Any, Any>())
        raw.isArray -> Box(java.lang.reflect.Array.newInstance(raw.componentType, 0))
        raw.isEnum -> Box(raw.enumConstants.firstOrNull())
        CoroutineDispatcher::class.java.isAssignableFrom(raw) -> Box(main)
        raw == CoroutineContext::class.java -> Box(main)
        raw == CoroutineScope::class.java -> Box(CoroutineScope(SupervisorJob() + main))
        StateFlow::class.java.isAssignableFrom(raw) -> Box(MutableStateFlow(element(type)))
        Flow::class.java.isAssignableFrom(raw) && raw.isInterface -> Box(flowOf(element(type)))
        else -> null
    }

    private fun element(type: Type): Any? {
        val arg = (type as? ParameterizedType)?.actualTypeArguments?.firstOrNull() ?: return null
        return try { build(arg, 1) } catch (_: Throwable) { null }
    }

    private fun make(raw: Class<*>, type: Type, depth: Int): Any? {
        if (raw.name == "androidx.lifecycle.SavedStateHandle") return raw.getConstructor().newInstance()
        objectInstance(raw)?.let { return it }
        val fake = fakes.firstOrNull { raw.isAssignableFrom(it) && it != raw }
        if (fake != null) {
            notes += "${raw.simpleName}: test double ${fake.simpleName}"
            return construct(fake, depth)
        }
        if (raw.isInterface) {
            if (raw.name.startsWith("kotlin.jvm.functions.") || raw.name.startsWith("kotlin.Function")) return function(raw)
            notes += "${raw.simpleName}: stand-in (returns empty values)"
            return standIn(raw, depth)
        }
        if (Modifier.isAbstract(raw.modifiers)) throw Unbuildable("${raw.name} is abstract and the app has no test double for it")
        return construct(raw, depth)
    }

    private fun objectInstance(raw: Class<*>): Any? = try {
        val field = raw.getDeclaredField("INSTANCE")
        if (Modifier.isStatic(field.modifiers) && field.type == raw) field.get(null) else null
    } catch (_: Throwable) { null }

    /** Kotlin compiles default arguments into a synthetic constructor ending in a bit mask and a marker. */
    private fun isDefaults(c: java.lang.reflect.Constructor<*>) =
        c.parameterTypes.lastOrNull()?.name == "kotlin.jvm.internal.DefaultConstructorMarker"

    fun construct(raw: Class<*>, depth: Int): Any {
        val constructors = raw.declaredConstructors.filter { !Modifier.isPrivate(it.modifiers) }
        var last: Throwable? = null
        // First the app’s own default arguments for plain values and for what can’t be built.
        // A plain value with no default makes Kotlin’s null check fail, and the next try builds it.
        val defaults = constructors.firstOrNull { isDefaults(it) }
        if (defaults != null) {
            val types = defaults.genericParameterTypes
            val masks = (1..types.size).first { m -> (types.size - 1 - m + 31) / 32 == m }
            val count = types.size - 1 - masks
            val args = arrayOfNulls<Any>(types.size)
            val bits = IntArray(masks)
            for (i in 0 until count) {
                val r = raw(types[i])
                val plainValue = r != null && !r.isEnum && simple(r, types[i]) != null && !CoroutineContext::class.java.isAssignableFrom(r) &&
                    r != CoroutineScope::class.java
                args[i] = if (plainValue) null else try { build(types[i], depth + 1) } catch (_: Throwable) { null }
                if (plainValue || (args[i] == null && r?.isPrimitive != true)) bits[i / 32] = bits[i / 32] or (1 shl (i % 32))
                if (args[i] == null && r?.isPrimitive == true) args[i] = zero(r)
            }
            bits.forEachIndexed { k, m -> args[count + k] = m }
            try {
                defaults.isAccessible = true
                return defaults.newInstance(*args)
            } catch (e: InvocationTargetException) { last = e.targetException } catch (e: Throwable) { last = e }
        }
        // Then every argument built: test doubles, stand-ins, nested constructors and empty values.
        for (c in constructors.filter { !isDefaults(it) }.sortedByDescending { it.parameterCount }) {
            try {
                c.isAccessible = true
                val args = c.genericParameterTypes.map { build(it, depth + 1) }.toTypedArray()
                return c.newInstance(*args)
            } catch (e: InvocationTargetException) { last = e.targetException } catch (e: Throwable) { last = e }
        }
        throw Unbuildable("${raw.name}: ${last?.let { it::class.java.simpleName + ": " + it.message } ?: "no constructor"}")
    }

    private fun zero(r: Class<*>?): Any? = if (r != null && r.isPrimitive) simple(r, r)?.value else null

    private fun function(raw: Class<*>): Any = Proxy.newProxyInstance(loader, arrayOf(raw)) { self, m, a ->
        when (m.name) {
            "equals" -> self === a?.getOrNull(0)
            "hashCode" -> System.identityHashCode(self)
            "toString" -> "Reflex stand-in function"
            else -> Unit
        }
    }

    /** An interface whose methods return empty values: no list items, no rows, nothing sent. */
    fun standIn(raw: Class<*>, depth: Int): Any = Proxy.newProxyInstance(loader, arrayOf(raw)) { self, m, a ->
        when (m.name) {
            "equals" -> return@newProxyInstance self === a?.getOrNull(0)
            "hashCode" -> return@newProxyInstance System.identityHashCode(self)
            "toString" -> return@newProxyInstance "Reflex stand-in for ${raw.simpleName}"
        }
        val params = m.genericParameterTypes
        val suspend = params.isNotEmpty() && raw(params.last()) == Continuation::class.java
        if (!suspend && m.returnType == Void.TYPE) return@newProxyInstance null
        val result = if (suspend) continuationResult(params.last()) else m.genericReturnType
        empty(result, depth)
    }

    private fun continuationResult(type: Type): Type {
        val arg = (type as? ParameterizedType)?.actualTypeArguments?.firstOrNull() ?: return Any::class.java
        return (arg as? WildcardType)?.lowerBounds?.firstOrNull() ?: arg
    }

    private fun empty(type: Type, depth: Int): Any? {
        val raw = raw(type) ?: return null
        if (raw == Any::class.java || raw == Unit::class.java || raw == Void::class.java) return Unit
        if (Flow::class.java.isAssignableFrom(raw) && raw.isInterface && !StateFlow::class.java.isAssignableFrom(raw)) {
            val arg = (type as? ParameterizedType)?.actualTypeArguments?.firstOrNull()
            val inner = arg?.let { raw(it) }
            // A list flow starts empty. Any other flow emits nothing, like a source with no rows yet.
            return if (inner != null && (List::class.java.isAssignableFrom(inner) || Set::class.java.isAssignableFrom(inner)
                    || Map::class.java.isAssignableFrom(inner) || inner == java.lang.Boolean::class.java)) flowOf(simple(inner, arg)!!.value)
            else emptyFlow<Any>()
        }
        simple(raw, type)?.let { return it.value }
        return try { build(type, depth + 1) } catch (_: Throwable) { null }
    }
}

fun raw(type: Type): Class<*>? = when (type) {
    is Class<*> -> type
    is ParameterizedType -> type.rawType as? Class<*>
    is WildcardType -> type.upperBounds.firstOrNull()?.let { raw(it) }
    is TypeVariable<*> -> type.bounds.firstOrNull()?.let { raw(it) }
    is GenericArrayType -> raw(type.genericComponentType)?.let { java.lang.reflect.Array.newInstance(it, 0).javaClass }
    else -> null
}

private val SKIP = JsonString("\u0000skip")

/** A flow that emitted null. */
object NOTHING

private fun platform(name: String) = name.startsWith("java.") || name.startsWith("javax.") || name.startsWith("kotlin.") ||
    name.startsWith("kotlinx.") || name.startsWith("android.") || name.startsWith("androidx.") || name.startsWith("sun.") ||
    name.startsWith("jdk.") || name.startsWith("dalvik.") || name.startsWith("com.google.common.")

/** Public no-argument getters as (state key, method), skipping platform base classes. */
fun getters(type: Class<*>): List<Pair<String, Method>> {
    val out = LinkedHashMap<String, Method>()
    for (m in type.methods.sortedBy { it.name }) {
        if (m.parameterCount != 0 || Modifier.isStatic(m.modifiers) || m.isSynthetic || m.isBridge) continue
        if (platform(m.declaringClass.name) || '$' in m.name) continue
        val n = m.name
        val key = when {
            n.startsWith("get") && n.length > 3 && n[3].isUpperCase() -> n[3].lowercaseChar() + n.substring(4)
            // Kotlin names the getter of `isSyncing` isSyncing, whatever its type.
            n.startsWith("is") && n.length > 2 && n[2].isUpperCase() -> n
            else -> continue
        }
        if (Regex("^component\\d+$").matches(n)) continue
        out.putIfAbsent(key, m)
    }
    return out.entries.map { it.key to it.value }
}

/** Converts what a ViewModel exposes into JSON with the same rules every run. */
class Jsonify(private val omit: Set<String>, private val latest: (Any) -> Any?) {
    fun of(value: Any?, depth: Int = 0, seen: IdentityHashMap<Any, Boolean> = IdentityHashMap()): JsonValue {
        if (value == null) return JsonNull
        when (value) {
            is Boolean -> return JsonBool(value)
            is Byte, is Short, is Int, is Long -> return JsonInt((value as Number).toLong())
            is Float, is Double -> {
                val d = (value as Number).toDouble()
                return if (d.isFinite()) (if (d == Math.rint(d) && Math.abs(d) < 1e15) JsonNumber(d.toLong().toString() + ".0") else JsonNumber(d.toString().replace("E", "e")))
                else JsonString(d.toString())
            }
            is Char -> return JsonString(value.toString())
            is CharSequence -> return JsonString(value.toString())
            is Enum<*> -> return JsonString(value.name)
            is StateFlow<*> -> return of(value.value, depth, seen)
            is Flow<*> -> return when (val seenValue = latest(value)) { null -> SKIP; NOTHING -> JsonNull; else -> of(seenValue, depth, seen) }
            is Number -> return JsonString(value.toString())
        }
        val type = value.javaClass
        if (type.name == "androidx.compose.runtime.State" || type.interfaces.any { it.name.startsWith("androidx.compose.runtime.") && it.simpleName.endsWith("State") }) {
            return try { of(type.getMethod("getValue").invoke(value), depth, seen) } catch (_: Throwable) { SKIP }
        }
        if (seen.containsKey(value)) return SKIP
        if (depth > 6) return JsonString(type.simpleName)
        seen[value] = true
        try {
            when (value) {
                is Map<*, *> -> return JsonObject(value.entries.take(100).associate { (k, v) -> k.toString() to of(v, depth + 1, seen) }.filterValues { it != SKIP })
                is Iterable<*> -> return JsonArray(value.take(100).map { of(it, depth + 1, seen) }.filter { it != SKIP })
                is Array<*> -> return JsonArray(value.take(100).map { of(it, depth + 1, seen) }.filter { it != SKIP })
            }
            if (type.isArray) return JsonArray((0 until minOf(100, java.lang.reflect.Array.getLength(value))).map { of(java.lang.reflect.Array.get(value, it), depth + 1, seen) })
            if (platform(type.name) || value is Function<*> || value is Job || value is CoroutineScope || Proxy.isProxyClass(type)) {
                return if (type.name.startsWith("java.time.") || type.name == "java.util.UUID" || type.name == "java.util.Date" ||
                    type.name.startsWith("kotlinx.datetime.")) JsonString(value.toString()) else SKIP
            }
            val fields = LinkedHashMap<String, JsonValue>()
            for ((key, getter) in getters(type)) {
                if (key in omit) continue
                val v = try { getter.isAccessible = true; of(getter.invoke(value), depth + 1, seen) } catch (_: Throwable) { SKIP }
                if (v != SKIP) fields[key] = v
            }
            // Sealed states such as Loading or Success: say which one it is.
            val polymorphic = (type.superclass != null && type.superclass != Any::class.java && Modifier.isAbstract(type.superclass.modifiers)) ||
                type.interfaces.any { !platform(it.name) }
            if (fields.isEmpty()) return JsonString(type.simpleName.ifEmpty { type.name.substringAfterLast('.') })
            if (polymorphic && "type" !in fields) fields["type"] = JsonString(type.simpleName)
            return JsonObject(fields)
        } finally {
            seen.remove(value)
        }
    }
}

/** The served state holder: its public properties as state and its public functions as actions. */
@OptIn(ExperimentalCoroutinesApi::class)
class AutoNode(private val vm: Any, private val config: AutoConfig, private val screen: CoroutineScope, private val settle: (Boolean) -> Unit) : Node {
    override val name = config.name
    private val latest = java.util.concurrent.ConcurrentHashMap<Any, Any?>()
    private val props = getters(vm.javaClass).filter { (key, m) ->
        key !in config.omit && !Job::class.java.isAssignableFrom(m.returnType) && !CoroutineScope::class.java.isAssignableFrom(m.returnType) &&
            !Function::class.java.isAssignableFrom(m.returnType) && !m.returnType.name.startsWith("kotlinx.coroutines.channels.")
    }
    private val json = Jsonify(config.omit) { latest[it] }

    init {
        // Collect every flow the way the screen does, so stateIn(WhileSubscribed) and plain flows stay live.
        for ((_, m) in props) {
            val flow = try { m.invoke(vm) } catch (_: Throwable) { null }
            if (flow is SharedFlow<*> || flow is StateFlow<*>) {
                screen.launch { (flow as Flow<*>).collect { } }
            } else if (flow is Flow<*>) {
                screen.launch { flow.collect { latest[flow] = it ?: NOTHING } }
            }
        }
    }

    private fun read(): JsonValue = JsonObject(props.associate { (key, m) ->
        key to (try { json.of(m.invoke(vm)) } catch (_: Throwable) { SKIP })
    }.filterValues { it != SKIP })

    /** Waits until two reads 25 ms apart agree, at most about a second, so a reply shows settled state. */
    override val state: JsonValue get() {
        settle(true)
        var before = read()
        repeat(40) {
            Thread.sleep(25)
            settle(false)
            val now = read()
            if (now == before) return now
            before = now
        }
        return before
    }

    override val actions: Map<String, NodeAction> by lazy { actionsOf() }

    private fun fieldType(type: Class<*>): FieldType? = when (type) {
        String::class.java, CharSequence::class.java -> FieldType.string
        java.lang.Boolean.TYPE, java.lang.Boolean::class.java -> FieldType.bool
        Integer.TYPE, Integer::class.java -> FieldType.int64(Int.MIN_VALUE.toLong(), Int.MAX_VALUE.toLong())
        java.lang.Long.TYPE, java.lang.Long::class.java -> FieldType.int64()
        else -> if (type.isEnum) FieldType.string else null
    }

    private fun actionsOf(): Map<String, NodeAction> {
        val out = sortedMapOf<String, NodeAction>()
        val getterNames = props.map { it.second.name }.toSet()
        val methods = vm.javaClass.methods.filter { m ->
            !Modifier.isStatic(m.modifiers) && !m.isSynthetic && !m.isBridge && '$' !in m.name && !platform(m.declaringClass.name) &&
                m.name !in getterNames && m.name !in setOf("equals", "hashCode", "toString", "copy", "onCleared", "close") &&
                !Regex("^(component\\d+|get[A-Z].*|set[A-Z].*)$").matches(m.name)
        }.sortedWith(compareBy({ it.name }, { it.parameterCount }))
        for (m in methods) {
            val types = m.parameterTypes.toList()
            val suspend = types.lastOrNull() == Continuation::class.java
            val real = if (suspend) types.dropLast(1) else types
            val fieldTypes = real.map { fieldType(it) }
            if (fieldTypes.any { it == null }) continue
            val names = config.params["${m.name}/${real.size}"] ?: real.indices.map { "arg${it + 1}" }
            if (names.size != real.size) continue
            var title = m.name.replaceFirstChar { it.uppercaseChar() }
            if (out.containsKey(title)) title += real.size
            val schema = if (real.isEmpty()) null else Schema(names.zip(fieldTypes).map { (n, t) -> Field.required(n, t!!) })
            out[title] = NodeAction(schema) { args -> invoke(m, real, names, suspend, args) }
        }
        return out
    }

    private fun invoke(m: Method, types: List<Class<*>>, names: List<String>, suspend: Boolean, args: Args) {
        val values = types.zip(names).map { (t, n) ->
            when {
                t == String::class.java || t == CharSequence::class.java -> args.string(n)
                t == java.lang.Boolean.TYPE || t == java.lang.Boolean::class.java -> args.bool(n)
                t == Integer.TYPE || t == Integer::class.java -> args.int64(n).toInt()
                t == java.lang.Long.TYPE || t == java.lang.Long::class.java -> args.int64(n)
                t.isEnum -> t.enumConstants.firstOrNull { (it as Enum<*>).name == args.string(n) }
                    ?: throw WireError(WireCode.VALUE_INVALID, "$.input.$n")
                else -> throw WireError(WireCode.TYPE, "$.input.$n")
            }
        }
        try {
            if (suspend) {
                runBlocking {
                    suspendCoroutineUninterceptedOrReturn<Any?> { cont -> m.invoke(vm, *values.toTypedArray(), cont) }
                }
            } else {
                m.invoke(vm, *values.toTypedArray())
            }
        } catch (e: InvocationTargetException) {
            throw e.targetException
        }
    }
}

/** Usage: java -cp <app unit test classpath>:reflex-auto.jar reflex.kit.auto.AutoHostKt <auto.json> [fixture] */
@OptIn(ExperimentalCoroutinesApi::class)
fun main(args: Array<String>) {
    val config = AutoConfig.read(File(args.firstOrNull() ?: error("ReflexKit auto: pass the auto.json path")))
    val loader = Thread.currentThread().contextClassLoader ?: AutoConfig::class.java.classLoader
    var settle: (Boolean) -> Unit = {}
    val main: CoroutineDispatcher = try {
        val test = kotlinx.coroutines.test.UnconfinedTestDispatcher()
        Dispatchers.setMain(test)
        // Virtual time: a delay or debounce in the ViewModel moves on by up to 2 seconds per reply, the same every run.
        settle = { full -> if (full) test.scheduler.advanceTimeBy(2000); test.scheduler.runCurrent() }
        test
    } catch (_: NoClassDefFoundError) {
        System.err.println("ReflexKit warning: kotlinx-coroutines-test is not on the classpath, so Dispatchers.Main is missing. " +
            "runner/reflex_init.py adds it. See docs/add-to-your-app.md.")
        Dispatchers.Unconfined
    }
    val type = Class.forName(config.className, true, loader)
    val builder = Builder(loader, config.fakes, main)
    val vm = try { builder.construct(type, 0) } catch (e: Unbuildable) {
        System.err.println("ReflexKit auto: could not build ${type.simpleName}: ${e.message}")
        builder.notes.forEach { System.err.println("ReflexKit auto: $it") }
        throw e
    }
    builder.notes.forEach { System.err.println("ReflexKit auto: $it") }
    val screen = CoroutineScope(SupervisorJob() + main)
    val node = AutoNode(vm, config, screen, settle)
    Session(config.name, { node }).serveStandardIO()
}
