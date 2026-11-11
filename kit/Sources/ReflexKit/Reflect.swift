import Foundation

/// Reads a value’s stored properties with `Mirror` and returns the same JSON for the same state every run.
/// Hosts written by `runner/reflex_init.py` use it, so a first run needs no hand-written state mapping.
/// `@Observable` backing names lose their underscore. Closures and opaque values are left out.
public enum Reflect {
    public static func state(of value: Any, omit: Set<String> = []) -> JSONValue {
        var seen = Set<ObjectIdentifier>()
        return json(value, omit, 0, &seen) ?? .object([:])
    }

    static func json(_ value: Any, _ omit: Set<String>, _ depth: Int, _ seen: inout Set<ObjectIdentifier>) -> JSONValue? {
        switch value {
        case let v as Bool: return .bool(v)
        case let v as Int: return .int(Int64(v))
        case let v as Int64: return .int(v)
        case let v as Int32: return .int(Int64(v))
        case let v as Int16: return .int(Int64(v))
        case let v as Int8: return .int(Int64(v))
        case let v as UInt8: return .int(Int64(v))
        case let v as UInt16: return .int(Int64(v))
        case let v as UInt32: return .int(Int64(v))
        case let v as UInt: return v <= UInt(Int64.max) ? .int(Int64(v)) : .string(String(v))
        case let v as Double: return .string(String(v))
        case let v as Float: return .string(String(v))
        case let v as String: return .string(v)
        case let v as Substring: return .string(String(v))
        case let v as Character: return .string(String(v))
        case let v as Date: return .string(String(v.timeIntervalSince1970))
        case let v as URL: return .string(v.absoluteString)
        case let v as UUID: return .string(v.uuidString)
        case let v as Decimal: return .string("\(v)")
        default: break
        }
        let mirror = Mirror(reflecting: value)
        let typeName = String(describing: type(of: value))
        switch mirror.displayStyle {
        case .optional:
            guard let child = mirror.children.first else { return .null }
            return json(child.value, omit, depth, &seen)
        case .enum:
            guard let child = mirror.children.first, let label = child.label else { return .string(String(describing: value)) }
            var fields: [String: JSONValue] = ["case": .string(label)]
            if depth < 5, let payload = json(child.value, omit, depth + 1, &seen) { fields["value"] = payload }
            return .object(fields)
        case .collection, .set:
            return .array(mirror.children.prefix(100).compactMap { json($0.value, omit, depth + 1, &seen) })
        case .dictionary:
            var out: [String: JSONValue] = [:]
            for child in mirror.children.prefix(100) {
                let pair = Array(Mirror(reflecting: child.value).children)
                guard pair.count == 2 else { continue }
                let key = String(describing: pair[0].value)
                if !omit.contains(key), let v = json(pair[1].value, omit, depth + 1, &seen) { out[key] = v }
            }
            return .object(out)
        case .tuple:
            let children = Array(mirror.children)
            if children.allSatisfy({ $0.label.map { !$0.hasPrefix(".") } ?? false }) {
                var out: [String: JSONValue] = [:]
                for child in children { if let v = json(child.value, omit, depth + 1, &seen) { out[child.label!] = v } }
                return .object(out)
            }
            return .array(children.compactMap { json($0.value, omit, depth + 1, &seen) })
        case .struct, .class:
            if depth > 4 { return .string(typeName) }
            if mirror.displayStyle == .class {
                let id = ObjectIdentifier(value as AnyObject)
                if seen.contains(id) { return nil }
                seen.insert(id)
            }
            defer { if mirror.displayStyle == .class { seen.remove(ObjectIdentifier(value as AnyObject)) } }
            var fields: [String: JSONValue] = [:]
            var current: Mirror? = mirror
            while let m = current {
                for child in m.children {
                    guard var label = child.label, !label.hasPrefix("$"), !label.hasPrefix("_$") else { continue }
                    if label.hasPrefix("_") { label.removeFirst() }
                    if omit.contains(label) || fields[label] != nil { continue }
                    if let v = json(child.value, omit, depth + 1, &seen) { fields[label] = v }
                }
                current = m.superclassMirror
            }
            return fields.isEmpty ? .string(typeName) : .object(fields)
        default:
            return nil
        }
    }
}
