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

Open your app’s repo in Cursor, Claude Code, Codex or any coding assistant and paste this:

```text
Add Reflex to this app using https://github.com/ashishkharche/reflex.
Follow docs/add-to-your-app.md in that repo step by step.
Keep my app’s code and behaviour unchanged. Only add new files and targets.
Start with my main screen’s ViewModel: add one adapter that lists its state and actions, plus a small Swift and Kotlin CLI.
Write a reflex.json manifest and one journey for that screen.
Run the runner with --platform both and show me the RESULT line.
If a step fails, fix it and tell me what you changed.
```

## More

Full docs index: [docs/README.md](docs/README.md).

MIT licence. Copyright (c) 2026 Ashish Kharche.
