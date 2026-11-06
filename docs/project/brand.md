# Reflex brand

Prism mark, Mono palette, Space Grotesk wordmark. Brand assets for Reflex.

## Mark

Variant A is a pure-line diamond: one beam into an outline diamond and two exit rays at a shared stroke weight. It reads as a prism splitting a single path into two native cores.

At 16 px and 32 px the mark uses a simplified solid diamond (same silhouette as the solid prism) so the favicon stays legible. At 64 px and above the pure-line geometry is used.

## Introspection commands

`ls` lists the current state and the available actions. `do` runs one action and returns the new state.

## Files

| Path | What |
|---|---|
| `assets/brand/icon-light.svg` · `icon-dark.svg` | Mark on transparent (ink / cloud) |
| `assets/brand/icon-light.png` · `icon-dark.png` | 512 px PNG |
| `assets/brand/icon-{light,dark}-{16,32,64,128,256,512}.png` | Size ladder (16/32 solid) |
| `assets/brand/lockup-light.svg` · `lockup-dark.svg` | Mark + outlined “Reflex” |
| `assets/brand/lockup-light.png` · `lockup-dark.png` | Lockup PNG |
| `assets/brand/readme-banner-light.png` · `readme-banner-dark.png` | README hero 1600×560 (+ SVG), direction B |
| `assets/brand/social-preview.png` | GitHub social 1280×640 (dark), matching B |
| `assets/brand/icons/favicon.ico` | 16 / 32 / 48 ICO |
| `assets/brand/icons/favicon-16.png` · `favicon-32.png` | Solid diamond favicons |
| `assets/brand/icons/favicon.svg` | Vector favicon |
| `assets/brand/icons/apple-touch-icon.png` | 180×180 |
| `assets/brand/icons/icon-192.png` · `icon-512.png` | App icons |
| `assets/brand/icons/icon-512-maskable.png` | Maskable with safe padding |
| `assets/brand/fonts/` | Space Grotesk + JetBrains Mono + OFL texts |

## Colours

| Token | Hex | Use |
|---|---|---|
| Ink | `#0d1117` | Mark and wordmark on light |
| Cloud | `#e6edf3` | Mark and wordmark on dark |
| Muted light | `#57606a` | Tagline on light |
| Muted dark | `#8b949e` | Tagline on dark |
| Dot light | `#afb8c1` | Soft field on light banners |
| Dot dark | `#484f58` | Soft field on dark banners |
| Surface light | `#ffffff` | GitHub light |
| Surface dark | `#0d1117` | GitHub dark |

## Type

| Role | Family | Weight | Licence |
|---|---|---|---|
| Wordmark | Space Grotesk | 600 | OFL-1.1 |
| Tagline | Space Grotesk | 500 | OFL-1.1 |
| CLI samples in docs | JetBrains Mono | 500 | OFL-1.1 |

Wordmarks are hand-kerned title-case “Reflex”, outlined as SVG paths. There is no underline under the x.

## Banners

README banners and the social preview use a centred stack: Prism A mark, then the wordmark, then one tagline line:

> Test your iOS and Android app logic without a screen.

A soft fading dot field sits behind the stack and falls to nothing well before the edges. Quiet depth only. They do not show `ls`, `do` or other diagram labels.

Full OFL texts live next to the font files in `assets/brand/fonts/`.

## Clear space and minimum size

Keep clear space around the mark of at least the diamond’s half-width on every side. Do not crowd the mark with other graphics or crop into the beam or rays.

Minimum sizes:
- Mark alone: 16 px (solid diamond form)
- Lockup: 24 px mark height
- README banner: use the shipped 1600×560 assets
- Social preview: use the shipped 1280×640 asset (content stays inside ≥80 px margins)

## Do

- Use the Mono ink/cloud pair on GitHub light and dark surfaces.
- Prefer the SVG for UI chrome; use the PNG ladder where SVG is awkward.
- Credit Space Grotesk and JetBrains Mono under the OFL when redistributing the font files.

## Don’t

- Don’t recolour the mark with teal, cyan or brand colours from other Ashish projects.
- Don’t add an underline under the x or restyle the wordmark in a live web font for shipping SVGs.
- Don’t put CLI or diagram chrome on the README banners or the social preview.
- Don’t use Shopify, Apple or Android marks.
- Don’t claim affiliation with Shopify.

## Affiliation

Reflex is a reference implementation of Shopify Engineering’s Reflex pattern. It is not affiliated with or endorsed by Shopify. Shopify is a trademark of its respective owner.
