import json
from pathlib import Path

import pandas as pd
import pytest

from dashboard.data_loader import PortfolioDataError, load_portfolio_data


def write_fixture(root: Path) -> None:
    tables = root / "results" / "tables"
    tables.mkdir(parents=True)

    metrics = {
        "basic": {"events": 10},
        "funnel": {"view_users": 4},
        "retention": {"day_1": 0.5},
        "repeat_purchase": {"rate": 0.25},
        "data_quality": {"invalid_rows": 0},
    }
    (root / "results" / "metrics.json").write_text(
        json.dumps(metrics), encoding="utf-8"
    )

    fixtures = {
        "daily_metrics.csv": pd.DataFrame(
            [{"event_date": "2017-11-25", "events": 10, "active_users": 4, "buy": 2}]
        ),
        "hourly_metrics.csv": pd.DataFrame(
            [{"event_hour": 9, "events": 10, "active_users": 4, "buy": 2}]
        ),
        "user_funnel.csv": pd.DataFrame(
            [{"stage": "view", "users": 4, "vs_view_rate": 1.0}]
        ),
        "retention.csv": pd.DataFrame(
            [
                {
                    "day_offset": 1,
                    "eligible_users": 4,
                    "retained_users": 2,
                    "retention_rate": 0.5,
                }
            ]
        ),
        "category_metrics.csv": pd.DataFrame(
            [
                {
                    "category_id": 101,
                    "pv": 10,
                    "cart": 3,
                    "fav": 2,
                    "buy": 1,
                    "active_users": 4,
                    "buy_to_pv_rate": 0.1,
                    "events": 16,
                }
            ]
        ),
    }
    for name, frame in fixtures.items():
        frame.to_csv(tables / name, index=False)


def test_load_portfolio_data_returns_validated_aggregates(tmp_path: Path) -> None:
    write_fixture(tmp_path)

    data = load_portfolio_data(tmp_path)

    assert data.metrics["basic"]["events"] == 10
    assert data.daily.iloc[0]["events"] == 10
    assert list(data.category.columns) == [
        "category_id",
        "pv",
        "cart",
        "fav",
        "buy",
        "active_users",
        "buy_to_pv_rate",
        "events",
    ]


def test_load_portfolio_data_reports_missing_metrics(tmp_path: Path) -> None:
    with pytest.raises(PortfolioDataError, match=r"results/metrics\.json"):
        load_portfolio_data(tmp_path)


def test_load_portfolio_data_reports_missing_daily_column(tmp_path: Path) -> None:
    write_fixture(tmp_path)
    pd.DataFrame(
        [{"event_date": "2017-11-25", "active_users": 4, "buy": 2}]
    ).to_csv(tmp_path / "results" / "tables" / "daily_metrics.csv", index=False)

    with pytest.raises(
        PortfolioDataError, match=r"daily_metrics\.csv.*events"
    ):
        load_portfolio_data(tmp_path)


def test_load_portfolio_data_reports_missing_metric_section(tmp_path: Path) -> None:
    write_fixture(tmp_path)
    metrics_path = tmp_path / "results" / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    del metrics["retention"]
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8")

    with pytest.raises(PortfolioDataError, match=r"metrics\.json.*retention"):
        load_portfolio_data(tmp_path)


def test_load_portfolio_data_wraps_invalid_metrics_json(tmp_path: Path) -> None:
    metrics_path = tmp_path / "results" / "metrics.json"
    metrics_path.parent.mkdir(parents=True)
    metrics_path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(
        PortfolioDataError, match=r"results/metrics\.json"
    ) as exc_info:
        load_portfolio_data(tmp_path)

    assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)


def test_load_portfolio_data_wraps_invalid_metrics_encoding(tmp_path: Path) -> None:
    metrics_path = tmp_path / "results" / "metrics.json"
    metrics_path.parent.mkdir(parents=True)
    metrics_path.write_bytes(b"\xff")

    with pytest.raises(
        PortfolioDataError, match=r"results/metrics\.json"
    ) as exc_info:
        load_portfolio_data(tmp_path)

    assert isinstance(exc_info.value.__cause__, UnicodeError)


@pytest.mark.parametrize(
    "payload",
    [
        ["basic", "funnel", "retention", "repeat_purchase", "data_quality"],
        None,
        7,
        "basic",
    ],
    ids=["list", "null", "number", "string"],
)
def test_load_portfolio_data_rejects_non_object_metrics(
    tmp_path: Path, payload: object
) -> None:
    metrics_path = tmp_path / "results" / "metrics.json"
    metrics_path.parent.mkdir(parents=True)
    metrics_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        PortfolioDataError, match=r"results/metrics\.json.*JSON object"
    ):
        load_portfolio_data(tmp_path)


def test_load_portfolio_data_wraps_malformed_csv(tmp_path: Path) -> None:
    write_fixture(tmp_path)
    daily_path = tmp_path / "results" / "tables" / "daily_metrics.csv"
    daily_path.write_text(
        'event_date,events,active_users,buy\n"unterminated', encoding="utf-8"
    )

    with pytest.raises(
        PortfolioDataError, match=r"results/tables/daily_metrics\.csv"
    ) as exc_info:
        load_portfolio_data(tmp_path)

    assert isinstance(exc_info.value.__cause__, pd.errors.ParserError)


def test_load_portfolio_data_wraps_invalid_csv_encoding(tmp_path: Path) -> None:
    write_fixture(tmp_path)
    daily_path = tmp_path / "results" / "tables" / "daily_metrics.csv"
    daily_path.write_bytes(
        b"event_date,events,active_users,buy\n\xff,10,4,2"
    )

    with pytest.raises(
        PortfolioDataError, match=r"results/tables/daily_metrics\.csv"
    ) as exc_info:
        load_portfolio_data(tmp_path)

    assert isinstance(exc_info.value.__cause__, UnicodeError)
