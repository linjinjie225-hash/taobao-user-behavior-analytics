from pathlib import Path

from tools.repository_guard import scan_paths


def test_scan_paths_blocks_sensitive_names_extensions_sizes_and_private_keys(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("TOKEN=not-a-real-token\n", encoding="utf-8")

    database = tmp_path / "sample.db"
    database.write_bytes(b"sqlite-placeholder")

    oversized = tmp_path / "oversized.txt"
    oversized.write_bytes(b"x" * 11)

    private_key = tmp_path / "key.txt"
    private_key.write_text(
        "-----BEGIN " + "PRIVATE KEY-----\nnot-a-real-key\n",
        encoding="utf-8",
    )

    problems = scan_paths(
        tmp_path,
        [env_file, database, oversized, private_key],
        max_bytes=10,
    )

    assert any("blocked name" in problem and ".env" in problem for problem in problems)
    assert any("blocked extension" in problem and "sample.db" in problem for problem in problems)
    assert any("exceeds 10 bytes" in problem and "oversized.txt" in problem for problem in problems)
    assert any("private marker" in problem and "key.txt" in problem for problem in problems)


def test_scan_paths_allows_readme(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Safe public project\n", encoding="utf-8")

    assert scan_paths(tmp_path, [readme]) == []
