import 'package:counter_flutter/counter_view_model.dart';
import 'package:counter_flutter/reflex/host.dart';

const _setInput = Schema({'value': FieldType.int64(min: 0, max: 99)});

/// Adapter: it only calls send on the same ViewModel the Flutter screen uses.
class CounterNode extends Node {
  CounterNode(this.vm);
  final CounterViewModel vm;
  @override
  String get name => 'Counter';
  @override
  Map<String, Object> get state => {'count': vm.state.count};
  @override
  Map<String, NodeAction> get actions => {
        'Decrement': NodeAction((_) => vm.send(const Decrement())),
        'Increment': NodeAction((_) => vm.send(const Increment())),
        'Reset': NodeAction((_) => vm.send(const Reset())),
        'Set': NodeAction((args) => vm.send(SetValue(args['value'] as int)), input: _setInput),
      };
}

Future<void> main() async {
  final vm = CounterViewModel();
  await Session('counter', () => CounterNode(vm)).serveStandardIO();
}
