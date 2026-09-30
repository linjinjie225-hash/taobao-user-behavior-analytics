from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    CHARTS_DIR,
    CLEAN_PATH,
    END_DATE,
    METRICS_PATH,
    SAMPLE_PATH,
    START_DATE,
    TABLES_DIR,
    VALID_BEHAVIORS,
    ensure_directories,
)


def _as_int(value) -> int:
    return int(value) if pd.notna(value) else 0


def clean_events(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    working = frame.copy()
    audit = {"input_rows": len(working)}

    missing_mask = working.isna().any(axis=1)
    audit["missing_rows_removed"] = _as_int(missing_mask.sum())
    working = working.loc[~missing_mask].copy()

    for column in ["user_id", "item_id", "category_id", "timestamp"]:
        working[column] = pd.to_numeric(working[column], errors="coerce")
    invalid_id_mask = working[["user_id", "item_id", "category_id", "timestamp"]].isna().any(axis=1)
    invalid_id_mask |= working[["user_id", "item_id", "category_id"]].le(0).any(axis=1)
    audit["invalid_id_rows_removed"] = _as_int(invalid_id_mask.sum())
    working = working.loc[~invalid_id_mask].copy()

    working["behavior"] = working["behavior"].astype(str).str.strip().str.lower()
    invalid_behavior_mask = ~working["behavior"].isin(VALID_BEHAVIORS)
    audit["invalid_behavior_rows_removed"] = _as_int(invalid_behavior_mask.sum())
    working = working.loc[~invalid_behavior_mask].copy()

    working["event_time"] = (
        pd.to_datetime(working["timestamp"], unit="s", utc=True, errors="coerce")
        .dt.tz_convert("Asia/Shanghai")
        .dt.tz_localize(None)
    )
    out_of_range_mask = working["event_time"].isna() | ~working["event_time"].between(
        pd.Timestamp(START_DATE), pd.Timestamp(END_DATE) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    )
    audit["out_of_range_rows_removed"] = _as_int(out_of_range_mask.sum())
    working = working.loc[~out_of_range_mask].copy()

    before = len(working)
    working = working.drop_duplicates(subset=["user_id", "item_id", "category_id", "behavior", "timestamp"])
    audit["duplicate_rows_removed"] = before - len(working)

    for column in ["user_id", "item_id", "category_id", "timestamp"]:
        working[column] = working[column].astype("int64")
    working["event_date"] = working["event_time"].dt.date
    working["event_hour"] = working["event_time"].dt.hour.astype("int8")
    working = working.sort_values(["event_time", "user_id", "item_id"]).reset_index(drop=True)
    audit["clean_rows"] = len(working)
    audit["rows_removed_total"] = audit["input_rows"] - audit["clean_rows"]
    return working, audit


def basic_metrics(frame: pd.DataFrame) -> dict:
    behavior_counts = frame["behavior"].value_counts().reindex(["pv", "cart", "fav", "buy"], fill_value=0)
    return {
        "events": len(frame),
        "users": frame["user_id"].nunique(),
        "items": frame["item_id"].nunique(),
        "categories": frame["category_id"].nunique(),
        "behavior_events": {key: int(value) for key, value in behavior_counts.items()},
        "date_start": str(frame["event_date"].min()),
        "date_end": str(frame["event_date"].max()),
    }


def daily_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    total = frame.groupby("event_date").agg(events=("behavior", "size"), active_users=("user_id", "nunique"))
    behavior = frame.pivot_table(index="event_date", columns="behavior", values="user_id", aggfunc="size", fill_value=0)
    result = total.join(behavior).reset_index()
    return result.rename_axis(None, axis=1)


def hourly_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    total = frame.groupby("event_hour").agg(events=("behavior", "size"), active_users=("user_id", "nunique"))
    behavior = frame.pivot_table(index="event_hour", columns="behavior", values="user_id", aggfunc="size", fill_value=0)
    return total.join(behavior).reset_index().rename_axis(None, axis=1)


def user_behavior_funnel(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    users_by_behavior = frame.groupby("behavior")["user_id"].nunique().to_dict()
    stage_users = {
        "view_users": int(users_by_behavior.get("pv", 0)),
        "engaged_users": int(frame.loc[frame["behavior"].isin(["cart", "fav"]), "user_id"].nunique()),
        "buyer_users": int(users_by_behavior.get("buy", 0)),
    }
    base = max(stage_users["view_users"], 1)
    table = pd.DataFrame(
        {
            "stage": ["浏览用户", "收藏/加购用户", "购买用户"],
            "users": [stage_users["view_users"], stage_users["engaged_users"], stage_users["buyer_users"]],
        }
    )
    table["vs_view_rate"] = table["users"] / base
    metrics = {
        **stage_users,
        "engagement_rate_vs_view_users": stage_users["engaged_users"] / base,
        "buyer_rate_vs_view_users": stage_users["buyer_users"] / base,
        "definition": "Distinct-user behavior-stage proxy; not a session-sequential funnel.",
    }
    return table, metrics


def retention_table(frame: pd.DataFrame, offsets=(1, 3, 7)) -> tuple[pd.DataFrame, dict]:
    active = frame[["user_id", "event_date"]].drop_duplicates().copy()
    active["event_date"] = pd.to_datetime(active["event_date"])
    first = active.groupby("user_id", as_index=False)["event_date"].min().rename(columns={"event_date": "cohort_date"})
    joined = active.merge(first, on="user_id", how="left")
    joined["day_offset"] = (joined["event_date"] - joined["cohort_date"]).dt.days
    max_date = active["event_date"].max()
    rows = []
    weighted = {}
    for offset in offsets:
        eligible_cohorts = first.loc[first["cohort_date"] + pd.Timedelta(days=offset) <= max_date]
        eligible_users = set(eligible_cohorts["user_id"])
        retained_users = set(joined.loc[(joined["day_offset"] == offset) & joined["user_id"].isin(eligible_users), "user_id"])
        denominator = len(eligible_users)
        rate = len(retained_users) / denominator if denominator else np.nan
        rows.append({"day_offset": offset, "eligible_users": denominator, "retained_users": len(retained_users), "retention_rate": rate})
        weighted[f"d{offset}_retention_rate"] = None if denominator == 0 else rate
        weighted[f"d{offset}_eligible_users"] = denominator
    return pd.DataFrame(rows), weighted


def repeat_purchase_metrics(frame: pd.DataFrame) -> dict:
    buys = frame.loc[frame["behavior"].eq("buy"), ["user_id", "event_date"]].copy()
    if buys.empty:
        return {
            "buyers": 0,
            "buyers_with_2plus_buy_events": 0,
            "buyers_with_2plus_purchase_days": 0,
            "repeat_event_buyer_rate": 0.0,
            "repeat_day_buyer_rate": 0.0,
        }
    by_user = buys.groupby("user_id").agg(buy_events=("event_date", "size"), purchase_days=("event_date", "nunique"))
    buyers = len(by_user)
    event_repeat = int(by_user["buy_events"].ge(2).sum())
    day_repeat = int(by_user["purchase_days"].ge(2).sum())
    return {
        "buyers": buyers,
        "buyers_with_2plus_buy_events": event_repeat,
        "buyers_with_2plus_purchase_days": day_repeat,
        "repeat_event_buyer_rate": event_repeat / buyers,
        "repeat_day_buyer_rate": day_repeat / buyers,
        "definition": "Purchase-event proxy because the source has no order ID.",
    }


def category_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    counts = frame.pivot_table(index="category_id", columns="behavior", values="user_id", aggfunc="size", fill_value=0)
    for column in ["pv", "cart", "fav", "buy"]:
        if column not in counts:
            counts[column] = 0
    users = frame.groupby("category_id")["user_id"].nunique().rename("active_users")
    result = counts.join(users).reset_index()
    result["buy_to_pv_rate"] = np.where(result["pv"] > 0, result["buy"] / result["pv"], np.nan)
    result["events"] = result[["pv", "cart", "fav", "buy"]].sum(axis=1)
    return result.sort_values(["buy", "pv"], ascending=False).reset_index(drop=True)


def _json_ready(value):
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    return value


def run_analysis(sample_path: Path = SAMPLE_PATH) -> dict:
    ensure_directories()
    frame = pd.read_csv(sample_path)
    cleaned, audit = clean_events(frame)
    cleaned.to_csv(CLEAN_PATH, index=False, compression="gzip")

    daily = daily_metrics(cleaned)
    hourly = hourly_metrics(cleaned)
    funnel, funnel_metrics = user_behavior_funnel(cleaned)
    retention, retention_metrics = retention_table(cleaned)
    category = category_metrics(cleaned)
    repeat = repeat_purchase_metrics(cleaned)
    base = basic_metrics(cleaned)

    tables = {
        "daily_metrics": daily,
        "hourly_metrics": hourly,
        "user_funnel": funnel,
        "retention": retention,
        "category_metrics": category,
        "data_quality": pd.DataFrame([audit]),
    }
    for name, table in tables.items():
        table.to_csv(TABLES_DIR / f"{name}.csv", index=False, encoding="utf-8-sig")

    top_categories = category.head(10)[["category_id", "pv", "buy", "buy_to_pv_rate", "active_users"]].to_dict(orient="records")
    metrics = _json_ready(
        {
            "data_quality": audit,
            "basic": base,
            "funnel": funnel_metrics,
            "retention": retention_metrics,
            "repeat_purchase": repeat,
            "top_categories_by_buy_events": top_categories,
        }
    )
    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    return metrics


def main() -> None:
    metrics = run_analysis()
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
