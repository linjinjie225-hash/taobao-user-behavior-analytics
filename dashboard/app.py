"""Streamlit entrypoint for the Taobao user-behavior data story."""

from __future__ import annotations

import os
from pathlib import Path
import sys

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(os.environ.get("TAOBAO_DASHBOARD_ROOT", ROOT)).resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.data_loader import PortfolioDataError, load_portfolio_data
from dashboard.sections import (
    render_activity,
    render_category,
    render_executive,
    render_funnel,
    render_retention,
    render_trust,
)


st.set_page_config(
    page_title="淘宝用户行为分析",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --accent: #f97316;
        --ink: #0f172a;
        --muted: #475569;
        --line: #e2e8f0;
        --surface: #ffffff;
        --radius: 12px;
    }
    .stApp { background: #f8fafc; color: var(--ink); }
    .block-container {
        max-width: 1180px;
        padding-top: 3.2rem;
        padding-bottom: 4rem;
    }
    h1 {
        max-width: 900px;
        color: var(--ink);
        font-weight: 760;
        letter-spacing: -0.035em;
        line-height: 1.16;
    }
    h2, h3 { color: var(--ink); letter-spacing: -0.018em; }
    p, [data-testid="stCaptionContainer"] { color: var(--muted); }
    [data-testid="stMetric"] {
        min-height: 112px;
        padding: 1rem 1.1rem;
        border: 1px solid var(--line);
        border-radius: var(--radius);
        background: var(--surface);
        box-shadow: none;
    }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stMetricValue"] {
        color: var(--ink);
        font-variant-numeric: tabular-nums;
    }
    [data-testid="stSidebar"] {
        background: var(--surface);
        border-right: 1px solid var(--line);
    }
    [data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {
        border-radius: var(--radius);
        overflow: hidden;
    }
    div[role="radiogroup"] label { border-radius: var(--radius); }
    div[role="radiogroup"] label:has(input:checked) {
        background: #fff7ed;
        color: #9a3412;
    }
    @media (max-width: 768px) {
        .block-container { padding: 1.5rem 1rem 3rem; }
        h1 { font-size: 2rem !important; letter-spacing: -0.025em; }
        [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
        [data-testid="stHorizontalBlock"] > div { min-width: 46%; }
    }
    @media (max-width: 560px) {
        [data-testid="stHorizontalBlock"] > div { min-width: 100%; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


try:
    portfolio = load_portfolio_data(DATA_ROOT)
except PortfolioDataError as exc:
    st.error(f"聚合结果加载失败：{exc}")
    st.code("python src/run_pipeline.py", language="powershell")
    st.stop()


PAGES = {
    "执行摘要": render_executive,
    "活跃节奏": render_activity,
    "行为阶段": render_funnel,
    "留存与重复购买代理": render_retention,
    "类目机会": render_category,
    "数据可信度": render_trust,
}

st.sidebar.title("淘宝用户行为分析")
selection = st.sidebar.radio("选择章节", list(PAGES), label_visibility="collapsed")
basic = portfolio.metrics["basic"]
st.sidebar.caption(
    f"数据范围：{basic['date_start']} 至 {basic['date_end']}\n\n"
    f"有效行为事件：{int(basic['events']):,}"
)
PAGES[selection](portfolio)
