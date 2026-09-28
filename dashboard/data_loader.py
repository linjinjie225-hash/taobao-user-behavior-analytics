"""Load the dashboard's committed aggregate result files."""

from dataclasses import dataclass
import json
from math import isfinite
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

NONNEGATIVE_NUMERIC_COLUMNS = {
    "daily_metrics.csv": {"events", "active_users", "buy"},
    "hourly_metrics.csv": {"event_hour", "events", "active_users", "buy"},
    "user_funnel.csv": {"users"},
    "retention.csv": {"day_offset", "eligible_users", "retained_users"},
    "category_metrics.csv": {
        "pv",
        "cart",
        "fav",
        "buy",
        "active_users",
        "events",
    },
}

RATE_COLUMNS = {
    "user_funnel.csv": {"vs_view_rate"},
    "retention.csv": {"retention_rate"},
    "category_metrics.csv": {"buy_to_pv_rate"},
}

REQUIRED_METRIC_SECTIONS = {
    "basic",
    "funnel",
    "retention",
    "repeat_purchase",
    "data_quality",
}


def _validate_numeric_columns(table: pd.DataFrame, name: str) -> pd.DataFrame:
    numeric_columns = NONNEGATIVE_NUMERIC_COLUMNS.get(name, set()) | RATE_COLUMNS.get(
        name, set()
    )
    for column in sorted(numeric_columns):
        converted = pd.to_numeric(table[column], errors="coerce")
        if converted.isna().any() or not all(map(isfinite, converted)):
            raise PortfolioDataError(
                f"Invalid {name}; column {column} must contain finite numeric values"
            )
        if column in NONNEGATIVE_NUMERIC_COLUMNS.get(name, set()) and (
            converted < 0
        ).any():
            raise PortfolioDataError(
                f"Invalid {name}; column {column} must be nonnegative"
            )
        if column in RATE_COLUMNS.get(name, set()) and (
            ((converted < 0) | (converted > 1)).any()
        ):
            raise PortfolioDataError(
                f"Invalid {name}; column {column} must be between 0 and 1"
            )
        table[column] = converted
    return table


def _read_csv(root: Path, name: str) -> pd.DataFrame:
    table_path = root / "results" / "tables" / name
    if not table_path.exists():
        raise PortfolioDataError(
            f"Missing result file: results/tables/{name}. "
            "Run python src/run_pipeline.py."
        )

    try:
        table = pd.read_csv(table_path)
    except (
        OSError,
        UnicodeError,
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
    ) as exc:
        raise PortfolioDataError(
            f"Unable to read results/tables/{name}: {exc}"
        ) from exc
    missing = TABLE_SCHEMAS[name] - set(table.columns)
    if missing:
        raise PortfolioDataError(
            f"Invalid {name}; missing columns: {', '.join(sorted(missing))}"
        )
    return _validate_numeric_columns(table, name)


def load_portfolio_data(root: Path) -> PortfolioData:
    metrics_path = root / "results" / "metrics.json"
    if not metrics_path.exists():
        raise PortfolioDataError(
            "Missing result file: results/metrics.json. Run python src/run_pipeline.py."
        )
    try:
        with metrics_path.open(encoding="utf-8") as metrics_file:
            metrics = json.load(metrics_file)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PortfolioDataError(
            f"Unable to read results/metrics.json: {exc}"
        ) from exc
    if not isinstance(metrics, dict):
        raise PortfolioDataError(
            "Invalid results/metrics.json; expected a JSON object."
        )
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
