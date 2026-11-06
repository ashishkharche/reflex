package reflex.kit

/** Strict RFC 8259 parser for one request line. Duplicate keys are rejected at any depth
 *  with their path, before any value reaches a decoder. Malformed input reports path `$`.
 *  Keys are compared by their exact UTF-16 code units with no Unicode normalisation, so
 *  `"\u00e9"` and `"e\u0301"` are two different keys, as on Swift. */
object WireJson {
    const val MAX_DEPTH = 64

    fun parse(text: String): JsonValue {
        val parser = Parser(text)
        val value = parser.value("$", 0)
        parser.skipWhitespace()
        if (parser.index != text.length) throw malformed()
        return value
    }
}

private fun malformed() = WireError(WireCode.MALFORMED, "$")

private class Parser(private val text: String) {
    var index = 0
    private val current: Char? get() = if (index < text.length) text[index] else null

    fun value(path: String, depth: Int): JsonValue {
        skipWhitespace()
        return when (current ?: throw malformed()) {
            '{' -> objectValue(path, depth + 1)
            '[' -> arrayValue(path, depth + 1)
            '"' -> JsonString(string())
            't' -> { literal("true"); JsonBool(true) }
            'f' -> { literal("false"); JsonBool(false) }
            'n' -> { literal("null"); JsonNull }
            '-', in '0'..'9' -> number()
            else -> throw malformed()
        }
    }

    private fun objectValue(path: String, depth: Int): JsonValue {
        if (depth > WireJson.MAX_DEPTH) throw WireError(WireCode.TOO_DEEP, "$")
        index++
        val fields = LinkedHashMap<String, JsonValue>()
        skipWhitespace()
        if (current == '}') { index++; return JsonObject(fields) }
        while (true) {
            skipWhitespace()
            if (current != '"') throw malformed()
            val key = string()
            val child = "$path.$key"
            skipWhitespace()
            if (current != ':') throw malformed()
            index++
            if (key in fields) throw WireError(WireCode.DUPLICATE_KEY, child)
            fields[key] = value(child, depth)
            skipWhitespace()
            when (current) {
                ',' -> index++
                '}' -> { index++; return JsonObject(fields) }
                else -> throw malformed()
            }
        }
    }

    private fun arrayValue(path: String, depth: Int): JsonValue {
        if (depth > WireJson.MAX_DEPTH) throw WireError(WireCode.TOO_DEEP, "$")
        index++
        val values = ArrayList<JsonValue>()
        skipWhitespace()
        if (current == ']') { index++; return JsonArray(values) }
        while (true) {
            values.add(value("$path[${values.size}]", depth))
            skipWhitespace()
            when (current) {
                ',' -> index++
                ']' -> { index++; return JsonArray(values) }
                else -> throw malformed()
            }
        }
    }

    private fun hex4(): Int {
        if (index + 4 > text.length) throw malformed()
        var code = 0
        repeat(4) {
            val digit = when (val ch = text[index++]) {
                in '0'..'9' -> ch - '0'
                in 'a'..'f' -> ch - 'a' + 10
                in 'A'..'F' -> ch - 'A' + 10
                else -> throw malformed()
            }
            code = code * 16 + digit
        }
        return code
    }

    private fun string(): String {
        index++
        val out = StringBuilder()
        while (true) {
            val ch = current ?: throw malformed()
            when {
                ch == '"' -> { index++; return out.toString() }
                ch == '\\' -> {
                    index++
                    val escape = current ?: throw malformed()
                    index++
                    when (escape) {
                        '"' -> out.append('"')
                        '\\' -> out.append('\\')
                        '/' -> out.append('/')
                        'b' -> out.append('\b')
                        'f' -> out.append('\u000c')
                        'n' -> out.append('\n')
                        'r' -> out.append('\r')
                        't' -> out.append('\t')
                        'u' -> {
                            val high = hex4()
                            if (high in 0xD800..0xDBFF) {
                                if (index + 2 > text.length || text[index] != '\\' || text[index + 1] != 'u') throw malformed()
                                index += 2
                                val low = hex4()
                                if (low !in 0xDC00..0xDFFF) throw malformed()
                                out.append(high.toChar()).append(low.toChar())
                            } else if (high in 0xDC00..0xDFFF) {
                                throw malformed()
                            } else out.append(high.toChar())
                        }
                        else -> throw malformed()
                    }
                }
                ch.code < 0x20 -> throw malformed()
                ch.isHighSurrogate() -> {
                    // A String handed to handle() directly may hold a lone surrogate. Bytes from the
                    // wire never do: strict UTF-8 cannot encode one.
                    if (index + 1 >= text.length || !text[index + 1].isLowSurrogate()) throw malformed()
                    out.append(ch).append(text[index + 1]); index += 2
                }
                ch.isLowSurrogate() -> throw malformed()
                else -> { out.append(ch); index++ }
            }
        }
    }

    private fun isDigit(ch: Char?) = ch != null && ch in '0'..'9'

    private fun number(): JsonValue {
        val start = index
        var integral = true
        if (current == '-') index++
        if (!isDigit(current)) throw malformed()
        if (current == '0') {
            index++
            if (isDigit(current)) throw malformed()
        } else while (isDigit(current)) index++
        if (current == '.') {
            integral = false
            index++
            if (!isDigit(current)) throw malformed()
            while (isDigit(current)) index++
        }
        if (current == 'e' || current == 'E') {
            integral = false
            index++
            if (current == '+' || current == '-') index++
            if (!isDigit(current)) throw malformed()
            while (isDigit(current)) index++
        }
        val raw = text.substring(start, index)
        if (integral) raw.toLongOrNull()?.let { return JsonInt(it) }
        return JsonNumber(raw)
    }

    private fun literal(word: String) {
        for (expected in word) {
            if (current != expected) throw malformed()
            index++
        }
    }

    fun skipWhitespace() {
        while (true) {
            val ch = current ?: return
            if (ch == ' ' || ch == '\t' || ch == '\n' || ch == '\r') index++ else return
        }
    }
}
