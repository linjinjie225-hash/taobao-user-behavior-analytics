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


def _sample_days(basic: dict[str, object]) -> int:
    start = pd.Timestamp(str(basic["date_start"]))
    end = pd.Timestamp(str(basic["date_end"]))
    return int((end - start).days) + 1


def render_executive(data: PortfolioData) -> None:
    """Render the recruiter-friendly executive summary."""
    basic = data.metrics["basic"]
    funnel = data.metrics["funnel"]
    engagement_rate = float(funnel["engagement_rate_vs_view_users"])
    buyer_rate = float(funnel["buyer_rate_vs_view_users"])
    comparison = "低于" if buyer_rate <= engagement_rate else "高于"
    coverage_gap = abs(engagement_rate - buyer_rate)

    st.title(
        f"购买阶段覆盖{_pct(buyer_rate)}，{comparison}兴趣阶段覆盖"
        f"{_pct(engagement_rate)}"
    )
    st.caption(
        "这里衡量的是去重用户的行为阶段覆盖，不是严格的会话顺序漏斗，也不代表真实转化率。"
    )
    st.write(
        f"分析范围为 {basic['date_start']} 至 {basic['date_end']} 的 "
        f"{int(basic['events']):,} 条有效行为事件，"
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
        st.plotly_chart(funnel_chart(data.funnel), use_container_width=True)

    st.subheader("观察")
    st.write(
        f"兴趣阶段覆盖与购买阶段覆盖相差 {coverage_gap * 100:.1f} 个百分点。"
        "两者是分别计算的独立覆盖率，"
        "不是嵌套人群，也不能据此推算有兴趣但未购买的人数。"
    )
    st.subheader("下一步实验")
    st.write(
        "先计算用户级 engaged_without_buy 交集人群并验证口径，"
        "再决定是否对该人群进行分层触达与对照测试。"
    )


def render_activity(data: PortfolioData) -> None:
    basic = data.metrics["basic"]
    sample_days = _sample_days(basic)
    peak_hour = None
    if not data.hourly.empty:
        peak_hour = int(data.hourly.loc[data.hourly["events"].idxmax(), "event_hour"])

    if peak_hour is None:
        st.title("当前样本的小时活跃峰值尚不可用")
        peak_label = "小时峰值"
    else:
        peak_label = f"{peak_hour:02d}:00"
        st.title(f"{peak_label} 是当前样本内的活跃峰值")
    st.caption(
        f"{peak_label} 是 {basic['date_start']} 至 {basic['date_end']} 这 "
        f"{sample_days} 天样本合并后的发现，只描述该观察窗口，不外推为长期规律。"
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
            use_container_width=True,
        )

    st.subheader("小时行为节奏")
    if data.hourly.empty:
        _empty("暂无小时聚合数据。请重新运行数据流水线后查看时段趋势。")
    else:
        st.plotly_chart(
            activity_chart(data.hourly, "event_hour", "小时行为量与购买行为量"),
            use_container_width=True,
        )

    st.info(
        "实验建议：优先比较样本峰值附近与日间基准时段的提醒效果，"
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
        st.plotly_chart(funnel_chart(data.funnel), use_container_width=True)

    st.warning(
        "解读边界：购买用户表示样本期内至少出现一次购买行为的用户，"
        "不表示从同一次浏览按顺序转化而来。"
    )


def render_retention(data: PortfolioData) -> None:
    basic = data.metrics["basic"]
    repeat = data.metrics["repeat_purchase"]
    st.title("短周期活跃留存稳定，重复购买代理仍需谨慎解释")
    st.caption(
        "留存以用户首次出现日为起点，观察后续指定天是否仍有任一行为；"
        f"窗口仅覆盖 {_sample_days(basic)} 天。"
    )

    if data.retention.empty:
        _empty("暂无留存聚合数据。请重新运行数据流水线后查看短周期留存。")
    else:
        st.plotly_chart(retention_chart(data.retention), use_container_width=True)

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
    st.plotly_chart(figure, use_container_width=True)

    st.subheader("购买行为量 Top 20")
    top_categories = data.category.nlargest(20, "buy")[
        ["category_id", "pv", "buy", "buy_to_pv_rate", "active_users"]
    ].copy()
    top_categories["buy_to_pv_rate"] = top_categories["buy_to_pv_rate"].map(
        lambda value: "未定义" if pd.isna(value) else f"{float(value):.3f}×"
    )
    top_categories = top_categories.rename(
        columns={
            "category_id": "类目ID",
            "pv": "浏览行为量",
            "buy": "购买行为量",
            "buy_to_pv_rate": "购买/浏览行为比",
            "active_users": "活跃用户数",
        }
    )
    st.dataframe(top_categories, use_container_width=True, hide_index=True)


def render_trust(data: PortfolioData) -> None:
    basic = data.metrics["basic"]
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
        f"数据窗口仅为 {basic['date_start']} 至 {basic['date_end']}，"
        "且无金额、订单 ID、渠道和用户属性。"
        "因此不能计算 GMV、客单价或真实订单复购率，也不能据此做总体外推。"
    )
