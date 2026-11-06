# Reflex test plan

Architecture sample at `ashishkharche/reflex`. This plan defines the go/no-go bar for inventory sample A and the outbox sample. Reference architecture (no library): https://shopify.engineering/reflex

## Goals

- Keep README Setup as the only supported onboarding path: a stranger with a clean clone must not need tribal knowledge.
- Prove a UI-free Core can run headlessly on Swift (macOS) and Kotlin (JVM).
- Prove Elm-style ViewModels (action in / state out / single `update`) are driveable through an Introspection Kit (name + state JSON + actions).
- Prove one shared journey test file can pass or fail the same way on both platforms via a platform-agnostic CLI (`ls` / `do`).
- Fail the suite if any real HTTP escapes a behavior session (fixtures + network guard).
- Complement device automation: grey-box ViewModel journeys not pixel or accessibility-tree checks.

## Non-goals

- UI pixel tests screenshot diffs or visual review gates.
- Third-party host apps outside this sample.
- XCUITest Espresso Appium or other device automation.
- Notarized apps device CI or simulator/emulator farms for this go/no-go.
- Claiming Shopify affiliation. Reflex here is architecture plus samples not a Shopify fork.

## Milestones

### Milestone 1 (this go/no-go) — target A confirmed

Thin inventory sample only:

1. List products.
2. Open one product’s detail.
3. Set quantity (and related decrement / save / navigation cases below).

Both platforms: Swift Core+CLI and Kotlin Core+CLI. One shared test file. Harness picks the platform.

Target A was confirmed on 5 Nov 2026 (Europe/London). No third-party app screen is in this milestone.

### Milestone 2 (out of this go/no-go)

A screen in an adopting app may follow after Milestone 1’s go. It is not part of the public-readiness bar and needs a separate plan.

## Go / no-go bar

All of the following must pass before inventory sample A is recommended:

| # | Criterion |
| --- | --- |
| 1 | One inventory screen journey runs headless on Swift Core+CLI and Kotlin Core+CLI from one shared test file. |
| 2 | Network guard fails the suite if any HTTP escapes a behavior session. |
| 3 | Parity: the same journey pass/fail outcome on both platforms. |
| 4 | Warm journey p50 < 1s (after a documented warm-up step; raw timings in the evidence pack). |
| 5 | Failure messages name step action expected state and actual state. |
| 6 | README and plan prose follow `docs/project/ux-writing.md` (plain facts curly apostrophes ’ no Oxford comma the banned-word rule end on a fact no AI wrap-ups). |
| 7 | Fresh-clone README check: a clean clone succeeds by following only the README Setup commands (no tribal knowledge). Failure of that clone-and-follow path is a no-go. |

A single miss is a no-go.

## Test layers

| Layer | Role | Volume |
| --- | --- | --- |
| Unit | Primitives: base ViewModel helpers formatters parsers JSON encode/decode of state and action inputs. | Small |
| CLI behavior journeys | Business rules validation navigation error paths full inventory journeys. Fixtures at the edges. Fail-on-any-network. | Bulk of coverage |
| Thin live / integration | Optional handful against a real build through the same `ls` / `do` protocol. Not required to open the Milestone 1 go/no-go if headless journeys already clear the bar. | Thin optional |

No mocking frameworks inside journey tests. Real reducers real services real navigation with fixtures swapped at constructor edges.

## Required journey set (inventory sample)

Shared journey files: `tests/inventory/journeys/`. `runner/reflex_runner.py` selects the native host. Cases:

1. **Happy path** — `ls` on list → `do` open detail → `ls` shows detail state → `do` set quantity → state shows new quantity.
2. **Decrement at zero** — detail at quantity 0 → `do` Decrement → state stays 0 (or documented clamp); no crash; action still listed.
3. **Save failure fixture** — save path fed a failing fixture → state exposes the error the UI would show; no network.
4. **Navigation / back** — list → detail → lent `goBack` (or equivalent) → focused node is list again.
5. **Malformed action rejected** — `do` with bad JSON or unknown action → CLI rejects before ViewModel mutation; lists available actions.
6. **Network-guard tripwire** — deliberate path that would HTTP without a fixture → suite fails because a request was attempted.

Journeys fold steps into one test per fixture setup. Separate tests only when fixtures differ.

## Parity protocol

- One shared test file checked into the repo.
- Harness selects Swift or Kotlin host (env flag or CLI arg).
- CI (once Core exists) runs the file twice once per platform and fails if outcomes diverge.
- Agents do not maintain two copies of the journey.

## Evidence pack (go/no-go)

Attach:

1. Exact commands to build Core+CLI and run the journey suite on each platform.
2. Raw timing lines for warm journeys (enough samples to report p50) with host OS and runner note.
3. Paths to CI logs or local log files for the green run and for a deliberate network-guard failure.
4. Short paste of one intentional failure message showing step / action / expected / actual.
5. Result of the flake budget rerun (below).
6. Commit SHA(s) under test.
7. Fresh-clone README check: exact commands copied from README Setup only plus the full command log (stdout/stderr exit codes). Host OS label Europe/London timestamp and commit SHA. Any step that needs undocumented setup is a no-go.

## Flake budget

0 flakes on a 10× rerun of the Milestone 1 journey suite (both platforms). Any intermittent failure is a no-go until fixed or explained with a deterministic cause outside the suite.

## Out of scope for this plan

- XCUITest Espresso device automation.
- Notarized app distribution.
- Device CI matrices.
- Third-party app screens for Milestone 1.
- Production inventory services or persisted customer data.

## Ownership

| Role | Owns |
| --- | --- |
| Maintainers | This plan journey definitions evidence pack go/no-go recommendation |
| Maintainers | Swift/Kotlin Core CLI Introspection Kit inventory sample implementation |
| Repo owner | Inventory acceptance decision after the go/no-go |

Milestone 1 target is the thin inventory sample (list → detail → set quantity) on Swift Core+CLI and Kotlin Core+CLI.
