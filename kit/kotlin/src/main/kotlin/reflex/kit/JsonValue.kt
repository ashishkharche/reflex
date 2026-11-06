package reflex.kit

/** A parsed or built JSON value. Integers that fit in a Long are [JsonInt]. Any other numeric
 *  literal (fraction, exponent or outside Long) stays verbatim in [JsonNumber], so the strict
 *  accessors can tell `90`, `90.0`, `1e2` and `9223372036854775808` apart. */
sealed interface JsonValue {
    val kind: String

    /** Canonical wire form: keys sorted by UTF-16 code unit, no whitespace, minimal escapes.
     *  The Swift kit writes the same bytes for the same value. */
    val wire: String get() = StringBuilder().also { write(it) }.toString()

    operator fun get(key: String): JsonValue? = (this as? JsonObject)?.fields?.get(key)
}

object JsonNull : JsonValue { override val kind = "null"; override fun toString() = "null" }
data class JsonBool(val value: Boolean) : JsonValue { override val kind get() = "boolean" }
data class JsonInt(val value: Long) : JsonValue { override val kind get() = "integer" }
data class JsonNumber(val raw: String) : JsonValue { override val kind get() = "number" }
data class JsonString(val value: String) : JsonValue { override val kind get() = "string" }
data class JsonArray(val items: List<JsonValue>) : JsonValue { override val kind get() = "array" }
data class JsonObject(val fields: Map<String, JsonValue>) : JsonValue { override val kind get() = "object" }

val Long.json: JsonValue get() = JsonInt(this)
val Int.json: JsonValue get() = JsonInt(toLong())
val String.json: JsonValue get() = JsonString(this)
val Boolean.json: JsonValue get() = JsonBool(this)
fun List<JsonValue>.json(): JsonValue = JsonArray(this)

/** Builds an object. Pairs whose value is null are omitted, which is how optional state is written. */
fun jsonObject(vararg pairs: Pair<String, JsonValue?>): JsonObject =
    JsonObject(pairs.mapNotNull { (k, v) -> v?.let { k to it } }.toMap())

private const val HEX = "0123456789abcdef"

private fun JsonValue.write(out: StringBuilder) {
    when (this) {
        JsonNull -> out.append("null")
        is JsonBool -> out.append(if (value) "true" else "false")
        is JsonInt -> out.append(value)
        is JsonNumber -> out.append(raw)
        is JsonString -> writeString(value, out)
        is JsonArray -> {
            out.append('[')
            items.forEachIndexed { i, v -> if (i > 0) out.append(','); v.write(out) }
            out.append(']')
        }
        is JsonObject -> {
            out.append('{')
            fields.keys.sorted().forEachIndexed { i, k ->
                if (i > 0) out.append(',')
                writeString(k, out); out.append(':'); fields.getValue(k).write(out)
            }
            out.append('}')
        }
    }
}

private fun writeString(text: String, out: StringBuilder) {
    out.append('"')
    for (ch in text) {
        when (ch) {
            '"' -> out.append("\\\"")
            '\\' -> out.append("\\\\")
            '\n' -> out.append("\\n")
            '\r' -> out.append("\\r")
            '\t' -> out.append("\\t")
            '\b' -> out.append("\\b")
            '\u000c' -> out.append("\\f")
            else -> if (ch.code < 0x20) {
                out.append("\\u00").append(HEX[ch.code shr 4]).append(HEX[ch.code and 0xF])
            } else out.append(ch)
        }
    }
    out.append('"')
}
