from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sqlite_verify import verify_behavior_counts


def test_sql_behavior_counts_equal_pandas_counts(tmp_path):
    frame = pd.DataFrame({"behavior": ["pv", "pv", "cart", "buy"]})
    assert verify_behavior_counts(frame, tmp_path / "test.db") == {
        "buy": 1,
        "cart": 1,
        "pv": 2,
    }
