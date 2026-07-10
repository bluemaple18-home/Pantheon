from __future__ import annotations

from app.calculators.bazi_rules import BRANCH_CLASHES, BRANCH_HARMONIES, STEM_CLASHES, STEM_COMBINES


RELATION_LABELS = {"combine": "合", "clash": "沖", "harmony": "合"}


def relation_pairs(values: list[str], mapping: dict[str, str], label: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for left in values:
        right = mapping.get(left)
        if right and right in values:
            relation_name = RELATION_LABELS.get(label, label)
            found.append({"type": label, "name": f"{left}{right}{relation_name}", "left": left, "right": right})
    return found


def chart_relations(pillars: dict[str, str]) -> dict[str, list[dict[str, str]]]:
    stems = [pillar[0] for pillar in pillars.values()]
    branches = [pillar[1] for pillar in pillars.values()]
    return _relations(stems, branches)


def annual_relations(annual_pillar: str, pillars: dict[str, str]) -> dict[str, list[dict[str, str]]]:
    stems = [annual_pillar[0], *[pillar[0] for pillar in pillars.values()]]
    branches = [annual_pillar[1], *[pillar[1] for pillar in pillars.values()]]
    return _relations(stems, branches)


def interaction_summary(relations: dict[str, list[dict[str, str]]]) -> str:
    names = [item["name"] for item in relations.get("stem", []) + relations.get("branch", [])]
    if not names:
        return "互動較少，年度重點以流年十神本身為主"
    clashes = [name for name in names if name.endswith("沖")]
    harmonies = [name for name in names if name.endswith("合")]
    if clashes and harmonies:
        return f"{'、'.join(clashes[:2])} 帶來變動，{'、'.join(harmonies[:2])} 帶來可借力之處"
    if clashes:
        return f"{'、'.join(clashes[:3])}，今年事件感與變動感較強"
    if harmonies:
        return f"{'、'.join(harmonies[:3])}，今年較適合整合資源與修補關係"
    return "有互動訊號，但仍需進一步校準權重"


def _relations(stems: list[str], branches: list[str]) -> dict[str, list[dict[str, str]]]:
    return {
        "stem": relation_pairs(stems, STEM_COMBINES, "combine")
        + relation_pairs(stems, STEM_CLASHES, "clash"),
        "branch": relation_pairs(branches, BRANCH_HARMONIES, "harmony")
        + relation_pairs(branches, BRANCH_CLASHES, "clash"),
    }
