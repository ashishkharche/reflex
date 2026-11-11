/// A minimal Reflex protocol v1 host in plain Dart (docs/protocol/v1.md). There is no Dart ReflexKit,
/// so this file is the part an app team writes once. It covers framing, strict UTF-8, strict JSON
/// with duplicate keys and Int64 literals, hello, ls, do, int64, string and bool fields and canonical
/// output. It does not run the kit conformance file, so check new rules against
/// kit/conformance/strict-decoder.json before relying on them.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

class WireError implements Exception {
  WireError(this.code, this.path);
  final String code;
  final String path;
}

/// An integer field with optional bounds, or a string or bool field.
class FieldType {
  const FieldType._(this.kind, [this.min, this.max]);
  const FieldType.int64({int? min, int? max}) : this._('integer', min, max);
  static const string = FieldType._('string');
  static const boolean = FieldType._('boolean');
  final String kind;
  final int? min;
  final int? max;

  Map<String, Object> get jsonSchema => kind == 'integer'
      ? {'type': 'integer', 'format': 'int64', if (min != null) 'minimum': min!, if (max != null) 'maximum': max!}
      : {'type': kind};
}

class Schema {
  const Schema(this.required, [this.optional = const {}]);
  final Map<String, FieldType> required;
  final Map<String, FieldType> optional;

  Map<String, Object> get jsonSchema => {
        'type': 'object',
        'properties': {for (final e in {...required, ...optional}.entries) e.key: e.value.jsonSchema},
        'required': required.keys.toList()..sort(),
        'additionalProperties': false,
      };

  Map<String, Object> decode(Object? input, String path) {
    if (input is! Map<String, Object?>) throw WireError('input.not_object', path);
    final fields = {...required, ...optional};
    final unknown = input.keys.where((k) => !fields.containsKey(k)).toList()..sort();
    if (unknown.isNotEmpty) throw WireError('field.unknown', '$path.${unknown.first}');
    final out = <String, Object>{};
    for (final name in fields.keys.toList()..sort()) {
      final at = '$path.$name';
      if (!input.containsKey(name)) {
        if (required.containsKey(name)) throw WireError('field.missing', at);
        continue;
      }
      out[name] = _value(input[name], fields[name]!, at);
    }
    return out;
  }

  static Object _value(Object? value, FieldType type, String at) {
    switch (type.kind) {
      case 'integer':
        if (value is! JsonNumber) throw WireError('field.type', at);
        if (!value.isInteger) throw WireError('int.syntax', at);
        final n = value.integer;
        if (n == null || (type.min != null && n < type.min!) || (type.max != null && n > type.max!)) {
          throw WireError('int.range', at);
        }
        return n;
      case 'string':
        if (value is! String) throw WireError('field.type', at);
        return value;
      default:
        if (value is! bool) throw WireError('field.type', at);
        return value;
    }
  }
}

/// [run] may return a Future, such as a ViewModel command that loads. The reply waits for it.
class NodeAction {
  const NodeAction(this.run, {this.input});
  final Schema? input;
  final FutureOr<void> Function(Map<String, Object> args) run;
}

abstract class Node {
  String get name;
  Map<String, Object?> get state;
  Map<String, NodeAction> get actions;

  Map<String, Object> get snapshot => {
        'name': name,
        'state': state,
        'actions': actions.keys.toList()..sort(),
        'inputs': {for (final e in actions.entries) if (e.value.input != null) e.key: e.value.input!.jsonSchema},
      };
}

/// A JSON number kept as written, so 5.0 and 1e2 stay distinct from integers.
class JsonNumber {
  JsonNumber(this.text) : isInteger = !text.contains(RegExp('[.eE]'));
  final String text;
  final bool isInteger;
  static final _low = BigInt.parse('-9223372036854775808');
  static final _high = BigInt.parse('9223372036854775807');
  int? get integer {
    final big = BigInt.parse(text);
    return big < _low || big > _high ? null : big.toInt();
  }
}

class _Parser {
  _Parser(this.s);
  final String s;
  int i = 0;

  Never _bad() => throw WireError('json.malformed', r'$');

  Object? document() {
    final value = _value(r'$', 0);
    _space();
    if (i != s.length) _bad();
    return value;
  }

  void _space() {
    while (i < s.length && ' \t\n\r'.contains(s[i])) {
      i++;
    }
  }

