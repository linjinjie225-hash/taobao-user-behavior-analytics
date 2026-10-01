import json
import tomllib
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dashboard" / "app.py"


@pytest.fixture
def dashboard_data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide every aggregate needed by all dashboard pages."""
    tables = tmp_path / "results" / "tables"
    tables.mkdir(parents=True)
    metrics = {
        "basic": {
            "events": 12_345,
            "users": 321,
            "items": 2_000,
            "categories": 200,
            "behavior_events": {"pv": 10_000, "cart": 1_000, "fav": 500, "buy": 845},
            "date_start": "2020-01-02",
            "date_end": "2020-01-10",
        },
        "funnel": {
            "view_users": 300,
            "engaged_users": 240,
            "buyer_users": 180,
            "engagement_rate_vs_view_users": 0.8,
            "buyer_rate_vs_view_users": 0.6,
        },
        "retention": {
            "d1_retention_rate": 0.5,
            "d1_eligible_users": 300,
            "d3_retention_rate": 0.4,
            "d3_eligible_users": 280,
            "d7_retention_rate": 0.3,
            "d7_eligible_users": 200,
        },
        "repeat_purchase": {
            "buyers": 180,
            "buyers_with_2plus_buy_events": 90,
            "buyers_with_2plus_purchase_days": 72,
            "repeat_event_buyer_rate": 0.5,
            "repeat_day_buyer_rate": 0.4,
        },
        "data_quality": {
            "input_rows": 12_350,
            "rows_removed_total": 5,
            "clean_rows": 12_345,
        },
    }
    (tmp_path / "results" / "metrics.json").write_text(
        json.dumps(metrics), encoding="utf-8"
    )

    fixtures = {
        "daily_metrics.csv": pd.DataFrame(
            [
                {"event_date": "2020-01-02", "events": 5_000, "active_users": 200, "buy": 300},
                {"event_date": "2020-01-10", "events": 7_345, "active_users": 280, "buy": 545},
            ]
        ),
        "hourly_metrics.csv": pd.DataFrame(
            [
                {"event_hour": 9, "events": 4_000, "active_users": 180, "buy": 200},
                {"event_hour": 22, "events": 8_345, "active_users": 300, "buy": 645},
            ]
        ),
        "user_funnel.csv": pd.DataFrame(
            [
                {"stage": "浏览", "users": 300, "vs_view_rate": 1.0},
                {"stage": "收藏或加购", "users": 240, "vs_view_rate": 0.8},
                {"stage": "购买", "users": 180, "vs_view_rate": 0.6},
            ]
        ),
        "retention.csv": pd.DataFrame(
            [
                {"day_offset": 1, "eligible_users": 300, "retained_users": 150, "retention_rate": 0.5},
                {"day_offset": 3, "eligible_users": 280, "retained_users": 112, "retention_rate": 0.4},
                {"day_offset": 7, "eligible_users": 200, "retained_users": 60, "retention_rate": 0.3},
            ]
        ),
        "category_metrics.csv": pd.DataFrame(
            [
                {
                    "category_id": 101,
                    "pv": 100,
                    "cart": 20,
                    "fav": 10,
                    "buy": 12,
                    "active_users": 80,
                    "buy_to_pv_rate": 0.12,
                    "events": 142,
                },
                {
                    "category_id": 102,
                    "pv": 0,
                    "cart": 1,
                    "fav": 0,
                    "buy": 1,
                    "active_users": 1,
                    "buy_to_pv_rate": float("nan"),
                    "events": 2,
                },
            ]
        ),
    }
    for filename, frame in fixtures.items():
        frame.to_csv(tables / filename, index=False)

    monkeypatch.setenv("TAOBAO_DASHBOARD_ROOT", str(tmp_path))
    return tmp_path


def run_dashboard(dashboard_data_root: Path) -> AppTest:
    return AppTest.from_file(str(APP), default_timeout=10).run()


def page_text(app: AppTest) -> str:
    return " ".join(
        str(item.value)
        for kind in ("title", "caption", "markdown", "info", "warning")
        for item in app.get(kind)
    )


def test_dashboard_opens_on_executive_summary(dashboard_data_root: Path) -> None:
    app = run_dashboard(dashboard_data_root)

    assert not app.exception
    assert any(
        "购买阶段覆盖60.0%，低于兴趣阶段覆盖80.0%" in title.value
        for title in app.title
    )
    assert len(app.metric) >= 4
    assert any(metric.value == "12,345" for metric in app.metric)
    assert "2020-01-02 至 2020-01-10" in page_text(app)


def test_executive_summary_does_not_invent_an_engaged_nonbuyer_cohort(
    dashboard_data_root: Path,
) -> None:
    app = run_dashboard(dashboard_data_root)
    visible_text = page_text(app)

    assert "8,654 名浏览用户出现收藏或加购行为" not in visible_text
    assert "其中仍有一部分未进入购买阶段" not in visible_text
    assert "收藏或加购但未购买的用户设计分层提醒" not in visible_text
    assert "20.0 个百分点" in visible_text
    assert "相差 20.0%，即" not in visible_text
    assert "独立覆盖率" in visible_text
    assert "不是嵌套人群" in visible_text
    assert "engaged_without_buy" in visible_text
    assert "计算用户级" in visible_text


def test_activity_page_frames_the_peak_within_the_sample(
    dashboard_data_root: Path,
) -> None:
    app = run_dashboard(dashboard_data_root)
    app.sidebar.radio[0].set_value("活跃节奏").run()

    assert not app.exception
    assert any("22:00" in title.value for title in app.title)
    assert any("9 天样本" in caption.value for caption in app.caption)
    assert len(app.get("plotly_chart")) == 2


def test_funnel_page_explains_stage_coverage_boundary(
    dashboard_data_root: Path,
) -> None:
    app = run_dashboard(dashboard_data_root)
    app.sidebar.radio[0].set_value("行为阶段").run()

    assert not app.exception
    assert any("行为阶段" in title.value for title in app.title)
    visible_captions = " ".join(item.value for item in app.caption)
    assert "非会话" in visible_captions
    assert "不要求顺序" in visible_captions
    assert len(app.get("plotly_chart")) == 1


def test_retention_page_labels_repeat_purchase_as_a_proxy(
    dashboard_data_root: Path,
) -> None:
    app = run_dashboard(dashboard_data_root)
    app.sidebar.radio[0].set_value("留存与重复购买代理").run()

    assert not app.exception
    assert any("重复购买代理" in title.value for title in app.title)
    metric_labels = {item.label for item in app.metric}
    assert {"重复购买行为买家占比", "跨日重复购买行为买家占比"} <= metric_labels
    warnings = " ".join(item.value for item in app.warning)
    assert "无订单 ID" in warnings
    assert "不是真实订单复购率" in warnings
    assert len(app.get("plotly_chart")) == 1


def test_category_page_keeps_behavior_ratio_distinct_from_conversion(
    dashboard_data_root: Path,
) -> None:
    app = run_dashboard(dashboard_data_root)
    app.sidebar.radio[0].set_value("类目机会").run()

    assert not app.exception
    assert any(
        title.value == "购买行为量与购买/浏览行为比需要同时观察"
        for title in app.title
    )
    explanatory_text = " ".join(item.value for item in app.caption)
    assert "行为比" in explanatory_text
    assert "概率" in explanatory_text
    assert "未定义" in explanatory_text
    assert len(app.get("plotly_chart")) == 1
    assert len(app.dataframe) == 1
    displayed = app.dataframe[0].value
    assert list(displayed.columns) == [
        "类目ID",
        "浏览行为量",
        "购买行为量",
        "购买/浏览行为比",
        "活跃用户数",
    ]
    assert displayed.iloc[0].to_dict() == {
        "类目ID": 101,
        "浏览行为量": 100,
        "购买行为量": 12,
        "购买/浏览行为比": "0.120×",
        "活跃用户数": 80,
    }


def test_trust_page_discloses_reproducibility_and_limitations(
    dashboard_data_root: Path,
) -> None:
    app = run_dashboard(dashboard_data_root)
    app.sidebar.radio[0].set_value("数据可信度").run()

    assert not app.exception
    assert any("可信度" in title.value for title in app.title)
    visible_text = page_text(app)
    assert "user_id % 100 == 0" in visible_text
    assert "SQL" in visible_text
    assert "AI" in visible_text and "人工" in visible_text
    assert "2020-01-02" in visible_text and "2020-01-10" in visible_text
    assert "GMV" in visible_text and "客单价" in visible_text
    assert "真实订单复购率" in visible_text
    assert "总体外推" in visible_text


def test_sidebar_shows_stable_scope_instead_of_a_github_placeholder(
    dashboard_data_root: Path,
) -> None:
    app = run_dashboard(dashboard_data_root)
    sidebar_text = " ".join(item.value for item in app.sidebar.caption)

    assert "2020-01-02 至 2020-01-10" in sidebar_text
    assert "GitHub" not in sidebar_text
    assert "补充" not in sidebar_text


def test_dashboard_source_uses_streamlit_140_compatible_width_api() -> None:
    source = (ROOT / "dashboard" / "sections.py").read_text(encoding="utf-8")

    assert 'width="stretch"' not in source
    assert source.count("use_container_width=True") == 7


def test_phone_layout_stacks_metric_and_column_blocks() -> None:
    source = (ROOT / "dashboard" / "app.py").read_text(encoding="utf-8")

    assert "@media (max-width: 560px)" in source
    assert "min-width: 100%" in source


def test_streamlit_disables_browser_usage_telemetry() -> None:
    config = tomllib.loads(
        (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    )

    assert config["browser"]["gatherUsageStats"] is False
