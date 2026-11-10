package counter.java;

/** The counter every stack check shares, written in Java: 0 to 99, Decrement stops at 0 and Increment at 99. */
public final class CounterViewModel {
    public static final class State {
        public final int count;
        State(int count) { this.count = count; }
    }

    public sealed interface Action permits Increment, Decrement, Reset, SetValue {}
    public record Increment() implements Action {}
    public record Decrement() implements Action {}
    public record Reset() implements Action {}
    public record SetValue(long value) implements Action {}

    private State state = new State(0);

    public State getState() { return state; }

    public void send(Action action) {
        if (action instanceof Increment) state = new State(Math.min(state.count + 1, 99));
        else if (action instanceof Decrement) state = new State(Math.max(state.count - 1, 0));
        else if (action instanceof Reset) state = new State(0);
        else if (action instanceof SetValue set) state = new State((int) Math.max(0, Math.min(set.value(), 99)));
    }
}
