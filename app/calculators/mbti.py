from typing import Any

from app.calculators.base import BaseDivination


DIMENSIONS = {
    "EI": ("E", "I", "外向互動", "內向沉澱"),
    "SN": ("S", "N", "具體經驗", "直覺概念"),
    "TF": ("T", "F", "邏輯準則", "情感價值"),
    "JP": ("J", "P", "結構規劃", "彈性探索"),
    "AO": ("A", "O", "自穩篤定", "波動敏銳"),
    "HC": ("H", "C", "和諧協調", "冷靜定錨"),
}

CORE_DIMENSIONS = ("EI", "SN", "TF", "JP")
BRANCH_DIMENSIONS = ("AO", "HC")
MIN_ANSWERS_PER_DIMENSION = 4
LOW_MARGIN = 0.2


class MbtiCalculator(BaseDivination):
    name = "mbti"

    def calculate(self, user_data: dict[str, Any]) -> dict[str, Any]:
        answers = user_data.get("personality_answers") or []
        if not answers:
            return {
                "system": self.name,
                "version": self.version,
                "status": "reserved",
                "notice": "MBTI 外掛插槽已保留，等待量表或使用者性格資料接入。",
            }

        dimensions = _score_dimensions(answers)
        insufficient = [
            key for key, item in dimensions.items() if item["answer_count"] < MIN_ANSWERS_PER_DIMENSION
        ]
        core_insufficient = [key for key in CORE_DIMENSIONS if key in insufficient]
        branch_insufficient = [key for key in BRANCH_DIMENSIONS if key in insufficient]
        if core_insufficient:
            status = "insufficient_data"
        elif branch_insufficient:
            status = "scored_core"
        else:
            status = "scored"
        core_type = _type_from_dimensions(dimensions, CORE_DIMENSIONS) if status != "insufficient_data" else None
        branch_code = _type_from_dimensions(dimensions, BRANCH_DIMENSIONS) if status == "scored" else None
        mbti_type = f"{core_type}-{branch_code}" if core_type and branch_code else core_type

        return {
            "system": self.name,
            "version": self.version,
            "status": status,
            "provider": "pantheon_mbti_questionnaire",
            "type": mbti_type,
            "core_type": core_type,
            "branch_code": branch_code,
            "dimensions": dimensions,
            "answer_count": len(answers),
            "notice": _notice_for_status(status, insufficient),
        }


def _score_dimensions(answers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    buckets = {key: {"total": 0.0, "count": 0} for key in DIMENSIONS}
    for answer in answers:
        dimension = str(answer.get("dimension", ""))
        direction = str(answer.get("direction", ""))
        value = int(answer.get("value", 3))
        if dimension not in DIMENSIONS:
            continue
        first, second, first_label, second_label = DIMENSIONS[dimension]
        if direction not in {first, second}:
            continue
        centered = max(1, min(5, value)) - 3
        contribution = -centered if direction == first else centered
        buckets[dimension]["total"] += contribution
        buckets[dimension]["count"] += 1

    result: dict[str, dict[str, Any]] = {}
    for key, (first, second, first_label, second_label) in DIMENSIONS.items():
        count = buckets[key]["count"]
        raw_score = buckets[key]["total"] / (count * 2) if count else 0.0
        score = round(raw_score, 3)
        preferred = first if score < 0 else second
        preferred_label = first_label if preferred == first else second_label
        confidence = _confidence(count, score)
        result[key] = {
            "score": score,
            "preferred": preferred,
            "preferred_label": preferred_label,
            "opposite": second if preferred == first else first,
            "confidence": confidence,
            "answer_count": count,
            "basis": "MBTI 自評問卷",
        }
    return result


def _confidence(answer_count: int, score: float) -> str:
    if answer_count < MIN_ANSWERS_PER_DIMENSION:
        return "insufficient"
    if abs(score) < LOW_MARGIN:
        return "low_margin"
    return "primary"


def _type_from_dimensions(dimensions: dict[str, dict[str, Any]], keys: tuple[str, ...]) -> str:
    return "".join(str(dimensions[key]["preferred"]) for key in keys)


def _notice_for_status(status: str, insufficient: list[str]) -> str:
    if status == "scored":
        return "64 分支人格結果來自個人自評問卷，適合作為偏好訊號，不作心理診斷。"
    if status == "scored_core":
        missing = "、".join(insufficient)
        return f"核心 MBTI 已完成，分支人格答案不足；不足維度：{missing}。"
    missing = "、".join(insufficient)
    return f"MBTI 答案不足，尚不能產生穩定四維結果；不足維度：{missing}。"
