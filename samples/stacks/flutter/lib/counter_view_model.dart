/// The counter every stack check shares, in plain Dart: 0 to 99, Decrement stops at 0 and Increment at 99.
/// No Flutter import, so the Reflex host can run it without the engine.
class CounterState {
  const CounterState(this.count);
  final int count;
}

sealed class CounterAction {
  const CounterAction();
}

class Increment extends CounterAction {
  const Increment();
}

class Decrement extends CounterAction {
  const Decrement();
}

class Reset extends CounterAction {
  const Reset();
}

class SetValue extends CounterAction {
  const SetValue(this.value);
  final int value;
}

class CounterViewModel {
  CounterState _state = const CounterState(0);
  CounterState get state => _state;

  void send(CounterAction action) {
    _state = switch (action) {
      Increment() => CounterState((_state.count + 1).clamp(0, 99)),
      Decrement() => CounterState((_state.count - 1).clamp(0, 99)),
      Reset() => const CounterState(0),
      SetValue(:final value) => CounterState(value.clamp(0, 99)),
    };
  }
}
