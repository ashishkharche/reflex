#!/usr/bin/env python3
"""Detection and generation checks for runner/reflex_init.py on small made-up apps. No build tools needed."""
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


class NodeTest(unittest.TestCase):
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
            self.assertEqual(ri.swift_methods(found[0]["body"]), [("refresh", True, False), ("clear", False, False)])
            self.assertLess(found[1]["score"], found[0]["score"])


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
