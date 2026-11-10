#!/usr/bin/env node
// Adapter: it only calls send on the same ViewModel the React Native screen uses.
const { CounterViewModel } = require('../src/counterViewModel');
const { Session, int64 } = require('../src/reflexHost');

const setInput = { required: { value: int64({ min: 0, max: 99 }) } };
const vm = new CounterViewModel();

const counterNode = () => ({
  name: 'Counter',
  state: { count: vm.state.count },
  actions: {
    Decrement: { run: () => vm.send({ type: 'decrement' }) },
    Increment: { run: () => vm.send({ type: 'increment' }) },
    Reset: { run: () => vm.send({ type: 'reset' }) },
    Set: { input: setInput, run: (args) => vm.send({ type: 'set', value: Number(args.value) }) },
  },
});

new Session('counter', counterNode).serveStandardIO();
