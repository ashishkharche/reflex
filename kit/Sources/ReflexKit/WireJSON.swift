/// Strict RFC 8259 parser for one request line. Duplicate keys are rejected at any depth
/// with their path, before any value reaches a decoder. Malformed input reports path `$`.
/// Keys are compared by their exact UTF-16 code units with no Unicode normalisation, so
/// `"\u00e9"` and `"e\u0301"` are two different keys, as on Kotlin.
public enum WireJSON {
    public static let maxDepth = 64

    /// Parses into `JSONValue`. A Swift `String`-keyed dictionary treats canonically equivalent
    /// keys as one, so an object holding two such keys (`"\u00e9"` and `"e\u0301"`, or `"K"` and
    /// `"\u212a"`) throws `json.duplicate_key` here. `Session` does not use this entry point: it
    /// keeps both keys and rejects the undeclared one with `field.unknown`, as Kotlin does.
    public static func parse(_ text: String) throws -> JSONValue {
        let tree = try parseTree(text)
        return try tree.json(path: "$")
    }

    static func parseTree(_ text: String) throws -> WireNode {
        var parser = Parser(bytes: Array(text.utf8))
        let value = try parser.value(path: "$", depth: 0)
        parser.skipWhitespace()
        guard parser.index == parser.bytes.count else { throw WireError(WireCode.malformed, "$") }
        return value
    }
}

/// A string compared and hashed by its exact UTF-16 code units. Swift `String` equality uses
/// Unicode canonical equivalence, which the wire must not.
struct ExactKey: Hashable {
    let text: String
    let units: [UInt16]
    init(_ text: String) { self.text = text; units = Array(text.utf16) }
    static func == (a: ExactKey, b: ExactKey) -> Bool { a.units == b.units }
    func hash(into hasher: inout Hasher) { hasher.combine(units) }
}

func exactlyEqual(_ a: String, _ b: String) -> Bool { a.utf16.elementsEqual(b.utf16) }

/// A parsed request value that keeps every key exactly as sent.
indirect enum WireNode {
    case scalar(JSONValue)
    case array([WireNode])
    case object(WireObject)

    var kind: String {
        switch self {
        case .scalar(let value): return value.kind
        case .array: return "array"
        case .object: return "object"
        }
    }

    init(_ value: JSONValue) {
        switch value {
        case .array(let items): self = .array(items.map(WireNode.init))
        case .object(let fields):
            var object = WireObject()
            for key in JSONValue.sortedKeys(fields.keys) { object.insert(key, WireNode(fields[key]!)) }
            self = .object(object)
        default: self = .scalar(value)
        }
    }

    func json(path: String) throws -> JSONValue {
        switch self {
        case .scalar(let value): return value
        case .array(let items): return .array(try items.enumerated().map { try $1.json(path: path + "[\($0)]") })
        case .object(let object):
            var fields: [String: JSONValue] = [:]
            for key in object.sortedKeys {
                if fields[key] != nil { throw WireError(WireCode.duplicateKey, path + "." + key) }
                fields[key] = try object[key]!.json(path: path + "." + key)
            }
            return .object(fields)
        }
    }
}

struct WireObject {
    private(set) var map: [ExactKey: WireNode] = [:]

    subscript(key: String) -> WireNode? { map[ExactKey(key)] }
    func contains(_ key: String) -> Bool { map[ExactKey(key)] != nil }
    mutating func insert(_ key: String, _ value: WireNode) { map[ExactKey(key)] = value }

    /// Keys sorted by UTF-16 code unit, the order unknown keys are reported in.
    var sortedKeys: [String] { map.keys.sorted { $0.units.lexicographicallyPrecedes($1.units) }.map(\.text) }
}

private struct Parser {
    let bytes: [UInt8]
    var index = 0

    init(bytes: [UInt8]) { self.bytes = bytes }

    private func malformed() -> WireError { WireError(WireCode.malformed, "$") }

    private var current: UInt8? { index < bytes.count ? bytes[index] : nil }

    mutating func value(path: String, depth: Int) throws -> WireNode {
        skipWhitespace()
        guard let byte = current else { throw malformed() }
        switch byte {
        case UInt8(ascii: "{"): return try object(path: path, depth: depth + 1)
        case UInt8(ascii: "["): return try array(path: path, depth: depth + 1)
        case UInt8(ascii: "\""): return .scalar(.string(try string()))
        case UInt8(ascii: "t"): try literal("true"); return .scalar(.bool(true))
        case UInt8(ascii: "f"): try literal("false"); return .scalar(.bool(false))
        case UInt8(ascii: "n"): try literal("null"); return .scalar(.null)
        case UInt8(ascii: "-"), UInt8(ascii: "0")...UInt8(ascii: "9"): return .scalar(try number())
        default: throw malformed()
        }
    }

    private mutating func object(path: String, depth: Int) throws -> WireNode {
        guard depth <= WireJSON.maxDepth else { throw WireError(WireCode.tooDeep, "$") }
        index += 1
        var fields = WireObject()
        skipWhitespace()
        if current == UInt8(ascii: "}") { index += 1; return .object(fields) }
        while true {
            skipWhitespace()
            guard current == UInt8(ascii: "\"") else { throw malformed() }
            let key = try string()
            let child = path + "." + key
            skipWhitespace()
            guard current == UInt8(ascii: ":") else { throw malformed() }
            index += 1
            if fields.contains(key) { throw WireError(WireCode.duplicateKey, child) }
            fields.insert(key, try value(path: child, depth: depth))
            skipWhitespace()
            switch current {
            case UInt8(ascii: ","): index += 1
            case UInt8(ascii: "}"): index += 1; return .object(fields)
            default: throw malformed()
            }
        }
    }

