package reflex.outbox

import reflex.kit.Field
import reflex.kit.FieldType
import reflex.kit.JsonArray
import reflex.kit.JsonValue
import reflex.kit.Node
import reflex.kit.NodeAction
import reflex.kit.Schema
import reflex.kit.Session
import reflex.kit.WireCode
import reflex.kit.WireError
import reflex.kit.json
import reflex.kit.jsonObject

// Adapter only: every closure dispatches through send. No delivery rules here.
private val enqueueInput = Schema(Field.required("key", FieldType.string), Field.required("body", FieldType.string))
private val onlineInput = Schema(Field.required("online", FieldType.bool))
private val keyInput = Schema(Field.required("key", FieldType.string))

private fun OutboxViewModel.Item.json() = jsonObject(
    "key" to key.json, "body" to body.json, "status" to status.wire.json, "attempts" to attempts.json,
    "nextAttemptAt" to nextAttemptAt?.json, "lastError" to lastError?.json, "ack" to ack?.json)

class OutboxNode(private val vm: OutboxViewModel) : Node {
    override val name = "Outbox"
    override val state: JsonValue get() = jsonObject(
        "online" to vm.state.online.json, "now" to vm.now.json, "deduped" to vm.state.deduped.json,
        "items" to JsonArray(vm.state.items.map { it.json() }), "nextWakeAt" to vm.nextWakeAt?.json, "error" to vm.state.error?.json)
    override val actions: Map<String, NodeAction> get() = buildMap {
        put("Enqueue", NodeAction(enqueueInput) { vm.send(OutboxViewModel.Action.Enqueue(it.string("key"), it.string("body"))) })
        put("SyncNow", NodeAction { vm.send(OutboxViewModel.Action.SyncNow) })
        put("SetOnline", NodeAction(onlineInput) { vm.send(OutboxViewModel.Action.SetOnline(it.bool("online"))) })
        if (vm.state.items.any { it.status == OutboxViewModel.Status.FAILED }) {
            put("Retry", NodeAction(keyInput) { vm.send(OutboxViewModel.Action.Retry(it.string("key"))) })
        }
        if (vm.state.items.any { it.status == OutboxViewModel.Status.SENT }) {
            put("PurgeSent", NodeAction { vm.send(OutboxViewModel.Action.PurgeSent) })
        }
    }
}

/** Host operations for behaviour sessions: fake time and the flaky network script. */
object OutboxOps {
    const val MAX_ADVANCE_MS = 86_400_000L

    fun make(vm: OutboxViewModel, clock: FakeClock, network: FlakyNetwork): Map<String, Session.Op> = mapOf(
        "advance" to Session.Op(Schema(Field.required("ms", FieldType.int64(min = 0, max = MAX_ADVANCE_MS)))) {
            clock.advance(it.int64("ms"), vm)
        },
        "network" to Session.Op(Schema(Field.required("script", FieldType.array(FieldType.string)))) { args ->
            val outcomes = args.strings("script").mapIndexed { index, name ->
                FlakyNetwork.Outcome.of(name) ?: throw WireError(WireCode.VALUE_INVALID, "$.input.script[$index]")
            }
            network.enqueue(outcomes)
        })

    fun server(network: FlakyNetwork): Map<String, JsonValue> = mapOf("server" to jsonObject(
        "requests" to network.requests.json, "stored" to JsonArray(network.stored.map { it.json }), "scripted" to network.scripted.json))
}
