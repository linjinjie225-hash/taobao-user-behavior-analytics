import pandas as pd
import plotly.graph_objects as go
import pytest

from dashboard.charts import (
    activity_chart,
    category_chart,
    funnel_chart,
    retention_chart,
)


def test_activity_chart_contains_series_and_title() -> None:
    daily = pd.DataFrame(
        {
            "event_date": ["2017-11-25", "2017-11-26"],
            "events": [10, 15],
            "buy": [2, 3],
        }
    )

    figure = activity_chart(daily, "event_date", "每日活跃趋势")

    assert figure.data
    assert figure.layout.title.text == "每日活跃趋势"
    assert figure.data[1].name == "购买行为量"
    assert figure.layout.yaxis2.title.text == "购买行为量"


def test_funnel_chart_contains_stage_coverage_data() -> None:
    funnel = pd.DataFrame(
        {
            "stage": ["浏览", "加购", "购买"],
            "users": [100, 40, 20],
            "vs_view_rate": [1.0, 0.4, 0.2],
        }
    )

    figure = funnel_chart(funnel)

    assert figure.data
    assert "非会话顺序漏斗" in figure.layout.title.text


def test_retention_chart_uses_percentage_axis() -> None:
    retention = pd.DataFrame(
        {
            "day_offset": [1, 2, 3],
            "retention_rate": [0.5, 0.35, 0.2],
        }
    )

    figure = retention_chart(retention)

    assert figure.data
    assert figure.layout.yaxis.tickformat == ".0%"


def test_category_chart_contains_purchase_data_in_reading_order() -> None:
    category = pd.DataFrame(
        {
            "category_id": [101, 102, 103],
            "pv": [100, 80, 120],
            "buy": [8, 3, 12],
            "active_users": [50, 40, 60],
            "buy_to_pv_rate": [0.08, 0.0375, 0.1],
        }
    )

    figure = category_chart(category)

    assert figure.data
    assert list(figure.data[0].y) == ["102", "101", "103"]
    assert figure.layout.xaxis.title.text == "购买行为量"
    hover_template = figure.data[0].hovertemplate
    assert "浏览行为量" in hover_template
    assert "活跃用户数" in hover_template
    assert "购买/浏览转化率" in hover_template
    assert ":.1%" in hover_template
    assert "订单" not in hover_template


@pytest.mark.parametrize(
    ("builder", "columns"),
    [
        (
            lambda frame: activity_chart(frame, "event_date", "每日活跃趋势"),
            ["event_date", "events", "buy"],
        ),
        (
            funnel_chart,
            ["stage", "users", "vs_view_rate"],
        ),
        (
            retention_chart,
            ["day_offset", "retention_rate"],
        ),
        (
            category_chart,
            ["category_id", "pv", "buy", "active_users", "buy_to_pv_rate"],
        ),
    ],
    ids=["activity", "funnel", "retention", "category"],
)
def test_chart_builders_accept_header_only_frames(builder, columns) -> None:
    figure = builder(pd.DataFrame(columns=columns))

    assert isinstance(figure, go.Figure)
