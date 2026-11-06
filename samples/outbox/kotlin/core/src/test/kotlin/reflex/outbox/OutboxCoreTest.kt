package reflex.outbox

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import reflex.outbox.OutboxViewModel.Action
import reflex.outbox.OutboxViewModel.Status

class OutboxCoreTest {
    private val start = 1_800_000_000_000L
    private lateinit var clock: FakeClock
    private lateinit var network: FlakyNetwork
    private lateinit var outbox: OutboxViewModel

    @Before fun setUp() {
        clock = FakeClock(start)
        network = FlakyNetwork()
        outbox = OutboxViewModel(clock, network)
    }

    @Test fun backoffDoublesCapsAndGivesUp() {
        assertEquals(listOf(1_000L, 2_000L, 4_000L, 8_000L, 16_000L, 30_000L), (1..6).map(Backoff::delayAfterAttempt))
        network.enqueue(List(7) { FlakyNetwork.Outcome.TIMEOUT })
        outbox.send(Action.Enqueue("a", "hi"))
        val schedule = mutableListOf<Long>()
        clock.advance(0, outbox)
        while (true) {
            val wake = outbox.nextWakeAt ?: break
            schedule.add(wake - start)
            clock.advance(wake - clock.now, outbox)
        }
        assertEquals(listOf(1_000L, 3_000L, 7_000L, 15_000L, 31_000L, 61_000L), schedule)
        assertEquals(Status.FAILED, outbox.state.items[0].status)
        assertEquals(7, outbox.state.items[0].attempts)
        assertEquals("timeout", outbox.state.items[0].lastError)
        assertEquals(7, network.requests)
    }

    @Test fun lostReplyIsDedupedByIdempotencyKey() {
        network.enqueue(listOf(FlakyNetwork.Outcome.LOST))
        outbox.send(Action.Enqueue("a", "hi"))
        clock.advance(0, outbox)
        assertEquals(Status.RETRYING, outbox.state.items[0].status)
        clock.advance(1_000, outbox)
        assertEquals(Status.SENT, outbox.state.items[0].status)
        assertEquals("duplicate", outbox.state.items[0].ack)
        assertEquals(listOf("a"), network.stored)
        assertEquals(2, network.requests)
    }

    @Test fun clientDedupAndValidation() {
        outbox.send(Action.Enqueue("a", "one"))
        outbox.send(Action.Enqueue("a", "two"))
        assertEquals(1, outbox.state.items.size)
        assertEquals(1, outbox.state.deduped)
        outbox.send(Action.Enqueue("bad key", ""))
        assertEquals(OutboxViewModel.KEY_ERROR, outbox.state.error)
        outbox.send(Action.Enqueue("b", "é".repeat(281)))
        assertEquals(OutboxViewModel.BODY_ERROR, outbox.state.error)
        outbox.send(Action.Enqueue("c", "😀".repeat(280)))
        assertNull(outbox.state.error)
    }

    @Test fun rejectedFailsAndRetryResets() {
        network.enqueue(listOf(FlakyNetwork.Outcome.REJECTED_422))
        outbox.send(Action.Enqueue("a", "hi"))
        outbox.send(Action.SyncNow)
        assertEquals(Status.FAILED, outbox.state.items[0].status)
        assertEquals("http-422", outbox.state.items[0].lastError)
        assertNull(outbox.nextWakeAt)
        outbox.send(Action.Retry("a"))
        assertEquals(Status.SENT, outbox.state.items[0].status)
        assertEquals(1, outbox.state.items[0].attempts)
    }

    @Test fun offlineHoldsThenReconnectFlushes() {
        outbox.send(Action.SetOnline(false))
        outbox.send(Action.Enqueue("a", "hi"))
        outbox.send(Action.SyncNow)
        assertEquals(OutboxViewModel.OFFLINE_ERROR, outbox.state.error)
        clock.advance(60_000, outbox)
        assertEquals(0, network.requests)
        outbox.send(Action.SetOnline(true))
        assertEquals(Status.SENT, outbox.state.items[0].status)
    }

    @Test fun syncNowIgnoresBackoffAndServerErrorsRetry() {
        network.enqueue(listOf(FlakyNetwork.Outcome.ERROR_500))
        outbox.send(Action.Enqueue("a", "hi"))
        outbox.send(Action.SyncNow)
        assertEquals(start + 1_000, outbox.state.items[0].nextAttemptAt)
        assertEquals("http-500", outbox.state.items[0].lastError)
        outbox.send(Action.SyncNow)
        assertEquals(Status.SENT, outbox.state.items[0].status)
        assertEquals("created", outbox.state.items[0].ack)
    }
}
