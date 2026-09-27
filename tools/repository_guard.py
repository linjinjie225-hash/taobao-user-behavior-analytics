"""Reject files that must not cross the public repository boundary."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Iterable


BLOCKED_NAMES = {".env", "secrets.toml", "analysis.db"}
BLOCKED_EXTENSIONS = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".doc",
    ".docx",
    ".pdf",
    ".jpg",
    ".jpeg",
}
PRIVATE_MARKERS = (
    b"-----BEGIN " + b"PRIVATE KEY-----",
    b"gh" + b"p_",
    b"github_" + b"pat_",
    b"AK" + b"IA",
)


def scan_paths(
    root: Path,
    paths: Iterable[Path | str],
    max_bytes: int = 10_000_000,
) -> list[str]:
    """Return publication problems found in candidate files."""
    root = root.resolve()
    problems: list[str] = []

    for candidate in paths:
        path = Path(candidate)
        if not path.is_absolute():
            path = root / path
        display_path = os.path.relpath(path, root).replace(os.sep, "/")

        if not path.is_file():
            continue

        name = path.name.lower()
        extension = path.suffix.lower()
        size = path.stat().st_size

        if name in BLOCKED_NAMES:
            problems.append(f"{display_path}: blocked name {path.name}")
        if extension in BLOCKED_EXTENSIONS:
            problems.append(f"{display_path}: blocked extension {extension}")
        if size > max_bytes:
            problems.append(f"{display_path}: exceeds {max_bytes} bytes ({size} bytes)")

        content = path.read_bytes()
        for marker in PRIVATE_MARKERS:
            if marker in content:
                problems.append(f"{display_path}: private marker detected")
                break

    return problems


def git_candidates(root: Path) -> list[Path]:
    """List tracked and unignored untracked files according to Git."""
    completed = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [Path(os.fsdecode(item)) for item in completed.stdout.split(b"\0") if item]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    problems = scan_paths(root, git_candidates(root))
    if problems:
        for problem in problems:
            print(f"publication guard: BLOCKED: {problem}")
        return 1

    print("publication guard: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
