from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.ticker import FuncFormatter

from config import CHARTS_DIR, TABLES_DIR, ensure_directories

NAVY = "#18344F"
TEAL = "#0F8B8D"
ORANGE = "#E07A5F"
LIGHT = "#E8F0F2"


def configure_style() -> None:
    sns.set_theme(style="whitegrid")
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 120
    plt.rcParams["savefig.dpi"] = 160


def _save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def generate_charts() -> None:
    ensure_directories()
    configure_style()
    count_formatter = FuncFormatter(
        lambda value, _pos: (
            f"{value / 1_000_000:.2f}M"
            if value >= 1_000_000
            else f"{value / 1_000:.0f}K"
            if value >= 1_000
            else f"{value:.0f}"
        )
    )

    daily = pd.read_csv(TABLES_DIR / "daily_metrics.csv")
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(daily["event_date"], daily["events"], marker="o", color=NAVY, linewidth=2.4, label="全部行为")
    ax2 = ax.twinx()
    ax2.plot(daily["event_date"], daily["buy"], marker="o", color=ORANGE, linewidth=2.0, label="购买行为")
    ax.set_title("每日用户行为趋势", loc="left", weight="bold")
    ax.set_xlabel("日期")
    ax.set_ylabel("行为次数")
    ax.yaxis.set_major_formatter(count_formatter)
    ax2.set_ylabel("购买行为次数", color=ORANGE)
    ax2.tick_params(axis="y", colors=ORANGE)
    ax2.yaxis.set_major_formatter(count_formatter)
    ax.tick_params(axis="x", rotation=30)
    lines = ax.get_lines() + ax2.get_lines()
    ax.legend(lines, [line.get_label() for line in lines], frameon=False, loc="upper left")
    _save(fig, "daily_activity.png")

    hourly = pd.read_csv(TABLES_DIR / "hourly_metrics.csv")
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(hourly["event_hour"], hourly["events"], marker="o", color=TEAL, linewidth=2.4, label="全部行为")
    ax2 = ax.twinx()
    ax2.plot(hourly["event_hour"], hourly["buy"], marker="o", color=ORANGE, linewidth=2.0, label="购买行为")
    ax.set_title("分时用户行为趋势", loc="left", weight="bold")
    ax.set_xlabel("小时")
    ax.set_ylabel("行为次数")
    ax.set_xticks(range(0, 24, 2))
    ax.yaxis.set_major_formatter(count_formatter)
    ax2.set_ylabel("购买行为次数", color=ORANGE)
    ax2.tick_params(axis="y", colors=ORANGE)
    ax2.yaxis.set_major_formatter(count_formatter)
    lines = ax.get_lines() + ax2.get_lines()
    ax.legend(lines, [line.get_label() for line in lines], frameon=False, loc="upper left")
    _save(fig, "hourly_activity.png")

    funnel = pd.read_csv(TABLES_DIR / "user_funnel.csv")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    bars = ax.bar(funnel["stage"], funnel["users"], color=[NAVY, TEAL, ORANGE])
    ax.set_title("用户行为阶段覆盖（非会话顺序漏斗）", loc="left", weight="bold")
    ax.set_ylabel("去重用户数")
    ax.yaxis.set_major_formatter(count_formatter)
    for bar, rate in zip(bars, funnel["vs_view_rate"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{rate:.1%}", ha="center", va="bottom", fontsize=10)
    _save(fig, "user_funnel.png")

    retention = pd.read_csv(TABLES_DIR / "retention.csv")
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    bars = ax.bar([f"D{int(day)}" for day in retention["day_offset"]], retention["retention_rate"], color=[TEAL, NAVY, ORANGE])
    ax.set_title("短周期活跃留存", loc="left", weight="bold")
    ax.set_ylabel("留存率")
    ax.set_ylim(0, max(0.05, retention["retention_rate"].max() * 1.22))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"{value:.0%}"))
    for bar, rate in zip(bars, retention["retention_rate"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{rate:.1%}", ha="center", va="bottom")
    _save(fig, "retention.png")

    categories = pd.read_csv(TABLES_DIR / "category_metrics.csv").head(10).sort_values("buy")
    fig, ax = plt.subplots(figsize=(8.5, 5.3))
    ax.barh(categories["category_id"].astype(str), categories["buy"], color=TEAL)
    ax.set_title("购买行为量最高的10个商品类目", loc="left", weight="bold")
    ax.set_xlabel("购买行为次数")
    ax.set_ylabel("类目ID")
    ax.xaxis.set_major_formatter(count_formatter)
    _save(fig, "category_performance.png")


if __name__ == "__main__":
    generate_charts()
