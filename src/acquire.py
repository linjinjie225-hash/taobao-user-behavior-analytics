from __future__ import annotations

import hashlib
import json
import shutil
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config import (
    COLUMNS,
    MANIFEST_PATH,
    MIRROR_DOWNLOAD_URL,
    OFFICIAL_URL,
    SAMPLE_MODULUS,
    SAMPLE_PATH,
    SAMPLE_REMAINDER,
    ZIP_PATH,
    ensure_directories,
)


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def select_sample(frame: pd.DataFrame, modulus: int = 100, remainder: int = 0) -> pd.DataFrame:
    return frame.loc[frame["user_id"].mod(modulus).eq(remainder)].copy()


def download_if_needed(url: str = MIRROR_DOWNLOAD_URL, destination: Path = ZIP_PATH) -> None:
    if destination.exists() and destination.stat().st_size > 900_000_000:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(url, timeout=60) as response, partial.open("wb") as output:
        shutil.copyfileobj(response, output, length=8 * 1024 * 1024)
    partial.replace(destination)


def build_sample(
    zip_path: Path = ZIP_PATH,
    output_path: Path = SAMPLE_PATH,
    modulus: int = SAMPLE_MODULUS,
    remainder: int = SAMPLE_REMAINDER,
    chunksize: int = 1_000_000,
) -> dict:
    ensure_directories()
    if output_path.exists():
        output_path.unlink()

    selected_rows = 0
    selected_users: set[int] = set()
    header = True
    source_rows = 0

    with zipfile.ZipFile(zip_path) as archive:
        member = archive.namelist()[0]
        with archive.open(member) as csv_file:
            reader = pd.read_csv(
                csv_file,
                header=None,
                names=COLUMNS,
                chunksize=chunksize,
                dtype={
                    "user_id": "int64",
                    "item_id": "int64",
                    "category_id": "int64",
                    "behavior": "string",
                    "timestamp": "int64",
                },
            )
            for index, chunk in enumerate(reader, start=1):
                source_rows += len(chunk)
                sample = select_sample(chunk, modulus=modulus, remainder=remainder)
                if not sample.empty:
                    sample.to_csv(
                        output_path,
                        mode="wt" if header else "at",
                        index=False,
                        header=header,
                        compression="gzip",
                    )
                    header = False
                    selected_rows += len(sample)
                    selected_users.update(sample["user_id"].unique().tolist())
                if index % 20 == 0:
                    print(f"processed={source_rows:,} selected={selected_rows:,}", flush=True)

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "official_source": OFFICIAL_URL,
        "mirror_download": MIRROR_DOWNLOAD_URL,
        "official_license": "CC BY-NC-SA 4.0",
        "official_date_window": ["2017-11-25", "2017-12-03"],
        "official_columns": COLUMNS,
        "sampling_rule": f"user_id % {modulus} == {remainder}",
        "sampling_note": "All events for selected users are retained; this is a deterministic user-level sample.",
        "source_rows_processed": source_rows,
        "sample_rows": selected_rows,
        "sample_users": len(selected_users),
        "source_zip_bytes": zip_path.stat().st_size,
        "source_zip_sha256": sha256_file(zip_path),
        "sample_bytes": output_path.stat().st_size,
        "sample_sha256": sha256_file(output_path),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    ensure_directories()
    download_if_needed()
    manifest = build_sample()
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
