// Checks serveStandardIO's around option with plain Node: run with `node test/around.js`.
// The state changes only after the action returns, like React state, so the reply must wait for it.
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const test = require('node:test');

const host = (around) => `
const { Session } = require(${JSON.stringify(require.resolve('../src/reflexHost'))});
let count = 0;
const node = () => ({ name: 'Later', state: { count }, actions: {
  Add: { run: () => new Promise((done) => setImmediate(() => { count += 1; done(); })) },
} });
new Session('later', node).serveStandardIO(${around});
`;

const replies = (around) => {
  const input = ['{"op":"hello","protocol":1}', '{"op":"do","action":"Add"}', '{"op":"do","action":"Add"}', '{"op":"do","action":"Nope"}', ''].join('\n');
  const run = spawnSync(process.execPath, ['-e', host(around)], { input, encoding: 'utf8' });
  assert.strictEqual(run.status, 0, run.stderr);
  return run.stdout.trim().split('\n').map((line) => JSON.parse(line));
};

test('around makes each reply wait for the work the action started', () => {
  const out = replies('{ around: (run) => run() }');
  assert.deepStrictEqual(out.map((r) => r.node.state.count), [0, 1, 2, 2]);
  assert.deepStrictEqual(out[3].error, { code: 'action.unknown', path: '$.action' });
});

test('without around the reply shows the state from before the work finished', () => {
  assert.strictEqual(replies('')[1].node.state.count, 0);
});
