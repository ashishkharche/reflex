<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/brand/readme-banner-dark.png">
    <img src="assets/brand/readme-banner-light.png" alt="Reflex" width="100%">
  </picture>
</p>

Reflex lets a test or an AI agent read your app’s screens as plain text and press their buttons. Your iOS and Android apps must give the same answer.

## Get started

Install it in your app’s repo:

```bash
# Grok
grok plugin install \
  ashishkharche/reflex --trust

# Claude Code, Codex, Cursor and more
npx skills add ashishkharche/reflex -g
```

Then ask your assistant:

```text
/reflex-start
```

## Skills

- **/reflex-start** adds Reflex and tests your first screen. Run it again to update.
- **/reflex-cover** covers a screen with one test for both apps.
- **/reflex-check** checks iOS and Android still match. Run it before you merge.
- **/reflex-explore** lets your agent use the app with no simulator.

## Learn more

- [How it works in practice](https://ashishkharche.com/notes/reflex/)
- [Try the sample](docs/setup.md)
- [Add it by hand](docs/add-to-your-app.md)
- [Plugins for each assistant](docs/assistants.md)
- [Platforms and FAQ](docs/faq.md)

Based on Shopify Engineering’s [Reflex](https://shopify.engineering/reflex). Not affiliated with Shopify. MIT licence, © 2026 Ashish Kharche.
