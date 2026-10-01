"""Plotly chart builders for the portfolio dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


NAVY = "#0f172a"
ORANGE = "#f97316"
TEAL = "#0f766e"


def _finish(figure: go.Figure, title: str) -> go.Figure:
    """Apply the shared dashboard presentation without a UI dependency."""
    figure.update_layout(
        title={"text": title, "x": 0, "xanchor": "left"},
        margin={"l": 16, "r": 16, "t": 54, "b": 16},
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={
            "family": "Inter, Microsoft YaHei, sans-serif",
            "color": NAVY,
        },
        hovermode="x unified",
        legend={"orientation": "h"},
    )
    return figure


def activity_chart(
    frame: pd.DataFrame,
    x_column: str,
    title: str,
) -> go.Figure:
    """Build an activity and purchase trend chart with two y axes."""
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=frame[x_column],
            y=frame["events"],
            name="行为量",
            mode="lines+markers",
            line={"color": NAVY, "width": 3},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=frame[x_column],
            y=frame["buy"],
            name="购买行为量",
            mode="lines+markers",
            line={"color": ORANGE, "width": 2},
            yaxis="y2",
        )
    )
    figure.update_layout(
        xaxis={
            "title": {"event_date": "日期", "event_hour": "小时"}.get(
                x_column,
                x_column,
            )
        },
        yaxis={"title": "行为量"},
        yaxis2={
            "title": "购买行为量",
            "overlaying": "y",
            "side": "right",
        },
    )
    return _finish(figure, title)


def funnel_chart(frame: pd.DataFrame) -> go.Figure:
    """Build the non-sequential user-stage coverage funnel."""
    percentage_text = frame["vs_view_rate"].map(lambda value: f"{value:.1%}")
    figure = px.bar(
        frame,
        x="stage",
        y="users",
        color="stage",
        text=percentage_text,
        color_discrete_sequence=[NAVY, TEAL, ORANGE],
    )
    figure.update_traces(textposition="outside")
    figure.update_layout(
        showlegend=False,
        xaxis_title="行为阶段",
        yaxis_title="用户数",
    )
    return _finish(figure, "用户行为阶段覆盖（非会话顺序漏斗）")


def retention_chart(frame: pd.DataFrame) -> go.Figure:
    """Build short-window active retention bars."""
    x_labels = frame["day_offset"].map(lambda value: f"D{int(value)}")
    percentage_text = frame["retention_rate"].map(
        lambda value: f"{value:.0%}"
    )
    figure = go.Figure(
        go.Bar(
            x=x_labels,
            y=frame["retention_rate"],
            text=percentage_text,
            textposition="outside",
            marker_color=TEAL,
            name="留存率",
        )
    )
    figure.update_layout(
        xaxis_title="距首日天数",
        yaxis={"title": "留存率", "tickformat": ".0%"},
        showlegend=False,
    )
    return _finish(figure, "短周期活跃留存（受九天窗口限制）")


def category_chart(frame: pd.DataFrame) -> go.Figure:
    """Build a horizontal ranking of the twelve most-purchased categories."""
    if frame.empty:
        figure = go.Figure()
        figure.update_layout(
            xaxis_title="购买行为量",
            yaxis={"title": "类目 ID", "type": "category"},
        )
        return _finish(figure, "购买行为量最高的类目")

    ranked = (
        frame.nlargest(12, "buy")
        .sort_values("buy", ascending=True)
        .assign(category_id=lambda data: data["category_id"].astype(str))
    )
    figure = px.bar(
        ranked,
        x="buy",
        y="category_id",
        orientation="h",
        hover_data={
            "pv": True,
            "active_users": True,
        },
        color_discrete_sequence=[TEAL],
        labels={
            "buy": "购买行为量",
            "category_id": "类目 ID",
            "pv": "浏览行为量",
            "active_users": "活跃用户数",
            "buy_to_pv_rate": "购买/浏览行为比",
        },
    )
    hover_templates = [
        (
            "购买行为量=%{x}<br>"
            "类目 ID=%{y}<br>"
            "浏览行为量=%{customdata[0]}<br>"
            "活跃用户数=%{customdata[1]}<br>"
            "购买/浏览行为比="
            f"{'未定义' if pd.isna(ratio) else f'{ratio:.2f}×'}"
            "<extra></extra>"
        )
        for ratio in ranked["buy_to_pv_rate"]
    ]
    figure.update_traces(marker_color=TEAL, hovertemplate=hover_templates)
    category_order = ranked["category_id"].tolist()
    figure.update_layout(
        xaxis_title="购买行为量",
        yaxis={
            "title": "类目 ID",
            "type": "category",
            "categoryorder": "array",
            "categoryarray": category_order,
        },
    )
    return _finish(figure, "购买行为量最高的类目")
