import XCTest
@testable import OutboxCore

final class OutboxCoreTests: XCTestCase {
    private let start: Int64 = 1_800_000_000_000
    private var clock: FakeClock!
    private var network: FlakyNetwork!
    private var outbox: OutboxViewModel!

    override func setUp() {
        clock = FakeClock(now: start)
        network = FlakyNetwork()
        outbox = OutboxViewModel(clock: clock, transport: network)
    }

    func testBackoffDoublesCapsAndGivesUp() {
        XCTAssertEqual((1...6).map(Backoff.delay(afterAttempt:)), [1_000, 2_000, 4_000, 8_000, 16_000, 30_000])
        network.enqueue(Array(repeating: .timeout, count: 7))
        outbox.send(.enqueue(key: "a", body: "hi"))
        var schedule: [Int64] = []
        clock.advance(by: 0, waking: outbox)
        while let wake = outbox.nextWakeAt {
            schedule.append(wake - start)
            clock.advance(by: wake - clock.now, waking: outbox)
        }
        XCTAssertEqual(schedule, [1_000, 3_000, 7_000, 15_000, 31_000, 61_000])
        XCTAssertEqual(outbox.state.items[0].status, .failed)
        XCTAssertEqual(outbox.state.items[0].attempts, 7)
        XCTAssertEqual(outbox.state.items[0].lastError, "timeout")
        XCTAssertEqual(network.requests, 7)
    }

    func testLostReplyIsDedupedByIdempotencyKey() {
        network.enqueue([.lost])
        outbox.send(.enqueue(key: "a", body: "hi"))
        clock.advance(by: 0, waking: outbox)
        XCTAssertEqual(outbox.state.items[0].status, .retrying)
        clock.advance(by: 1_000, waking: outbox)
        XCTAssertEqual(outbox.state.items[0].status, .sent)
        XCTAssertEqual(outbox.state.items[0].ack, "duplicate")
        XCTAssertEqual(network.stored, ["a"])
        XCTAssertEqual(network.requests, 2)
    }

    func testClientDedupAndValidation() {
        outbox.send(.enqueue(key: "a", body: "one"))
        outbox.send(.enqueue(key: "a", body: "two"))
        XCTAssertEqual(outbox.state.items.count, 1)
        XCTAssertEqual(outbox.state.deduped, 1)
        outbox.send(.enqueue(key: "bad key", body: ""))
        XCTAssertEqual(outbox.state.error, OutboxViewModel.keyError)
        outbox.send(.enqueue(key: "b", body: String(repeating: "é", count: 281)))
        XCTAssertEqual(outbox.state.error, OutboxViewModel.bodyError)
        outbox.send(.enqueue(key: "c", body: String(repeating: "😀", count: 280)))
        XCTAssertNil(outbox.state.error)
    }

    func testRejectedFailsAndRetryResets() {
        network.enqueue([.rejected422])
        outbox.send(.enqueue(key: "a", body: "hi"))
        outbox.send(.syncNow)
        XCTAssertEqual(outbox.state.items[0].status, .failed)
        XCTAssertEqual(outbox.state.items[0].lastError, "http-422")
        XCTAssertNil(outbox.nextWakeAt)
        outbox.send(.retry(key: "a"))
        XCTAssertEqual(outbox.state.items[0].status, .sent)
        XCTAssertEqual(outbox.state.items[0].attempts, 1)
    }

    func testOfflineHoldsThenReconnectFlushes() {
        outbox.send(.setOnline(false))
        outbox.send(.enqueue(key: "a", body: "hi"))
        outbox.send(.syncNow)
        XCTAssertEqual(outbox.state.error, OutboxViewModel.offlineError)
        clock.advance(by: 60_000, waking: outbox)
        XCTAssertEqual(network.requests, 0)
        outbox.send(.setOnline(true))
        XCTAssertEqual(outbox.state.items[0].status, .sent)
    }

    func testSyncNowIgnoresBackoffAndServerErrorsRetry() {
        network.enqueue([.error500])
        outbox.send(.enqueue(key: "a", body: "hi"))
        outbox.send(.syncNow)
        XCTAssertEqual(outbox.state.items[0].nextAttemptAt, start + 1_000)
        XCTAssertEqual(outbox.state.items[0].lastError, "http-500")
        outbox.send(.syncNow)
        XCTAssertEqual(outbox.state.items[0].status, .sent)
        XCTAssertEqual(outbox.state.items[0].ack, "created")
    }
}
