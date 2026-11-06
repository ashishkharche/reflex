#!/usr/bin/env python3
"""Mechanical prose checks for the repository’s hand-written docs (docs/project/ux-writing.md)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EM_DASH = "\u2014"
SKIP_DIRS = {".git", ".build", "build", ".gradle", "node_modules"}
TEXT_SUFFIXES = {".md", ".swift", ".kt", ".kts", ".py", ".json", ".c", ".h", ".sh", ".yml", ".yaml", ".mmd", ".txt"}
for path in ROOT.rglob("*"):
    if path.is_file() and path.suffix in TEXT_SUFFIXES and not SKIP_DIRS.intersection(path.relative_to(ROOT).parts):
        assert EM_DASH not in path.read_text(encoding="utf-8", errors="ignore"), f"{path.relative_to(ROOT)}: em dash"
NAMES = [
    "README.md",
    "TEST_PLAN.md",
    "AGENTS.md",
    "kit/README.md",
    "runner/README.md",
    "samples/outbox/README.md",
    "samples/inventory/README.md",
    "docs/README.md",
    "docs/architecture.md",
    "docs/cli.md",
    "docs/testing.md",
    "docs/setup.md",
    "docs/how-you-use-it.md",
    "docs/add-to-your-app.md",
    "docs/glossary.md",
    "docs/faq.md",
    "docs/protocol/README.md",
    "docs/protocol/v1.md",
    "docs/protocol/CHANGELOG.md",
    "docs/project/brand.md",
]
for name in NAMES:
    text = (ROOT / name).read_text(encoding="utf-8")
    assert EM_DASH not in text, f"{name}: em dash"
    prose = re.sub(r"```.*?```", "", text, flags=re.S)
    prose = re.sub(r"`[^`]*`", "CODE", prose)
    prose = re.sub(r"https?://\S+", "URL", prose)
    banned = "along" + "side"
    assert banned not in prose.lower(), f"{name}: banned word"
    assert not re.search(r",\s+(and|or)\b", prose), f"{name}: Oxford comma"
    assert not re.search(r"[A-Za-z]'[A-Za-z]", prose), f"{name}: straight apostrophe"
    assert not re.search(r"In summary|Hopefully|Overall", prose), f"{name}: wrap-up"
    print(f"STYLE PASS {name}")
