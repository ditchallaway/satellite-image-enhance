#!/usr/bin/env python3
"""Lightweight privacy scan for the public real-estate-photo-editing package."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


TEXT_EXTS = {
    ".md",
    ".txt",
    ".py",
    ".yaml",
    ".yml",
    ".json",
}

DENY_PATTERNS = [
    re.compile(r"C:\\Users\\", re.IGNORECASE),
    re.compile(r"D:\\", re.IGNORECASE),
    re.compile(r"[A-Z]:\\\\", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    re.compile(r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b"),
]


def should_scan(path: Path) -> bool:
    if ".git" in path.parts:
        return False
    if "__pycache__" in path.parts:
        return False
    if path.suffix.lower() in TEXT_EXTS:
        return True
    return path.name == "LICENSE"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Repository root to scan.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    findings: list[str] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file() or not should_scan(path):
            continue
        if path.name == "privacy_scan.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), 1):
            for pattern in DENY_PATTERNS:
                if pattern.search(line):
                    rel = path.relative_to(root)
                    findings.append(f"{rel}:{lineno}: {line.strip()}")

    if findings:
        print("privacy scan failed")
        for item in findings:
            print(item)
        return 1

    print("privacy scan passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
