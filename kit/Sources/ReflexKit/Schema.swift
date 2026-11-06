/// Field types the strict decoder accepts. Integers are Int64 on every platform.
/// `null` is never a valid value: an optional field is absent, not null.
public indirect enum FieldType: Sendable {
    case integer(min: Int64?, max: Int64?)
    case string
    case bool
    case object(Schema)
    case array(FieldType)

    public static var int64: FieldType { .integer(min: nil, max: nil) }
    public static func int64(min: Int64? = nil, max: Int64? = nil) -> FieldType { .integer(min: min, max: max) }

    var jsonSchema: JSONValue {
        switch self {
        case .integer(let min, let max):
            var schema: [String: JSONValue] = ["type": "integer", "format": "int64"]
            if let min { schema["minimum"] = .int(min) }
            if let max { schema["maximum"] = .int(max) }
            return .object(schema)
        case .string: return ["type": "string"]
        case .bool: return ["type": "boolean"]
        case .object(let schema): return schema.jsonSchema
        case .array(let items): return ["type": "array", "items": items.jsonSchema]
        }
    }

    init(jsonSchema: JSONValue) throws {
        guard case .object(let fields) = jsonSchema, case .string(let type)? = fields["type"] else {
            throw SchemaError.unsupported
        }
        switch type {
        case "integer":
            func bound(_ key: String) throws -> Int64? {
                guard let value = fields[key] else { return nil }
                guard case .int(let n) = value else { throw SchemaError.unsupported }
                return n
            }
            self = .integer(min: try bound("minimum"), max: try bound("maximum"))
        case "string": self = .string
        case "boolean": self = .bool
        case "object": self = .object(try Schema(jsonSchema: jsonSchema))
        case "array":
            guard let items = fields["items"] else { throw SchemaError.unsupported }
            self = .array(try FieldType(jsonSchema: items))
        default: throw SchemaError.unsupported
        }
    }

    func decode(_ value: JSONValue, at path: String) throws -> JSONValue {
        try decode(WireNode(value), at: path)
    }

    func decode(_ node: WireNode, at path: String) throws -> JSONValue {
        switch (self, node) {
        case (.integer(let min, let max), .scalar(.int(let n))):
            if let min, n < min { throw WireError(WireCode.intRange, path) }
            if let max, n > max { throw WireError(WireCode.intRange, path) }
            return .int(n)
        case (.integer, .scalar(.number(let raw))):
            let fractional = raw.contains(".") || raw.contains("e") || raw.contains("E")
            throw WireError(fractional ? WireCode.intSyntax : WireCode.intRange, path)
        case (.string, .scalar(.string(let text))):
            return .string(text)
        case (.bool, .scalar(.bool(let flag))):
            return .bool(flag)
        case (.object(let schema), .object):
            return try schema.decode(node, at: path).json
        case (.array(let items), .array(let values)):
            return .array(try values.enumerated().map { try items.decode($1, at: path + "[\($0)]") })
        default:
            throw WireError(WireCode.type, path)
        }
    }
}

public enum SchemaError: Error { case unsupported }

public struct Field: Sendable {
    public let name: String
    public let type: FieldType
    public let required: Bool

    public static func required(_ name: String, _ type: FieldType) -> Field {
        Field(name: name, type: type, required: true)
    }

    public static func optional(_ name: String, _ type: FieldType) -> Field {
        Field(name: name, type: type, required: false)
    }
}

/// A strict object shape. Decoding checks, in order: the value is an object; unknown keys
/// (sorted by UTF-16 code unit); then each declared field sorted by name (missing, type, range),
/// recursing into nested objects and arrays. The first failure wins.
public struct Schema: Sendable {
    public let fields: [Field]

    public init(_ fields: [Field]) {
        self.fields = fields.sorted { $0.name.utf16.lexicographicallyPrecedes($1.name.utf16) }
    }

    public static let empty = Schema([])

    public func decode(_ value: JSONValue, at path: String) throws -> Args {
        try decode(WireNode(value), at: path)
    }

    /// Field names match request keys by exact UTF-16 code units: `"e\u0301"` is not the
    /// declared field `"\u00e9"` and `"\u212a"` (Kelvin sign) is not `"K"`.
    func decode(_ node: WireNode, at path: String) throws -> Args {
        guard case .object(let values) = node else { throw WireError(WireCode.type, path) }
        let declared = Set(fields.map { ExactKey($0.name) })
        for key in values.sortedKeys where !declared.contains(ExactKey(key)) {
            throw WireError(WireCode.unknown, path + "." + key)
        }
        var decoded: [String: JSONValue] = [:]
        for field in fields {
            guard let raw = values[field.name] else {
                if field.required { throw WireError(WireCode.missing, path + "." + field.name) }
                continue
            }
            decoded[field.name] = try field.type.decode(raw, at: path + "." + field.name)
        }
        return Args(schema: self, values: decoded)
    }

