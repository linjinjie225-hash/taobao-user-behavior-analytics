from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analysis import clean_events, repeat_purchase_metrics


def test_clean_events_removes_duplicates_and_invalid_rows():
    frame = pd.DataFrame(
        [
            [1, 11, 111, "pv", 1511568000],
            [1, 11, 111, "pv", 1511568000],
            [2, 22, 222, "bad", 1511568000],
        ],
        columns=["user_id", "item_id", "category_id", "behavior", "timestamp"],
    )
    cleaned, audit = clean_events(frame)
    assert len(cleaned) == 1
    assert audit["duplicate_rows_removed"] == 1
    assert audit["invalid_behavior_rows_removed"] == 1


def test_repeat_purchase_metrics_uses_events_and_days():
    frame = pd.DataFrame(
        {
            "user_id": [1, 1, 1, 2],
            "behavior": ["buy", "buy", "pv", "buy"],
            "event_date": pd.to_datetime(
                ["2017-11-25", "2017-11-26", "2017-11-26", "2017-11-25"]
            ).date,
        }
    )
    result = repeat_purchase_metrics(frame)
    assert result["buyers"] == 2
    assert result["buyers_with_2plus_buy_events"] == 1
    assert result["buyers_with_2plus_purchase_days"] == 1
