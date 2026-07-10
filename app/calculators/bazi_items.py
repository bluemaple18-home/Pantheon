from __future__ import annotations

from typing import Any

from app.calculators.bazi_rules import EARTHLY_BRANCHES
TWELVE_GROWTH = {
    "甲": {"亥": "長生", "子": "沐浴", "丑": "冠帶", "寅": "臨官", "卯": "帝旺", "辰": "衰", "巳": "病", "午": "死", "未": "墓", "申": "絕", "酉": "胎", "戌": "養"},
    "乙": {"午": "長生", "巳": "沐浴", "辰": "冠帶", "卯": "臨官", "寅": "帝旺", "丑": "衰", "子": "病", "亥": "死", "戌": "墓", "酉": "絕", "申": "胎", "未": "養"},
    "丙": {"寅": "長生", "卯": "沐浴", "辰": "冠帶", "巳": "臨官", "午": "帝旺", "未": "衰", "申": "病", "酉": "死", "戌": "墓", "亥": "絕", "子": "胎", "丑": "養"},
    "丁": {"酉": "長生", "申": "沐浴", "未": "冠帶", "午": "臨官", "巳": "帝旺", "辰": "衰", "卯": "病", "寅": "死", "丑": "墓", "子": "絕", "亥": "胎", "戌": "養"},
    "戊": {"寅": "長生", "卯": "沐浴", "辰": "冠帶", "巳": "臨官", "午": "帝旺", "未": "衰", "申": "病", "酉": "死", "戌": "墓", "亥": "絕", "子": "胎", "丑": "養"},
    "己": {"酉": "長生", "申": "沐浴", "未": "冠帶", "午": "臨官", "巳": "帝旺", "辰": "衰", "卯": "病", "寅": "死", "丑": "墓", "子": "絕", "亥": "胎", "戌": "養"},
    "庚": {"巳": "長生", "午": "沐浴", "未": "冠帶", "申": "臨官", "酉": "帝旺", "戌": "衰", "亥": "病", "子": "死", "丑": "墓", "寅": "絕", "卯": "胎", "辰": "養"},
    "辛": {"子": "長生", "亥": "沐浴", "戌": "冠帶", "酉": "臨官", "申": "帝旺", "未": "衰", "午": "病", "巳": "死", "辰": "墓", "卯": "絕", "寅": "胎", "丑": "養"},
    "壬": {"申": "長生", "酉": "沐浴", "戌": "冠帶", "亥": "臨官", "子": "帝旺", "丑": "衰", "寅": "病", "卯": "死", "辰": "墓", "巳": "絕", "午": "胎", "未": "養"},
    "癸": {"卯": "長生", "寅": "沐浴", "丑": "冠帶", "子": "臨官", "亥": "帝旺", "戌": "衰", "酉": "病", "申": "死", "未": "墓", "午": "絕", "巳": "胎", "辰": "養"},
}
GROWTH_DISPLAY_ORDER = ["長生", "臨官", "帝旺", "墓", "胎", "養"]
LU_BRANCH = {"甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳", "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子"}
YANGREN_BRANCH = {"甲": "卯", "乙": "寅", "丙": "午", "丁": "巳", "戊": "午", "己": "巳", "庚": "酉", "辛": "申", "壬": "子", "癸": "亥"}
SIX_ELEGANCE_DAYS = {"丙午", "丁未", "戊子", "戊午", "己丑", "己未"}
WENCHANG_BRANCH = {"甲": "巳", "乙": "午", "丙": "申", "丁": "酉", "戊": "申", "己": "酉", "庚": "亥", "辛": "子", "壬": "寅", "癸": "卯"}
TAOHUA_BRANCH = {"申子辰": "酉", "寅午戌": "卯", "巳酉丑": "午", "亥卯未": "子"}
YIMA_BRANCH = {"申子辰": "寅", "寅午戌": "申", "巳酉丑": "亥", "亥卯未": "巳"}
HUAGAI_BRANCH = {"申子辰": "辰", "寅午戌": "戌", "巳酉丑": "丑", "亥卯未": "未"}
YUEDE_STEM = {"寅": "丙", "午": "丙", "戌": "丙", "申": "壬", "子": "壬", "辰": "壬", "亥": "甲", "卯": "甲", "未": "甲", "巳": "庚", "酉": "庚", "丑": "庚"}
TIAN_YI_BRANCHES = {"甲": ["丑", "未"], "戊": ["丑", "未"], "庚": ["丑", "未"], "乙": ["子", "申"], "己": ["子", "申"], "丙": ["亥", "酉"], "丁": ["亥", "酉"], "壬": ["卯", "巳"], "癸": ["卯", "巳"], "辛": ["寅", "午"]}


