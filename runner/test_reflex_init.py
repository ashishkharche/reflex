#!/usr/bin/env python3
"""Detection and generation checks for runner/reflex_init.py on small made-up apps. No build tools needed."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reflex_init as ri  # noqa: E402


def make(root, files):
    for name, text in files.items():
        path = Path(root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return Path(root)


KOTLIN = {
    "settings.gradle.kts": 'include(":feature:home", ":core:testing")\n',
    "feature/home/build.gradle.kts": "plugins { id(\"com.android.library\") }\n",
    "feature/home/src/main/kotlin/app/home/HomeViewModel.kt": """package app.home

import androidx.lifecycle.ViewModel
class HomeViewModel @Inject constructor(
    private val repo: NewsRepository,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {
    val feed: StateFlow<List<String>> = repo.news().stateIn(viewModelScope, WhileSubscribed(5000), emptyList())
    fun follow(topicId: String, followed: Boolean) {}
    suspend fun refresh() {}
}
""",
    "feature/home/src/main/kotlin/app/home/SettingsViewModel.kt": "package app.home\nclass SettingsViewModel : ViewModel() { val x = MutableStateFlow(1) }\n",
    "feature/home/src/main/kotlin/app/home/HomeScreen.kt": "package app.home\nfun HomeScreen(vm: HomeViewModel) {}\n",
    "core/testing/src/main/kotlin/app/testing/TestNewsRepository.kt": "package app.testing\nclass TestNewsRepository : NewsRepository\n",
    "core/testing/src/main/kotlin/app/testing/Helpers.kt": "package app.testing\nclass Helpers\n",
}

FLUTTER = {
    "pubspec.yaml": "name: travel\ndependencies:\n  flutter:\n    sdk: flutter\n",
    "lib/ui/home_view_model.dart": """import 'package:flutter/foundation.dart';
import '../data/booking_repository.dart';

class HomeViewModel extends ChangeNotifier {
  HomeViewModel({required BookingRepository bookingRepository, this.title = 'Home'}) : _repo = bookingRepository {
    load = Command0(_load)..execute();
  }

  final BookingRepository _repo;
  final String title;
  late Command0 load;
  late Command1<void, int> deleteBooking;
  List<String> _items = [];

  List<String> get items => _items;
  bool get empty => _items.isEmpty;

  void select(int id) {}
  Future<void> rename(String name, bool keep) async {}
  void pick(Booking booking) {}
}
""",
    "lib/data/booking_repository.dart": "abstract class BookingRepository {}\n",
    "testing/fakes/fake_booking_repository.dart": "import 'package:travel/data/booking_repository.dart';\n\nclass FakeBookingRepository implements BookingRepository {\n}\n",
}

NODE = {
    "package.json": '{"dependencies": {"react": "19.0.0", "react-native": "0.80.0"}}\n',
    "app/context/EpisodeContext.tsx": """import { createContext, useContext, useState } from "react"
export const EpisodeContext = createContext(null)
export const EpisodeProvider = ({ children }) => {
  const [items, setItems] = useState([])
  return null
}
export const useEpisodes = () => {
  const context = useContext(EpisodeContext)
  return context
}
""",
    "app/stores/cart.ts": "import { create } from 'zustand'\nexport const useCartStore = create((set) => ({ items: [] }))\n",
    "app/screens/Home.tsx": "import { useEpisodes } from '../context/EpisodeContext'\n",
}

SWIFT = {
    "Packages/Feed/Package.swift": """// swift-tools-version: 6.0
import PackageDescription
let package = Package(
  name: "Feed",
  platforms: [.iOS(.v17)],
  products: [.library(name: "FeedKit", targets: ["Feed"])],
  targets: [.target(name: "Feed")]
)
""",
    "Packages/Feed/Sources/Feed/FeedViewModel.swift": """import Observation

@MainActor
@Observable public final class FeedViewModel {
  var items: [String] = []
  init(service: FeedService = LiveFeedService(), limit: Int = 20) {}
  func refresh() async {}
  public func clear() {}
  func open(id: String) {}
}
""",
    "Packages/Feed/Sources/Feed/EditFeedViewModel.swift": "@Observable final class EditFeedViewModel {}\n",
    "App/Home.swift": "import Feed\nlet vm = FeedViewModel()\n",
}


class DetectTest(unittest.TestCase):
    def test_stacks(self):
        for files, stack in ((KOTLIN, "kotlin"), (FLUTTER, "flutter"), (NODE, "node"), (SWIFT, "swift")):
            with tempfile.TemporaryDirectory() as tmp:
                self.assertEqual(ri.detect(make(tmp, files)), [stack])

    def test_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ri.detect(make(tmp, {"README.md": "hi"})), [])
            self.assertEqual(ri.main([tmp]), 2)


class KotlinTest(unittest.TestCase):
    def test_finds_view_model_and_test_doubles(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make(tmp, KOTLIN)
            found = ri.rank_by_use(app, ri.kotlin_candidates(app))
            self.assertEqual([c["name"] for c in found], ["HomeViewModel", "SettingsViewModel"])
            self.assertEqual(found[0]["class"], "app.home.HomeViewModel")
            self.assertEqual(ri.gradle_project(app, found[0]["file"]), ":feature:home")
            self.assertEqual(ri.kotlin_fakes(app), ["app.testing.TestNewsRepository"])
            methods = ri.kotlin_methods(ri.read(found[0]["file"]))
            self.assertEqual(methods["follow/2"], ["topicId", "followed"])
            self.assertEqual(methods["refresh/0"], [])

    def test_gradle_errors_become_one_next_step(self):
        log = "FAILURE: Build failed\n* What went wrong:\nSDK location not found. Define ANDROID_HOME\n* Try:\n"
        why = ri.gradle_error(log)
        self.assertIn("SDK location not found", why)
        self.assertIn("ANDROID_HOME", ri.kotlin_next_step(why))
        self.assertIn("JDK 17", ri.kotlin_next_step("Cannot find a Java installation matching languageVersion=17 toolchain"))
        self.assertIn("can’t run on Java 27", ri.kotlin_next_step("BUG! Unsupported class file major version 71"))
        log = ("FAIL platform=kotlin journey=probe end expected network=clean actual network=denied\n"
               "NOTE platform=kotlin network: HomeViewModel → PodcastsRepository → OkHttpClient can reach the network\n")
        self.assertIn("give HomeViewModel a test double for PodcastsRepository", ri.explain(log))

    def test_sealed_events_and_data_classes(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make(tmp, {"app/src/main/kotlin/app/Home.kt": """package app
class HomeViewModel : ViewModel() {
    fun onAction(action: HomeAction) {}
}
sealed interface HomeAction {
    data class Select(val id: String, val pinned: Boolean) : HomeAction
    data object Refresh : HomeAction
    data class Open(val item: Item) : HomeAction
}
data class Item(val id: Long, val title: String)
class Plain(val x: Int)
"""})
            self.assertEqual(ri.kotlin_events(app), {"HomeAction": ["app.Open", "app.Refresh", "app.Select"]})
            ctors = ri.kotlin_ctors(app)
            self.assertEqual(ctors["Select"], ["id", "pinned"])
            self.assertEqual(ctors["Item"], ["id", "title"])
            self.assertNotIn("Plain", ctors)
        self.assertEqual(ri.gradle_error("Reflex: no Gradle project :x\n"), "Reflex: no Gradle project :x")


class FlutterTest(unittest.TestCase):
    def test_generates_host_with_fakes_commands_and_methods(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make(tmp, FLUTTER)
            found = ri.flutter_candidates(app)
            self.assertEqual(found[0]["name"], "HomeViewModel")
            pos, named = ri.dart_params(found[0]["body"], "HomeViewModel")
            self.assertEqual([(p["name"], p["required"]) for p in named], [("bookingRepository", True), ("title", False)])
            source, entries, used = ri.flutter_source(app, found[0], app / ri.OUT, {"entries": set(), "omit": ["empty"]})
            self.assertIn("HomeViewModel(bookingRepository: FakeBookingRepository())", source)
            self.assertIn("import '../../../testing/fakes/fake_booking_repository.dart';", source)
            self.assertIn("import 'package:travel/ui/home_view_model.dart';", source)
            self.assertIn("'items': _j(vm.items),", source)
            self.assertIn("'title': _j(vm.title),", source)
            self.assertNotIn("'empty': _j", source)
            self.assertIn("'Load': NodeAction((_) => vm.load.execute()),", source)
            self.assertIn("'DeleteBooking': NodeAction((a) => vm.deleteBooking.execute(a['value'] as int)", source)
            self.assertIn("'Rename': NodeAction((a) => vm.rename(a['name'] as String, a['keep'] as bool)", source)
            self.assertNotIn("'Pick'", source)
            self.assertEqual(used, {"BookingRepository": "test double FakeBookingRepository"})
            # A compile error on an entry line drops that entry on the next try.
            line = next(n for n, e in entries.items() if e == "state:items")
            again, entries2, _ = ri.flutter_source(app, found[0], app / ri.OUT, {"entries": {entries[line]}, "omit": []})
            self.assertNotIn("'items': _j", again)


RIVERPOD = {
    "pubspec.yaml": "name: todos\ndependencies:\n  flutter:\n    sdk: flutter\n  hooks_riverpod: ^3.0.0\n",
    "lib/todo.dart": """import 'package:riverpod/riverpod.dart';

class Todo {
  const Todo({required this.id, required this.description, this.completed = false});
  final String id;
  final String description;
  final bool completed;
}

class TodoList extends Notifier<List<Todo>> {
  @override
  List<Todo> build() => [];

  void add(String description) {}
  void edit({required String id, required String description}) {}
  void remove(Todo target) {}
}
""",
    "lib/main.dart": "final todoListProvider = NotifierProvider<TodoList, List<Todo>>(\n  TodoList.new,\n);\n",
}

BLOC = {
    "pubspec.yaml": "name: todos\ndependencies:\n  flutter_bloc: ^9.0.0\n",
    "lib/overview/overview_bloc.dart": """import 'package:bloc/bloc.dart';
import '../filter.dart';
part 'overview_event.dart';

final class OverviewState {
  const OverviewState({this.items = const []});
  final List<String> items;
}

class OverviewBloc extends Bloc<OverviewEvent, OverviewState> {
  OverviewBloc({required this._repository}) : super(const OverviewState());
  final TodosRepository _repository;
}
""",
    "lib/overview/overview_event.dart": """part of 'overview_bloc.dart';

sealed class OverviewEvent {
  const OverviewEvent();
}

final class OverviewRefreshed extends OverviewEvent {
  const OverviewRefreshed();
}

final class OverviewFilterChanged extends OverviewEvent {
  const OverviewFilterChanged(this.filter);
  final Filter filter;
}

final class OverviewItemDeleted extends OverviewEvent {
  const OverviewItemDeleted(this.item);
  final Item item;
}
""",
    "lib/filter.dart": "enum Filter { all, done }\n",
    "lib/repository.dart": "class TodosRepository {\n  TodosRepository({required Api api});\n}\n",
    "test/helpers.dart": "class MockTodosRepository extends Mock implements TodosRepository {}\n",
}


class XcodeTargetTest(unittest.TestCase):
    def test_models_in_the_app_target_get_their_own_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make(tmp, {"App.xcodeproj/project.pbxproj": "", "App/SyncUpsList.swift": "import SwiftUI\n@Observable\nfinal class SyncUpsListModel {\n  var syncUps: [String] = []\n}\n"})
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = ri.main([str(app)])
            self.assertEqual(code, 2)
            self.assertIn("STOP SyncUpsListModel in App/SyncUpsList.swift holds state, but it is in the Xcode app target", out.getvalue())


class StateManagementTest(unittest.TestCase):
    def test_riverpod_notifier(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make(tmp, RIVERPOD)
            found = ri.flutter_candidates(app)
            self.assertEqual((found[0]["name"], found[0]["kind"], found[0]["provider"]), ("TodoList", "riverpod", "todoListProvider"))
            source, _, _ = ri.flutter_source(app, found[0], app / ri.OUT, {"entries": set(), "omit": []})
            self.assertIn("import 'package:hooks_riverpod/hooks_riverpod.dart';", source)
            self.assertIn("import 'package:todos/main.dart';", source)
            self.assertIn("'state': _j(_container.read(todoListProvider)),", source)
            self.assertIn("final vm = _container.read(todoListProvider.notifier);", source)
            self.assertIn("vm.edit(id: a['id'] as String, description: a['description'] as String)", source)
            self.assertIn("'Add': NodeAction((a) => vm.add(a['description'] as String)", source)
            self.assertIn("if (v is Todo) return {'id': v.id, 'description': v.description, 'completed': v.completed};", source)
            self.assertEqual(ri.dart_source_meta["skipped"], ["remove(Todo target)"])

    def test_bloc_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make(tmp, BLOC)
            found = ri.flutter_candidates(app)
            self.assertEqual((found[0]["name"], found[0]["kind"]), ("OverviewBloc", "bloc"))
            source, _, used = ri.flutter_source(app, found[0], app / ri.OUT, {"entries": set(), "omit": []})
            self.assertIn("OverviewBloc(repository: MockTodosRepository())", source)
            self.assertIn("'Refreshed': NodeAction((a) => vm.add(const OverviewRefreshed())),", source)
            self.assertIn("'FilterChanged': NodeAction((a) => vm.add(OverviewFilterChanged(Filter.values.byName(a['filter'] as String)))", source)
            self.assertIn("import 'package:todos/overview/overview_bloc.dart';", source)
            self.assertNotIn("overview_event.dart", source)
            self.assertIn("if (v is OverviewState) return {'items': v.items};", source)
            self.assertIn("OverviewItemDeleted", ri.dart_source_meta["skipped"])
            self.assertIn("a stand-in", used["TodosRepository"])


class NodeTest(unittest.TestCase):
    def test_wrapped_zustand_store_and_typed_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make(tmp, {"package.json": '{"dependencies": {"zustand": "5.0.0"}}', "src/auth.tsx": """import { create } from 'zustand';
type AuthState = { token: string | null; signIn: (data: Token) => void; rename: (name: string, age: number) => void };
const _useAuthStore = create<AuthState>()((set) => ({ token: null }));
export const useAuthStore = createSelectors(_useAuthStore);
"""})
            found = ri.node_candidates(app)
            self.assertEqual([(c["kind"], c["hook"], c["name"]) for c in found], [("zustand", "useAuthStore", "AuthStore")])
            sigs, skipped = ri.node_signatures(ri.read(app / "src/auth.tsx"))
            self.assertEqual(sigs, {"rename": [("name", "string"), ("age", "number")]})
            self.assertEqual(skipped, ["signIn"])

    def test_finds_context_and_zustand(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make(tmp, NODE)
            found = ri.rank_by_use(app, ri.node_candidates(app))
            self.assertEqual([(c["kind"], c["hook"]) for c in found], [("context", "useEpisodes"), ("zustand", "useCartStore")])
            self.assertEqual(found[0]["provider"], "EpisodeProvider")

    def test_missing_packages_say_what_to_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make(tmp, NODE)
            pick = ri.node_candidates(app)[0]
            with self.assertRaisesRegex(ri.Stop, "node_modules is missing"):
                ri.node_setup(app, pick, app / ri.OUT)
            (app / "node_modules/react").mkdir(parents=True)
            (app / "node_modules/react/package.json").write_text('{"version": "19.0.0"}')
            with self.assertRaisesRegex(ri.Stop, "react-test-renderer@19.0.0"):
                ri.node_setup(app, pick, app / ri.OUT)


class SwiftTest(unittest.TestCase):
    def test_finds_observable_and_reads_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make(tmp, SWIFT)
            found = ri.rank_by_use(app, ri.swift_candidates(app))
            self.assertEqual(found[0]["name"], "FeedViewModel")
            self.assertTrue(found[0]["main_actor"])
            self.assertEqual(found[0]["target"], "Feed")
            self.assertEqual(ri.swift_product(found[0]["package"], "Feed"), "FeedKit")
            self.assertEqual(ri.swift_init(found[0]["body"]), [[("service", "FeedService", True), ("limit", "Int", True)]])
            self.assertEqual(ri.swift_methods(found[0]["body"]), [("refresh", True, False, []), ("clear", False, False, []),
                                                                 ("open", False, False, [("id", "id", "String")])])
            self.assertLess(found[1]["score"], found[0]["score"])

    def test_actions_with_arguments_and_target_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make(tmp, {
                "Kit/Package.swift": 'let package = Package(name: "Kit", products: [.library(name: "Kit", targets: ["Kit"])], '
                                    'targets: [.target(name: "Kit", dependencies: [], path: "Sources")])\n',
                "Kit/Sources/Model/Store.swift": """import Combine
public final class Store: ObservableObject {
    @Published var orders: [Order] = []
    public func complete(id: Order.ID) {}
    public func rename(_ name: String, count: Int) {}
    public func update(id: Order.ID, to order: Order) {}
    public func total(id: Order.ID) -> Int { 0 }
}
""",
                "Kit/Sources/Model/Order.swift": "public struct Order: Identifiable {\n    public var id: String\n}\n",
            })
            found = ri.swift_candidates(app)
            self.assertEqual((found[0]["name"], found[0]["target"]), ("Store", "Kit"))
            methods = ri.swift_methods(found[0]["body"], ri.swift_ids(app / "Kit"))
            self.assertEqual([(m[0], m[3]) for m in methods],
                             [("complete", [("id", "id", "String")]), ("rename", [("_", "name", "String"), ("count", "count", "Int")])])
            self.assertEqual(ri.swift_methods.skipped, ["update(id: Order.ID, to order: Order)"])


class FirstRunTest(unittest.TestCase):
    def test_keys_that_change_between_runs(self):
        a = {"title": "Home", "clock": "12:00", "items": [{"id": 1, "seen": "a"}], "user": {"name": "x", "at": 1}}
        b = {"title": "Home", "clock": "12:01", "items": [{"id": 1, "seen": "b"}], "user": {"name": "x", "at": 2}}
        self.assertEqual(ri.differing_keys(a, b, set()), {"clock", "seen", "at"})
        self.assertEqual(ri.differing_keys(a, a, set()), set())

    def test_failures_end_with_a_next_step(self):
        out = "NOTE platform=kotlin could not build HomeViewModel: app.Api is abstract and the app has no test double for it\n"
        self.assertIn("Next: add a test double", ri.explain(out))
        self.assertIn("rebuild the classpath", ri.explain("STDERR x ClassNotFoundException: app.Home"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
