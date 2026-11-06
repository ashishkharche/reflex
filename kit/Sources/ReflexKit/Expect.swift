/// Type-strict deep partial match used by journeys and unit tests.
/// Objects: every expected key must be present and match; extra actual keys are allowed.
/// Arrays: same length, element by element. Scalars: same JSON kind and equal value.
/// `true` never matches `1`, `"90"` never matches `90` and `90` never matches `90.0`.
/// Keys and strings compare by exact UTF-16 code units with no Unicode normalisation.
public enum Expect {
    public static func matches(_ actual: JSONValue, _ expected: JSONValue) -> Bool {
        mismatch(actual, expected) == nil
    }

    /// The first mismatch as `path expected=… actual=…`, or nil when it matches.
    public static func mismatch(_ actual: JSONValue, _ expected: JSONValue, at path: String = "$") -> String? {
        switch (expected, actual) {
        case (.object(let want), .object(let got)):
            for key in JSONValue.sortedKeys(want.keys) {
                guard let value = JSONValue.exactValue(got, key) else { return "\(path).\(key) expected=\(want[key]!.wire) actual=<absent>" }
                if let problem = mismatch(value, want[key]!, at: path + "." + key) { return problem }
            }
            return nil
        case (.array(let want), .array(let got)):
            guard want.count == got.count else {
                return "\(path) expected=\(want.count) items actual=\(got.count) items"
            }
            for (index, pair) in zip(want, got).enumerated() {
                if let problem = mismatch(pair.1, pair.0, at: "\(path)[\(index)]") { return problem }
            }
            return nil
        case (.number(let want), .number(let got)):
            return Double(want) == Double(got) ? nil : describe(path, expected, actual)
        default:
            return expected == actual ? nil : describe(path, expected, actual)
        }
    }

    private static func describe(_ path: String, _ expected: JSONValue, _ actual: JSONValue) -> String {
        "\(path) expected=\(expected.wire) (\(expected.kind)) actual=\(actual.wire) (\(actual.kind))"
    }
}
