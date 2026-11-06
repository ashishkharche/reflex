package reflex.kit

import java.io.FileDescriptor
import java.io.FileOutputStream
import java.io.PrintStream
import kotlin.system.exitProcess

/** Reflex NDJSON protocol v1 for one host process. See docs/protocol/v1.md.
 *  @param sample name reported by `hello`.
 *  @param root builds the root node for each response, so focus follows navigation.
 *  @param ops extra operations next to `hello`, `ls` and `do`.
 *  @param extras fields merged into every response, such as a network attempt counter. */
class Session(
    val sample: String,
    private val root: () -> Node,
    private val ops: Map<String, Op> = emptyMap(),
    private val extras: () -> Map<String, JsonValue> = { emptyMap() },
) {
    /** A host-specific operation, such as advancing a fake clock. Its input is decoded strictly. */
    class Op(val input: Schema? = null, val run: (Args) -> Unit)

    companion object {
        const val PROTOCOL_VERSION = 1L
        val supportedVersions = listOf(1L)
        const val KIT_VERSION = "1.0.1"

        /** Input must be absent or an object. Absent input decodes as `{}`. */
        fun decodeInput(value: JsonValue?, schema: Schema?): Args {
            val input = value ?: JsonObject(emptyMap())
            if (input !is JsonObject) throw WireError(WireCode.INPUT_NOT_OBJECT, "$.input")
            return (schema ?: Schema.empty).decode(input, "$.input")
        }
    }

    init { require(ops.keys.none { it in setOf("hello", "ls", "do") }) { "ReflexKit: reserved op name" } }

    var negotiated: Long? = null
        private set

    /** Handles one request line given as text. */
    fun handle(line: String): JsonValue = respond { dispatch(line) }

    /** Handles one request line given as raw bytes without its LF. Bytes that are not strict
     *  UTF-8 are `json.malformed` at `$` and are never decoded or echoed. */
    fun handle(bytes: ByteArray): JsonValue = respond {
        dispatch(StrictUtf8.decode(bytes) ?: throw WireError(WireCode.MALFORMED, "$"))
    }

    private fun respond(body: () -> Map<String, JsonValue>): JsonValue {
        val response = LinkedHashMap<String, JsonValue>()
        try {
            response.putAll(body())
            response["ok"] = true.json
        } catch (error: WireError) {
            response["ok"] = false.json
            response["error"] = error.json
            if (error.code == WireCode.UNSUPPORTED_PROTOCOL) response["supported"] = JsonArray(supportedVersions.map { it.json })
        }
        response["node"] = Focus(root()).snapshot
        response.putAll(extras())
        return JsonObject(response)
    }

    private fun dispatch(line: String): Map<String, JsonValue> {
        val request = (WireJson.parse(line) as? JsonObject)?.fields ?: throw WireError(WireCode.REQUEST_NOT_OBJECT, "$")
        val opValue = request["op"] ?: throw WireError(WireCode.MISSING, "$.op")
        val op = (opValue as? JsonString)?.value ?: throw WireError(WireCode.TYPE, "$.op")
        if (op != "hello" && op != "ls" && op != "do" && op !in ops) throw WireError(WireCode.UNKNOWN_OP, "$.op")
        if (op != "hello" && negotiated == null) throw WireError(WireCode.HANDSHAKE_REQUIRED, "$.op")
        when (op) {
            "hello" -> {
                only(request, setOf("op", "protocol"))
                val raw = request["protocol"] ?: throw WireError(WireCode.MISSING, "$.protocol")
                FieldType.int64.decode(raw, "$.protocol")
                val version = (raw as JsonInt).value
                if (version !in supportedVersions) throw WireError(WireCode.UNSUPPORTED_PROTOCOL, "$.protocol")
                negotiated = version
                return mapOf("protocol" to version.json, "sample" to sample.json, "kit" to KIT_VERSION.json)
            }
            "ls" -> only(request, setOf("op"))
            "do" -> {
                only(request, setOf("op", "action", "input"))
                val actionValue = request["action"] ?: throw WireError(WireCode.MISSING, "$.action")
                val title = (actionValue as? JsonString)?.value ?: throw WireError(WireCode.TYPE, "$.action")
                val action = Focus(root()).actions[title] ?: throw WireError(WireCode.UNKNOWN_ACTION, "$.action")
                action.run(decodeInput(request["input"], action.input))
            }
            else -> {
                val custom = ops.getValue(op)
                only(request, setOf("op", "input"))
                custom.run(decodeInput(request["input"], custom.input))
            }
        }
        return emptyMap()
    }

    private fun only(request: Map<String, JsonValue>, allowed: Set<String>) {
        request.keys.sorted().firstOrNull { it !in allowed }?.let { throw WireError(WireCode.UNKNOWN, "$.$it") }
    }

    /** Reads NDJSON from stdin until EOF with [LineFramer] and answers each line with
     *  [handle] on its bytes. After each response, [stop] may return an exit code. */
    fun serveStandardIO(stop: () -> Int? = { null }) {
        val out = PrintStream(FileOutputStream(FileDescriptor.out), false, Charsets.UTF_8)
        val input = System.`in`
        val framer = LineFramer()
        val buffer = ByteArray(65_536)
        fun answer(line: ByteArray) {
            out.print(handle(line).wire + "\n")
            out.flush()
            stop()?.let { out.flush(); exitProcess(it) }
        }
        while (true) {
            val count = input.read(buffer)
            if (count < 0) break
            for (line in framer.push(buffer, count)) answer(line)
        }
        framer.finish()?.let { answer(it) }
        out.flush()
    }
}
