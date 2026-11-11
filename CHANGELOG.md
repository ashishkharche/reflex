# Changelog

Changes to Reflex by version. Newest first. Each entry says whether the protocol or the kit API changed. Full protocol history: [docs/protocol/CHANGELOG.md](docs/protocol/CHANGELOG.md).

## Unreleased

- New `runner/reflex_init.py` sets up Reflex in an app with no hand-written code. It finds the stack and the class that holds screen state, writes a host, `reflex.json` and a first-run journey in `tests/reflex/` and runs it with `--repeat 3`. It changes no app file. It ends with PASS or with STOP and one next step. Kotlin uses the new `kit/kotlin-auto` reflective host on the app’s JVM unit test classpath from a Gradle init script, with the app’s own test doubles, a Main dispatcher and every flow collected. Flutter and React Native hosts are generated over the sample hosts. Swift gets a SwiftPM host with `@testable import` and the new `Reflect.state(of:)` in the Swift kit, with a simulator fallback. `/reflex-start` runs it first and writes code by hand only when it stops. Tried on fresh clones of six open-source apps (`evidence/plug-and-play-2026-11/`). Additive kit API. No protocol change. Tests: `runner/test_reflex_init.py`, `AutoHostTest` and `ReflectTests`.
- Runner: stderr lines that start with `ReflexKit auto:` print once per platform as `NOTE` and stay out of `STDERR`.
- Dart and Node sample hosts write `null` state values.
- Swift kit: `serveStandardIOOnMain` runs the main run loop instead of `dispatchMain()`, so main actor work runs on the main thread and app checks of `Thread.isMainThread` pass. Found on NetNewsWire. No API change. Guide: embed an `Info.plist` when app code reads `Bundle.main.infoDictionary`. Tried on the Ignite boilerplate and NetNewsWire (`evidence/real-apps-2026-11/`). Tests: `runner/test_host_checks.py`.
- Node sample host: `serveStandardIO({ around })` runs each action inside `around` and waits for it before the reply, for state that changes after the call returns, such as React state set in `act`. The runner’s `node.state never changed` causes name it. Guide: “React Native apps”, for state in a React context rendered with `react-test-renderer`. Proved on the Ignite boilerplate’s podcast list, repeat 3. No protocol change. Tests: `samples/stacks/react-native/test/around.js`.
- Runner and guard: on macOS the guard called itself for a Unix socket `connect`, so a host that talks to a helper over a Unix socket, such as `tsx`, spun forever. It now calls the real function. Hosts run in their own process group and the runner stops the whole group, so a child that keeps stdout open no longer hangs a run. Found on the Ignite boilerplate. No protocol or kit API change. Tests: `runner/test_host_checks.py`.
- iOS simulator hosts. A Swift host built for the iOS simulator runs there headless with `simctl spawn` on a throwaway device that the runner deletes at the end. The runner picks it from the binary or from `"simulator"` on a platform. The network guard builds for the simulator and a canary proves it on the device. Each journey gets a private home. New `runner/swift_host.py` builds for the Mac and falls back to the simulator when the Mac build says a package is iOS only. `explore.py` uses the same device. Proved on Ice Cubes, repeat 3. No protocol change.
- Swift kit: `serveStandardIOOnMain(settle:)` and `handle(bytes:settle:)` answer on the main actor after the work an action started, so `@MainActor` ViewModels that change state in a Task work. Additive kit API. Tests: `MainActorTests`, `runner/test_simulator.py`.
- New stack sample `samples/stacks/swiftui-ios/`: an iOS-only SwiftUI counter run on the simulator with byte parity against UIKit (`ios-simulator.json`).
- Runner: when a step expects `node.state` to change after an action or while an `eventually` step polls and the state is still the one from before, it prints `WARN … node.state never changed` with the likely causes: no Main dispatcher, `stateIn(WhileSubscribed)` with no subscriber or async work the host did not wait for. No protocol or kit API change. Tests: `runner/test_host_checks.py`.
- Tried on five open-source apps (`evidence/real-apps-2026-11/`). From what they needed:
  - Kotlin kit: a JVM host with kotlinx.coroutines but no `Dispatchers.Main` prints `ReflexKit warning: Dispatchers.Main is missing`, because `viewModelScope` work then never runs and state stays at its first value. The kit still has no dependencies; it checks by reflection. The kit build works with Gradle isolated projects. Kotlin kit API unchanged.
  - Runner: an app manifest no longer needs `guard`; the guard comes from the Reflex clone. A command whose classpath folder, `@` argument file or script is missing stops with exit 2 and `host input not found` instead of failing every step. Kit warnings print as `WARN` even on a pass. A failed journey shows the host’s stderr as a `STDERR` line. A crash keeps the exception line of its stack trace. The stateKeys hint shows only with two or more platforms. New `{flutter_tester}` placeholder and `runner/flutter_kernel.py`.
  - Dart sample host: an action may return a `Future`; the reply waits for it and for queued microtasks. `fixture(args)` reads the fixture on `flutter_tester` too. The stack sample runs on `flutter_tester` as a third platform.
  - Guide: hosts for ViewModels in Android modules on the unit test classpath, `viewModelScope` and `stateIn` in a JVM host, and Flutter apps on `flutter_tester`.
  - No protocol change. Tests: `runner/test_host_checks.py`, `runner/test_state_keys.py` and `MainDispatcherTest` in the Kotlin kit.
