package reflex.outbox

/** Offline outbox: messages queue locally and deliver through a [Transport] with retry,
 *  exponential backoff and an idempotency key per message. UI-free and platform-free. */

interface Clock {
    /** Milliseconds since the Unix epoch. */
    val now: Long
}

sealed interface DeliveryResult {
    data object Created : DeliveryResult
    data object Duplicate : DeliveryResult
    data object Timeout : DeliveryResult
    data class ServerError(val code: Int) : DeliveryResult
    data class Rejected(val code: Int) : DeliveryResult
}

interface Transport {
    fun deliver(key: String, body: String): DeliveryResult
}

object Backoff {
    const val BASE_MS = 1_000L
    const val CAP_MS = 30_000L
    const val MAX_ATTEMPTS = 7

    /** Delay after failed attempt [attempt] (1-based): 1 s, 2 s, 4 s … capped at 30 s. No jitter. */
    fun delayAfterAttempt(attempt: Int): Long {
        var delay = BASE_MS
        for (i in 1 until maxOf(attempt, 1)) {
            delay *= 2
            if (delay >= CAP_MS) return CAP_MS
        }
        return minOf(delay, CAP_MS)
    }
}

class OutboxViewModel(private val clock: Clock, private val transport: Transport) {
    enum class Status(val wire: String) { PENDING("pending"), RETRYING("retrying"), SENT("sent"), FAILED("failed") }

    data class Item(
        val key: String,
        val body: String,
        val status: Status,
        val attempts: Int,
        val nextAttemptAt: Long?,
        val lastError: String?,
        val ack: String?,
    )

    data class State(
        val items: List<Item> = emptyList(),
        val online: Boolean = true,
        val deduped: Int = 0,
        val error: String? = null,
    )

    sealed interface Action {
        data class Enqueue(val key: String, val body: String) : Action
        data object SyncNow : Action
        data class SetOnline(val online: Boolean) : Action
        data class Retry(val key: String) : Action
        data object PurgeSent : Action
        /** The host’s timer fired at or after [nextWakeAt]. */
        data object Wake : Action
    }

    private sealed interface Message {
        data class ViewAction(val action: Action) : Message
        data class Attempting(val key: String) : Message
        data class Delivered(val key: String, val result: DeliveryResult) : Message
    }

    companion object {
        const val MAX_BODY_CODE_POINTS = 280
        const val KEY_ERROR = "Key must be 1 to 64 letters, digits, dots, dashes or underscores."
        const val BODY_ERROR = "Message must be 280 characters or fewer."
        const val OFFLINE_ERROR = "You’re offline. Messages will send when you’re back online."
        const val RETRY_ERROR = "Only failed messages can be retried."

        internal fun isValidKey(key: String) =
            key.length in 1..64 && key.all { it in 'a'..'z' || it in 'A'..'Z' || it in '0'..'9' || it == '.' || it == '-' || it == '_' }
    }

    var state = State()
        private set

    val now: Long get() = clock.now

    /** When the host should send [Action.Wake] next, or null when nothing is waiting. */
    val nextWakeAt: Long? get() =
        if (!state.online) null
        else state.items.filter { it.status == Status.PENDING || it.status == Status.RETRYING }.mapNotNull { it.nextAttemptAt }.minOrNull()

    fun send(action: Action) = update(Message.ViewAction(action))

    /** Pure helper: a copy of [state] with one item swapped. Only [update] assigns the result. */
    private fun State.withItem(index: Int, item: Item) = copy(items = items.toMutableList().also { it[index] = item })

    private fun update(message: Message) {
        when (message) {
            is Message.ViewAction -> when (val action = message.action) {
                is Action.Enqueue -> {
                    if (!isValidKey(action.key)) { state = state.copy(error = KEY_ERROR); return }
                    if (action.body.codePointCount(0, action.body.length) > MAX_BODY_CODE_POINTS) {
                        state = state.copy(error = BODY_ERROR); return
                    }
                    state = if (state.items.any { it.key == action.key }) state.copy(error = null, deduped = state.deduped + 1)
                    else state.copy(error = null, items = state.items + Item(action.key, action.body, Status.PENDING, 0, clock.now, null, null))
                }
                Action.SyncNow -> {
                    if (!state.online) { state = state.copy(error = OFFLINE_ERROR); return }
                    state = state.copy(error = null)
                    deliver(force = true)
                }
                is Action.SetOnline -> {
                    state = state.copy(online = action.online, error = null)
                    if (action.online) deliver(force = false)
                }
                is Action.Retry -> {
                    // Always offered. Only a failed message can be retried; anything else sets RETRY_ERROR.
                    val index = state.items.indexOfFirst { it.key == action.key && it.status == Status.FAILED }
                    if (index < 0) { state = state.copy(error = RETRY_ERROR); return }
                    state = state.copy(error = null).withItem(index,
                        state.items[index].copy(status = Status.PENDING, attempts = 0, nextAttemptAt = clock.now, lastError = null))
                    if (state.online) deliver(force = false)
                }
                // Always offered. With nothing sent this is a no-op.
                Action.PurgeSent -> state = state.copy(items = state.items.filter { it.status != Status.SENT })
                Action.Wake -> deliver(force = false)
            }
            is Message.Attempting -> {
                val index = state.items.indexOfFirst { it.key == message.key }
                if (index < 0) return
                state = state.withItem(index, state.items[index].let { it.copy(attempts = it.attempts + 1) })
            }
            is Message.Delivered -> {
                val index = state.items.indexOfFirst { it.key == message.key }
                if (index < 0) return
                val item = state.items[index]
                state = state.withItem(index, when (val result = message.result) {
                    DeliveryResult.Created, DeliveryResult.Duplicate -> item.copy(status = Status.SENT,
                        ack = if (result == DeliveryResult.Created) "created" else "duplicate", nextAttemptAt = null, lastError = null)
                    is DeliveryResult.Rejected -> item.copy(status = Status.FAILED, nextAttemptAt = null, lastError = "http-${result.code}")
                    DeliveryResult.Timeout, is DeliveryResult.ServerError -> {
                        val error = if (result is DeliveryResult.ServerError) "http-${result.code}" else "timeout"
                        if (item.attempts >= Backoff.MAX_ATTEMPTS) item.copy(status = Status.FAILED, nextAttemptAt = null, lastError = error)
                        else item.copy(status = Status.RETRYING, lastError = error,
                            nextAttemptAt = clock.now + Backoff.delayAfterAttempt(item.attempts))
                    }
                })
            }
        }
    }

    /** One pass in queue order. Each waiting item is attempted at most once per pass.
     *  Reads state only. Every write goes through [update]. */
    private fun deliver(force: Boolean) {
        if (!state.online) return
        val now = clock.now
        val due = state.items.filter {
            (it.status == Status.PENDING || it.status == Status.RETRYING) && (force || (it.nextAttemptAt ?: Long.MAX_VALUE) <= now)
        }.map { it.key }
        for (key in due) {
            update(Message.Attempting(key))
            val item = state.items.firstOrNull { it.key == key } ?: continue
            update(Message.Delivered(key, transport.deliver(item.key, item.body)))
        }
    }
}
