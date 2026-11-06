/// A parsed or built JSON value. Integers that fit in Int64 are `.int`. Any other numeric
/// literal (fraction, exponent or outside Int64) stays verbatim in `.number`, so the strict
/// accessors can tell `90`, `90.0`, `1e2` and `9223372036854775808` apart.
/// Equality and key lookup compare strings by exact UTF-16 code units, never by Unicode canonical
/// equivalence, so `"\u00e9"` and `"e\u0301"` differ here as they do on Kotlin.
public enum JSONValue: Equatable, Sendable {
    case null
    case bool(Bool)
    case int(Int64)
    case number(String)
    case string(String)
    case array([JSONValue])
    case object([String: JSONValue])

    public init(_ value: Int) { self = .int(Int64(value)) }

    /// Canonical wire form: keys sorted by UTF-16 code unit, no whitespace, minimal escapes.
    /// The Kotlin kit writes the same bytes for the same value.
    public var wire: String {
        var out = ""
        write(to: &out)
        return out
    }

    public var kind: String {
        switch self {
        case .null: return "null"
        case .bool: return "boolean"
        case .int: return "integer"
        case .number: return "number"
        case .string: return "string"
        case .array: return "array"
        case .object: return "object"
        }
    }

    public subscript(key: String) -> JSONValue? {
        if case .object(let fields) = self { return JSONValue.exactValue(fields, key) }
        return nil
    }

    /// The value stored under exactly `key`. A Swift dictionary finds canonically equivalent keys
    /// too, so the stored key is checked code unit by code unit.
    static func exactValue(_ fields: [String: JSONValue], _ key: String) -> JSONValue? {
        guard let index = fields.index(forKey: key), exactlyEqual(fields[index].key, key) else { return nil }
        return fields[index].value
    }

    public static func == (lhs: JSONValue, rhs: JSONValue) -> Bool {
        switch (lhs, rhs) {
        case (.null, .null): return true
        case (.bool(let a), .bool(let b)): return a == b
        case (.int(let a), .int(let b)): return a == b
        case (.number(let a), .number(let b)): return exactlyEqual(a, b)
        case (.string(let a), .string(let b)): return exactlyEqual(a, b)
        case (.array(let a), .array(let b)): return a.count == b.count && zip(a, b).allSatisfy { $0 == $1 }
        case (.object(let a), .object(let b)):
            guard a.count == b.count else { return false }
            return zip(sortedKeys(a.keys), sortedKeys(b.keys)).allSatisfy { left, right in
                exactlyEqual(left, right) && a[left]! == b[right]!
            }
        default: return false
        }
    }

    private func write(to out: inout String) {
        switch self {
        case .null: out += "null"
        case .bool(let value): out += value ? "true" : "false"
        case .int(let value): out += String(value)
        case .number(let raw): out += raw
        case .string(let text): JSONValue.writeString(text, to: &out)
        case .array(let values):
            out += "["
            for (index, value) in values.enumerated() {
                if index > 0 { out += "," }
                value.write(to: &out)
            }
            out += "]"
        case .object(let fields):
            out += "{"
            for (index, key) in JSONValue.sortedKeys(fields.keys).enumerated() {
                if index > 0 { out += "," }
                JSONValue.writeString(key, to: &out)
                out += ":"
                fields[key]!.write(to: &out)
            }
            out += "}"
        }
    }

    static func sortedKeys<S: Sequence>(_ keys: S) -> [String] where S.Element == String {
        keys.sorted { $0.utf16.lexicographicallyPrecedes($1.utf16) }
    }

    private static let hex = Array("0123456789abcdef")

    private static func writeString(_ text: String, to out: inout String) {
        out += "\""
        for scalar in text.unicodeScalars {
            switch scalar {
            case "\"": out += "\\\""
            case "\\": out += "\\\\"
            case "\n": out += "\\n"
            case "\r": out += "\\r"
            case "\t": out += "\\t"
            case "\u{08}": out += "\\b"
            case "\u{0C}": out += "\\f"
            default:
                if scalar.value < 0x20 {
                    out += "\\u00"
                    out.append(hex[Int(scalar.value >> 4)])
                    out.append(hex[Int(scalar.value & 0xF)])
                } else {
                    out.unicodeScalars.append(scalar)
                }
            }
        }
        out += "\""
    }
}

extension JSONValue: ExpressibleByNilLiteral, ExpressibleByBooleanLiteral, ExpressibleByIntegerLiteral,
    ExpressibleByStringLiteral, ExpressibleByArrayLiteral, ExpressibleByDictionaryLiteral {
    public init(nilLiteral: ()) { self = .null }
    public init(booleanLiteral value: Bool) { self = .bool(value) }
    public init(integerLiteral value: Int64) { self = .int(value) }
    public init(stringLiteral value: String) { self = .string(value) }
    public init(arrayLiteral elements: JSONValue...) { self = .array(elements) }
    public init(dictionaryLiteral elements: (String, JSONValue)...) {
        self = .object(Dictionary(elements, uniquingKeysWith: { _, new in new }))
    }
}