- New `samples/stacks/`: one counter journey run on UIKit, Android Views, Java on Android, Kotlin Multiplatform, Compose Multiplatform, Flutter and React Native hosts. All pass under the guard with byte parity against the Swift kit host. Flutter and React Native use small Dart and Node hosts in the samples because there is no kit for them. Manifests can use `{node}`. The README and FAQ list only what passed. No protocol or kit API change.
- The runner takes an optional `stateKeys` map in the manifest or a journey. `rename` gives a platform’s state keys shared names before `expect` and parity, with dotted paths for nested state. `only` lists keys one platform has alone: parity skips them and prints `PARITY NOT COMPARED`. Values still have to match, so a real difference still fails. With no map nothing changes. Unmapped key differences end with a hint to add a mapping. `explore.py` uses the same map. Tests: `runner/test_state_keys.py` and `runner/keys/`. No protocol or kit API change.
- The runner finds the JDK for Kotlin hosts once with your real home: `JAVA_HOME`, then `java` on the path, then `/usr/libexec/java_home` on macOS. Hosts get that `JAVA_HOME`, so the macOS `/usr/bin/java` stub no longer fails inside the private home. With no JDK the run stops with a clear “no Java runtime found” line. A host that exits before its first reply now shows `network=host-did-not-start`, not `guard-not-loaded`. No protocol or kit API change.
- Skills run every build and test in the foreground, one native app at a time. The report is the final message.
- Every `xcodebuild` command gets `-derivedDataPath .build/ios`, including `-list`, so package resolution stays in the repo. Builds get a long wait so the assistant can’t move them to the background. macOS picks a JDK with `/usr/libexec/java_home -v`.
- Kotlin Multiplatform iOS builds run `xcodebuild` with `GRADLE_OPTS=-Dorg.gradle.daemon=false`, so no Gradle daemon is left running.
- Grok Build installs with `grok plugin install ashishkharche/reflex --trust`. `npx skills add` uses `-g` so an untrusted folder can’t hide the skills.

- Native result counting now uses suite headers and the agent’s own arithmetic, not a custom script. Executed, skipped and failed cases are kept separate.

- Grok headless setup now checks skill discovery before a run. A copied but unlisted skill is not an active command; stop and use the plugin install instead of searching global folders.
- Skills keep SDK diagnostics repo-local and forbid Spotlight searches or stopping shared build daemons. Use SDK list commands, `JAVA_HOME` and `--no-daemon` instead.

- Native test evidence now excludes cached, skipped or empty test tasks. Gradle test commands force a fresh run and Xcode build and test output stays in repo-local DerivedData.

- macOS guarded hosts now get a kernel preferences boundary before exec. Named and standard UserDefaults remain process-local without app-specific memory stores. A native canary and fail-closed profile checks run in macOS CI.

- CI now checks docs and both guarded sample suites on Linux with Kotlin, in addition to Swift and Kotlin on macOS. Actions are pinned to full commit revisions. No repository secrets are needed.

- `reflex-cover` now stops when the previous Reflex branch is not merged instead of merging it implicitly. A second helper instance in the harness cannot stand in for view-owned state.

- Swift UserDefaults harnesses now require an injected in-memory store before the first launch. Named suites can survive a temporary home on macOS, so the runner guide no longer promises isolation for every persistent store.

