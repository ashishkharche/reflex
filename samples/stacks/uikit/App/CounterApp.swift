import CounterCore
import UIKit

/// UIKit screen over the shared Core. The view holds no state of its own.
final class CounterViewController: UIViewController {
    private let vm = CounterViewModel()
    private let label = UILabel()

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        label.font = .monospacedDigitSystemFont(ofSize: 48, weight: .semibold)
        label.accessibilityIdentifier = "count"
        let minus = button("−", #selector(decrement))
        let plus = button("+", #selector(increment))
        let reset = button("Reset", #selector(resetCount))
        let stack = UIStackView(arrangedSubviews: [label, minus, plus, reset])
        stack.axis = .vertical
        stack.spacing = 12
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            stack.centerYAnchor.constraint(equalTo: view.centerYAnchor)
        ])
        render()
    }

    private func button(_ title: String, _ action: Selector) -> UIButton {
        let button = UIButton(type: .system)
        button.setTitle(title, for: .normal)
        button.addTarget(self, action: action, for: .touchUpInside)
        return button
    }

    private func render() { label.text = String(vm.state.count) }
    @objc private func increment() { vm.send(.increment); render() }
    @objc private func decrement() { vm.send(.decrement); render() }
    @objc private func resetCount() { vm.send(.reset); render() }
}

@main
final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        window = UIWindow(frame: UIScreen.main.bounds)
        window?.rootViewController = CounterViewController()
        window?.makeKeyAndVisible()
        return true
    }
}
