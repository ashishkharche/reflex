---
name: reflex-explore
description: Let your agent use the app headless while it builds, with no simulator. Reads any screen’s state and runs its actions through the Reflex CLI on iOS and Android. Use when building or debugging a feature, checking what a screen does or comparing the two platforms by hand.
license: MIT
---

# Explore the app

The fastest way to find out what the app does is to ask it. The CLI talks only to ViewModels, so what you see is what the screen would show.

## Steps

1. **Find the CLIs** in `tests/reflex.json` under `platforms`. Rebuild one if its source changed since the last build.
2. **Start a session.** Send NDJSON, one object per line, starting with hello:
   ```bash
   printf '%s\n' '{"op":"hello","protocol":1}' '{"op":"ls"}' | <cli command>
   ```
3. **Look** with `{"op":"ls"}`. It returns the focused screen’s name, its state as JSON and the actions it accepts.
4. **Act** with `{"op":"do","action":"Name","input":{...}}`, then `ls` again. Send a sequence in one call so you pay for one process start, not one per step.
5. **Compare** by sending the same lines to the other platform’s CLI. Report any difference as a fact, not a fix.
6. **Keep what you learn.** A sequence worth keeping becomes a journey with `reflex-cover`.

## Rules

- Read only. Do not change app code to explore.
- An action the focused screen does not offer returns `action.unknown`. Run `ls` and use the actions it lists instead of guessing.
- The network is blocked in tests. A screen that needs data needs a fixture.

## Reply

Answer in a few lines: the screen, the state fields that matter, what changed after each action and any difference between iOS and Android. No five-part report unless you changed files. End with one next step, for example `Next: /reflex-cover cart to keep this as a test`.
