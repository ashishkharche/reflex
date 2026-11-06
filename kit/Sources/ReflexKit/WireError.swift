/// A rejected request. `code` and `path` are identical on Swift and Kotlin for the same bytes.
/// Paths start at `$` (the request line) and use `.key` and `[index]`.
public struct WireError: Error, Equatable, Sendable {
    public let code: String
    public let path: String
    public init(_ code: String, _ path: String) {
        self.code = code
        self.path = path
    }
    public var json: JSONValue { ["code": .string(code), "path": .string(path)] }
    /// Exact code units, as on Kotlin: a path through `"\u00e9"` differs from one through `"e\u0301"`.
    public static func == (lhs: WireError, rhs: WireError) -> Bool {
        exactlyEqual(lhs.code, rhs.code) && exactlyEqual(lhs.path, rhs.path)
    }
}

/// Every wire error code the kit emits. Hosts may throw `WireError` with `valueInvalid`
/// from an action or op when a well-typed value is outside the host’s accepted set.
public enum WireCode {
    public static let malformed = "json.malformed"
    public static let tooDeep = "json.depth"
    public static let duplicateKey = "json.duplicate_key"
    public static let requestNotObject = "request.not_object"
    public static let unknownOp = "request.unknown_op"
    public static let handshakeRequired = "protocol.handshake_required"
    public static let unsupportedProtocol = "protocol.unsupported"
    public static let unknownAction = "action.unknown"
    public static let inputNotObject = "input.not_object"
    public static let missing = "field.missing"
    public static let unknown = "field.unknown"
    public static let type = "field.type"
    public static let valueInvalid = "field.value"
    public static let intSyntax = "int.syntax"
    public static let intRange = "int.range"
    public static let all = [malformed, tooDeep, duplicateKey, requestNotObject, unknownOp, handshakeRequired,
                             unsupportedProtocol, unknownAction, inputNotObject, missing, unknown, type,
                             valueInvalid, intSyntax, intRange]
}