  Object? _value(String path, int depth) {
    _space();
    if (i >= s.length) _bad();
    final c = s[i];
    if (c == '{' || c == '[') {
      if (depth + 1 > 64) throw WireError('json.depth', r'$');
      return c == '{' ? _object(path, depth + 1) : _array(path, depth + 1);
    }
    if (c == '"') return _string();
    for (final (word, value) in [('true', true), ('false', false), ('null', null)]) {
      if (s.startsWith(word, i)) {
        i += word.length;
        return value;
      }
    }
    final match = RegExp(r'-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?').matchAsPrefix(s, i);
    if (match == null || match.end == i) _bad();
    i = match.end;
    return JsonNumber(match[0]!);
  }

  Map<String, Object?> _object(String path, int depth) {
    i++;
    final out = <String, Object?>{};
    _space();
    if (i < s.length && s[i] == '}') {
      i++;
      return out;
    }
    while (true) {
      _space();
      if (i >= s.length || s[i] != '"') _bad();
      final key = _string();
      if (out.containsKey(key)) throw WireError('json.duplicate_key', '$path.$key');
      _space();
      if (i >= s.length || s[i] != ':') _bad();
      i++;
      out[key] = _value('$path.$key', depth);
      _space();
      if (i < s.length && s[i] == ',') {
        i++;
        continue;
      }
      if (i < s.length && s[i] == '}') {
        i++;
        return out;
      }
      _bad();
    }
  }

  List<Object?> _array(String path, int depth) {
    i++;
    final out = <Object?>[];
    _space();
    if (i < s.length && s[i] == ']') {
      i++;
      return out;
    }
    while (true) {
      out.add(_value('$path[${out.length}]', depth));
      _space();
      if (i < s.length && s[i] == ',') {
        i++;
        continue;
      }
      if (i < s.length && s[i] == ']') {
        i++;
        return out;
      }
      _bad();
    }
  }

  String _string() {
    i++;
    final out = StringBuffer();
    while (true) {
      if (i >= s.length) _bad();
      final unit = s.codeUnitAt(i);
      if (unit == 0x22) {
        i++;
        return out.toString();
      }
      if (unit < 0x20) _bad();
      if (unit != 0x5c) {
        out.writeCharCode(unit);
        i++;
        continue;
      }
      i++;
      if (i >= s.length) _bad();
      final e = s[i++];
      const simple = {'"': '"', r'\': r'\', '/': '/', 'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t'};
      if (simple.containsKey(e)) {
        out.write(simple[e]);
      } else if (e == 'u') {
        final high = _hex();
        if (high >= 0xdc00 && high <= 0xdfff) _bad();
        if (high >= 0xd800 && high <= 0xdbff) {
          if (!s.startsWith(r'\u', i)) _bad();
          i += 2;
          final low = _hex();
          if (low < 0xdc00 || low > 0xdfff) _bad();
          out.writeCharCode(high);
          out.writeCharCode(low);
        } else {
          out.writeCharCode(high);
        }
      } else {
        _bad();
      }
    }
  }

  int _hex() {
    if (i + 4 > s.length) _bad();
    final value = int.tryParse(s.substring(i, i + 4), radix: 16);
    if (value == null || s.substring(i, i + 4).contains(RegExp('[^0-9a-fA-F]'))) _bad();
    i += 4;
    return value;
  }
}

/// Canonical output: keys sorted by UTF-16 code unit, no whitespace, only " \ and controls escaped.
String canonical(Object? value) {
  if (value == null) return 'null';
  if (value is String) {
    final out = StringBuffer('"');
    for (final unit in value.codeUnits) {
      const named = {0x22: r'\"', 0x5c: r'\\', 0x0a: r'\n', 0x0d: r'\r', 0x09: r'\t', 0x08: r'\b', 0x0c: r'\f'};
      if (named.containsKey(unit)) {
        out.write(named[unit]);
      } else if (unit < 0x20) {
        out.write('\\u${unit.toRadixString(16).padLeft(4, '0')}');
      } else {
        out.writeCharCode(unit);
      }
    }
    return (out..write('"')).toString();
  }
  if (value is bool || value is int) return '$value';
  if (value is List) return '[${value.map(canonical).join(',')}]';
  if (value is Map<String, Object?>) {
    final keys = value.keys.toList()..sort();
    return '{${keys.map((k) => '${canonical(k)}:${canonical(value[k])}').join(',')}}';
  }
  throw ArgumentError('not a canonical value: $value');
}

class Session {
  Session(this.sample, this.root, {this.kit = 'dart-minimal-1'});
  final String sample;
  final Node Function() root;
  final String kit;
  bool negotiated = false;