- The failure-first step now starts with a runnable `explore.py ... ls` command before any helper code read. Native build and test attempts remain mandatory when a request only names one failure.
- Install guidance names Claude Code 2.0.20 as the first version with Skills support and checks the executable the shell selects. Empty headless replies are not successful runs.
- Report rules now state the prose style explicitly: curly apostrophes with no Oxford commas or em dashes.

- Error handling is the first numbered skill step: run the failing step through `explore.py` and read STDERR before any app or helper code.
- PASS needs separate current-session build and test evidence for each native app, including iOS in KMP projects. A Kotlin shared-code suite is not iOS evidence. Missing native checks mean INCOMPLETE with no merge next step.
- `reflex-check` reopens views and adapters and carries forward unresolved view-state and navigation gaps. Recording a callback does not prove the destination loaded.
- Skills use native read and search tools, `git commit -m` for messages and repo-local build output paths. No inline Python, heredocs or `~/Library` searches.

- Skills diagnose a failing step with `explore.py` and read its STDERR before reading code.
- Skills forbid all custom scripts, including inline Python and heredocs. Build and test logs stay in the app repo’s gitignored `.build/`, never `/tmp`.
- Changed code is committed on the Reflex branch before reporting. PASS requires every manifest platform and each app’s build and unit tests to pass in the current session with no uncommitted changes. A skipped platform is named with INCOMPLETE.
- Reports end with the Next line. The extra merge claim is gone. Only PASS permits a merge next step.

- New `scripts/guide.py` prints only the guide sections a step needs, for example `guide.py 3 4 5 7`. The skills use it instead of opening the whole guide.
- New `runner/explore.py` runs `ls` and `do` lines on every platform under the network guard in one process each, then prints the network status and parity. It stops with `BLOCKED` when the guard can’t run. `reflex-explore` uses only this.
- `reflex-start` and `reflex-cover` now name the screen’s main action, check its state is outside the views and prove it runs offline before writing the journey. A journey that skips the main action is INCOMPLETE.
- Every skill carries a literal report shape under 20 lines. Result and Where it is are one line each.
- `explore.py` takes `wait Name [ms]` and `wait {json} [ms]` lines for actions that load. The explore skill forbids writing your own script around the runner.
- Every CLI process gets a fresh empty home folder, including the JVM’s `user.home` and `CFFIXED_USER_HOME`. JVM CLIs also get an in-memory `java.util.prefs` store, because on macOS Java Preferences ignore `user.home` and write the account’s own settings. Saved data can’t leak between runs or app copies or touch the user’s settings.
- `explore.py` prints a failing CLI’s last error lines. Every skill forbids launching a CLI or probe script by hand and touching the user’s own settings.
- One Kotlin host covers Kotlin Multiplatform shared logic without a Swift harness. Native app build and test checks are still required.
- The readiness check also opens the view file. State a user sees that lives there, such as a pager position, is a readiness gap and makes the Result INCOMPLETE.
- The Next line follows the Result word, so nothing says merge before PASS. Reports are 19 lines at most with three decisions at most and nothing outside the block.
- Merge each Reflex branch before covering the next screen. The skills stay inside the app repo and `../reflex`.

No protocol change and no kit API change.

