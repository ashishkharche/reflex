import CounterCore
import CounterIntrospection
import ReflexKit

let vm = CounterViewModel()
Session(sample: "counter", root: { CounterNode(vm: vm) }).serveStandardIO()
