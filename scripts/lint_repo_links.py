#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TARGETS = [
    ROOT / "README.md",
    ROOT / "CHATGPT_CODEX_CURSOR_HANDOFF.md",
    ROOT / "WINDOWS_MULTI_PC_PACKAGE.md",
]
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
ABS_WINDOWS_PATTERN = re.compile(r"(?i)(?:/)?[a-z]:/users/")


def iter_problems(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    problems: list[str] = []

    for index, line in enumerate(text.splitlines(), start=1):
        if ABS_WINDOWS_PATTERN.search(line.replace("\\", "/")):
            problems.append(f"{path.name}:{index}: absolute Windows path found")

    for match in LINK_PATTERN.finditer(text):
        target = match.group(1).strip()
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        normalized = target.split("#", 1)[0]
        if not normalized:
            continue
        resolved = (path.parent / normalized).resolve()
        if not resolved.exists():
            problems.append(f"{path.name}: broken relative link -> {target}")
    return problems


def main() -> int:
    all_problems: list[str] = []
    for path in TARGETS:
        all_problems.extend(iter_problems(path))

    if all_problems:
        for problem in all_problems:
            print(problem)
        return 1

    print("repo links clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
