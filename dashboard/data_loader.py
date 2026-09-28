"""Load the dashboard's committed aggregate result files."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import pandas as pd


class PortfolioDataError(RuntimeError):
    """Raised when a required aggregate result cannot be loaded."""


@dataclass(frozen=True)
class PortfolioData:
    metrics: dict[str, Any]
    daily: pd.DataFrame
    hourly: pd.DataFrame
    funnel: pd.DataFrame
    retention: pd.DataFrame
    category: pd.DataFrame


TABLE_SCHEMAS = {
    "daily_metrics.csv": {"event_date", "events", "active_users", "buy"},
    "hourly_metrics.csv": {"event_hour", "events", "active_users", "buy"},
    "user_funnel.csv": {"stage", "users", "vs_view_rate"},
    "retention.csv": {
        "day_offset",
        "eligible_users",
        "retained_users",
        "retention_rate",
    },
    "category_metrics.csv": {
        "category_id",
        "pv",
        "cart",
        "fav",
        "buy",
        "active_users",
        "buy_to_pv_rate",
        "events",
    },
}

REQUIRED_METRIC_SECTIONS = {
    "basic",
    "funnel",
    "retention",
    "repeat_purchase",
    "data_quality",
}


def _read_csv(root: Path, name: str) -> pd.DataFrame:
    table_path = root / "results" / "tables" / name
    if not table_path.exists():
        raise PortfolioDataError(
            f"Missing result file: results/tables/{name}. "
            "Run python src/run_pipeline.py."
        )

    table = pd.read_csv(table_path)
    missing = TABLE_SCHEMAS[name] - set(table.columns)
    if missing:
        raise PortfolioDataError(
            f"Invalid {name}; missing columns: {', '.join(sorted(missing))}"
        )
    return table


def load_portfolio_data(root: Path) -> PortfolioData:
    metrics_path = root / "results" / "metrics.json"
    if not metrics_path.exists():
        raise PortfolioDataError(
            "Missing result file: results/metrics.json. Run python src/run_pipeline.py."
        )
    try:
        with metrics_path.open(encoding="utf-8") as metrics_file:
            metrics = json.load(metrics_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise PortfolioDataError(
            f"Unable to read results/metrics.json: {exc}"
        ) from exc
    missing_sections = REQUIRED_METRIC_SECTIONS - set(metrics)
    if missing_sections:
        raise PortfolioDataError(
            "Invalid results/metrics.json; missing sections: "
            f"{', '.join(sorted(missing_sections))}"
        )

    return PortfolioData(
        metrics=metrics,
        daily=_read_csv(root, "daily_metrics.csv"),
        hourly=_read_csv(root, "hourly_metrics.csv"),
        funnel=_read_csv(root, "user_funnel.csv"),
        retention=_read_csv(root, "retention.csv"),
        category=_read_csv(root, "category_metrics.csv"),
    )
