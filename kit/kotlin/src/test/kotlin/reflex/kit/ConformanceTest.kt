package reflex.kit

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.fail
import org.junit.Test
import java.io.File

/** Runs kit/conformance/strict-decoder.json. The Swift kit runs the same file. */
class ConformanceTest {
    private class Probe(override val name: String, private val schemas: Map<String, Schema?>) : Node {
        var last: JsonValue? = null
        override val state: JsonValue get() = jsonObject("last" to last)
        override val actions: Map<String, NodeAction> get() = schemas.mapValues { (title, schema) ->
            NodeAction(schema) { args -> last = jsonObject("action" to title.json, "input" to args.json) }
        }
    }

    private fun fixture(): JsonValue = WireJson.parse(File(System.getProperty("reflex.conformance")).readText(Charsets.UTF_8))

    private fun str(value: JsonValue?) = (value as JsonString).value

    private fun describe(response: JsonValue, accept: JsonValue?): String {
        val error = response["error"]
        return if (response["ok"] == JsonBool(false) && error != null) "reject ${error["code"]!!.wire} ${error["path"]!!.wire}"
        else "accept " + (accept?.wire ?: "")
    }

    @Test fun sharedConformanceFixture() {
        val root = fixture()
        val schemaMap = (root["schemas"] as JsonObject).fields
        val schemas = schemaMap.mapValues { Schema.fromJsonSchema(it.value) }
        schemaMap.forEach { (name, schema) -> assertEquals("schema $name round trip", schema, schemas.getValue(name).jsonSchema) }
        val probeSpec = root["probe"] as JsonObject
        val probeSchemas = (probeSpec["actions"] as JsonObject).fields.mapValues { (_, ref) ->
            if (ref is JsonString) schemas.getValue(ref.value) else null
        }
        val report = mutableListOf<String>()
        val failures = mutableListOf<String>()
        var passed = 0
        val cases = (root["cases"] as JsonArray).items
        val matcherCases = (root["matcher"] as JsonArray).items
        for (item in cases) {
            val id = str(item["id"])
            val probe = Probe(str(probeSpec["name"]), probeSchemas)
            val session = Session("conformance", { probe })
            if (item["handshake"] != JsonBool(false)) session.handle("""{"op":"hello","protocol":1}""")
            val hex = item["stream"]
            if (hex != null) {
                val wanted = (item["wire"] as JsonArray).items
                val node = Focus(probe).snapshot.wire
                val expected = wanted.map { str(it).replace("@node", node) }
                val bytes = hexBytes(str(hex))
                val whole = serve(session, bytes, maxOf(bytes.size, 1))
                val fresh = Session("conformance", { Probe(str(probeSpec["name"]), probeSchemas) })
                if (item["handshake"] != JsonBool(false)) fresh.handle("""{"op":"hello","protocol":1}""")
                val single = serve(fresh, bytes, 1)
                val problems = mutableListOf<String>()
                if (whole != expected) problems.add("replies $whole")
                if (single != whole) problems.add("byte-at-a-time replies differ: $single")
                val pass = problems.isEmpty()
                if (pass) passed++ else failures.add("$id: expected $expected got ${problems.joinToString("; ")}")
                val summary = whole.map { reply ->
                    val value = WireJson.parse(reply)
                    val error = value["error"]
                    if (value["ok"] == JsonBool(false) && error != null) "reject ${error["code"]!!.wire} ${error["path"]!!.wire}" else "ok"
                }
                report.add(jsonObject("platform" to "kotlin".json, "group" to "stream".json, "id" to id.json,
                    "finding" to item["finding"], "expected" to "${wanted.size} replies".json,
                    "got" to summary.joinToString(", ").json, "pass" to pass.json, "wire" to whole.joinToString("\n").json).wire)
                continue
            }
            val line = item["line"]?.let { str(it) } ?: run {
                val action = str(item["action"])
                item["input"]?.let { """{"op":"do","action":"$action","input":${str(it)}}""" } ?: """{"op":"do","action":"$action"}"""
            }
            val before = probe.state
            val response = session.handle(line)
            val problems = mutableListOf<String>()
            var expected = "response"
            (item["reject"] as? JsonArray)?.items?.let { pair ->
                expected = "reject ${pair[0].wire} ${pair[1].wire}"
                if (response["ok"] != JsonBool(false)) problems.add("expected ok:false")
                if (response["error"] != jsonObject("code" to pair[0], "path" to pair[1])) problems.add("error ${response["error"]?.wire}")
                if (probe.state != before) problems.add("state changed to ${probe.state.wire}")
            }
            item["accept"]?.let { accept ->
                expected = "accept " + accept.wire
                if (response["ok"] != JsonBool(true)) problems.add("expected ok:true, got ${response["error"]?.wire}")
                if (probe.last != jsonObject("action" to item["action"]!!, "input" to accept)) problems.add("decoded ${probe.last?.wire}")
            }
            item["response"]?.let { partial -> Expect.mismatch(response, partial)?.let { problems.add(it) } }
            val got = describe(response, probe.last?.get("input"))
            val pass = problems.isEmpty()
            if (pass) passed++ else failures.add("$id: expected $expected got $got: ${problems.joinToString("; ")}")
            report.add(jsonObject("platform" to "kotlin".json, "group" to "decoder".json, "id" to id.json,
                "finding" to item["finding"], "expected" to expected.json, "got" to got.json, "pass" to pass.json,
                "wire" to response.wire.json).wire)
        }
        for (item in matcherCases) {
            val id = str(item["id"])
            val want = (item["match"] as JsonBool).value
            val got = Expect.matches(item["actual"]!!, item["expected"]!!)
            val pass = got == want
            if (pass) passed++ else failures.add("$id: Expect.matches expected $want got $got")
            report.add(jsonObject("platform" to "kotlin".json, "group" to "matcher".json, "id" to id.json,
                "finding" to item["finding"], "expected" to (if (want) "match" else "no match").json,
                "got" to (if (got) "match" else "no match").json, "pass" to pass.json).wire)
        }
        println("CONFORMANCE platform=kotlin cases=${cases.size + matcherCases.size} passed=$passed")
        System.getenv("REFLEX_CONFORMANCE_REPORT")?.let { dir ->
            File(dir).mkdirs()
            File(dir, "kotlin.ndjson").writeText(report.joinToString("\n") + "\n", Charsets.UTF_8)
        }
        if (failures.isNotEmpty()) fail(failures.joinToString("\n"))
    }

