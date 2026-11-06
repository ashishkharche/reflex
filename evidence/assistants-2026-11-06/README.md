# Assistant skills, 6 Nov 2026

Mac: Apple silicon, macOS 26.5.1. Grok Build 1.0.69, Claude Code 2.1.319 and Codex 0.167.0. Cursor was not installed.

## Fixture

- `reflex/`: a `git archive` export of this repo with the skills, made into a local git repo with a local bare upstream. Nothing was cloned from GitHub.
- `toy-app/`: a small app made for the test. A Swift package Core and a Kotlin Gradle Core, each with a Counter and a Notes ViewModel. A Settings screen keeps its state in the view on both platforms.

The plugin was installed with `grok plugin install <export> --trust` and removed afterwards.

## Grok Build sessions

Each step was a separate headless `grok -p` session in `toy-app/` with:

- `--sandbox` set to a profile that extends `workspace` and adds only the Gradle and SwiftPM cache folders.
- `--permission-mode dontAsk` with allow rules for file edits in the fixture, read-only commands, `git`, `swift build`, `./gradlew` and `python3 ../reflex/...`.
- Deny rules for `git push`, `git clone`, `git reset`, `rm -rf`, `sudo` and `curl`.

| Step | Report | Checked by hand |
| --- | --- | --- |
| `/reflex-setup`, first setup | `r1-setup-report.txt`: PASS on swift and kotlin. Counter node and CLI on both platforms and one journey. | The runner passed with `guard=canary-pass`. In existing files only `Package.swift` and `settings.gradle.kts` changed, to register targets. Core and UI files were unchanged. No Core rule was copied. |
| `/reflex-add-screens`, whole app | `r2-add-screens-report.txt`: INCOMPLETE. Notes added on both platforms. Settings skipped as needing a refactor. | The new Notes journey found a real difference: Swift keeps a note of `"\nhello\n"` and Kotlin trims it to `hello`. The step is marked `parity` and the report puts it under Needs your decision. |
| `/reflex-run` | `r3-run-report.txt`: INCOMPLETE. Nothing changed. | The runner printed `RESULT PASS` with one known difference. The skill still reported INCOMPLETE as it should. |
| `/reflex-setup`, update | `r4-update-report.txt`: INCOMPLETE, with the same two decisions. | The upstream had one fixture-only CHANGELOG entry asking for an `about` field in each journey. The session pulled it, read the diff, added `about` to the two journey files only, rebuilt and reran. `runner-after-update.log` is the rerun by hand. |
| `/reflex-setup` dry run | INCOMPLETE with reason dry run | Only read tools ran. The toy app was unchanged. |

What went wrong on the way:

- Headless sessions end on the first command no rule allows. Early setup runs ended on an `echo` chain and on `ls` after `cd`. They were rerun with more read-only allow rules. A later session tried to write a scratch file outside the fixture. That was refused. The session was resumed with a scratch folder inside the fixture.
- `swift build` fails inside the Grok sandbox because SwiftPM starts its own sandbox. Each session retried with `swift build --disable-sandbox` and that worked.
- After add-screens, `reflex-add-screens` gained the rule that a `parity` or `xfail` step makes the Result INCOMPLETE. The session had already reported INCOMPLETE. This wording was not rerun.

## Claude Code and Codex

From the same export, with an isolated home folder and no sign-in:

- Claude Code: `claude plugin validate` passed with one warning, no listing icon. Marketplace add, install and `plugin details` showed the 3 skills.
- Codex: `codex plugin marketplace add` read `.claude-plugin/marketplace.json` and `codex plugin add` installed the 3 skills. `codex plugin marketplace upgrade` refused a local marketplace, which is expected.

Sessions were not run with either because they need a sign-in.

## Cursor

Not installed. Both `.cursor-plugin` manifests pass the JSON schemas in https://github.com/cursor/plugins.