    public var jsonSchema: JSONValue {
        var properties: [String: JSONValue] = [:]
        for field in fields { properties[field.name] = field.type.jsonSchema }
        return ["type": "object", "properties": .object(properties),
                "required": .array(fields.filter(\.required).map { .string($0.name) }),
                "additionalProperties": false]
    }

    /// Reads the subset of JSON Schema that `jsonSchema` writes.
    public init(jsonSchema: JSONValue) throws {
        guard case .object(let root) = jsonSchema, root["type"] == "object",
              root["additionalProperties"] == false else { throw SchemaError.unsupported }
        var required = Set<String>()
        if let list = root["required"] {
            guard case .array(let names) = list else { throw SchemaError.unsupported }
            for name in names {
                guard case .string(let text) = name else { throw SchemaError.unsupported }
                required.insert(text)
            }
        }
        var fields: [Field] = []
        if let properties = root["properties"] {
            guard case .object(let map) = properties else { throw SchemaError.unsupported }
            for (name, type) in map {
                fields.append(Field(name: name, type: try FieldType(jsonSchema: type), required: required.contains(name)))
            }
        }
        self.init(fields)
    }

    func field(_ name: String) -> Field? { fields.first { exactlyEqual($0.name, name) } }
}

/// Decoded input. Every value already matched its declared type, so accessors don’t throw.
/// Asking for an undeclared field or the wrong type is a programming error and traps.
public struct Args: Sendable {
    public let schema: Schema
    public let values: [String: JSONValue]

    public static let empty = Args(schema: .empty, values: [:])

    public var json: JSONValue { .object(values) }

    private func value(_ key: String, _ kind: String) -> JSONValue? {
        guard schema.field(key) != nil else { preconditionFailure("ReflexKit: \(key) is not a declared field") }
        guard let value = values[key] else { return nil }
        guard value.kind == kind else { preconditionFailure("ReflexKit: \(key) is \(value.kind), not \(kind)") }
        return value
    }

    public func int64(_ key: String) -> Int64 {
        guard let value = int64IfPresent(key) else { preconditionFailure("ReflexKit: \(key) is absent") }
        return value
    }
    public func int64IfPresent(_ key: String) -> Int64? {
        if case .int(let n)? = value(key, "integer") { return n }
        return nil
    }
    public func string(_ key: String) -> String {
        guard let value = stringIfPresent(key) else { preconditionFailure("ReflexKit: \(key) is absent") }
        return value
    }
    public func stringIfPresent(_ key: String) -> String? {
        if case .string(let text)? = value(key, "string") { return text }
        return nil
    }
    public func bool(_ key: String) -> Bool {
        guard let value = boolIfPresent(key) else { preconditionFailure("ReflexKit: \(key) is absent") }
        return value
    }
    public func boolIfPresent(_ key: String) -> Bool? {
        if case .bool(let flag)? = value(key, "boolean") { return flag }
        return nil
    }
    public func object(_ key: String) -> Args {
        guard let value = objectIfPresent(key) else { preconditionFailure("ReflexKit: \(key) is absent") }
        return value
    }
    public func objectIfPresent(_ key: String) -> Args? {
        guard case .object(let fields)? = value(key, "object"),
              case .object(let nested)? = schema.field(key)?.type else { return nil }
        return Args(schema: nested, values: fields)
    }
    public func array(_ key: String) -> [JSONValue] {
        if case .array(let items)? = value(key, "array") { return items }
        preconditionFailure("ReflexKit: \(key) is absent")
    }
    public func arrayIfPresent(_ key: String) -> [JSONValue]? {
        if case .array(let items)? = value(key, "array") { return items }
        return nil
    }
    public func strings(_ key: String) -> [String] {
        array(key).map { if case .string(let text) = $0 { return text }; preconditionFailure("ReflexKit: \(key) holds \($0.kind)") }
    }
    public func int64s(_ key: String) -> [Int64] {
        array(key).map { if case .int(let n) = $0 { return n }; preconditionFailure("ReflexKit: \(key) holds \($0.kind)") }
    }
}