    private fun hexBytes(hex: String) = ByteArray(hex.length / 2) { hex.substring(it * 2, it * 2 + 2).toInt(16).toByte() }

    /** Frames [bytes] in chunks of [chunk] and returns each reply exactly as serveStandardIO writes it. */
    private fun serve(session: Session, bytes: ByteArray, chunk: Int): List<String> {
        val framer = LineFramer()
        val replies = mutableListOf<String>()
        var start = 0
        while (start < bytes.size) {
            val end = minOf(start + chunk, bytes.size)
            framer.push(bytes.copyOfRange(start, end)).forEach { replies.add(session.handle(it).wire) }
            start = end
        }
        framer.finish()?.let { replies.add(session.handle(it).wire) }
        return replies
    }

    @Test fun strictUtf8() {
        assertEquals(true, StrictUtf8.isValid("caf\u00e9 \ud83d\ude00".toByteArray(Charsets.UTF_8)))
        for (bad in listOf(byteArrayOf(0xC0.toByte(), 0xAF.toByte()), byteArrayOf(0xED.toByte(), 0xA0.toByte(), 0x80.toByte()),
            byteArrayOf(0xF4.toByte(), 0x90.toByte(), 0x80.toByte(), 0x80.toByte()), byteArrayOf(0xE2.toByte(), 0x82.toByte()))) {
            assertEquals(false, StrictUtf8.isValid(bad))
        }
    }

    @Test fun loneSurrogateInStringArgument() {
        val response = Session("conformance", { Probe("Probe", emptyMap()) }).handle("{\"op\":\"ls\",\"x\":\"\ud800\"}")
        assertEquals(jsonObject("code" to "json.malformed".json, "path" to "$".json), response["error"])
    }

    @Test fun canonicalWire() {
        val value = WireJson.parse("""{"b":[1,-0,9223372036854775807,1.50e3],"a":"q\"\\\n\u0001’","c":{"z":null,"y":true}}""")
        assertEquals("""{"a":"q\"\\\n\u0001’","b":[1,0,9223372036854775807,1.50e3],"c":{"y":true,"z":null}}""", value.wire)
    }

    @Test fun mismatchIsReadable() {
        val actual = WireJson.parse("""{"ok":true,"node":{"state":{"saved":false}}}""")
        val expected = WireJson.parse("""{"ok":true,"node":{"state":{"saved":1}}}""")
        assertEquals("$.node.state.saved expected=1 (integer) actual=false (boolean)", Expect.mismatch(actual, expected))
    }

    @Test fun typedAccessors() {
        val schema = Schema(Field.required("n", FieldType.int64), Field.optional("s", FieldType.string),
            Field.optional("b", FieldType.bool), Field.optional("o", FieldType.obj(Schema(Field.required("k", FieldType.string)))),
            Field.optional("xs", FieldType.array(FieldType.int64)))
        val args = schema.decode(WireJson.parse("""{"n":4294967296,"b":false,"o":{"k":"v"},"xs":[1,2]}"""), "$.input")
        assertEquals(4294967296L, args.int64("n"))
        assertNull(args.stringOrNull("s"))
        assertEquals(false, args.bool("b"))
        assertEquals("v", args.obj("o").string("k"))
        assertEquals(listOf(1L, 2L), args.int64s("xs"))
    }
}
