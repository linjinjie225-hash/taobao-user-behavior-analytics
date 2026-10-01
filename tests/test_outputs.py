import re
from pathlib import Path


def test_required_outputs_exist_after_pipeline():
    root = Path(__file__).resolve().parents[1]
    required = [
        root / "results/metrics.json",
        root / "results/charts/daily_activity.png",
        root / "results/charts/hourly_activity.png",
        root / "results/charts/user_funnel.png",
        root / "results/charts/retention.png",
        root / "results/charts/category_performance.png",
        root / "report/淘宝用户行为分析报告.md",
        root / "report/面试应急讲解.md",
        root / "README.md",
        root / "dashboard/app.py",
        root / "site/index.html",
        root / "site/assets/user_funnel.png",
        root / "site/assets/daily_activity.png",
        root / "site/assets/retention.png",
        root / "docs/AI_COLLABORATION.md",
    ]
    assert all(path.exists() and path.stat().st_size > 0 for path in required)


def _static_page() -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / "site/index.html").read_text(encoding="utf-8")


def test_static_page_has_accessible_metadata_and_truthful_metrics():
    page = _static_page()
    normalized = " ".join(page.split())

    assert re.search(r'<meta\s+charset=["\']utf-8["\']', page, re.IGNORECASE)
    assert re.search(
        r'<meta\s+name=["\']viewport["\']\s+content=["\'][^"\']*width=device-width',
        page,
        re.IGNORECASE,
    )
    assert "购买阶段覆盖 67.9% 低于兴趣阶段覆盖 87.8%" in normalized
    assert "1,001,832" in page
    assert "9,895" in page
    assert "87.8%" in page
    assert "67.9%" in page


def test_static_page_explains_independent_coverage_before_experiment():
    page = _static_page()

    assert "19.9 个百分点" in page
    assert "独立覆盖率" in page
    assert "engaged_without_buy" in page
    assert "engaged_users ∩ non_buyers" in page
    assert "先在用户层计算" in page
    unsupported_claims = (
        "19.9% 的用户",
        "19.9%的用户",
        "兴趣未购人群占比为 19.9%",
        "兴趣未购用户占比为 19.9%",
        "漏斗转化率为 67.9%",
        "会话转化率为 67.9%",
    )
    assert not any(claim in page for claim in unsupported_claims)


def test_static_page_uses_expected_charts_alt_text_and_caveats():
    page = _static_page()

    assert 'src="assets/user_funnel.png"' in page
    assert 'alt="浏览、兴趣与购买的独立行为阶段覆盖，不代表顺序转化漏斗"' in page
    assert 'src="assets/daily_activity.png"' in page
    assert 'alt="九天样本窗口内全部行为事件量与购买行为事件量趋势"' in page
    assert 'alt="九天样本窗口内每日事件量与活跃用户数趋势"' not in page
    assert 'src="assets/retention.png"' in page
    assert 'alt="按可观察后续天数筛选合格分母的 D1、D3、D7 活跃留存"' in page
    assert "合格分母" in page
    assert "可观察" in page


def test_static_page_links_are_functional_and_deployment_copy_is_honest():
    root = Path(__file__).resolve().parents[1]
    page = _static_page()
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', page, re.IGNORECASE)

    assert "https://tianchi.aliyun.com/dataset/649" in hrefs
    assert "../README.md" in hrefs
    assert "../dashboard/app.py" in hrefs
    assert hrefs
    assert all(not href.startswith(("#", "javascript:")) for href in hrefs)
    assert all("OWNER" not in href and "example.com" not in href for href in hrefs)
    for href in hrefs:
        if href.startswith(("http://", "https://", "mailto:")):
            continue
        assert (root / "site" / href).resolve().exists(), href
    assert "公开部署后" in page
    assert "当前未上线" in page


def test_static_page_has_required_responsive_breakpoint():
    page = _static_page()

    assert re.search(r"@media\s*\(max-width:\s*760px\)", page)


def test_ci_invokes_pytest_as_a_python_module():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert re.search(
        r"^\s*run:\s*python -m pytest -q\s*$",
        workflow,
        re.MULTILINE,
    )
    assert not re.search(r"^\s*run:\s*pytest\b", workflow, re.MULTILINE)
