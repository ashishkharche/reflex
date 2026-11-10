// The counter every stack check shares, in plain JavaScript: 0 to 99, Decrement stops at 0 and Increment at 99.
// No React Native import, so the Reflex host can run it in Node.
const clamp = (n) => Math.min(Math.max(n, 0), 99);

class CounterViewModel {
  constructor() {
    this.state = { count: 0 };
  }

  send(action) {
    switch (action.type) {
      case 'increment': this.state = { count: clamp(this.state.count + 1) }; break;
      case 'decrement': this.state = { count: clamp(this.state.count - 1) }; break;
      case 'reset': this.state = { count: 0 }; break;
      case 'set': this.state = { count: clamp(action.value) }; break;
      default: throw new Error(`unknown action ${action.type}`);
    }
  }
}

module.exports = { CounterViewModel };
