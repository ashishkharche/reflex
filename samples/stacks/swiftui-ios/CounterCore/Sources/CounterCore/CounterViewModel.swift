import Observation
import UIKit

/// The counter every stack check shares: 0 to 99, Decrement stops at 0 and Increment at 99.
/// Like many SwiftUI ViewModels it lives on the main actor and does its work in a Task.
@MainActor
@Observable
public final class CounterViewModel {
    public struct State: Equatable { public var count: Int }
    public enum Action { case increment, decrement, reset, set(Int) }

    public private(set) var state = State(count: 0)
    public init() {}

    public func send(_ action: Action) {
        Task {
            await Task.yield()
            let next = Self.update(state, action)
            if next != state { UIAccessibility.post(notification: .announcement, argument: "\(next.count)") }
            state = next
        }
    }

    static func update(_ state: State, _ action: Action) -> State {
        switch action {
        case .increment: return State(count: min(state.count + 1, 99))
        case .decrement: return State(count: max(state.count - 1, 0))
        case .reset: return State(count: 0)
        case .set(let value): return State(count: min(max(value, 0), 99))
        }
    }
}
