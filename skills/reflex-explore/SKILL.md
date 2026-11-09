---
name: reflex-explore
description: Let your agent use the app headless while it builds, with no simulator. Reads any screen’s state and runs its actions through the Reflex CLI on iOS and Android. Use when building or debugging a feature, checking what a screen does or comparing the two platforms by hand.
license: MIT
---

# Explore the app

The fastest way to find out what the app does is to ask it. The CLI talks only to ViewModels, so what you see is what the screen would show. Use one command for everything:

```bash
python3 ../reflex/runner/explore.py tests/reflex.json ls 'do Name {"key":"value"}' 'wait NextScreen'
```

`wait NextScreen` sends only `ls` until the screen is NextScreen, up to 5 seconds. `wait {"node":{"state":{"status":"ready"}}} 10000` waits for any part of a reply. Use it after an action that loads.

It builds and proves the network guard, runs every line in one process per platform, prints each reply, the network status and whether iOS and Android agree. Add `--platform swift` or `--platform kotlin` for one side and `--fixture <name>` for another start state.

Guarded macOS CLIs get process-local UserDefaults automatically. Keep the app’s real defaults binding, not an in-memory subclass added for isolation. A failed storage sandbox blocks the run. These journeys do not test real persistence between processes. Run Swift package unit tests with `python3 ../reflex/runner/swift_tests.py <package>`; plain `swift test` is not guarded.

## Steps

1. **Handle a failure first.** If a Reflex step has failed, run `python3 ../reflex/runner/explore.py tests/reflex.json ls` before reading any app or helper code. For an action failure, include its preceding actions and failing step in that call. Read STDERR, then diagnose. Return here immediately when a later step fails.
2. **Build** the CLIs only if their source changed since the last build. `BLOCKED ... CLI is not built` tells you which.
3. **Look first:** run it with `ls`. It shows the screen, its state and the actions it accepts.
4. **Act in one batch:** put every `do`, `wait` and `ls` you need in one call. Do not run one call per step and do not read app source to find what `ls` already lists.
5. **Read the end lines.** `NETWORK denied` means the action tried the network and needs a fixture. `PARITY ... differs at line N` names the first step where the platforms disagree. Report a difference as a fact, not a fix.
6. **Keep what you learn.** A sequence worth keeping becomes a journey with `reflex-cover`.

## Rules

- Read only. Do not change app code to explore.
- Run every command in the foreground. Your reply is your final message.
- Never launch a CLI yourself, never write your own script around the runner and never explore without the guard. If the helper can’t do something, say so in the reply. If the helper prints `BLOCKED`, stop and report that line. Never claim “no network calls” without its `network=clean` line.
- An action the screen does not offer returns `action.unknown`. Use the actions `ls` lists.
- Work only in the app repo and `../reflex`.
- Debug a CLI only through `explore.py`, which prints its error output when something fails. Never launch the CLI, `java` or a probe script yourself. Never read or write the user’s own settings (Java Preferences, UserDefaults or anything in `~/Library`). Write nothing outside the app repo and `../reflex`. No custom scripts of any kind, including inline `python -c` and heredocs. Read and search files with your own tools instead of inline Python or heredocs. Write commit messages with `git commit -m`. Keep build and test logs in the app repo’s gitignored `.build/`, never `/tmp`. Find build output there or at the repo-local path the build prints, never by searching `~/Library`. Pass `-derivedDataPath .build/ios` to every `xcodebuild` command, including `-list` and `-showBuildSettings`, which resolve packages too. Do not use `mdfind` or stop shared build daemons. Keep SDK diagnostics to repo files and SDK list commands. Select `JAVA_HOME` for the command (on macOS `/usr/libexec/java_home -v <version>`) and use `--no-daemon` if needed.

## Reply

A few lines: the screen, the state fields that matter, what changed after each action, the network line and any difference between iOS and Android. No five-part report unless you changed files. If you changed files, commit them on `reflex/<screen>` before reporting and use the `reflex-check` report rules. End with one next step, for example `Next: /reflex-cover cart to keep this as a test`.
