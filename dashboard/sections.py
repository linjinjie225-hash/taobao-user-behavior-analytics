"""Narrative sections for the Streamlit portfolio."""

from __future__ import annotations

from numbers import Real

import pandas as pd
import streamlit as st

from dashboard.charts import (
    activity_chart,
    category_chart,
    funnel_chart,
    retention_chart,
)
from dashboard.data_loader import PortfolioData


def _pct(value: Real | None, digits: int = 1) -> str:
    """Format a decimal ratio as a percentage for reader-facing metrics."""
    if value is None or pd.isna(value):
        return "未定义"
    return f"{float(value):.{digits}%}"


def _empty(message: str) -> None:
    st.info(message)


def render_executive(data: PortfolioData) -> None:
    """Render the recruiter-friendly executive summary."""
    basic = data.metrics["basic"]
    funnel = data.metrics["funnel"]

    st.title("购买阶段覆盖67.9%，增长机会集中在有兴趣但未购买的人群中")
    st.caption(
        "这里衡量的是去重用户的行为阶段覆盖，不是严格的会话顺序漏斗，也不代表真实转化率。"
    )
    st.write(
        "分析范围为 2017-11-25 至 2017-12-03 的 1,001,832 条有效行为事件，"
        "使用 Pandas 完成清洗与分析，并用 SQL 交叉核验核心指标。"
    )

    columns = st.columns(4)
    columns[0].metric("有效行为事件", f"{int(basic['events']):,}")
    columns[1].metric("去重用户", f"{int(basic['users']):,}")
    columns[2].metric(
        "兴趣阶段覆盖",
        _pct(funnel["engagement_rate_vs_view_users"]),
    )
    columns[3].metric(
        "购买阶段覆盖",
        _pct(funnel["buyer_rate_vs_view_users"]),
    )

    if data.funnel.empty:
        _empty("暂无行为阶段数据。请重新运行数据流水线后查看阶段覆盖。")
    else:
        st.plotly_chart(funnel_chart(data.funnel), width="stretch")

    st.subheader("观察")
    st.write(
        "8,654 名浏览用户出现收藏或加购行为，其中仍有一部分未进入购买阶段。"
        "这组人群比单纯扩大流量更接近可验证的增长机会。"
    )
    st.subheader("下一步实验")
    st.write(
        "针对收藏或加购但未购买的用户设计分层提醒，并以购买阶段覆盖的增量进行对照评估。"
    )


def render_activity(data: PortfolioData) -> None:
    st.title("22:00 出现样本内活跃峰值，周末两日行为量明显抬升")
    st.caption(
        "22:00 是这 9 天样本合并后的行为量峰值，只描述该观察窗口，不外推为长期规律。"
    )
    st.write(
        "先看每日规模变化，再看一天内的时段分布。两种粒度共同帮助确定触达实验的时间窗口。"
    )

    st.subheader("每日行为节奏")
    if data.daily.empty:
        _empty("暂无每日聚合数据。请重新运行数据流水线后查看日期趋势。")
    else:
        st.plotly_chart(
            activity_chart(data.daily, "event_date", "每日行为量与购买行为量"),
            width="stretch",
        )

    st.subheader("小时行为节奏")
    if data.hourly.empty:
        _empty("暂无小时聚合数据。请重新运行数据流水线后查看时段趋势。")
    else:
        st.plotly_chart(
            activity_chart(data.hourly, "event_hour", "小时行为量与购买行为量"),
            width="stretch",
        )

    st.info(
        "实验建议：优先比较 20:00-22:00 与日间基准时段的提醒效果，"
        "避免把单一峰值直接解释为因果机会。"
    )


def render_funnel(data: PortfolioData) -> None:
    funnel = data.metrics["funnel"]
    st.title("行为阶段覆盖显示：兴趣建立充分，购买阶段仍有提升空间")
    st.caption(
        "这是非会话顺序的去重用户阶段覆盖，各行为不要求顺序发生，"
        "也不代表浏览、兴趣、购买来自同一次访问。"
    )
    st.write(
        "该视图回答有多少用户曾到达某一行为阶段，适合描述覆盖面，"
        "不能替代按会话或路径构建的严格漏斗。"
    )

    columns = st.columns(3)
    columns[0].metric("浏览用户", f"{int(funnel['view_users']):,}")
    columns[1].metric("收藏或加购用户", f"{int(funnel['engaged_users']):,}")
    columns[2].metric("购买用户", f"{int(funnel['buyer_users']):,}")

    if data.funnel.empty:
        _empty("暂无行为阶段数据。请重新运行数据流水线后查看阶段覆盖。")
    else:
        st.plotly_chart(funnel_chart(data.funnel), width="stretch")

    st.warning(
        "解读边界：购买用户表示样本期内至少出现一次购买行为的用户，"
        "不表示从同一次浏览按顺序转化而来。"
    )


