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
    ]
    assert all(path.exists() and path.stat().st_size > 0 for path in required)
