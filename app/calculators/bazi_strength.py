from __future__ import annotations

from typing import Any

from app.calculators.bazi_rules import ELEMENT_CONTROLS, ELEMENT_GENERATES, HIDDEN_STEMS, STEM_ELEMENTS


def strength_analysis(pillars: dict[str, str], scores: dict[str, int], day_master: str) -> dict[str, Any]:
    day_element = STEM_ELEMENTS[day_master]
    month_branch = pillars["month"][1]
    supporting_elements = {
        day_element,
        next(element for element, generated in ELEMENT_GENERATES.items() if generated == day_element),
    }
    draining_element = ELEMENT_GENERATES[day_element]
    controlling_element = next(element for element, controlled in ELEMENT_CONTROLS.items() if controlled == day_element)
    wealth_element = ELEMENT_CONTROLS[day_element]
    support_score = sum(scores[element] for element in supporting_elements)
    pressure_score = scores[draining_element] + scores[controlling_element] + scores[wealth_element]
    month_support = STEM_ELEMENTS[HIDDEN_STEMS[month_branch][0]["stem"]] in supporting_elements
    total = support_score + pressure_score or 1
    ratio = support_score / total
    if month_support:
        ratio += 0.08
    label = "strong_candidate" if ratio >= 0.58 else "weak_candidate" if ratio <= 0.42 else "balanced_candidate"
    return {
        "status": "candidate_not_final_useful_god",
        "model": "pantheon_strength_v1",
        "day_element": day_element,
        "supporting_elements": sorted(supporting_elements),
        "support_score": support_score,
        "pressure_score": pressure_score,
        "month_branch": month_branch,
        "month_command_supports_day_master": month_support,
        "ratio": round(ratio, 3),
        "label": label,
        "basis": [
            "日主同五行與生日主五行列為 support",
            "日主所生、剋日主、日主所剋列為 pressure",
            "月令主氣若支持日主，ratio 加權 0.08",
        ],
        "caution": "旺衰只是候選評分；格局、調候、通關與用神不可由此單獨定案。",
    }
