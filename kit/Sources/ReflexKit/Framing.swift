/// Protocol v1 line framing over raw bytes. LF (0x0A) is the only line terminator. A CR is an
/// ordinary byte, which RFC 8259 reads as whitespace between tokens, so a CRLF line parses and a
/// lone CR between two objects leaves both on one line. Bytes after the last LF form one more
/// line at EOF when there is at least one. The Kotlin kit frames the same bytes the same way.
public struct LineFramer {
    private var pending: [UInt8] = []

    public init() {}

    /// Appends a chunk and returns every line it completes, without the LF.
    public mutating func push<C: Collection>(_ chunk: C) -> [[UInt8]] where C.Element == UInt8 {
        var lines: [[UInt8]] = []
        for byte in chunk {
            if byte == 0x0A {
                lines.append(pending)
                pending.removeAll(keepingCapacity: true)
            } else {
                pending.append(byte)
            }
        }
        return lines
    }

    /// Call at EOF. Returns the unterminated last line, or nil when nothing is left.
    public mutating func finish() -> [UInt8]? {
        guard !pending.isEmpty else { return nil }
        defer { pending.removeAll() }
        return pending
    }
}

/// Strict UTF-8 (RFC 3629): no overlong forms, no encoded surrogates (U+D800 to U+DFFF), nothing
/// above U+10FFFF and no truncated sequences. The Kotlin kit uses the same table.
public enum StrictUTF8 {
    public static func decode(_ bytes: [UInt8]) -> String? {
        guard isValid(bytes) else { return nil }
        return String(decoding: bytes, as: UTF8.self)
    }

    public static func isValid(_ bytes: [UInt8]) -> Bool {
        var i = 0
        let n = bytes.count
        func cont(_ at: Int, _ low: UInt8 = 0x80, _ high: UInt8 = 0xBF) -> Bool {
            at < n && bytes[at] >= low && bytes[at] <= high
        }
        while i < n {
            let b = bytes[i]
            switch b {
            case 0x00...0x7F: i += 1
            case 0xC2...0xDF: guard cont(i + 1) else { return false }; i += 2
            case 0xE0: guard cont(i + 1, 0xA0), cont(i + 2) else { return false }; i += 3
            case 0xE1...0xEC, 0xEE...0xEF: guard cont(i + 1), cont(i + 2) else { return false }; i += 3
            case 0xED: guard cont(i + 1, 0x80, 0x9F), cont(i + 2) else { return false }; i += 3
            case 0xF0: guard cont(i + 1, 0x90), cont(i + 2), cont(i + 3) else { return false }; i += 4
            case 0xF1...0xF3: guard cont(i + 1), cont(i + 2), cont(i + 3) else { return false }; i += 4
            case 0xF4: guard cont(i + 1, 0x80, 0x8F), cont(i + 2), cont(i + 3) else { return false }; i += 4
            default: return false
            }
        }
        return true
    }
}
