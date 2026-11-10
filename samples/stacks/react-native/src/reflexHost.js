// A minimal Reflex protocol v1 host in plain JavaScript for Node (docs/protocol/v1.md). There is no
// JavaScript ReflexKit, so this file is the part an app team writes once. It covers framing, strict
// UTF-8, strict JSON with duplicate keys and Int64 literals, hello, ls, do, int64, string and boolean
// fields and canonical output. It does not run the kit conformance file, so check new rules against
// kit/conformance/strict-decoder.json before relying on them.
class WireError extends Error {
  constructor(code, path) { super(`${code} at ${path}`); this.code = code; this.path = path; }
}

class JsonNumber {
  constructor(text) { this.text = text; this.isInteger = !/[.eE]/.test(text); }
  integer() {
    const big = BigInt(this.text);
    return big < -(2n ** 63n) || big > 2n ** 63n - 1n ? null : big;
  }
}

const int64 = ({ min, max } = {}) => ({ kind: 'integer', min, max });
const string = { kind: 'string' };
const boolean = { kind: 'boolean' };

function fieldSchema(type) {
  if (type.kind !== 'integer') return { type: type.kind };
  return { type: 'integer', format: 'int64', ...(type.min !== undefined && { minimum: type.min }), ...(type.max !== undefined && { maximum: type.max }) };
}

function schemaJson(schema) {
  const fields = { ...schema.required, ...(schema.optional || {}) };
  return {
    type: 'object',
    properties: Object.fromEntries(Object.entries(fields).map(([k, v]) => [k, fieldSchema(v)])),
    required: Object.keys(schema.required).sort(),
    additionalProperties: false,
  };
}

function decodeValue(value, type, at) {
  if (type.kind === 'integer') {
    if (!(value instanceof JsonNumber)) throw new WireError('field.type', at);
    if (!value.isInteger) throw new WireError('int.syntax', at);
    const n = value.integer();
    if (n === null || (type.min !== undefined && n < BigInt(type.min)) || (type.max !== undefined && n > BigInt(type.max))) {
      throw new WireError('int.range', at);
    }
    return n;
  }
  if (typeof value !== type.kind) throw new WireError('field.type', at);
  return value;
}

const isObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v) && !(v instanceof JsonNumber);

function decodeInput(input, schema, path) {
  if (!isObject(input)) throw new WireError('input.not_object', path);
  const fields = { ...schema.required, ...(schema.optional || {}) };
  const unknown = Object.keys(input).filter((k) => !(k in fields)).sort();
  if (unknown.length) throw new WireError('field.unknown', `${path}.${unknown[0]}`);
  const out = {};
  for (const name of Object.keys(fields).sort()) {
    const at = `${path}.${name}`;
    if (!(name in input)) {
      if (name in schema.required) throw new WireError('field.missing', at);
      continue;
    }
    out[name] = decodeValue(input[name], fields[name], at);
  }
  return out;
}

function parse(s) {
  let i = 0;
  const bad = () => { throw new WireError('json.malformed', '$'); };
  const space = () => { while (i < s.length && ' \t\n\r'.includes(s[i])) i++; };
  const hex = () => {
    const text = s.slice(i, i + 4);
    if (!/^[0-9a-fA-F]{4}$/.test(text)) bad();
    i += 4;
    return parseInt(text, 16);
  };
  const str = () => {
    i++;
    let out = '';
    for (;;) {
      if (i >= s.length) bad();
      const unit = s.charCodeAt(i);
      if (unit === 0x22) { i++; return out; }
      if (unit < 0x20) bad();
      if (unit !== 0x5c) { out += s[i++]; continue; }
      i++;
      const e = s[i++];
      const simple = { '"': '"', '\\': '\\', '/': '/', b: '\b', f: '\f', n: '\n', r: '\r', t: '\t' };
      if (e in simple) out += simple[e];
      else if (e === 'u') {
        const high = hex();
        if (high >= 0xdc00 && high <= 0xdfff) bad();
        if (high >= 0xd800 && high <= 0xdbff) {
          if (s.slice(i, i + 2) !== '\\u') bad();
          i += 2;
          const low = hex();
          if (low < 0xdc00 || low > 0xdfff) bad();
          out += String.fromCharCode(high, low);
        } else out += String.fromCharCode(high);
      } else bad();
    }
  };
  const value = (path, depth) => {
    space();
    if (i >= s.length) bad();
    const c = s[i];
    if (c === '{' || c === '[') {
      if (depth + 1 > 64) throw new WireError('json.depth', '$');
      return c === '{' ? object(path, depth + 1) : array(path, depth + 1);
    }
    if (c === '"') return str();
    for (const [word, v] of [['true', true], ['false', false], ['null', null]]) {
      if (s.startsWith(word, i)) { i += word.length; return v; }
    }
    const m = /-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?/y;
    m.lastIndex = i;
    const found = m.exec(s);
    if (!found || found[0] === '') bad();
    i += found[0].length;
    return new JsonNumber(found[0]);
  };
  const object = (path, depth) => {
    i++;
    const out = Object.create(null);
    space();
    if (s[i] === '}') { i++; return out; }
    for (;;) {
      space();
      if (s[i] !== '"') bad();
      const key = str();
      if (Object.prototype.hasOwnProperty.call(out, key)) throw new WireError('json.duplicate_key', `${path}.${key}`);
      space();
      if (s[i] !== ':') bad();
      i++;
      out[key] = value(`${path}.${key}`, depth);
      space();
      if (s[i] === ',') { i++; continue; }
      if (s[i] === '}') { i++; return out; }
      bad();
    }
  };
  const array = (path, depth) => {
    i++;
    const out = [];
    space();
    if (s[i] === ']') { i++; return out; }
    for (;;) {
      out.push(value(`${path}[${out.length}]`, depth));
      space();
      if (s[i] === ',') { i++; continue; }
      if (s[i] === ']') { i++; return out; }
      bad();
    }
  };
  const result = value('$', 0);
  space();
  if (i !== s.length) bad();
  return result;
}

