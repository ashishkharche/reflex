package reflex.kit

import java.io.ByteArrayOutputStream

/** Protocol v1 line framing over raw bytes. LF (0x0A) is the only line terminator. A CR is an
 *  ordinary byte, which RFC 8259 reads as whitespace between tokens, so a CRLF line parses and a
 *  lone CR between two objects leaves both on one line. Bytes after the last LF form one more
 *  line at EOF when there is at least one. The Swift kit frames the same bytes the same way. */
class LineFramer {
    private val pending = ByteArrayOutputStream()

    /** Appends [count] bytes of [chunk] and returns every line they complete, without the LF. */
    fun push(chunk: ByteArray, count: Int = chunk.size): List<ByteArray> {
        val lines = ArrayList<ByteArray>()
        for (i in 0 until count) {
            val byte = chunk[i]
            if (byte == 0x0A.toByte()) {
                lines.add(pending.toByteArray())
                pending.reset()
            } else pending.write(byte.toInt())
        }
        return lines
    }

    /** Call at EOF. Returns the unterminated last line, or null when nothing is left. */
    fun finish(): ByteArray? {
        if (pending.size() == 0) return null
        return pending.toByteArray().also { pending.reset() }
    }
}

/** Strict UTF-8 (RFC 3629): no overlong forms, no encoded surrogates (U+D800 to U+DFFF), nothing
 *  above U+10FFFF and no truncated sequences. The Swift kit uses the same table. */
object StrictUtf8 {
    fun decode(bytes: ByteArray): String? = if (isValid(bytes)) String(bytes, Charsets.UTF_8) else null

    fun isValid(bytes: ByteArray): Boolean {
        val n = bytes.size
        fun at(i: Int) = bytes[i].toInt() and 0xFF
        fun cont(i: Int, low: Int = 0x80, high: Int = 0xBF) = i < n && at(i) in low..high
        var i = 0
        while (i < n) {
            when (at(i)) {
                in 0x00..0x7F -> i += 1
                in 0xC2..0xDF -> { if (!cont(i + 1)) return false; i += 2 }
                0xE0 -> { if (!cont(i + 1, 0xA0) || !cont(i + 2)) return false; i += 3 }
                in 0xE1..0xEC, 0xEE, 0xEF -> { if (!cont(i + 1) || !cont(i + 2)) return false; i += 3 }
                0xED -> { if (!cont(i + 1, 0x80, 0x9F) || !cont(i + 2)) return false; i += 3 }
                0xF0 -> { if (!cont(i + 1, 0x90) || !cont(i + 2) || !cont(i + 3)) return false; i += 4 }
                in 0xF1..0xF3 -> { if (!cont(i + 1) || !cont(i + 2) || !cont(i + 3)) return false; i += 4 }
                0xF4 -> { if (!cont(i + 1, 0x80, 0x8F) || !cont(i + 2) || !cont(i + 3)) return false; i += 4 }
                else -> return false
            }
        }
        return true
    }
}
