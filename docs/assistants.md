# Reflex skills for AI assistants

Three skills in [`skills/`](../skills) in the [Agent Skills](https://agentskills.io/specification) format. They hold the steps and the rules. The details stay in [add-to-your-app.md](add-to-your-app.md).

| Skill | Use it to |
| --- | --- |
| `reflex-setup` | Set Reflex up in an app for the first time or update it. Ask for a dry run to see the plan without any change. |
| `reflex-add-screens` | List the app’s screens, flag the ones that need a refactor and cover one, several or all of them. |
| `reflex-run` | Rebuild, rerun, explain each FAIL and update expected values only for intentional changes. |

The repo root is also a plugin for Claude Code and Grok Build (`.claude-plugin/`) and for Cursor (`.cursor-plugin/`). The plugin is named `reflex`. Its marketplace is named `ashishkharche-reflex`.

## Install

| Assistant | Install | Run |
| --- | --- | --- |
| Claude Code | `/plugin marketplace add ashishkharche/reflex`, then `/plugin install reflex@ashishkharche-reflex` | `/reflex:reflex-setup` |
| Grok Build | `grok plugin install ashishkharche/reflex --trust` | `/reflex-setup` |
| Codex | `codex plugin marketplace add ashishkharche/reflex`, then `codex plugin add reflex@ashishkharche-reflex` | `/skills`, then pick `reflex-setup` |
| Cursor | Customize, then import this repository from GitHub. It has a `.cursor-plugin/marketplace.json`. | Type `/` and pick `reflex-setup` |
| Other assistants | Copy the three folders in `skills/` into the assistant’s skills folder, for example `~/.agents/skills/` | Ask for `reflex-setup` |

Claude Code puts the plugin name in front of each skill, so the command is `/reflex:reflex-setup`. The shell forms are `claude plugin marketplace add ashishkharche/reflex` and `claude plugin install reflex@ashishkharche-reflex`.

Grok Build asks for `--trust` before it loads a plugin’s skills. Run the install without it first to see what it activates. Grok Build does not list a plugin from this repo through `grok plugin marketplace add`, so install it directly as shown.

No skills support? Paste the prompt from the [README](../README.md). It points at the same guide.

## What was tested

On 6 Nov 2026 with this repo’s skills and manifests:

| Assistant | Version | Checked | Not checked |
| --- | --- | --- | --- |
| Grok Build | 1.0.69 | `grok plugin validate` passed. The install listed the 3 skills as `plugin: reflex`. A headless `/reflex-setup` dry run in a toy app only read files, changed nothing and ended with an INCOMPLETE report. | Install from GitHub before this commit was pushed |
| Claude Code | 2.1.319 | `claude plugin validate` passed with one warning: no listing icon. Marketplace add, install and `plugin details` showed the 3 skills. | A session, which needs a sign-in |
| Codex | 0.167.0 | `codex plugin marketplace add` read `.claude-plugin/marketplace.json`. `codex plugin add` installed the 3 skills. | A session, which needs a sign-in |
| Cursor | none | Both manifests pass Cursor’s published JSON schemas. | Cursor was not installed |

Raw notes: [evidence/assistants-2026-11-06](../evidence/assistants-2026-11-06/README.md).

## Update

Claude Code: `claude plugin marketplace update ashishkharche-reflex`, then `claude plugin update reflex@ashishkharche-reflex` and a restart. Grok Build: `grok plugin update reflex`. Codex: `codex plugin marketplace upgrade ashishkharche-reflex`. Then run `reflex-setup` again in the app to pull the Reflex clone and apply the CHANGELOG.

## Sources

- Agent Skills: https://agentskills.io/specification
- Claude Code: https://code.claude.com/docs/en/plugin-marketplaces and https://code.claude.com/docs/en/plugins-reference
- Cursor: https://cursor.com/docs/plugins and https://cursor.com/docs/skills
- Codex: https://developers.openai.com/codex/skills and https://developers.openai.com/codex/plugins/build
- Grok Build: `grok plugin --help` and the user guide installed with it
