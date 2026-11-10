import 'package:flutter/widgets.dart';

import 'counter_view_model.dart';

void main() => runApp(CounterApp(vm: CounterViewModel()));

/// Flutter screen over the plain Dart ViewModel. The widget holds no count of its own.
class CounterApp extends StatefulWidget {
  const CounterApp({super.key, required this.vm});
  final CounterViewModel vm;

  @override
  State<CounterApp> createState() => _CounterAppState();
}

class _CounterAppState extends State<CounterApp> {
  void _send(CounterAction action) => setState(() => widget.vm.send(action));

  Widget _button(String label, CounterAction action) =>
      GestureDetector(onTap: () => _send(action), child: Text(label, key: Key(label)));

  @override
  Widget build(BuildContext context) => Directionality(
        textDirection: TextDirection.ltr,
        child: Center(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Text('${widget.vm.state.count}', key: const Key('count')),
            _button('−', const Decrement()),
            _button('+', const Increment()),
            _button('Reset', const Reset()),
          ]),
        ),
      );
}
