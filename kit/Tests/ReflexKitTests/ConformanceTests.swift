import Foundation
import XCTest
import ReflexKit

/// Runs kit/conformance/strict-decoder.json. The Kotlin kit runs the same file.
private extension Session {
    /// Sends hello unless the case sets handshake to false.
    func primed(_ item: JSONValue) -> Session {
        if item["handshake"] != false { _ = handle(#"{"op":"hello","protocol":1}"#) }
        return self
    }
}

final class ConformanceTests: XCTestCase {
    private final class Probe: Node {
        let name: String
        let schemas: [String: Schema?]
        var last: JSONValue?
        init(name: String, schemas: [String: Schema?]) { self.name = name; self.schemas = schemas }
        var state: JSONValue { last.map { ["last": $0] } ?? [:] }
        var actions: [String: NodeAction] {
            Dictionary(uniqueKeysWithValues: schemas.map { title, schema in
                (title, NodeAction(input: schema) { [unowned self] args in
                    self.last = ["action": .string(title), "input": args.json]
                })
            })
        }
    }

    static var fixtureURL: URL {
        URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().appendingPathComponent("conformance/strict-decoder.json")
    }

    private func loadFixture() throws -> JSONValue {
        try WireJSON.parse(String(contentsOf: Self.fixtureURL, encoding: .utf8))
    }

    private func describe(ok: JSONValue?, error: JSONValue?, accept: JSONValue?) -> String {
        if ok == false, case .object(let e)? = error { return "reject \(e["code"]!.wire) \(e["path"]!.wire)" }
        return "accept " + (accept?.wire ?? "")
    }

    func testSharedConformanceFixture() throws {
        let fixture = try loadFixture()
        guard case .object(let schemaMap)? = fixture["schemas"], case .object(let probeSpec)? = fixture["probe"],
              case .object(let actionSpec)? = probeSpec["actions"], case .string(let probeName)? = probeSpec["name"],
              case .array(let cases)? = fixture["cases"], case .array(let matcherCases)? = fixture["matcher"] else {
            return XCTFail("fixture shape")
        }
        let schemas = try schemaMap.mapValues { try Schema(jsonSchema: $0) }
        for (name, schema) in schemaMap {
            XCTAssertEqual(schemas[name]!.jsonSchema, schema, "schema \(name) round trip")
        }
        var probeSchemas: [String: Schema?] = [:]
        for (action, ref) in actionSpec {
            if case .string(let schemaName) = ref { probeSchemas[action] = schemas[schemaName]! } else { probeSchemas[action] = .some(nil) }
        }
        var report: [String] = []
        var passed = 0
        for item in cases {
            guard case .string(let id)? = item["id"], case .string(let finding)? = item["finding"] else { return XCTFail("case id") }
            let probe = Probe(name: probeName, schemas: probeSchemas)
            let session = Session(sample: "conformance", root: { probe })
            if item["handshake"] != false { _ = session.handle(#"{"op":"hello","protocol":1}"#) }
            if case .string(let hex)? = item["stream"] {
                guard case .array(let wanted)? = item["wire"] else { return XCTFail("\(id): stream needs wire") }
                let node = Focus(root: probe).snapshot.wire
                let expected = wanted.map { value -> String in
                    guard case .string(let text) = value else { return "" }
                    return text.replacingOccurrences(of: "@node", with: node)
                }
                let bytes = Self.bytes(hex: hex)
                let whole = Self.serve(session, bytes, chunk: max(bytes.count, 1))
                let single = Self.serve(Session(sample: "conformance", root: { Probe(name: probeName, schemas: probeSchemas) }).primed(item), bytes, chunk: 1)
                var problems: [String] = []
                if whole != expected { problems.append("replies \(whole)") }
                if single != whole { problems.append("byte-at-a-time replies differ: \(single)") }
                let pass = problems.isEmpty
                if pass { passed += 1 } else { XCTFail("\(id): expected \(expected) got \(problems.joined(separator: "; "))") }
                let summary = whole.map { reply -> String in
                    let value = try? WireJSON.parse(reply)
                    if value?["ok"] == false, case .object(let e)? = value?["error"] { return "reject \(e["code"]!.wire) \(e["path"]!.wire)" }
                    return "ok"
                }
                report.append((["platform": "swift", "group": "stream", "id": .string(id), "finding": .string(finding),
                                "expected": .string("\(wanted.count) replies"), "got": .string(summary.joined(separator: ", ")),
                                "pass": .bool(pass), "wire": .string(whole.joined(separator: "\n"))] as JSONValue).wire)
                continue
            }
            let line: String
            if case .string(let raw)? = item["line"] {
                line = raw
            } else if case .string(let action)? = item["action"] {
                if case .string(let input)? = item["input"] {
                    line = #"{"op":"do","action":"\#(action)","input":\#(input)}"#
                } else {
                    line = #"{"op":"do","action":"\#(action)"}"#
                }
            } else { return XCTFail("\(id): no line or action") }
            let before = probe.state
            let response = session.handle(line)
            var problems: [String] = []
            var expected = "response"
            if case .array(let pair)? = item["reject"] {
                expected = "reject \(pair[0].wire) \(pair[1].wire)"
                if response["ok"] != false { problems.append("expected ok:false") }
                if response["error"] != ["code": pair[0], "path": pair[1]] { problems.append("error \(response["error"]?.wire ?? "<absent>")") }
                if probe.state != before { problems.append("state changed to \(probe.state.wire)") }
            }
            if let accept = item["accept"], case .string(let action)? = item["action"] {
                expected = "accept " + accept.wire
                if response["ok"] != true { problems.append("expected ok:true, got \(response["error"]?.wire ?? "")") }
                if probe.last != ["action": .string(action), "input": accept] { problems.append("decoded \(probe.last?.wire ?? "nothing")") }
            }
            if let partial = item["response"], let problem = Expect.mismatch(response, partial) {
                problems.append(problem)
            }
            let got = describe(ok: response["ok"], error: response["error"], accept: probe.last?["input"])
            let pass = problems.isEmpty
            if pass { passed += 1 } else { XCTFail("\(id): expected \(expected) got \(got): \(problems.joined(separator: "; "))") }
            report.append((["platform": "swift", "group": "decoder", "id": .string(id), "finding": .string(finding),
                            "expected": .string(expected), "got": .string(got), "pass": .bool(pass),
                            "wire": .string(response.wire)] as JSONValue).wire)
        }
        for item in matcherCases {
            guard case .string(let id)? = item["id"], case .string(let finding)? = item["finding"],
                  let actual = item["actual"], let expected = item["expected"], case .bool(let want)? = item["match"] else {
                return XCTFail("matcher case shape")
            }
            let got = Expect.matches(actual, expected)
            let pass = got == want
            if pass { passed += 1 } else { XCTFail("\(id): Expect.matches expected \(want) got \(got)") }
            report.append((["platform": "swift", "group": "matcher", "id": .string(id), "finding": .string(finding),
                            "expected": .string(want ? "match" : "no match"), "got": .string(got ? "match" : "no match"),
                            "pass": .bool(pass)] as JSONValue).wire)
        }
        print("CONFORMANCE platform=swift cases=\(cases.count + matcherCases.count) passed=\(passed)")
        if let dir = ProcessInfo.processInfo.environment["REFLEX_CONFORMANCE_REPORT"] {
            try FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
            try (report.joined(separator: "\n") + "\n").write(toFile: dir + "/swift.ndjson", atomically: true, encoding: .utf8)
        }
    }

    private static func bytes(hex: String) -> [UInt8] {
        let digits = Array(hex.utf8)
        return stride(from: 0, to: digits.count, by: 2).map { UInt8(String(decoding: digits[$0..<$0 + 2], as: UTF8.self), radix: 16)! }
    }

    /// Frames `bytes` in chunks of `chunk` and returns each reply exactly as serveStandardIO writes it.
    private static func serve(_ session: Session, _ bytes: [UInt8], chunk: Int) -> [String] {
        var framer = LineFramer()
        var replies: [String] = []
        var start = 0
        while start < bytes.count {
            let end = min(start + chunk, bytes.count)
            for line in framer.push(bytes[start..<end]) { replies.append(session.handle(bytes: line).wire) }
            start = end
        }
        if let last = framer.finish() { replies.append(session.handle(bytes: last).wire) }
        return replies
    }

    func testStrictUTF8() {
        XCTAssertTrue(StrictUTF8.isValid(Array("caf\u{e9} \u{1F600}".utf8)))
        XCTAssertFalse(StrictUTF8.isValid([0xC0, 0xAF]))
        XCTAssertFalse(StrictUTF8.isValid([0xED, 0xA0, 0x80]))
        XCTAssertFalse(StrictUTF8.isValid([0xF4, 0x90, 0x80, 0x80]))
        XCTAssertFalse(StrictUTF8.isValid([0xE2, 0x82]))
    }

    func testPublicParseRejectsEquivalentKeys() {
        XCTAssertThrowsError(try WireJSON.parse(#"{"\u00e9":1,"e\u0301":2}"#)) { error in
            XCTAssertEqual(error as? WireError, WireError(WireCode.duplicateKey, "$.\u{e9}"))
        }
    }

    func testCanonicalWire() throws {
        let value = try WireJSON.parse(#"{"b":[1,-0,9223372036854775807,1.50e3],"a":"q\"\\\n\u0001’","c":{"z":null,"y":true}}"#)
        XCTAssertEqual(value.wire, #"{"a":"q\"\\\n\u0001’","b":[1,0,9223372036854775807,1.50e3],"c":{"y":true,"z":null}}"#)
    }

    func testMismatchIsReadable() throws {
        let actual = try WireJSON.parse(#"{"ok":true,"node":{"state":{"saved":false}}}"#)
        let expected = try WireJSON.parse(#"{"ok":true,"node":{"state":{"saved":1}}}"#)
        XCTAssertEqual(Expect.mismatch(actual, expected), "$.node.state.saved expected=1 (integer) actual=false (boolean)")
    }

    func testTypedAccessors() throws {
        let schema = Schema([.required("n", .int64), .optional("s", .string), .optional("b", .bool),
                             .optional("o", .object(Schema([.required("k", .string)]))), .optional("xs", .array(.int64))])
        let args = try schema.decode(WireJSON.parse(#"{"n":4294967296,"b":false,"o":{"k":"v"},"xs":[1,2]}"#), at: "$.input")
        XCTAssertEqual(args.int64("n"), 4294967296)
        XCTAssertNil(args.stringIfPresent("s"))
        XCTAssertEqual(args.bool("b"), false)
        XCTAssertEqual(args.object("o").string("k"), "v")
        XCTAssertEqual(args.int64s("xs"), [1, 2])
    }
}