def calculate_bazi_items(day_master: str, pillars: dict[str, str], hidden_stems: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    shensha = _bazi_shensha(day_master, pillars, hidden_stems)
    return {
        "growth_states": _growth_states(day_master, pillars),
        "special_forces": _special_forces(day_master, pillars),
        "shensha": shensha,
        "policy": {
            "source": "pantheon_deterministic_rules",
            "ruleset_version": "pantheon-bazi-items-0.1",
            "display_rule": "只輸出命中項目；未命中保持空陣列，不由前端補判。",
        },
    }


def _pillar_branches(pillars: dict[str, str]) -> list[str]:
    return [pillar[1] for pillar in pillars.values() if len(pillar) >= 2]


def _pillar_stems(pillars: dict[str, str]) -> list[str]:
    return [pillar[0] for pillar in pillars.values() if pillar]


def _group_key(branch: str | None) -> str:
    if branch in {"申", "子", "辰"}:
        return "申子辰"
    if branch in {"寅", "午", "戌"}:
        return "寅午戌"
    if branch in {"巳", "酉", "丑"}:
        return "巳酉丑"
    if branch in {"亥", "卯", "未"}:
        return "亥卯未"
    return ""


def _growth_states(day_master: str, pillars: dict[str, str]) -> list[dict[str, Any]]:
    growth_map = TWELVE_GROWTH.get(day_master, {})
    hits: dict[str, dict[str, Any]] = {}
    for palace, pillar in pillars.items():
        branch = pillar[1]
        label = growth_map.get(branch)
        if not label or label not in GROWTH_DISPLAY_ORDER:
            continue
        item = hits.setdefault(
            label,
            {
                "label": label,
                "count": 0,
                "branches": [],
                "palaces": [],
                "basis": f"{day_master}日主十二長生",
            },
        )
        item["count"] += 1
        item["branches"].append(branch)
        item["palaces"].append(palace)
    return [hits[label] for label in GROWTH_DISPLAY_ORDER if label in hits]


def _special_forces(day_master: str, pillars: dict[str, str]) -> list[dict[str, Any]]:
    branches = _pillar_branches(pillars)
    results: list[dict[str, Any]] = []
    lu = LU_BRANCH.get(day_master)
    if lu and lu in branches:
        results.append(
            {
                "label": "祿",
                "branch": lu,
                "count": branches.count(lu),
                "note": f"{lu} 為祿地，代表吃飯能力和位置資源。",
                "basis": f"{day_master}日祿在{lu}",
            }
        )
    yangren = YANGREN_BRANCH.get(day_master)
    if yangren and yangren in branches:
        count = branches.count(yangren)
        results.append(
            {
                "label": "羊刃",
                "branch": yangren,
                "count": count,
                "note": f"{yangren} 命中{f' {count} 次' if count > 1 else ''}，代表主導、爆發與硬度。",
                "basis": f"{day_master}日羊刃在{yangren}",
            }
        )
    return results


def _bazi_shensha(day_master: str, pillars: dict[str, str], hidden_stems: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    day_pillar = pillars.get("day", "")
    branches = _pillar_branches(pillars)
    stems = _pillar_stems(pillars)
    hidden_stem_values = [item["stem"] for values in hidden_stems.values() for item in values]
    year_branch = pillars.get("year", "")[1:2]
    month_branch = pillars.get("month", "")[1:2]
    day_branch = pillars.get("day", "")[1:2]
    items: list[dict[str, Any]] = []

    def add(label: str, note: str, basis: str) -> None:
        if not any(item["label"] == label and item["note"] == note for item in items):
            items.append({"label": label, "note": note, "basis": basis})

    if day_pillar in SIX_ELEGANCE_DAYS:
        add("六秀", f"{day_pillar} 日，才氣、審美、表達與包裝能力加分。", "六秀日")

    wenchang = WENCHANG_BRANCH.get(day_master)
    if wenchang and wenchang in branches:
        add("文昌", f"{day_master} 日文昌在 {wenchang}，學習、文字、企劃與說明能力加分。", f"{day_master}日文昌")

    taohua = TAOHUA_BRANCH.get(_group_key(year_branch)) or TAOHUA_BRANCH.get(_group_key(day_branch))
    if taohua and taohua in branches:
        add("桃花", f"{taohua} 入盤，人緣、曝光、話題感與吸引力較明顯。", "年支/日支桃花")

    yima_hits = sorted(
        {
            branch
            for branch in [YIMA_BRANCH.get(_group_key(year_branch)), YIMA_BRANCH.get(_group_key(day_branch))]
            if branch and branch in branches
        },
        key=EARTHLY_BRANCHES.index,
    )
    if yima_hits:
        add("驛馬", f"{'、'.join(yima_hits)} 入盤，工作與環境容易有移動、變動、跨域。", "年支/日支驛馬")

    huagai = HUAGAI_BRANCH.get(_group_key(day_branch)) or HUAGAI_BRANCH.get(_group_key(year_branch))
    if huagai and huagai in branches:
        add("華蓋", f"{huagai} 入盤，專注、研究、獨立感明顯，也容易悶著想。", "年支/日支華蓋")

    yuede = YUEDE_STEM.get(month_branch)
    if yuede and yuede in stems:
        add("月德", f"{month_branch} 月月德在 {yuede}，明透，遇事較有轉圜與貴人緩衝。", "月令月德")
    elif yuede and yuede in hidden_stem_values:
        add("月德", f"{month_branch} 月月德在 {yuede}，藏於地支，屬暗中緩衝。", "月令月德")

    tianyi_hits = [branch for branch in TIAN_YI_BRANCHES.get(day_master, []) if branch in branches]
    if tianyi_hits:
        add("天乙", f"{'、'.join(tianyi_hits)} 入盤，貴人與解圍機會較明顯。", f"{day_master}日天乙")

    return items