    private mutating func array(path: String, depth: Int) throws -> WireNode {
        guard depth <= WireJSON.maxDepth else { throw WireError(WireCode.tooDeep, "$") }
        index += 1
        var values: [WireNode] = []
        skipWhitespace()
        if current == UInt8(ascii: "]") { index += 1; return .array(values) }
        while true {
            values.append(try value(path: path + "[\(values.count)]", depth: depth))
            skipWhitespace()
            switch current {
            case UInt8(ascii: ","): index += 1
            case UInt8(ascii: "]"): index += 1; return .array(values)
            default: throw malformed()
            }
        }
    }

    private mutating func hex4() throws -> UInt32 {
        guard index + 4 <= bytes.count else { throw malformed() }
        var code: UInt32 = 0
        for _ in 0..<4 {
            let byte = bytes[index]
            index += 1
            let digit: UInt32
            switch byte {
            case UInt8(ascii: "0")...UInt8(ascii: "9"): digit = UInt32(byte - UInt8(ascii: "0"))
            case UInt8(ascii: "a")...UInt8(ascii: "f"): digit = UInt32(byte - UInt8(ascii: "a") + 10)
            case UInt8(ascii: "A")...UInt8(ascii: "F"): digit = UInt32(byte - UInt8(ascii: "A") + 10)
            default: throw malformed()
            }
            code = code * 16 + digit
        }
        return code
    }

    private mutating func string() throws -> String {
        index += 1
        var out = String.UnicodeScalarView()
        var run: [UInt8] = []
        // The line came from a Swift String, so byte runs are valid UTF-8.
        func flush(_ run: inout [UInt8], into out: inout String.UnicodeScalarView) throws {
            guard !run.isEmpty else { return }
            out.append(contentsOf: String(decoding: run, as: UTF8.self).unicodeScalars)
            run.removeAll(keepingCapacity: true)
        }
        while let byte = current {
            switch byte {
            case UInt8(ascii: "\""):
                index += 1
                try flush(&run, into: &out)
                return String(out)
            case UInt8(ascii: "\\"):
                try flush(&run, into: &out)
                index += 1
                guard let escape = current else { throw malformed() }
                index += 1
                switch escape {
                case UInt8(ascii: "\""): out.append("\"")
                case UInt8(ascii: "\\"): out.append("\\")
                case UInt8(ascii: "/"): out.append("/")
                case UInt8(ascii: "b"): out.append("\u{08}")
                case UInt8(ascii: "f"): out.append("\u{0C}")
                case UInt8(ascii: "n"): out.append("\n")
                case UInt8(ascii: "r"): out.append("\r")
                case UInt8(ascii: "t"): out.append("\t")
                case UInt8(ascii: "u"):
                    let high = try hex4()
                    var scalarValue = high
                    if (0xD800...0xDBFF).contains(high) {
                        guard index + 2 <= bytes.count, bytes[index] == UInt8(ascii: "\\"),
                              bytes[index + 1] == UInt8(ascii: "u") else { throw malformed() }
                        index += 2
                        let low = try hex4()
                        guard (0xDC00...0xDFFF).contains(low) else { throw malformed() }
                        scalarValue = 0x10000 + ((high - 0xD800) << 10) + (low - 0xDC00)
                    } else if (0xDC00...0xDFFF).contains(high) {
                        throw malformed()
                    }
                    guard let scalar = Unicode.Scalar(scalarValue) else { throw malformed() }
                    out.append(scalar)
                default: throw malformed()
                }
            default:
                guard byte >= 0x20 else { throw malformed() }
                run.append(byte)
                index += 1
            }
        }
        throw malformed()
    }

    private func isDigit(_ byte: UInt8?) -> Bool {
        guard let byte else { return false }
        return (UInt8(ascii: "0")...UInt8(ascii: "9")).contains(byte)
    }

    private mutating func number() throws -> JSONValue {
        let start = index
        var integral = true
        if current == UInt8(ascii: "-") { index += 1 }
        guard isDigit(current) else { throw malformed() }
        if current == UInt8(ascii: "0") {
            index += 1
            if isDigit(current) { throw malformed() }
        } else {
            while isDigit(current) { index += 1 }
        }
        if current == UInt8(ascii: ".") {
            integral = false
            index += 1
            guard isDigit(current) else { throw malformed() }
            while isDigit(current) { index += 1 }
        }
        if current == UInt8(ascii: "e") || current == UInt8(ascii: "E") {
            integral = false
            index += 1
            if current == UInt8(ascii: "+") || current == UInt8(ascii: "-") { index += 1 }
            guard isDigit(current) else { throw malformed() }
            while isDigit(current) { index += 1 }
        }
        let raw = String(decoding: bytes[start..<index], as: UTF8.self)
        if integral, let value = Int64(raw) { return .int(value) }
        return .number(raw)
    }

    private mutating func literal(_ word: String) throws {
        for expected in word.utf8 {
            guard current == expected else { throw malformed() }
            index += 1
        }
    }

    mutating func skipWhitespace() {
        while let byte = current, byte == 0x20 || byte == 0x09 || byte == 0x0A || byte == 0x0D { index += 1 }
    }
}