def render_retention(data: PortfolioData) -> None:
    repeat = data.metrics["repeat_purchase"]
    st.title("短周期活跃留存稳定，重复购买代理仍需谨慎解释")
    st.caption(
        "留存以用户首次出现日为起点，观察后续指定天是否仍有任一行为；窗口仅覆盖 9 天。"
    )

    if data.retention.empty:
        _empty("暂无留存聚合数据。请重新运行数据流水线后查看短周期留存。")
    else:
        st.plotly_chart(retention_chart(data.retention), width="stretch")

    st.subheader("重复购买代理")
    columns = st.columns(2)
    columns[0].metric(
        "重复购买行为买家占比",
        _pct(repeat["repeat_event_buyer_rate"]),
        help="样本期内出现至少两次购买行为的买家占比。",
    )
    columns[1].metric(
        "跨日重复购买行为买家占比",
        _pct(repeat["repeat_day_buyer_rate"]),
        help="样本期内至少两个自然日出现购买行为的买家占比。",
    )
    st.warning(
        "源数据无订单 ID，以上指标是购买行为与跨日购买行为代理，"
        "不是真实订单复购率，也不能识别一次订单内的多条商品行为。"
    )


def render_category(data: PortfolioData) -> None:
    st.title("购买行为量与购买/浏览行为比需要同时观察")
    st.caption(
        "购买/浏览行为比是购买行为量除以浏览行为量，属于事件数之比，"
        "不是用户转化概率；当浏览行为量为 0 时记为未定义。"
    )
    st.write(
        "购买行为量反映机会规模，购买/浏览行为比帮助识别行为结构。"
        "两者一起看，可以避免只追逐高占比但规模很小的类目。"
    )

    if data.category.empty:
        _empty("暂无类目聚合数据。请重新运行数据流水线后查看类目机会。")
        return

    figure = category_chart(data.category)
    figure.update_traces(marker_color="#f97316")
    st.plotly_chart(figure, width="stretch")

    st.subheader("购买行为量 Top 20")
    top_categories = data.category.nlargest(20, "buy")[
        ["category_id", "pv", "buy", "buy_to_pv_rate", "active_users"]
    ].copy()
    top_categories["buy_to_pv_rate"] = top_categories["buy_to_pv_rate"].map(
        lambda value: "未定义" if pd.isna(value) else f"{float(value):.3f}×"
    )
    st.dataframe(top_categories, width="stretch", hide_index=True)


def render_trust(data: PortfolioData) -> None:
    quality = data.metrics["data_quality"]
    st.title("数据可信度：结论可复现，边界也必须同时公开")
    st.caption(
        "固定抽样规则：选择 user_id % 100 == 0 的用户，并保留这些用户在窗口内的全部行为。"
    )

    columns = st.columns(3)
    columns[0].metric("原始样本事件", f"{int(quality['input_rows']):,}")
    columns[1].metric("清洗移除事件", f"{int(quality['rows_removed_total']):,}")
    columns[2].metric("有效行为事件", f"{int(quality['clean_rows']):,}")

    st.subheader("双路径核验")
    st.write(
        "Pandas 负责清洗、聚合与输出；SQL 独立重算核心规模、阶段覆盖和重复购买代理，"
        "用于交叉检查口径与结果。"
    )

    st.subheader("AI 与人工分工")
    st.info(
        "AI 参与代码脚手架、测试补全和文案一致性检查。"
        "人工负责业务问题、指标定义、抽样规则、结果复核与最终发布判断。"
    )

    st.subheader("已知限制")
    st.warning(
        "数据窗口仅为 2017-11-25 至 2017-12-03，且无金额、订单 ID、渠道和用户属性。"
        "因此不能计算 GMV、客单价或真实订单复购率，也不能据此做总体外推。"
    )
