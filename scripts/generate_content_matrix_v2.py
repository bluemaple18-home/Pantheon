#!/usr/bin/env python3
"""產生 Pantheon 第二期 1000+ 篇內容矩陣。"""

from __future__ import annotations

import argparse
import json
from itertools import combinations_with_replacement
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path(
    "artifacts/fortune_council/content_seo_execution/evidence/content_matrix_v2/content-matrix-v2.json"
)

ZODIAC_SIGNS = (
    ("ARIES", "牡羊座"),
    ("TAURUS", "金牛座"),
    ("GEMINI", "雙子座"),
    ("CANCER", "巨蟹座"),
    ("LEO", "獅子座"),
    ("VIRGO", "處女座"),
    ("LIBRA", "天秤座"),
    ("SCORPIO", "天蠍座"),
    ("SAGITTARIUS", "射手座"),
    ("CAPRICORN", "摩羯座"),
    ("AQUARIUS", "水瓶座"),
    ("PISCES", "雙魚座"),
)
MBTI_TYPES = tuple((value, value) for value in (
    "INTJ", "INTP", "ENTJ", "ENTP",
    "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ",
    "ISTP", "ISFP", "ESTP", "ESFP",
))
ZIWEI_STARS = tuple(
    (code, name)
    for code, name in (
        ("ZIWEI", "紫微"), ("TIANJI", "天機"), ("TAIYANG", "太陽"), ("WUQU", "武曲"),
        ("TIANTONG", "天同"), ("LIANZHEN", "廉貞"), ("TIANFU", "天府"), ("TAIYIN", "太陰"),
        ("TANLANG", "貪狼"), ("JUMEN", "巨門"), ("TIANXIANG", "天相"), ("TIANLIANG", "天梁"),
        ("QISHA", "七殺"), ("POJUN", "破軍"),
    )
)
BAZI_TEN_GODS = tuple(
    (code, name)
    for code, name in (
        ("BIJIAN", "比肩"), ("JIECAI", "劫財"), ("SHISHEN", "食神"), ("SHANGGUAN", "傷官"),
        ("PIANCAI", "偏財"), ("ZHENGCAI", "正財"), ("QISHA", "七殺"), ("ZHENGGUAN", "正官"),
        ("PIANYIN", "偏印"), ("ZHENGYIN", "正印"),
    )
)

MAJOR_ARCANA = (
    ("FOOL", "愚者"), ("MAGICIAN", "魔術師"), ("HIGH-PRIESTESS", "女祭司"), ("EMPRESS", "皇后"),
    ("EMPEROR", "皇帝"), ("HIEROPHANT", "教皇"), ("LOVERS", "戀人"), ("CHARIOT", "戰車"),
    ("STRENGTH", "力量"), ("HERMIT", "隱者"), ("WHEEL-OF-FORTUNE", "命運之輪"), ("JUSTICE", "正義"),
    ("HANGED-MAN", "吊人"), ("DEATH", "死神"), ("TEMPERANCE", "節制"), ("DEVIL", "惡魔"),
    ("TOWER", "高塔"), ("STAR", "星星"), ("MOON", "月亮"), ("SUN", "太陽"),
    ("JUDGEMENT", "審判"), ("WORLD", "世界"),
)
MINOR_RANKS = (
    ("ACE", "一"), ("TWO", "二"), ("THREE", "三"), ("FOUR", "四"), ("FIVE", "五"),
    ("SIX", "六"), ("SEVEN", "七"), ("EIGHT", "八"), ("NINE", "九"), ("TEN", "十"),
    ("PAGE", "侍者"), ("KNIGHT", "騎士"), ("QUEEN", "皇后"), ("KING", "國王"),
)
MINOR_SUITS = (
    ("WANDS", "權杖"), ("CUPS", "聖杯"), ("SWORDS", "寶劍"), ("PENTACLES", "錢幣"),
)
TAROT_CARDS = MAJOR_ARCANA + tuple(
    (f"{suit_code}-{rank_code}", f"{suit_name}{rank_name}")
    for suit_code, suit_name in MINOR_SUITS
    for rank_code, rank_name in MINOR_RANKS
)

SINGLE_SCENARIOS = (
    ("LOVE", "感情", "正在觀察曖昧、交往或分手後的互動"),
    ("WORK", "工作", "遇到求職、合作、升遷或職涯選擇"),
    ("RELATIONSHIPS", "人際", "想整理朋友、家人或同事之間的界線"),
    ("MONEY", "金錢", "面對消費、收入、分配或風險選擇"),
    ("STRESS", "低潮", "壓力升高、反覆卡住或需要重新整理步調"),
)
PAIR_SCENARIOS = (
    ("LOVE", "戀愛", "想核對吸引方式、需求差異與交往節奏"),
    ("FRIENDSHIP", "朋友", "想理解友情中的靠近方式、界線與誤會"),
    ("WORK", "工作", "想改善分工、溝通與共同決策"),
    ("CONFLICT", "衝突", "意見不合時想辨認摩擦來源與修復方法"),
    ("LONG-TERM", "長期相處", "想評估長期互動需要協調的地方"),
)


