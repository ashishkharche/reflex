import Foundation
import CoreFoundation
import Darwin
let suite = CommandLine.arguments[1]
let store = UserDefaults(suiteName: suite)!
let key = "reflex.canary"
let before = store.object(forKey: key)
let standardBefore = UserDefaults.standard.object(forKey: key)
store.set(42, forKey: key)
UserDefaults.standard.set(73, forKey: key)
let after = store.integer(forKey: key)
let standardAfter = UserDefaults.standard.integer(forKey: key)
let synced = store.synchronize()
let output: [String: Any] = ["before": before ?? NSNull(), "after": after,
    "standardBefore": standardBefore ?? NSNull(), "standardAfter": standardAfter, "synchronized": synced]
print(String(data: try! JSONSerialization.data(withJSONObject: output, options: [.sortedKeys]), encoding: .utf8)!)
