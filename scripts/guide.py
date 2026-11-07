#!/usr/bin/env python3
"""Prints only the named sections of docs/add-to-your-app.md, so an assistant never reads the whole guide.

Use: guide.py ai 2 4 5 7 | results | update | list
Numbers pick numbered sections. ai is For AI assistants, results is What you get back, update is Updating Reflex.
"""
import re
import sys
from pathlib import Path

GUIDE = Path(__file__).resolve().parents[1] / "docs/add-to-your-app.md"
NAMES = {"ai": "For AI assistants", "results": "What you get back", "update": "Updating Reflex"}


def sections():
    out, title, lines = {}, None, []
    for line in GUIDE.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if title:
                out[title] = lines
            title, lines = line[3:].strip(), [line]
        elif title:
            lines.append(line)
    if title:
        out[title] = lines
    return out


def find(all_sections, key):
    if key in NAMES:
        return NAMES[key] if NAMES[key] in all_sections else None
    for title in all_sections:
        if re.match(rf"{re.escape(key)}\.\s", title):
            return title
    return None


def main(keys):
    all_sections = sections()
    if not keys or keys == ["list"]:
        print("\n".join(all_sections))
        return 0
    missing = [k for k in keys if not find(all_sections, k)]
    if missing:
        print(f"Unknown section {', '.join(missing)}. Sections:\n" + "\n".join(all_sections), file=sys.stderr)
        return 2
    for key in keys:
        print("\n".join(all_sections[find(all_sections, key)]).rstrip() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
