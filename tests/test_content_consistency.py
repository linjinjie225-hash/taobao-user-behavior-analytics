import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_readme_presents_verified_metrics_and_recruiter_sections() -> None:
    metrics = json.loads((ROOT / "results/metrics.json").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    expected_values = {
        f"{metrics['basic']['events']:,}",
        f"{metrics['basic']['users']:,}",
        f"{metrics['funnel']['engagement_rate_vs_view_users']:.1%}",
        f"{metrics['funnel']['buyer_rate_vs_view_users']:.1%}",
    }
    expected_headings = {
        "## 在线演示",
        "## 核心发现",
        "## 数据可信度",
        "## AI协作",
        "## 分析边界",
        "## 本地运行",
    }

    assert expected_values <= set(readme.split())
    assert all(heading in readme for heading in expected_headings)


def test_public_methodology_documents_are_substantive() -> None:
    documents = [
        ROOT / "docs/AI_COLLABORATION.md",
        ROOT / "docs/METRIC_DEFINITIONS.md",
        ROOT / "docs/DATA_PROVENANCE.md",
    ]

    assert all(path.exists() and path.stat().st_size > 300 for path in documents)


def test_readme_does_not_invent_an_engaged_nonbuyer_cohort() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    invented_cohort_claim = re.compile(
        r"(?:已|已经|当前).{0,16}(?:计算|识别|得到).{0,24}"
        r"(?:兴趣未购|有兴趣.{0,4}未购买|收藏.{0,4}加购.{0,4}未购买)"
    )
    independent_stage_caveat = re.compile(
        r"(?:独立.{0,20}(?:阶段|统计)|(?:阶段|统计).{0,20}独立)"
    )

    assert invented_cohort_claim.search(readme) is None
    assert independent_stage_caveat.search(readme)
    assert "交集" in readme and "engaged_without_buy" in readme
