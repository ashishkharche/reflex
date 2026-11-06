package reflex.kit

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

// Compiles the kit/README.md adoption snippet against stand-in app types.
private class FakeClock(var now: Long) { fun advance(ms: Long) { now += ms } }

private class OvenTimerViewModel(val clock: FakeClock) {
    enum class Status(val wire: String) { IDLE("idle"), RUNNING("running"), ENDED("ended") }
    data class State(val status: Status = Status.IDLE, val remainingSeconds: Long = 0, val label: String? = null, val fanOn: Boolean = false)
    sealed interface Action {
        data class Start(val seconds: Long, val label: String?, val fanOn: Boolean) : Action
        data object Skip : Action
    }
    var state = State()
        private set
    fun send(action: Action) {
        state = when (action) {
            is Action.Start -> State(Status.RUNNING, action.seconds, action.label, action.fanOn)
            Action.Skip -> state.copy(status = Status.ENDED)
        }
    }
}

private val startInput = Schema(
    Field.required("seconds", FieldType.int64(min = 1, max = 3_600)),
    Field.optional("label", FieldType.string),
    Field.optional("fanOn", FieldType.bool))

private class OvenTimerNode(private val vm: OvenTimerViewModel) : Node {
    override val name = "OvenTimer"
    override val state: JsonValue get() = jsonObject(
        "status" to vm.state.status.wire.json,
        "remainingSeconds" to vm.state.remainingSeconds.json,
        "label" to vm.state.label?.json)
    override val actions get() = mapOf(
        "Start" to NodeAction(startInput) { args ->
            vm.send(OvenTimerViewModel.Action.Start(args.int64("seconds"), args.stringOrNull("label"), args.boolOrNull("fanOn") ?: false))
        },
        "Skip" to NodeAction { vm.send(OvenTimerViewModel.Action.Skip) })
}

class AdoptionExampleTest {
    @Test fun readmeSnippet() {
        val clock = FakeClock(1_800_000_000_000L)
        val vm = OvenTimerViewModel(clock)
        val session = Session("oven-timer", { OvenTimerNode(vm) }, mapOf(
            "tick" to Session.Op(Schema(Field.required("ms", FieldType.int64(min = 0, max = 86_400_000)))) { clock.advance(it.int64("ms")) }))
        session.handle("""{"op":"hello","protocol":1}""")
        assertEquals(jsonObject("code" to "field.type".json, "path" to "$.input.seconds".json),
            session.handle("""{"op":"do","action":"Start","input":{"seconds":"90"}}""")["error"])
        assertEquals(jsonObject("code" to "int.range".json, "path" to "$.input.seconds".json),
            session.handle("""{"op":"do","action":"Start","input":{"seconds":3601}}""")["error"])
        val started = session.handle("""{"op":"do","action":"Start","input":{"seconds":90,"label":"Row"}}""")
        assertTrue(Expect.matches(started, WireJson.parse("""{"ok":true,"node":{"state":{"status":"running","remainingSeconds":90,"label":"Row"}}}""")))
        assertEquals(true.json, session.handle("""{"op":"tick","input":{"ms":1000}}""")["ok"])
        assertEquals(1_800_000_001_000L, clock.now)
    }
}