def _single_row(
    family: str,
    entity_type: str,
    code: str,
    name: str,
    scenario_code: str,
    scenario: str,
    situation: str,
    *,
    section: str,
    product: str,
    category: str,
) -> dict[str, str]:
    if family == "tarot":
        keyword = f"塔羅{name}在{scenario}中代表什麼"
        title = f"{keyword}？先看牌義、處境與不能直接斷定的事"
    elif family == "ziwei":
        keyword = f"紫微斗數{name}在{scenario}中的表現"
        title = f"{keyword}怎麼看？從生活線索理解優勢與限制"
    elif family == "bazi":
        keyword = f"八字十神{name}在{scenario}中的表現"
        title = f"{keyword}怎麼看？從生活線索理解傾向與限制"
    else:
        keyword = f"{name}在{scenario}中的表現"
        title = f"{keyword}怎麼看？從生活情境理解傾向與限制"
    return {
        "priority": "V2-SINGLE",
        "id": f"V2-{family.upper()}-{code}-{scenario_code}",
        "primaryKeyword": keyword,
        "title": title,
        "intent": f"{situation}，想知道{name}能提供哪些觀察角度、反例與使用限制",
        "family": family,
        "entityType": entity_type,
        "entity": name,
        "scenario": scenario,
        "section": section,
        "product": product,
        "category": category,
    }


def _pair_row(
    family: str,
    left: tuple[str, str],
    right: tuple[str, str],
    scenario_code: str,
    scenario: str,
    situation: str,
    *,
    section: str,
    product: str,
    category: str,
) -> dict[str, str]:
    left_code, left_name = left
    right_code, right_name = right
    keyword = f"{left_name}和{right_name}{scenario}適合嗎"
    return {
        "priority": "V2-PAIR",
        "id": f"V2-{family.upper()}-PAIR-{left_code}-{right_code}-{scenario_code}",
        "primaryKeyword": keyword,
        "title": f"{keyword}？從互動差異、優勢與磨合方式判斷",
        "intent": f"{situation}，想理解{left_name}和{right_name}可能順手或卡住之處，不把類型直接判成適合或不適合",
        "family": f"{family}_pair",
        "entityType": f"{family}_pair",
        "entity": left_name,
        "pairedEntity": right_name,
        "scenario": scenario,
        "section": section,
        "product": product,
        "category": category,
    }


def build_rows() -> list[dict[str, str]]:
    """建立每篇只含一個單體／配對與一個情境的固定順序矩陣。"""
    rows: list[dict[str, str]] = []
    single_families = (
        ("zodiac", "zodiac_sign", ZODIAC_SIGNS, "astro", "astro", "astrology"),
        ("mbti", "mbti_type", MBTI_TYPES, "mbti", "personality", "personality"),
        ("tarot", "tarot_card", TAROT_CARDS, "tarot", "tarot", "tarot"),
        ("ziwei", "ziwei_main_star", ZIWEI_STARS, "ziwei", "fortune", "fortune"),
        ("bazi", "bazi_ten_god", BAZI_TEN_GODS, "bazi", "fortune", "fortune"),
    )
    for family, entity_type, entities, section, product, category in single_families:
        for code, name in entities:
            for scenario_code, scenario, situation in SINGLE_SCENARIOS:
                rows.append(
                    _single_row(
                        family, entity_type, code, name, scenario_code, scenario, situation,
                        section=section, product=product, category=category,
                    )
                )

    for family, entities, section, product, category in (
        ("mbti", MBTI_TYPES, "mbti", "personality", "personality"),
        ("zodiac", ZODIAC_SIGNS, "astro", "astro", "astrology"),
    ):
        for left, right in combinations_with_replacement(entities, 2):
            for scenario_code, scenario, situation in PAIR_SCENARIOS:
                rows.append(
                    _pair_row(
                        family, left, right, scenario_code, scenario, situation,
                        section=section, product=product, category=category,
                    )
                )
    return rows


def build_payload() -> dict[str, Any]:
    rows = build_rows()
    family_counts: dict[str, int] = {}
    for row in rows:
        family = row["family"]
        family_counts[family] = family_counts.get(family, 0) + 1
    return {
        "schemaVersion": "content-matrix-v2.0",
        "generationRule": "一篇文章只處理一個單體或一組配對，並且只處理一個情境",
        "total": len(rows),
        "familyCounts": family_counts,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    rendered = json.dumps(build_payload(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"matrix is stale: {output}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
