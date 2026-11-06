package reflex.kit

/** Type-strict deep partial match used by journeys and unit tests.
 *  Objects: every expected key must be present and match; extra actual keys are allowed.
 *  Arrays: same length, element by element. Scalars: same JSON kind and equal value.
 *  `true` never matches `1`, `"90"` never matches `90` and `90` never matches `90.0`. */
object Expect {
    fun matches(actual: JsonValue, expected: JsonValue): Boolean = mismatch(actual, expected) == null

    /** The first mismatch as `path expected=… actual=…`, or null when it matches. */
    fun mismatch(actual: JsonValue, expected: JsonValue, path: String = "$"): String? = when {
        expected is JsonObject && actual is JsonObject -> expected.fields.keys.sorted().firstNotNullOfOrNull { key ->
            val value = actual.fields[key]
            if (value == null) "$path.$key expected=${expected.fields.getValue(key).wire} actual=<absent>"
            else mismatch(value, expected.fields.getValue(key), "$path.$key")
        }
        expected is JsonArray && actual is JsonArray ->
            if (expected.items.size != actual.items.size) "$path expected=${expected.items.size} items actual=${actual.items.size} items"
            else expected.items.indices.firstNotNullOfOrNull { i -> mismatch(actual.items[i], expected.items[i], "$path[$i]") }
        expected is JsonNumber && actual is JsonNumber ->
            if (expected.raw.toDouble() == actual.raw.toDouble()) null else describe(path, expected, actual)
        else -> if (expected == actual) null else describe(path, expected, actual)
    }

    private fun describe(path: String, expected: JsonValue, actual: JsonValue) =
        "$path expected=${expected.wire} (${expected.kind}) actual=${actual.wire} (${actual.kind})"
}
