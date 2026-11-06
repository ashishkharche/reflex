package reflex.outbox

/** Test fixtures passed in at construction. No production endpoint exists in this sample. */
class FakeClock(now: Long) : Clock {
    override var now: Long = now
        private set

    /** Moves time forward by [ms], firing the outbox timer at every wake time on the way,
     *  the way a host’s scheduler would. */
    fun advance(ms: Long, outbox: OutboxViewModel) {
        require(ms >= 0) { "time only moves forward" }
        val target = now + ms
        var fired = 0
        while (fired < 10_000) {
            val wake = outbox.nextWakeAt ?: break
            if (wake > target) break
            now = maxOf(now, wake)
            outbox.send(OutboxViewModel.Action.Wake)
            fired++
        }
        now = target
    }
}

/** A scripted flaky network in front of a fake server that dedups by idempotency key.
 *  Each delivery consumes one scripted outcome; an empty script means `ok`. */
class FlakyNetwork : Transport {
    enum class Outcome(val wire: String) {
        /** Server stores the message (or already has it) and the reply arrives. */
        OK("ok"),
        /** Server stores the message but the reply is lost: the client sees a timeout. */
        LOST("lost"),
        /** The request never reaches the server. */
        TIMEOUT("timeout"),
        ERROR_500("500"),
        /** Another writer already created this key: the server answers 409. */
        CONFLICT_409("409"),
        REJECTED_422("422");

        companion object { fun of(wire: String) = entries.firstOrNull { it.wire == wire } }
    }

    private val storedKeys = mutableListOf<String>()
    val stored: List<String> get() = storedKeys.toList()
    var requests = 0
        private set
    private val script = ArrayDeque<Outcome>()
    val scripted: Int get() = script.size

    fun enqueue(outcomes: List<Outcome>) { script.addAll(outcomes) }

    override fun deliver(key: String, body: String): DeliveryResult {
        requests++
        return when (script.removeFirstOrNull() ?: Outcome.OK) {
            Outcome.OK -> if (key in storedKeys) DeliveryResult.Duplicate else { storedKeys.add(key); DeliveryResult.Created }
            Outcome.LOST -> { if (key !in storedKeys) storedKeys.add(key); DeliveryResult.Timeout }
            Outcome.TIMEOUT -> DeliveryResult.Timeout
            Outcome.ERROR_500 -> DeliveryResult.ServerError(500)
            Outcome.CONFLICT_409 -> { if (key !in storedKeys) storedKeys.add(key); DeliveryResult.Duplicate }
            Outcome.REJECTED_422 -> DeliveryResult.Rejected(422)
        }
    }
}