// Canonical output: keys sorted by UTF-16 code unit, no whitespace, only " \ and controls escaped.
function canonical(v) {
  if (typeof v === 'string') {
    const named = { '"': '\\"', '\\': '\\\\', '\n': '\\n', '\r': '\\r', '\t': '\\t', '\b': '\\b', '\f': '\\f' };
    let out = '"';
    for (const ch of v.split('')) {
      const unit = ch.charCodeAt(0);
      if (ch in named) out += named[ch];
      else if (unit < 0x20) out += `\\u${unit.toString(16).padStart(4, '0')}`;
      else out += ch;
    }
    return `${out}"`;
  }
  if (typeof v === 'boolean' || typeof v === 'bigint') return String(v);
  if (typeof v === 'number' && Number.isInteger(v)) return String(v);
  if (Array.isArray(v)) return `[${v.map(canonical).join(',')}]`;
  if (isObject(v)) return `{${Object.keys(v).sort().map((k) => `${canonical(k)}:${canonical(v[k])}`).join(',')}}`;
  throw new Error(`not a canonical value: ${v}`);
}

function snapshot(node) {
  const actions = node.actions;
  return {
    name: node.name,
    state: node.state,
    actions: Object.keys(actions).sort(),
    inputs: Object.fromEntries(Object.entries(actions).filter(([, a]) => a.input).map(([k, a]) => [k, schemaJson(a.input)])),
  };
}

const ENVELOPE = { hello: ['op', 'protocol'], ls: ['op'], do: ['op', 'action', 'input'] };

class Session {
  constructor(sample, root, kit = 'js-minimal-1') {
    this.sample = sample; this.root = root; this.kit = kit; this.negotiated = false;
    this.decoder = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true });
  }

  handle(bytes) {
    let response = {};
    try {
      let text;
      try { text = this.decoder.decode(bytes); } catch { throw new WireError('json.malformed', '$'); }
      response = { ...this.dispatch(parse(text)), ok: true };
    } catch (error) {
      if (!(error instanceof WireError)) throw error;
      response = { ok: false, error: { code: error.code, path: error.path } };
      if (error.code === 'protocol.unsupported') response.supported = [1];
    }
    response.node = snapshot(this.root());
    return canonical(response);
  }

  dispatch(request) {
    if (!isObject(request)) throw new WireError('request.not_object', '$');
    if (!('op' in request)) throw new WireError('field.missing', '$.op');
    const op = request.op;
    if (typeof op !== 'string') throw new WireError('field.type', '$.op');
    if (!Object.prototype.hasOwnProperty.call(ENVELOPE, op)) throw new WireError('request.unknown_op', '$.op');
    if (op !== 'hello' && !this.negotiated) throw new WireError('protocol.handshake_required', '$.op');
    const unknown = Object.keys(request).filter((k) => !ENVELOPE[op].includes(k)).sort();
    if (unknown.length) throw new WireError('field.unknown', `$.${unknown[0]}`);
    if (op === 'hello') {
      if (!('protocol' in request)) throw new WireError('field.missing', '$.protocol');
      if (decodeValue(request.protocol, int64(), '$.protocol') !== 1n) throw new WireError('protocol.unsupported', '$.protocol');
      this.negotiated = true;
      return { protocol: 1, sample: this.sample, kit: this.kit };
    }
    if (op === 'do') {
      if (!('action' in request)) throw new WireError('field.missing', '$.action');
      if (typeof request.action !== 'string') throw new WireError('field.type', '$.action');
      const actions = this.root().actions;
      const action = Object.prototype.hasOwnProperty.call(actions, request.action) ? actions[request.action] : null;
      if (!action) throw new WireError('action.unknown', '$.action');
      const input = 'input' in request ? request.input : {};
      if (!isObject(input)) throw new WireError('input.not_object', '$.input');
      action.run(decodeInput(input, action.input || { required: {} }, '$.input'));
    }
    return {};
  }

  // Reads LF-framed requests from stdin and writes one reply line for each until EOF.
  serveStandardIO() {
    let buffer = Buffer.alloc(0);
    process.stdin.on('data', (chunk) => {
      buffer = Buffer.concat([buffer, chunk]);
      let at;
      while ((at = buffer.indexOf(0x0a)) !== -1) {
        process.stdout.write(`${this.handle(buffer.subarray(0, at))}\n`);
        buffer = buffer.subarray(at + 1);
      }
    });
    process.stdin.on('end', () => {
      if (buffer.length) process.stdout.write(`${this.handle(buffer)}\n`);
    });
  }
}

module.exports = { Session, WireError, int64, string, boolean };
