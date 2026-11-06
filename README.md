<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/brand/readme-banner-dark.png">
    <img src="assets/brand/readme-banner-light.png" alt="Reflex" width="100%">
  </picture>
</p>

**Test your iOS and Android app logic without a screen.**

Reflex lets a test or an AI agent talk to your app in plain text. `ls` asks what’s on screen and `do` presses a button. Your iOS and Android apps must give the same answer. Based on Shopify Engineering’s [Reflex](https://shopify.engineering/reflex) article. Not affiliated with Shopify.

## Try it

You need macOS, Xcode, JDK 17 and Python 3.

```bash
git clone https://github.com/ashishkharche/reflex.git
cd reflex
bash scripts/build.sh
python3 scripts/console.py swift
```

Then type:

```text
> ls
{"ok":true,"node":{"name":"InventoryList","state":{"products":[…]},"actions":["OpenProduct","Refresh","goBack"]}}
> do OpenProduct {"id":"shirt"}
{"ok":true,"node":{"name":"InventoryDetail","state":{"product":{"id":"shirt","quantity":3,…},"saved":false},…}}
```

Now check that both apps agree:

```bash
python3 runner/reflex_runner.py tests/inventory/reflex.json --platform both
```

You should see `RESULT PASS`.

## Use it in your app

1. Keep your ViewModel as it is.
2. Add a small adapter that lists its state and actions.
3. Follow [the full setup guide](docs/add-to-your-app.md).

## Set it up with your AI assistant

Open your app’s repo in Grok Build, Grok Bot, Cursor, Claude Code, Codex or any coding assistant and paste this:

```text
Add Reflex to this app using https://github.com/ashishkharche/reflex.
Clone that repo next to this repo, not inside it (for example ../reflex). Do not copy Reflex files into my repo.
If my iOS and Android apps live in separate repos, ask me where the other one is before you start.
Follow docs/add-to-your-app.md in the Reflex repo step by step.
Keep my app’s code and behaviour unchanged. Only add new files and targets. If a screen keeps its state in the views, tell me before you refactor anything.
Start with my main screen: add one adapter that lists its state and actions, plus a small Swift and Kotlin CLI.
Write a reflex.json manifest and one journey for that screen.
Run the runner with --platform both. If a step fails, fix it and rerun.
When you finish, reply with only this report, short and in plain words:
1. Result: the RESULT line.
2. Needs your decision: anything I must choose, such as a refactor or a difference between iOS and Android. Write "None" if empty.
3. What I added: files and where they live, one line each.
4. Where it is: branch, commit and whether it is pushed.
5. Try it: the one command to rerun the tests.
```

Reflex stays a separate folder next to your app. Your app only points at it by a relative path. Your phone targets never link it.

## Update Reflex later

Already set up? Paste this into your coding assistant to pull the latest Reflex and check your app still passes:

```text
Update Reflex in this app to the latest https://github.com/ashishkharche/reflex.
Pull the latest main in my Reflex clone next to this repo (or update the submodule if I use one).
Read CHANGELOG.md in Reflex for anything that changed since my version and apply it to my adapters, CLIs and reflex.json.
Rebuild the Swift and Kotlin CLIs and run the runner with --platform both.
If a step fails, fix it and rerun.
When you finish, reply with the same five-part report: Result, Needs your decision, What I changed, Where it is, Try it.
```

## More

Full docs index: [docs/README.md](docs/README.md).

MIT licence. Copyright (c) 2026 Ashish Kharche.
