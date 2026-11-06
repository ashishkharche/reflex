package reflex.kit

/** A rejected request. [code] and [path] are identical on Swift and Kotlin for the same bytes.
 *  Paths start at `$` (the request line) and use `.key` and `[index]`. */
class WireError(val code: String, val path: String) : RuntimeException("$code at $path") {
    val json: JsonObject get() = jsonObject("code" to code.json, "path" to path.json)
    override fun equals(other: Any?) = other is WireError && other.code == code && other.path == path
    override fun hashCode() = code.hashCode() * 31 + path.hashCode()
}

/** Every wire error code the kit emits. Hosts may throw [WireError] with [VALUE_INVALID]
 *  from an action or op when a well-typed value is outside the host’s accepted set. */
object WireCode {
    const val MALFORMED = "json.malformed"
    const val TOO_DEEP = "json.depth"
    const val DUPLICATE_KEY = "json.duplicate_key"
    const val REQUEST_NOT_OBJECT = "request.not_object"
    const val UNKNOWN_OP = "request.unknown_op"
    const val HANDSHAKE_REQUIRED = "protocol.handshake_required"
    const val UNSUPPORTED_PROTOCOL = "protocol.unsupported"
    const val UNKNOWN_ACTION = "action.unknown"
    const val INPUT_NOT_OBJECT = "input.not_object"
    const val MISSING = "field.missing"
    const val UNKNOWN = "field.unknown"
    const val TYPE = "field.type"
    const val VALUE_INVALID = "field.value"
    const val INT_SYNTAX = "int.syntax"
    const val INT_RANGE = "int.range"
    val all = listOf(MALFORMED, TOO_DEEP, DUPLICATE_KEY, REQUEST_NOT_OBJECT, UNKNOWN_OP, HANDSHAKE_REQUIRED,
        UNSUPPORTED_PROTOCOL, UNKNOWN_ACTION, INPUT_NOT_OBJECT, MISSING, UNKNOWN, TYPE, VALUE_INVALID, INT_SYNTAX, INT_RANGE)
}
