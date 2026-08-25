from pathlib import Path


def test_related_failure_stop_line_contract_is_pinned() -> None:
    rules = (Path(__file__).resolve().parents[1] / "AGENTS.md").read_text(encoding="utf-8")

    assert "原本成功的流程出現第二個相關故障時" in rules
    assert "最後成功版本為何" in rules
    assert "哪個 durable invariant 被破壞" in rules
    assert "四項證據未閉合前，不得 push、promotion、production canary" in rules
    assert "公開網址 HTTP 200 且正文可見" in rules
