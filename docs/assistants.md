# Reflex skills for AI assistants

Four skills in [`skills/`](../skills) in the [Agent Skills](https://agentskills.io/specification) format, one per job. Each loads only the part of [add-to-your-app.md](add-to-your-app.md) it needs. Shopify’s idea behind them: share the test, not the code.

| Skill | Use it to |
| --- | --- |
| `reflex-start` | Add Reflex to your app and get your first screen under test. Run it again to update. Ask for a dry run to see the plan first. |
| `reflex-cover` | Cover a screen or feature with one test for iOS and Android, one screen per branch. |
| `reflex-check` | Check iOS and Android still match and fix what doesn’t. Builds both apps, runs their unit tests and explains each failure. Run it before you merge. |
| `reflex-explore` | Let your agent read any screen’s state and run its actions through the CLI while it builds, with no simulator. |

Every skill ends with one next step, so you always know what to run.

The repo root is also a plugin for Claude Code and Grok Build (`.claude-plugin/`) and for Cursor (`.cursor-plugin/`). The plugin is named `reflex`. Its marketplace is named `ashishkharche-reflex`.

## Install

Claude Code skills need version 2.0.20 or newer. Check `claude --version` in the same shell you will use. If several installations are on the path, select a supported executable explicitly. An older CLI can return an empty headless reply to a skill command; that is not a successful run.

Grok Build: `grok plugin install ashishkharche/reflex --trust`. That’s all. The four skills load in every repo.

Any assistant: `npx skills add ashishkharche/reflex -g` installs for your user and asks which assistants to use. Pick one without questions with `-a <assistant> -y`, for example `npx skills add ashishkharche/reflex -g -a grok -y`. Without `-g` the skills go into the current repo. Grok Build only loads those after you trust the folder, for example by opening `grok` there once.

| Assistant | Install | Run |
| --- | --- | --- |
| Claude Code | `/plugin marketplace add ashishkharche/reflex`, then `/plugin install reflex@ashishkharche-reflex` | `/reflex:reflex-start` |
| Grok Build | `grok plugin install ashishkharche/reflex --trust` | `/reflex-start` |
| Codex | `codex plugin marketplace add ashishkharche/reflex`, then `codex plugin add reflex@ashishkharche-reflex` | `/skills`, then pick `reflex-start` |
| Cursor | Customize, then import this repository from GitHub. It has a `.cursor-plugin/marketplace.json`. | Type `/` and pick `reflex-start` |
| Other assistants | Copy the four folders in `skills/` into the assistant’s skills folder, for example `~/.agents/skills/` | Ask for `reflex-start` |

Claude Code puts the plugin name in front of each skill, so the command is `/reflex:reflex-start`. The shell forms are `claude plugin marketplace add ashishkharche/reflex` and `claude plugin install reflex@ashishkharche-reflex`.

Check with `grok inspect --json` from the app repo. Its skills list must include `reflex-start`, `reflex-cover`, `reflex-check` and `reflex-explore`. If they are absent, run the plugin install above and check again. Copied files are not proof that the commands loaded. Do not search home folders for the missing skills.

A sandbox such as Grok Build’s `--sandbox workspace` writes only to the app repo. The runner then builds its network guard in `tests/reflex/.build/`. Kotlin builds still need `../reflex` and the Gradle cache folders to be writable, so add them to the sandbox profile.

Grok Build asks for `--trust` before it loads a plugin’s skills. Run the install without it first to see what it activates. Grok Build does not list a plugin from this repo through `grok plugin marketplace add`, so install it directly as shown.

## What every skill does

| Rule | Why |
| --- | --- |
| Checks the stack and runner tools first and stops with BLOCKED if one is missing | You hear what to install before anything changes. |
| Builds both apps and runs their unit tests before it reports | A green runner does not prove the app still builds. |
| Keeps Reflex in a separate harness package | The app builds without the Reflex clone. |
| Marks a screen INCOMPLETE when its view still does the real work | The test would only drive a copy. |
| Puts a product change on its own branch, after asking | Coverage and behaviour changes are reviewed apart. |
| Does one screen per branch and stops after each screen or refactor | Each branch stays small enough to review. |
| Says how far the branch is behind the main branch and rebases first | The result matches what you would merge. |
| Finds the main branch, whether it is `main`, `master` or another name | It works with any repo. |
| Commits on the branch but never pushes unless you ask | You decide what leaves your computer. |
| Ends with exactly five headings: Result, Needs your decision, What I added, Where it is, Try it | Reports look the same every time. |

No skills support? Paste the prompt from the [README](../README.md). It points at the same guide.

## What was tested

On 6 Nov 2026 with this repo’s skills and manifests. Nothing was cloned from GitHub for these tests.

| Assistant | Version | Checked | Not checked |
| --- | --- | --- | --- |
| Grok Build | 1.0.69 | `grok plugin validate` passed. Installed from a clean export of this repo, it listed the 3 skills (before the rename to 4) as `plugin: reflex`. Headless sessions in a small toy app ran all 3 skills end to end: first setup, add the whole app, rerun and an update from a local upstream with a new CHANGELOG entry. Each ended with a five-part report that matched the runner. A dry run changed nothing. On 9 Nov 2026 a GitHub plugin install on a second Mac ran all four skills headless in CodeYam Counter (native) and Confetti (Compose Multiplatform). Every report came last. | An interactive session |
| Claude Code | 2.1.319 | `claude plugin validate` passed with one warning: no listing icon. Marketplace add, install and `plugin details` showed the 3 skills. | A session, which needs a sign-in |
| Codex | 0.167.0 | `codex plugin marketplace add` read `.claude-plugin/marketplace.json`. `codex plugin add` installed the 3 skills. | A session, which needs a sign-in |
| Cursor | none | Both manifests pass Cursor’s published JSON schemas. | Cursor was not installed |

Raw notes: [evidence/assistants-2026-11-06](../evidence/assistants-2026-11-06/README.md).

## Update

Claude Code: `claude plugin marketplace update ashishkharche-reflex`, then `claude plugin update reflex@ashishkharche-reflex` and a restart. Grok Build: `grok plugin update reflex`. Codex: `codex plugin marketplace upgrade ashishkharche-reflex`. Then run `reflex-start` again in the app to pull the Reflex clone and apply the CHANGELOG.

## Sources

- Agent Skills: https://agentskills.io/specification
- Claude Code: https://code.claude.com/docs/en/plugin-marketplaces and https://code.claude.com/docs/en/plugins-reference
- Claude Code 2.0.20 added Skills: https://github.com/anthropics/claude-code/blob/337cc419c3cfb9a9a5869f1b0bff135d3dd48598/CHANGELOG.md#2020
- Cursor: https://cursor.com/docs/plugins and https://cursor.com/docs/skills
- Codex: https://developers.openai.com/codex/skills and https://developers.openai.com/codex/plugins/build
- Grok Build: `grok plugin --help` and the user guide installed with it
