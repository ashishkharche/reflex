<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/brand/readme-banner-dark.png">
    <img src="assets/brand/readme-banner-light.png" alt="Reflex" width="100%">
  </picture>
</p>

**Test your iOS and Android app logic without a screen.**

Reflex lets a test or an AI agent talk to your app in plain text. `ls` asks what’s on screen and `do` presses a button. Your iOS and Android apps must give the same answer. Based on Shopify Engineering’s [Reflex](https://shopify.engineering/reflex) article. Not affiliated with Shopify. How it works in practice: [ashishkharche.com/notes/reflex](https://ashishkharche.com/notes/reflex/).

## Use it with an assistant

Paste this into a coding assistant that can use a shell in your app’s repo (Grok, Cursor or any coding assistant):

```text
Set up or update Reflex in this app using https://github.com/ashishkharche/reflex.
Keep Reflex in its own clone next to this repo, never inside it. If it’s already there, pull the latest and apply CHANGELOG.md.
Follow docs/add-to-your-app.md, For AI assistants first. Do my main screen only, on its own branch, and keep Reflex out of my app’s build. Only add new files and targets. Ask me before any refactor or product change, or if my iOS and Android apps are in separate repos.
Run the Reflex tests, build both apps and run their unit tests, then reply with only the five-part report from that guide.
```

<details>
<summary>Claude Code</summary>

Install the skills, then run `/reflex-start`. In Claude Code the plugin command is `/reflex:reflex-start`.

```bash
npx skills add ashishkharche/reflex -g
```

Or `/plugin marketplace add ashishkharche/reflex`, then `/plugin install reflex@ashishkharche-reflex`.

If the skill is not loaded, paste this:

```text
Fetch https://github.com/ashishkharche/reflex and follow skills/reflex-start/SKILL.md and the For AI assistants section of docs/add-to-your-app.md.
Set up or update Reflex in this app using that guide.
Keep Reflex in its own clone next to this repo, never inside it. If it’s already there, pull the latest and apply CHANGELOG.md.
Do my main screen only, on its own branch, and keep Reflex out of my app’s build. Only add new files and targets. Ask me before any refactor or product change, or if my iOS and Android apps are in separate repos.
Run the Reflex tests, build both apps and run their unit tests, then reply with only the five-part report from that guide.
```

</details>

<details>
<summary>ChatGPT</summary>

ChatGPT’s chat UI cannot install skills or run a shell in your repo. Use a coding agent with shell access, for example Codex, then paste this:

```text
You need a shell in this app’s repo. Fetch https://github.com/ashishkharche/reflex and read skills/reflex-start/SKILL.md and the For AI assistants section of docs/add-to-your-app.md. Follow those files. Do not invent steps.
Set up or update Reflex in this app using that guide.
Keep Reflex in its own clone next to this repo, never inside it. If it’s already there, pull the latest and apply CHANGELOG.md.
Do my main screen only, on its own branch, and keep Reflex out of my app’s build. Only add new files and targets. Ask me before any refactor or product change, or if my iOS and Android apps are in separate repos.
Run the Reflex tests, build both apps and run their unit tests, then reply with only the five-part report from that guide.
```

</details>

To load the skills instead of pasting, Grok Build: `grok plugin install ashishkharche/reflex --trust`. Any other assistant: `npx skills add ashishkharche/reflex -g`. Then run `/reflex-start` from your app’s repo. Claude Code, Codex and Cursor plugins: [docs/assistants.md](docs/assistants.md).

| Skill | When |
| --- | --- |
| `/reflex-start` | Add Reflex to your app and get your first screen under test. Run it again to update. |
| `/reflex-cover` | Cover a screen or feature with one test for iOS and Android. |
| `/reflex-check` | Check iOS and Android still match and fix what doesn’t. Run it before you merge. |
| `/reflex-explore` | Let your agent use the app while it builds, no simulator. |

Ask for a dry run first to see the plan without any change.

Reflex stays a separate folder next to your app. Only a separate test package points at it, so your app still builds without it. To update later, run `/reflex-start` or paste the prompt again.

## Try the sample

macOS is needed for the Swift (iOS) side. Linux, Docker and Linux CI work for Kotlin-only and Kotlin Multiplatform apps with `--platform kotlin`. The network guard runs there through `LD_PRELOAD` when a C compiler is installed. Windows works through WSL 2. Details: [docs/faq.md](docs/faq.md).

For the full sample below you also need Xcode, JDK 17 and Python 3.

```bash
git clone https://github.com/ashishkharche/reflex.git
cd reflex
bash scripts/build.sh
python3 scripts/console.py swift
```

Then type `ls` to see the screen and `do OpenProduct {"id":"shirt"}` to open one. Both apps should agree:

```bash
python3 runner/reflex_runner.py tests/inventory/reflex.json --platform both
```

You should see `RESULT PASS`.

## Use it in your app

1. Keep your ViewModel as it is.
2. Add a small adapter that lists its state and actions.
3. Follow [the full setup guide](docs/add-to-your-app.md).

## More

Environments, stacks and workflows: [docs/faq.md](docs/faq.md). Full docs index: [docs/README.md](docs/README.md).

MIT licence. Copyright (c) 2026 Ashish Kharche.