  static const _envelope = {
    'hello': {'op', 'protocol'},
    'ls': {'op'},
    'do': {'op', 'action', 'input'},
  };

  /// Answers one request line. It waits for the action's Future and then lets queued
  /// microtasks and zero-length timers run, so the reply shows settled state.
  Future<String> handle(List<int> line) async {
    final response = <String, Object>{};
    try {
      final String text;
      try {
        text = utf8.decode(line);
      } on FormatException {
        throw WireError('json.malformed', r'$');
      }
      response.addAll(await _dispatch(_Parser(text).document()));
      await settle();
      response['ok'] = true;
    } on WireError catch (error) {
      response['ok'] = false;
      response['error'] = {'code': error.code, 'path': error.path};
      if (error.code == 'protocol.unsupported') response['supported'] = [1];
    }
    response['node'] = root().snapshot;
    return canonical(response);
  }

  Future<Map<String, Object>> _dispatch(Object? request) async {
    if (request is! Map<String, Object?>) throw WireError('request.not_object', r'$');
    if (!request.containsKey('op')) throw WireError('field.missing', r'$.op');
    final op = request['op'];
    if (op is! String) throw WireError('field.type', r'$.op');
    final allowed = _envelope[op];
    if (allowed == null) throw WireError('request.unknown_op', r'$.op');
    if (op != 'hello' && !negotiated) throw WireError('protocol.handshake_required', r'$.op');
    final unknown = request.keys.where((k) => !allowed.contains(k)).toList()..sort();
    if (unknown.isNotEmpty) throw WireError('field.unknown', '\$.${unknown.first}');
    if (op == 'hello') {
      if (!request.containsKey('protocol')) throw WireError('field.missing', r'$.protocol');
      final version = Schema._value(request['protocol'], const FieldType.int64(), r'$.protocol');
      if (version != 1) throw WireError('protocol.unsupported', r'$.protocol');
      negotiated = true;
      return {'protocol': 1, 'sample': sample, 'kit': kit};
    }
    if (op == 'do') {
      if (!request.containsKey('action')) throw WireError('field.missing', r'$.action');
      final title = request['action'];
      if (title is! String) throw WireError('field.type', r'$.action');
      final action = root().actions[title];
      if (action == null) throw WireError('action.unknown', r'$.action');
      final input = request.containsKey('input') ? request['input'] : <String, Object?>{};
      if (input is! Map<String, Object?>) throw WireError('input.not_object', r'$.input');
      await action.run((action.input ?? const Schema({})).decode(input, r'$.input'));
    }
    return {};
  }

  /// Lets work the app queued run: microtasks first, then zero-length timers.
  /// Real delays or I/O still need an `eventually` step in the journey.
  static Future<void> settle() async {
    for (var i = 0; i < 3; i++) {
      await Future<void>.delayed(Duration.zero);
    }
  }

  /// Reads LF-framed requests from stdin and writes one reply line for each until EOF.
  Future<void> serveStandardIO() async {
    final buffer = <int>[];
    await for (final chunk in stdin) {
      for (final byte in chunk) {
        if (byte == 0x0a) {
          final line = List<int>.of(buffer);
          buffer.clear();
          stdout.add(utf8.encode('${await handle(line)}\n'));
        } else {
          buffer.add(byte);
        }
      }
      await stdout.flush();
    }
    if (buffer.isNotEmpty) stdout.add(utf8.encode('${await handle(buffer)}\n'));
    await stdout.flush();
  }
}

/// The fixture name. `dart` passes it as the first argument. `flutter_tester` does not pass
/// arguments to main, so a manifest gives it as `--dart-entrypoint-args=<fixture>` instead.
String fixture(List<String> args) {
  if (args.isNotEmpty) return args.first;
  const flag = '--dart-entrypoint-args=';
  for (final arg in Platform.executableArguments) {
    if (arg.startsWith(flag)) return arg.substring(flag.length);
  }
  return 'default';
}
