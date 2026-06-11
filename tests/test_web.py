from fastapi.testclient import TestClient
from pathlib import Path

from main import app


def test_home_serves_frontend() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Mystic Engine" in response.text
    assert "Pantheon 命書" in response.text
    assert "基本資料" in response.text
    assert "命書報告" in response.text
    assert "進階排盤設定" in response.text
    assert "命盤總覽" in response.text
    assert "開始推演命盤" in response.text
    assert "/personality" in response.text
    assert "64 分支人格測試" in response.text
    assert "id=\"personality-form\"" not in response.text
    assert "/static/app.js" in response.text


def test_personality_page_serves_standalone_frontend() -> None:
    client = TestClient(app)
    response = client.get("/personality")
    assert response.status_code == 200
    assert "64 分支人格測試" in response.text
    assert "id=\"personality-form\"" in response.text
    assert "段落 1 / 6" in response.text
    assert "返回" in response.text
    assert "繼續" in response.text
    assert "完成後產生結果" in response.text
    assert "/static/personality.js" in response.text


def test_mbti_questions_use_mixed_display_order() -> None:
    personality_js = Path("app/web/static/personality.js").read_text()
    assert "const QUESTION_ORDER" in personality_js
    assert "const QUESTIONS_PER_PAGE = 8" in personality_js
    assert "data-question-page" in personality_js
    order_start = personality_js.index("const QUESTION_ORDER")
    order_end = personality_js.index("];", order_start)
    order_block = personality_js[order_start:order_end]
    first_ids = [
        "mbti.sn.01",
        "mbti.ei.03",
        "mbti.hc.01",
        "mbti.jp.02",
        "mbti.tf.05",
        "mbti.ao.04",
    ]
    last_position = -1
    for question_id in first_ids:
        position = order_block.index(question_id)
        assert position > last_position
        last_position = position


def test_fortune_paper_renders_nameology_nested_fields_explicitly() -> None:
    paper_js = Path("app/web/static/paper.js").read_text()
    assert "function renderFiveGrid" in paper_js
    assert "function renderThreeTalents" in paper_js
    assert "renderKeyValueRows(grids)" not in paper_js
    assert "renderKeyValueRows(talents)" not in paper_js


def test_fortune_paper_uses_final_narrative_order() -> None:
    paper_js = Path("app/web/static/paper.js").read_text()
    sections = [
        "姓名合參",
        "本命底色",
        "五行怎麼用",
        "十神",
        "十二長生 / 祿刃",
        "神煞",
        "紫微星曜",
        "今年工作運",
        "今年財務、健康、人際",
        "算法依據",
    ]
    positions = [paper_js.index(section) for section in sections]
    assert positions == sorted(positions)
    assert "function deriveGrowthStates" in paper_js
    assert "function deriveSpecialForces" in paper_js
    assert "function deriveShensha" in paper_js
    assert "function nameologyNarrative" in paper_js
