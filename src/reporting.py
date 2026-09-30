from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from config import MANIFEST_PATH, METRICS_PATH, REPORT_DIR, TABLES_DIR


def pct(value) -> str:
    return f"{float(value):.1%}"


def num(value) -> str:
    return f"{int(value):,}"


def build_reports() -> None:
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    daily = pd.read_csv(TABLES_DIR / "daily_metrics.csv")
    hourly = pd.read_csv(TABLES_DIR / "hourly_metrics.csv")
    categories = pd.read_csv(TABLES_DIR / "category_metrics.csv")

    peak_day = daily.loc[daily["events"].idxmax()]
    peak_hour = hourly.loc[hourly["events"].idxmax()]
    top_category = categories.iloc[0]
    base = metrics["basic"]
    funnel = metrics["funnel"]
    retention = metrics["retention"]
    repeat = metrics["repeat_purchase"]
    quality = metrics["data_quality"]

    report = f"""# 淘宝用户行为分析报告

## 1. 项目背景

为识别电商用户活跃规律、行为阶段覆盖和潜在转化改进点，使用阿里云天池公开的淘宝用户购物行为数据集开展分析。原数据包含约1亿条行为记录；本项目按 `{manifest['sampling_rule']}` 固定抽取用户并保留其全部行为，得到 {num(manifest['sample_rows'])} 条样本记录、{num(manifest['sample_users'])} 名样本用户。

## 2. 数据与方法

数据字段包括用户ID、商品ID、类目ID、行为类型和时间戳，行为类型为浏览、收藏、加购和购买。使用 Pandas 进行清洗与指标计算，以 SQLite/SQL 复核核心指标，并用 Matplotlib/Seaborn 生成图表。

质量检查覆盖缺失值、非法ID、非法行为类型、时间范围和重复事件。清洗前 {num(quality['input_rows'])} 条，清洗后 {num(quality['clean_rows'])} 条，共剔除 {num(quality['rows_removed_total'])} 条不符合规则或重复的记录。

## 3. 核心指标

- 分析窗口：{base['date_start']} 至 {base['date_end']}。
- 有效行为：{num(base['events'])} 条；用户 {num(base['users'])} 名；商品 {num(base['items'])} 个；类目 {num(base['categories'])} 个。
- 行为结构：浏览 {num(base['behavior_events']['pv'])} 次，加购 {num(base['behavior_events']['cart'])} 次，收藏 {num(base['behavior_events']['fav'])} 次，购买 {num(base['behavior_events']['buy'])} 次。
- 行为阶段覆盖：收藏/加购用户占浏览用户 {pct(funnel['engagement_rate_vs_view_users'])}，购买用户占浏览用户 {pct(funnel['buyer_rate_vs_view_users'])}。
- 短周期留存：D1 {pct(retention['d1_retention_rate'])}，D3 {pct(retention['d3_retention_rate'])}，D7 {pct(retention['d7_retention_rate'])}。
- 购买行为代理：购买用户 {num(repeat['buyers'])} 名，其中 {pct(repeat['repeat_event_buyer_rate'])} 发生至少2次购买行为，{pct(repeat['repeat_day_buyer_rate'])} 在至少2个自然日出现购买行为。

## 4. 主要发现

1. **活跃节奏明显。** 样本行为量在 {peak_day['event_date']} 达到窗口内峰值，共 {num(peak_day['events'])} 次；分时峰值出现在 {int(peak_hour['event_hour'])}:00，说明运营触达和资源保障应重点覆盖高峰时段。
2. **兴趣与购买覆盖存在独立阶段差。** 收藏/加购用户覆盖率为 {pct(funnel['engagement_rate_vs_view_users'])}，购买用户覆盖率为 {pct(funnel['buyer_rate_vs_view_users'])}。两者相差 {(funnel['engagement_rate_vs_view_users'] - funnel['buyer_rate_vs_view_users']) * 100:.1f} 个百分点，但这只是独立去重用户总量的比较，不是“兴趣未购”人群规模。
3. **类目表现分化。** 类目 {int(top_category['category_id'])} 的购买行为量最高，为 {num(top_category['buy'])} 次；应同时结合浏览量和购买/PV行为计数比判断，而不能只按购买次数排序。该比值不是转化概率。
4. **短期重复购买行为可观测。** {pct(repeat['repeat_day_buyer_rate'])} 的购买用户在多个自然日发生购买行为，可作为短周期复购人群代理，用于后续分层运营。

## 5. 建议

- 在高活跃小时前配置提醒、推荐位和容量监控，并用分时指标观察效果。
- 先在用户层计算 `engaged_without_buy` 交集并核验规模与结构，再决定是否设计分层召回；正式上线前采用随机对照实验评估增量效果。
- 对高浏览低购买类目检查商品详情、价格竞争力、库存和履约信息；对高购买/浏览比类目增加曝光测试。
- 建立每日数据质量规则和SQL对账，监控时间范围、行为枚举、重复事件及核心指标突变。

## 6. 局限

本数据仅覆盖9天且没有价格、金额、订单ID、渠道和用户属性。本文的行为阶段不是严格的会话顺序漏斗；“复购”是基于购买事件和购买日的代理指标；购买/PV是行为计数比，可能大于1且在PV为0时无定义；结论不能直接外推到当前淘宝整体业务。

## 7. 可复现性

数据来源、镜像、哈希和抽样规则见 `data/source_manifest.json`；核心SQL见 `sql/analysis_queries.sql`；Pandas与SQLite核验结果由流水线自动生成。
"""
    (REPORT_DIR / "淘宝用户行为分析报告.md").write_text(report, encoding="utf-8")

    brief = f"""# 淘宝用户行为分析：面试应急讲解

## 60秒项目介绍

我使用阿里云天池公开的淘宝用户行为数据集做了一个电商用户行为分析项目。原数据约1亿条，为兼顾可复现性和本地处理效率，我按用户ID固定抽取约1%的用户并保留这些用户的全部行为，最终清洗得到 {num(base['events'])} 条有效记录。项目使用 Pandas 完成清洗、趋势、行为阶段、留存和短周期重复购买分析，再用 SQLite 编写SQL复核核心指标，最后输出可视化与运营建议。主要发现包括窗口内的日/小时活跃峰值、购买用户占浏览用户 {pct(funnel['buyer_rate_vs_view_users'])}，以及多日购买用户占购买用户 {pct(repeat['repeat_day_buyer_rate'])}。我也明确记录了数据只有9天、没有金额和订单ID等局限。

## 你必须记住的数字

- 有效记录：{num(base['events'])}；用户：{num(base['users'])}；商品：{num(base['items'])}；类目：{num(base['categories'])}。
- 购买用户占浏览用户：{pct(funnel['buyer_rate_vs_view_users'])}。
- D1 / D3 / D7 留存：{pct(retention['d1_retention_rate'])} / {pct(retention['d3_retention_rate'])} / {pct(retention['d7_retention_rate'])}。
- 至少2个购买日的用户占购买用户：{pct(repeat['repeat_day_buyer_rate'])}。
- 日峰值：{peak_day['event_date']}；小时峰值：{int(peak_hour['event_hour'])}:00。

## 高频追问

**为什么不是随机抽100万行？** 直接抽行会破坏同一用户的行为轨迹，影响留存和重复购买分析；按用户ID固定取模可以保留完整用户历史并保证每次结果一致。

**漏斗是严格漏斗吗？** 不是。数据没有会话和页面路径，因此我称其为“去重用户行为阶段覆盖”，不声称用户一定按浏览、收藏/加购、购买的顺序转化。

**怎样保证结果可靠？** 我做了字段类型、缺失、行为枚举、日期范围、重复事件检查，并用SQLite SQL对行为数、用户数和购买用户数进行交叉核验。

**为什么不能算销售额和客单价？** 原始数据没有价格、金额和订单ID，强行计算会制造不真实结论，所以只分析行为次数和去重用户。

**如果继续做会增加什么？** 先显式计算兴趣但未购买的用户交集，再补充订单金额、渠道、活动曝光和实验分组数据，建立更严格的会话漏斗与用户分层，并用A/B Test检验召回策略的增量效果。
"""
    (REPORT_DIR / "面试应急讲解.md").write_text(brief, encoding="utf-8")

if __name__ == "__main__":
    build_reports()
