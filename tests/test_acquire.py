from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acquire import select_sample


def test_select_sample_keeps_complete_user_histories():
    frame = pd.DataFrame(
        {
            "user_id": [100, 100, 101, 200, 200, 201],
            "item_id": [1, 2, 3, 4, 5, 6],
            "category_id": [10, 10, 11, 12, 12, 13],
            "behavior": ["pv", "buy", "pv", "cart", "buy", "fav"],
            "timestamp": [1511568000] * 6,
        }
    )
    sampled = select_sample(frame, modulus=100, remainder=0)
    assert sampled["user_id"].tolist() == [100, 100, 200, 200]
