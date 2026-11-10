import React from 'react';
import renderer, { act } from 'react-test-renderer';
import App from '../src/App';
import { CounterViewModel } from '../src/counterViewModel';

test('the screen shows and drives the same ViewModel the Reflex host serves', () => {
  const vm = new CounterViewModel();
  let tree;
  act(() => { tree = renderer.create(<App vm={vm} />); });
  const press = (id) => act(() => { tree.root.findByProps({ testID: id }).props.onPress(); });
  press('plus');
  press('plus');
  press('minus');
  expect(vm.state.count).toBe(1);
  expect(tree.root.findByProps({ testID: 'count' }).props.children).toBe('1');
});
