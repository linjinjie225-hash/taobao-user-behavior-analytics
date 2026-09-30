from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dashboard" / "app.py"


def test_dashboard_opens_on_executive_summary() -> None:
    app = AppTest.from_file(str(APP), default_timeout=10).run()

    assert not app.exception
    assert any("购买阶段覆盖" in title.value for title in app.title)
    assert len(app.metric) >= 4


def test_activity_page_frames_the_peak_within_the_sample() -> None:
    app = AppTest.from_file(str(APP), default_timeout=10).run()
    app.sidebar.radio[0].set_value("活跃节奏").run()

    assert not app.exception
    assert any("22:00" in title.value for title in app.title)
    assert any("9 天样本" in caption.value for caption in app.caption)
    assert len(app.get("plotly_chart")) == 2


def test_funnel_page_explains_stage_coverage_boundary() -> None:
    app = AppTest.from_file(str(APP), default_timeout=10).run()
    app.sidebar.radio[0].set_value("行为阶段").run()

    assert not app.exception
    assert any("行为阶段" in title.value for title in app.title)
    visible_captions = " ".join(item.value for item in app.caption)
    assert "非会话" in visible_captions
    assert "不要求顺序" in visible_captions
    assert len(app.get("plotly_chart")) == 1


def test_retention_page_labels_repeat_purchase_as_a_proxy() -> None:
    app = AppTest.from_file(str(APP), default_timeout=10).run()
    app.sidebar.radio[0].set_value("留存与重复购买代理").run()

    assert not app.exception
    assert any("重复购买代理" in title.value for title in app.title)
    metric_labels = {item.label for item in app.metric}
    assert {"重复购买行为买家占比", "跨日重复购买行为买家占比"} <= metric_labels
    warnings = " ".join(item.value for item in app.warning)
    assert "无订单 ID" in warnings
    assert "不是真实订单复购率" in warnings
    assert len(app.get("plotly_chart")) == 1


def test_category_page_keeps_behavior_ratio_distinct_from_conversion() -> None:
    app = AppTest.from_file(str(APP), default_timeout=10).run()
    app.sidebar.radio[0].set_value("类目机会").run()

    assert not app.exception
    assert any(
        title.value == "购买行为量与购买/浏览行为比需要同时观察"
        for title in app.title
    )
    explanatory_text = " ".join(item.value for item in app.caption)
    assert "行为比" in explanatory_text
    assert "概率" in explanatory_text
    assert "未定义" in explanatory_text
    assert len(app.get("plotly_chart")) == 1
    assert len(app.dataframe) == 1


def test_trust_page_discloses_reproducibility_and_limitations() -> None:
    app = AppTest.from_file(str(APP), default_timeout=10).run()
    app.sidebar.radio[0].set_value("数据可信度").run()

    assert not app.exception
    assert any("可信度" in title.value for title in app.title)
    page_text = " ".join(
        item.value
        for kind in ("caption", "markdown", "info", "warning")
        for item in app.get(kind)
    )
    assert "user_id % 100 == 0" in page_text
    assert "SQL" in page_text
    assert "AI" in page_text and "人工" in page_text
    assert "2017-11-25" in page_text and "2017-12-03" in page_text
    assert "GMV" in page_text and "客单价" in page_text
    assert "真实订单复购率" in page_text
    assert "总体外推" in page_text