- Skills: renamed and regrouped by job. `reflex-setup` is now `reflex-start`, `reflex-add-screens` is now `reflex-cover` and `reflex-run` is now `reflex-check`, which also fixes what it finds. New `reflex-explore` lets an agent read and drive any screen through the CLI. Each skill loads only the guide sections it needs and ends with one next step. Install into any assistant with `npx skills add ashishkharche/reflex`. Reinstall to pick up the new names.
- Skills: `reflex-setup` checks the stack and the tools before any change. Flutter, React Native and other stacks without a kit, or a missing tool such as Xcode, a JDK or Python 3, stop with BLOCKED and say what is needed. Kotlin Multiplatform runs with `--platform kotlin`. All three skills find the main branch instead of assuming `main`, ask before touching uncommitted changes and commit on the branch without pushing.
- AI setup: a CLI that starts from an empty or made-up state the app fills in elsewhere makes that screen INCOMPLETE, and a `parity` or `xfail` mark can’t hide it. When the Result is FAIL or BLOCKED, the report still names each INCOMPLETE screen and its reason.
- Outbox sample: the adapter always lists Enqueue, PurgeSent, Retry, SetOnline and SyncNow. `update` decides validity and is the only state writer, including attempt counts. New journey `16-stable-actions.json`.
- AI report: Result is PASS only when every adapter wraps the real Core and no platform difference is hidden. Otherwise it is FAIL, BLOCKED or INCOMPLETE with the reasons under Needs your decision. New example.
- Runner: `eventually` steps poll `ls` up to a deadline without re-sending the action and print the last state on failure. `before` checks a precondition before a step is sent. The outbox CLIs add an `advanceLater` host op that changes state on a background thread, with journey `17-eventually.json` and two new red paths. No wire change.
- Network guard: also builds and loads on Linux through `LD_PRELOAD`, with the same canary. A clean run without the guard now prints `RESULT PASS-UNGUARDED` and exits 3 unless `--allow-unguarded` is passed. `guard=skipped-not-macos` is now `guard=skipped-unavailable`. Linux was tested on one Debian 13 x86_64 host with Kotlin hosts only.
- Debug socket host, first part. New Swift product `ReflexSocketHost` and Kotlin module `kit/kotlin-socket` serve a `Session` on 127.0.0.1. Runner platforms may set `socket`. The outbox CLIs take `--listen PORT` and `samples/outbox/live.json` runs a live journey on both. Kit API addition, no protocol change.
- Debug socket host in the sample apps. The inventory iOS and Android debug builds start it when launched with `reflexPort`, run each request on the main thread and redraw. `scripts/live_ui_check.py` checks the real screen after each action and `tests/inventory/live.json` runs a live journey. `scripts/check_release_exclusion.sh` proves the Release app and release APK leave out the host, its dependencies and on Android the `INTERNET` permission. The Kotlin host now binds IPv4 127.0.0.1 instead of the loopback default, which was `::1` on Android. Tested on one iOS simulator and one Android emulator, not on a physical phone. No protocol change.
- Assistant skills. `skills/` holds `reflex-setup`, `reflex-add-screens` and `reflex-run` in the Agent Skills format. The repo root is a `reflex` plugin for Claude Code and Grok Build (`.claude-plugin/`) and Cursor (`.cursor-plugin/`). Codex installs it from the same marketplace file. `reflex-setup` supports a dry run that changes nothing. The guide now says how to update files Reflex added earlier. See `docs/assistants.md`. No protocol change and no kit API change.
- Safer setup by assistants. No protocol change and no kit API change. Apply it on your next run:
  - Before reporting, build both apps and run their existing unit tests. A failed build or unit test makes the Result FAIL.
  - Keep Reflex out of the app build. The Swift Introspection target and CLI move to their own harness package, for example `ReflexHarness/`. The app’s `Package.swift`, Core package and Xcode project never name `../reflex`. On Kotlin, include the Reflex modules only when the clone exists. If your app already points at `../reflex`, move those parts out.
  - A screen whose view still does the real work is INCOMPLETE and named under Needs your decision.
  - A product change found through parity goes on its own branch in its own commit, after asking.
  - One screen per branch. Stop and report after each screen or refactor. “The whole app” means list first, then one at a time.
  - Where it is says how many commits the branch is behind the main branch. Rebase first when it is behind.
  - The report has exactly five headings: Result, Needs your decision, What I added, Where it is, Try it. “What I changed” is gone.

- Shorter README with a plain-language intro, banner and AI setup prompt.
- One AI prompt covers first setup and later updates and ends with a five-part report.
- New guide for adding Reflex to your app, including separate iOS and Android repos.
- Docs reorganised into an index, a glossary and `docs/project/`.
- How-it-works diagrams in `assets/diagrams/`.
- FAQ for environments, tech stacks, workflows and safety (`docs/faq.md`).
- Shorter AI prompt in the README. The full instructions moved to a For AI assistants section in the setup guide.
- The AI report is one text block with a heading per part, a numbered list of decisions and a new example, so it stays readable in a terminal.
- README, setup and add-to-your-app now say when macOS is needed (Swift / iOS and the network guard). Linux, Docker, Linux CI and WSL 2 cover Kotlin-only paths. See [docs/faq.md](docs/faq.md).

## 1.0.0 (6 Nov 2026)

First public release.

- Protocol 1, clarified. See [docs/protocol/v1.md](docs/protocol/v1.md).
- ReflexKit 1.0.1 for Swift and Kotlin: strict decoder, schemas, nodes, `Session` and the `Expect` matcher. See [kit/README.md](kit/README.md).
- Runner with Swift and Kotlin parity checks, the macOS network guard and `RESULT` lines.
- Inventory and outbox samples with shared journeys.
