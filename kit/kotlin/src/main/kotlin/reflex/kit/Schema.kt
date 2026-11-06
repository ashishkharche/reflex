package reflex.kit

/** Field types the strict decoder accepts. Integers are Long (Int64) on every platform.
 *  `null` is never a valid value: an optional field is absent, not null. */
sealed class FieldType {
    data class Integer(val min: Long?, val max: Long?) : FieldType()
    object Text : FieldType()
    object Flag : FieldType()
    data class Obj(val schema: Schema) : FieldType()
    data class Arr(val items: FieldType) : FieldType()

    companion object {
        fun int64(min: Long? = null, max: Long? = null): FieldType = Integer(min, max)
        val int64: FieldType = Integer(null, null)
        val string: FieldType = Text
        val bool: FieldType = Flag
        fun obj(schema: Schema): FieldType = Obj(schema)
        fun array(items: FieldType): FieldType = Arr(items)

        fun fromJsonSchema(value: JsonValue): FieldType {
            val fields = (value as? JsonObject)?.fields ?: throw SchemaError()
            return when ((fields["type"] as? JsonString)?.value) {
                "integer" -> {
                    fun bound(key: String): Long? = fields[key]?.let { (it as? JsonInt)?.value ?: throw SchemaError() }
                    Integer(bound("minimum"), bound("maximum"))
                }
                "string" -> Text
                "boolean" -> Flag
                "object" -> Obj(Schema.fromJsonSchema(value))
                "array" -> Arr(fromJsonSchema(fields["items"] ?: throw SchemaError()))
                else -> throw SchemaError()
            }
        }
    }

    val jsonSchema: JsonValue get() = when (this) {
        is Integer -> jsonObject("type" to "integer".json, "format" to "int64".json,
            "minimum" to min?.json, "maximum" to max?.json)
        Text -> jsonObject("type" to "string".json)
        Flag -> jsonObject("type" to "boolean".json)
        is Obj -> schema.jsonSchema
        is Arr -> jsonObject("type" to "array".json, "items" to items.jsonSchema)
    }

    fun decode(value: JsonValue, path: String): JsonValue = when {
        this is Integer && value is JsonInt -> {
            if (min != null && value.value < min) throw WireError(WireCode.INT_RANGE, path)
            if (max != null && value.value > max) throw WireError(WireCode.INT_RANGE, path)
            value
        }
        this is Integer && value is JsonNumber -> {
            val fractional = value.raw.any { it == '.' || it == 'e' || it == 'E' }
            throw WireError(if (fractional) WireCode.INT_SYNTAX else WireCode.INT_RANGE, path)
        }
        this is Text && value is JsonString -> value
        this is Flag && value is JsonBool -> value
        this is Obj && value is JsonObject -> schema.decode(value, path).json
        this is Arr && value is JsonArray -> JsonArray(value.items.mapIndexed { i, v -> items.decode(v, "$path[$i]") })
        else -> throw WireError(WireCode.TYPE, path)
    }
}

class SchemaError : IllegalArgumentException("Unsupported JSON Schema")

data class Field(val name: String, val type: FieldType, val required: Boolean) {
    companion object {
        fun required(name: String, type: FieldType) = Field(name, type, true)
        fun optional(name: String, type: FieldType) = Field(name, type, false)
    }
}

/** A strict object shape. Decoding checks, in order: the value is an object; unknown keys
 *  (sorted by UTF-16 code unit); then each declared field sorted by name (missing, type, range),
 *  recursing into nested objects and arrays. The first failure wins. */
class Schema(fields: List<Field>) {
    constructor(vararg fields: Field) : this(fields.toList())

    val fields: List<Field> = fields.sortedBy { it.name }

    companion object {
        val empty = Schema(emptyList())

        /** Reads the subset of JSON Schema that [jsonSchema] writes. */
        fun fromJsonSchema(value: JsonValue): Schema {
            val root = (value as? JsonObject)?.fields ?: throw SchemaError()
            if (root["type"] != JsonString("object") || root["additionalProperties"] != JsonBool(false)) throw SchemaError()
            val required = root["required"]?.let { list ->
                ((list as? JsonArray) ?: throw SchemaError()).items.map { (it as? JsonString)?.value ?: throw SchemaError() }.toSet()
            } ?: emptySet()
            val properties = root["properties"]?.let { (it as? JsonObject)?.fields ?: throw SchemaError() } ?: emptyMap()
            return Schema(properties.map { (name, type) -> Field(name, FieldType.fromJsonSchema(type), name in required) })
        }
    }

    fun decode(value: JsonValue, path: String): Args {
        val values = (value as? JsonObject)?.fields ?: throw WireError(WireCode.TYPE, path)
        val declared = fields.map { it.name }.toSet()
        values.keys.sorted().firstOrNull { it !in declared }?.let { throw WireError(WireCode.UNKNOWN, "$path.$it") }
        val decoded = LinkedHashMap<String, JsonValue>()
        for (field in fields) {
            val raw = values[field.name]
            if (raw == null) {
                if (field.required) throw WireError(WireCode.MISSING, "$path.${field.name}")
                continue
            }
            decoded[field.name] = field.type.decode(raw, "$path.${field.name}")
        }
        return Args(this, decoded)
    }

    val jsonSchema: JsonValue get() = jsonObject(
        "type" to "object".json,
        "properties" to JsonObject(fields.associate { it.name to it.type.jsonSchema }),
        "required" to JsonArray(fields.filter { it.required }.map { it.name.json }),
        "additionalProperties" to false.json)

    internal fun field(name: String) = fields.firstOrNull { it.name == name }
}

/** Decoded input. Every value already matched its declared type, so accessors don’t throw
 *  wire errors. Asking for an undeclared field or the wrong type is a programming error. */
class Args(val schema: Schema, val values: Map<String, JsonValue>) {
    companion object { val empty = Args(Schema.empty, emptyMap()) }

    val json: JsonObject get() = JsonObject(values)

    private fun value(key: String): JsonValue? {
        check(schema.field(key) != null) { "ReflexKit: $key is not a declared field" }
        return values[key]
    }
    private inline fun <reified T : JsonValue> typed(key: String): T? = value(key)?.let {
        it as? T ?: error("ReflexKit: $key is ${it.kind}")
    }

    fun int64(key: String): Long = int64OrNull(key) ?: error("ReflexKit: $key is absent")
    fun int64OrNull(key: String): Long? = typed<JsonInt>(key)?.value
    fun string(key: String): String = stringOrNull(key) ?: error("ReflexKit: $key is absent")
    fun stringOrNull(key: String): String? = typed<JsonString>(key)?.value
    fun bool(key: String): Boolean = boolOrNull(key) ?: error("ReflexKit: $key is absent")
    fun boolOrNull(key: String): Boolean? = typed<JsonBool>(key)?.value
    fun obj(key: String): Args = objOrNull(key) ?: error("ReflexKit: $key is absent")
    fun objOrNull(key: String): Args? = typed<JsonObject>(key)?.let {
        Args((schema.field(key)!!.type as FieldType.Obj).schema, it.fields)
    }
    fun array(key: String): List<JsonValue> = arrayOrNull(key) ?: error("ReflexKit: $key is absent")
    fun arrayOrNull(key: String): List<JsonValue>? = typed<JsonArray>(key)?.items
    fun strings(key: String): List<String> = array(key).map { (it as JsonString).value }
    fun int64s(key: String): List<Long> = array(key).map { (it as JsonInt).value }
}
