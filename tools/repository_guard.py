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
    b"-----BEGIN " + b"RSA " + b"PRIVATE KEY-----",
    b"-----BEGIN " + b"OPENSSH " + b"PRIVATE KEY-----",
    b"-----BEGIN " + b"EC " + b"PRIVATE KEY-----",
    b"-----BEGIN " + b"DSA " + b"PRIVATE KEY-----",
    b"gh" + b"p_",
    b"gh" + b"o_",
    b"gh" + b"u_",
    b"gh" + b"s_",
    b"gh" + b"r_",
    b"github_" + b"pat_",
    b"AK" + b"IA",
    b"AS" + b"IA",
)


class PublicationGuardError(RuntimeError):
    """Raised when repository content cannot be inspected safely."""


def _contains_private_marker(content: bytes) -> bool:
    return any(marker in content for marker in PRIVATE_MARKERS)


def _file_contains_private_marker(path: Path, chunk_bytes: int) -> bool:
    """Scan a file with bounded memory, preserving matches across chunks."""
    chunk_bytes = max(1, min(64 * 1024, chunk_bytes))
    overlap = max(len(marker) for marker in PRIVATE_MARKERS) - 1
    tail = b""

    with path.open("rb") as stream:
        while chunk := stream.read(chunk_bytes):
            window = tail + chunk
            if _contains_private_marker(window):
                return True
            tail = window[-overlap:]
    return False


def _run_git(root: Path, *args: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"") or b""
        message = os.fsdecode(detail).strip() or str(exc)
        raise PublicationGuardError(f"git command failed: {message}") from exc
    return completed.stdout


def _metadata_problems(display_path: str, size: int, max_bytes: int) -> list[str]:
    path = Path(display_path)
    problems: list[str] = []
    if path.name.lower() in BLOCKED_NAMES:
        problems.append(f"{display_path}: blocked name {path.name}")
    if path.suffix.lower() in BLOCKED_EXTENSIONS:
        problems.append(f"{display_path}: blocked extension {path.suffix.lower()}")
    if size > max_bytes:
        problems.append(f"{display_path}: exceeds {max_bytes} bytes ({size} bytes)")
    return problems


def _parse_index_entry(item: bytes) -> tuple[str, str]:
    try:
        metadata, raw_path = item.split(b"\t", 1)
        fields = metadata.split()
        object_id = os.fsdecode(fields[1])
    except (IndexError, ValueError) as exc:
        raise PublicationGuardError("could not parse Git index entry") from exc
    return object_id, os.fsdecode(raw_path).replace(os.sep, "/")


def scan_repository(root: Path, max_bytes: int = 10_000_000) -> list[str]:
    """Scan indexed blobs and unignored, untracked working-tree files."""
    root = root.resolve()
    problems: list[str] = []
    entries = _run_git(root, "ls-files", "--stage", "-z")

    for item in entries.split(b"\0"):
        if not item:
            continue
        object_id, display_path = _parse_index_entry(item)
        try:
            size = int(_run_git(root, "cat-file", "-s", object_id).strip())
        except ValueError as exc:
            raise PublicationGuardError(
                f"could not read index blob size for {display_path}"
            ) from exc

        problems.extend(_metadata_problems(display_path, size, max_bytes))
        if size > max_bytes:
            continue

        content = _run_git(root, "cat-file", "blob", object_id)
        if _contains_private_marker(content):
            problems.append(f"{display_path}: private marker detected")

    untracked = _run_git(root, "ls-files", "--others", "--exclude-standard", "-z")
    untracked_paths = [
        Path(os.fsdecode(item)) for item in untracked.split(b"\0") if item
    ]
    problems.extend(scan_paths(root, untracked_paths, max_bytes=max_bytes))

    return problems


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

        size = path.stat().st_size
        problems.extend(_metadata_problems(display_path, size, max_bytes))

        if _file_contains_private_marker(path, max_bytes):
            problems.append(f"{display_path}: private marker detected")

    return problems


def git_candidates(root: Path) -> list[Path]:
    """List tracked and unignored untracked files according to Git."""
    output = _run_git(
        root,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
    )
    return [Path(os.fsdecode(item)) for item in output.split(b"\0") if item]


def main(root: Path | None = None) -> int:
    root = Path(__file__).resolve().parents[1] if root is None else root
    try:
        problems = scan_repository(root)
    except PublicationGuardError as exc:
        print(f"publication guard: ERROR: {exc}")
        return 2
    if problems:
        for problem in problems:
            print(f"publication guard: BLOCKED: {problem}")
        return 1

    print("publication guard: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
