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

## Steps

1. **Build** the CLIs only if their source changed since the last build. `BLOCKED ... CLI is not built` tells you which.
2. **Look first:** run it with `ls`. It shows the screen, its state and the actions it accepts.
3. **Act in one batch:** put every `do`, `wait` and `ls` you need in one call. Do not run one call per step and do not read app source to find what `ls` already lists.
4. **Read the end lines.** `NETWORK denied` means the action tried the network and needs a fixture. `PARITY ... differs at line N` names the first step where the platforms disagree. Report a difference as a fact, not a fix.
5. **Keep what you learn.** A sequence worth keeping becomes a journey with `reflex-cover`.

## Rules

- When a step fails, run `python3 ../reflex/runner/explore.py tests/reflex.json` with the failing step first and read its STDERR before reading code.
- Read only. Do not change app code to explore.
- Never launch a CLI yourself, never write your own script around the runner and never explore without the guard. If the helper can’t do something, say so in the reply. If the helper prints `BLOCKED`, stop and report that line. Never claim “no network calls” without its `network=clean` line.
- An action the screen does not offer returns `action.unknown`. Use the actions `ls` lists.
- Work only in the app repo and `../reflex`.
- Debug a CLI only through `explore.py`, which prints its error output when something fails. Never launch the CLI, `java` or a probe script yourself. Never read or write the user’s own settings (Java Preferences, UserDefaults or anything in `~/Library`). Write nothing outside the app repo and `../reflex`. No custom scripts of any kind, including inline `python -c` and heredocs. Use your own read and search tools. Keep build and test logs in the app repo’s `.build/` and ensure it is gitignored, never `/tmp`.

## Reply

A few lines: the screen, the state fields that matter, what changed after each action, the network line and any difference between iOS and Android. No five-part report unless you changed files. If you changed files, commit them on `reflex/<screen>` before reporting and use the `reflex-check` report rules. End with one next step, for example `Next: /reflex-cover cart to keep this as a test`.
