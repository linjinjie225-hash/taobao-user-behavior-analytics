import subprocess
from pathlib import Path

import pytest

from tools import repository_guard
from tools.repository_guard import scan_paths


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def init_repo(repo: Path) -> None:
    run_git(repo, "init", "-q")
    run_git(repo, "config", "user.email", "guard-tests@example.invalid")
    run_git(repo, "config", "user.name", "Publication Guard Tests")


def test_repository_scan_reads_staged_content_not_safe_working_copy(
    tmp_path: Path,
) -> None:
    init_repo(tmp_path)
    candidate = tmp_path / "config.txt"
    candidate.write_bytes(b"gh" + b"p_" + b"0123456789abcdef\n")
    run_git(tmp_path, "add", "config.txt")
    candidate.write_text("safe working copy\n", encoding="utf-8")

    problems = repository_guard.scan_repository(tmp_path)

    assert any(
        "private marker" in problem and "config.txt" in problem
        for problem in problems
    )


def test_repository_scan_reads_staged_file_removed_from_disk(tmp_path: Path) -> None:
    init_repo(tmp_path)
    candidate = tmp_path / "key.txt"
    candidate.write_bytes(b"-----BEGIN " + b"PRIVATE KEY-----\nplaceholder\n")
    run_git(tmp_path, "add", "key.txt")
    candidate.unlink()

    problems = repository_guard.scan_repository(tmp_path)

    assert any(
        "private marker" in problem and "key.txt" in problem for problem in problems
    )


def test_repository_scan_reads_untracked_nonignored_file(tmp_path: Path) -> None:
    init_repo(tmp_path)
    candidate = tmp_path / "untracked.txt"
    candidate.write_bytes(b"AK" + b"IA" + b"0123456789ABCDEF\n")

    problems = repository_guard.scan_repository(tmp_path)

    assert any(
        "private marker" in problem and "untracked.txt" in problem
        for problem in problems
    )


@pytest.mark.parametrize(
    "credential",
    [
        pytest.param(b"-----BEGIN " + b"PRIVATE KEY-----", id="pem-generic"),
        pytest.param(b"-----BEGIN " + b"RSA " + b"PRIVATE KEY-----", id="pem-rsa"),
        pytest.param(b"-----BEGIN " + b"OPENSSH " + b"PRIVATE KEY-----", id="pem-openssh"),
        pytest.param(b"-----BEGIN " + b"EC " + b"PRIVATE KEY-----", id="pem-ec"),
        pytest.param(b"-----BEGIN " + b"DSA " + b"PRIVATE KEY-----", id="pem-dsa"),
        pytest.param(b"gh" + b"p_" + b"x" * 20, id="github-personal"),
        pytest.param(b"gh" + b"o_" + b"x" * 20, id="github-oauth"),
        pytest.param(b"gh" + b"u_" + b"x" * 20, id="github-user"),
        pytest.param(b"gh" + b"s_" + b"x" * 20, id="github-server"),
        pytest.param(b"gh" + b"r_" + b"x" * 20, id="github-refresh"),
        pytest.param(b"github_" + b"pat_" + b"x" * 20, id="github-fine-grained"),
        pytest.param(b"AK" + b"IA" + b"0" * 16, id="aws-long-lived"),
        pytest.param(b"AS" + b"IA" + b"0" * 16, id="aws-temporary"),
    ],
)
def test_repository_scan_detects_credential_variants(
    tmp_path: Path,
    credential: bytes,
) -> None:
    init_repo(tmp_path)
    candidate = tmp_path / "candidate.txt"
    candidate.write_bytes(b"prefix " + credential + b" suffix\n")
    run_git(tmp_path, "add", "candidate.txt")

    problems = repository_guard.scan_repository(tmp_path)

    assert problems == ["candidate.txt: private marker detected"]


def test_repository_scan_fails_closed_when_git_cannot_read_index(
    tmp_path: Path,
) -> None:
    with pytest.raises(repository_guard.PublicationGuardError, match="git"):
        repository_guard.scan_repository(tmp_path)


def test_main_blocks_secret_from_index(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    init_repo(tmp_path)
    candidate = tmp_path / "token.txt"
    candidate.write_bytes(b"gh" + b"o_" + b"x" * 20)
    run_git(tmp_path, "add", "token.txt")
    candidate.write_text("safe\n", encoding="utf-8")

    result = repository_guard.main(tmp_path)

    assert result == 1
    assert (
        "publication guard: BLOCKED: token.txt: private marker detected"
        in capsys.readouterr().out
    )


def test_main_reports_git_failure_and_returns_nonzero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert repository_guard.main(tmp_path) == 2
    assert "publication guard: ERROR: git command failed:" in capsys.readouterr().out


def test_main_fails_closed_when_git_index_is_unreadable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    init_repo(tmp_path)
    candidate = tmp_path / "safe.txt"
    candidate.write_text("safe\n", encoding="utf-8")
    run_git(tmp_path, "add", "safe.txt")
    (tmp_path / ".git" / "index").write_bytes(b"not a git index")

    assert repository_guard.main(tmp_path) == 2
    assert "publication guard: ERROR: git command failed:" in capsys.readouterr().out


def test_scan_paths_does_not_use_whole_file_read_for_oversized_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oversized = tmp_path / "oversized.txt"
    oversized.write_bytes(b"x" * 64)

    def reject_whole_file_read(path: Path) -> bytes:
        raise AssertionError(f"whole-file read attempted for {path}")

    monkeypatch.setattr(Path, "read_bytes", reject_whole_file_read)

    problems = scan_paths(tmp_path, [oversized], max_bytes=8)

    assert problems == ["oversized.txt: exceeds 8 bytes (64 bytes)"]


def test_repository_scan_checks_index_blob_size_before_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init_repo(tmp_path)
    oversized = tmp_path / "oversized.txt"
    oversized.write_bytes(b"x" * 64)
    run_git(tmp_path, "add", "oversized.txt")
    actual_run_git = repository_guard._run_git

    def reject_blob_read(root: Path, *args: str) -> bytes:
        if args[:2] == ("cat-file", "blob"):
            raise AssertionError("oversized index blob was read")
        return actual_run_git(root, *args)

    monkeypatch.setattr(repository_guard, "_run_git", reject_blob_read)

    problems = repository_guard.scan_repository(tmp_path, max_bytes=8)

    assert problems == ["oversized.txt: exceeds 8 bytes (64 bytes)"]


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
