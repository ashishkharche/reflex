package counter.views

/** The counter every stack check shares: 0 to 99, Decrement stops at 0 and Increment at 99. No Android or ReflexKit import. */
class CounterViewModel {
    data class State(val count: Int)
    sealed interface Action {
        data object Increment : Action
        data object Decrement : Action
        data object Reset : Action
        data class Set(val value: Long) : Action
    }

    var state = State(0)
        private set

    fun send(action: Action) {
        state = when (action) {
            Action.Increment -> State(minOf(state.count + 1, 99))
            Action.Decrement -> State(maxOf(state.count - 1, 0))
            Action.Reset -> State(0)
            is Action.Set -> State(action.value.coerceIn(0, 99).toInt())
        }
    }
}
