#!/usr/bin/env python3
"""Mechanical prose checks for the repository’s hand-written docs (docs/ux-writing.md)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ["README.md", "TEST_PLAN.md", "AGENTS.md", "kit/README.md", "runner/README.md", "samples/outbox/README.md",
         "docs/architecture.md", "docs/cli.md", "docs/testing.md", "docs/setup.md", "docs/use-cases.md", "docs/how-you-use-it.md", "docs/add-to-your-app.md",
         "docs/protocol/README.md", "docs/protocol/v1.md", "docs/protocol/CHANGELOG.md"]
for name in NAMES:
    text = (ROOT / name).read_text(encoding="utf-8")
    prose = re.sub(r"```.*?```", "", text, flags=re.S)
    prose = re.sub(r"`[^`]*`", "CODE", prose)
    prose = re.sub(r"https?://\S+", "URL", prose)
    banned = "along" + "side"
    assert banned not in prose.lower(), f"{name}: banned word"
    assert not re.search(r",\s+(and|or)\b", prose), f"{name}: Oxford comma"
    assert not re.search(r"[A-Za-z]'[A-Za-z]", prose), f"{name}: straight apostrophe"
    assert not re.search(r"In summary|Hopefully|Overall", prose), f"{name}: wrap-up"
    print(f"STYLE PASS {name}")
