import 'package:counter_flutter/counter_view_model.dart';
import 'package:counter_flutter/main.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('the screen shows and drives the same ViewModel the Reflex host serves', (tester) async {
    final vm = CounterViewModel();
    await tester.pumpWidget(CounterApp(vm: vm));
    await tester.tap(find.byKey(const Key('+')));
    await tester.tap(find.byKey(const Key('+')));
    await tester.tap(find.byKey(const Key('−')));
    await tester.pump();
    expect(vm.state.count, 1);
    expect(find.text('1'), findsOneWidget);
  });
}
