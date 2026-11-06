import Foundation
import Dispatch

public struct Product: Codable, Equatable {
    public let id: String
    public let title: String
    public var quantity: Int
}

public protocol InventoryService {
    func products() -> [Product]
    func save(_ product: Product) throws
}

public enum InventoryError: Error, LocalizedError {
    case saveFailed, networkForbidden
    public var errorDescription: String? {
        switch self {
        case .saveFailed: return "Couldn’t save stock. Try again."
        case .networkForbidden: return "HTTP attempted: fixture missing"
        }
    }
}

// Sticky even when a service catches the error and returns a successful result.
public final class NetworkGuard {
    public private(set) var attempts = 0
    public init() {}
    public func request(_ url: String) throws {
        attempts += 1
        throw InventoryError.networkForbidden
    }
}

public final class FixtureInventoryService: InventoryService {
    private var values = [Product(id: "shirt", title: "Cotton shirt", quantity: 3),
                          Product(id: "mug", title: "Ceramic mug", quantity: 0)]
    private let fixture: String
    private let guardrail: NetworkGuard
    public init(fixture: String = "happy", guardrail: NetworkGuard) {
        self.fixture = fixture
        self.guardrail = guardrail
    }
    public func products() -> [Product] { values }
    public func save(_ product: Product) throws {
        if fixture == "http-caught" {
            let done = DispatchSemaphore(value: 0)
            let config = URLSessionConfiguration.ephemeral
            config.timeoutIntervalForRequest = 2
            let session = URLSession(configuration: config)
            session.dataTask(with: URL(string: "http://127.0.0.1:9/reflex-tripwire")!) { _, _, _ in done.signal() }.resume()
            _ = done.wait(timeout: .now() + 3)
            session.invalidateAndCancel()
        }
        if fixture == "save-failure" { throw InventoryError.saveFailed }
        if fixture == "network" { try guardrail.request("https://inventory.invalid/products") }
        if fixture == "network-caught" { try? guardrail.request("https://inventory.invalid/products") }
        if let i = values.firstIndex(where: { $0.id == product.id }) { values[i] = product }
    }
}

public final class InventoryListViewModel {
    public struct State: Codable { public var products: [Product] }
    public enum Action { case refresh }
    private enum Message { case viewAction(Action), loaded([Product]) }
    public private(set) var state: State
    private let service: InventoryService
    public init(service: InventoryService) {
        self.service = service
        state = State(products: service.products())
    }
    public func send(_ action: Action) { update(.viewAction(action)) }
    private func update(_ message: Message) {
        switch message {
        case .viewAction(.refresh): update(.loaded(service.products()))
        case .loaded(let products): state.products = products
        }
    }
}

public final class InventoryDetailViewModel {
    public struct State: Codable {
        public var product: Product
        public var saved: Bool = false
        public var error: String? = nil
    }
    public enum Action { case setQuantity(Int), decrement, save }
    private enum Message { case viewAction(Action), saved, failed(String) }
    public private(set) var state: State
    private let service: InventoryService
    public init(product: Product, service: InventoryService) {
        state = State(product: product)
        self.service = service
    }
    public func send(_ action: Action) { update(.viewAction(action)) }
    private func update(_ message: Message) {
        switch message {
        case .viewAction(.setQuantity(let value)):
            guard (0...999999).contains(value) else {
                state.error = "Quantity must be between 0 and 999999."
                return
            }
            state.product.quantity = value
            state.saved = false
            state.error = nil
        case .viewAction(.decrement):
            state.product.quantity = max(0, state.product.quantity - 1)
            state.saved = false
            state.error = nil
        case .viewAction(.save):
            do { try service.save(state.product); update(.saved) }
            catch { update(.failed(error.localizedDescription)) }
        case .saved: state.saved = true; state.error = nil
        case .failed(let error): state.saved = false; state.error = error
        }
    }
}

// Navigation is Core state, not a view operation.
public final class InventoryNavigator {
    public struct State { public var detail: InventoryDetailViewModel? }
    public enum Action { case openProduct(String), goBack }
    private enum Message { case viewAction(Action) }
    public private(set) var state = State()
    public let list: InventoryListViewModel
    private let service: InventoryService
    public init(service: InventoryService) {
        self.service = service
        list = InventoryListViewModel(service: service)
    }
    public func send(_ action: Action) { update(.viewAction(action)) }
    private func update(_ message: Message) {
        switch message {
        case .viewAction(.openProduct(let id)):
            guard state.detail == nil,
                  let product = list.state.products.first(where: { $0.id == id }) else { return }
            state.detail = InventoryDetailViewModel(product: product, service: service)
        case .viewAction(.goBack):
            state.detail = nil
            list.send(.refresh)
        }
    }
}

public final class InventoryApp {
    public let navigator: InventoryNavigator
    public init(service: InventoryService) { navigator = InventoryNavigator(service: service) }
}
