#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hvdc_ops.domain_context import (  # noqa: E402
    AGENTS_PATH,
    CURSOR_RULE_PATH,
    README_PATH,
    load_domain_rules,
    render_agents_md,
    render_cursor_rule_mdc,
    render_readme_one_pager,
    replace_readme_generated_section,
)


def _write_if_changed(path: Path, content: str) -> bool:
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate README/AGENTS/Cursor domain context from domain_rules.yaml")
    parser.add_argument("--check", action="store_true", help="Exit non-zero if generated outputs are out of date.")
    args = parser.parse_args()

    rules = load_domain_rules()
    generated = {
        AGENTS_PATH: render_agents_md(rules),
        CURSOR_RULE_PATH: render_cursor_rule_mdc(rules),
    }
    readme = README_PATH.read_text(encoding="utf-8")
    generated[README_PATH] = replace_readme_generated_section(readme, render_readme_one_pager(rules))

    changed_paths: list[Path] = []
    for path, content in generated.items():
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if current != content:
            changed_paths.append(path)
            if not args.check:
                _write_if_changed(path, content)

    if changed_paths and args.check:
        for path in changed_paths:
            print(f"outdated: {path.relative_to(ROOT)}")
        return 1

    if not args.check:
        for path in changed_paths:
            print(f"updated: {path.relative_to(ROOT)}")
        if not changed_paths:
            print("no changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
