#if DEBUG
// Debug builds only. The Release configuration excludes this file and never links
// InventoryIntrospection, ReflexKit or ReflexSocketHost (scripts/check_release_exclusion.sh).
import Foundation
import InventoryIntrospection
import ReflexKit
import ReflexSocketHost

/// Starts the Reflex socket host only when the app is launched with `-reflexPort PORT`.
/// It binds 127.0.0.1. Each request runs on the main thread through the real Core, then the screen redraws.
enum DebugSocket {
    private static var host: SocketHost?

    static func startIfRequested(_ model: InventoryModel) {
        guard host == nil, let value = UserDefaults.standard.string(forKey: "reflexPort"), let port = UInt16(value) else { return }
        let session = Session(sample: "inventory", root: { AppNode(app: model.app) },
                              extras: { ["networkAttempts": JSONValue(model.network.attempts)] })
        do {
            let socket = try SocketHost(session: session, port: port) { work in
                DispatchQueue.main.sync {
                    let reply = work()
                    model.revision += 1
                    return reply
                }
            }
            socket.start()
            host = socket
            print("REFLEX LISTENING 127.0.0.1:\(socket.port)")
        } catch {
            print("REFLEX socket host failed: \(error)")
        }
    }
}
#endif
