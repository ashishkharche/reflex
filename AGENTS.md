# Inventory agent workflow

Read `TEST_PLAN.md` and `docs/architecture.md` before edits. Scope is inventory sample A, the outbox sample, ReflexKit and the runner.

1. Run README Setup commands in a clean clone.
2. Explore with `python3 scripts/console.py swift` or `kotlin` and an optional sample name. Use `ls`, `do Action [json]` and `op name [json]`.
3. Keep state writes in `update`. Add services as constructor protocols. Keep platform imports out of Core.
4. Add each public action to the sample’s kit adapter as a closure over `send` with a kit `Schema` for its input. Do not duplicate business logic in nodes or hand-write decoders.
5. Put behavior assertions in shared journey files (`tests/inventory/journeys/`, `samples/outbox/journeys/`). Put decoder rules in `kit/conformance/strict-decoder.json`. Keep failure fixtures at constructor edges.
6. Run `python3 runner/reflex_runner.py <manifest> --platform both --repeat 3 --timings 20` for each sample. Confirm the guard canary passes, tripwires report `network=denied` or exit 70 and full JSON parity passes.
7. Capture raw logs under `evidence/`. Run deliberate red paths and record exit codes.
8. Recheck a fresh clone from README after command changes. Build Mobile hosts one at a time.

Follow `docs/ux-writing.md`. No secrets or production inventory belong in fixtures.
