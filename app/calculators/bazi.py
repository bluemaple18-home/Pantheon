from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta
from typing import Any

from app.calculators.base import BaseDivination


HEAVENLY_STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
EARTHLY_BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
ZODIACS = {
    "子": "鼠",
    "丑": "牛",
    "寅": "虎",
    "卯": "兔",
    "辰": "龍",
    "巳": "蛇",
    "午": "馬",
    "未": "羊",
    "申": "猴",
    "酉": "雞",
    "戌": "狗",
    "亥": "豬",
}
STEM_POLARITY = {
    "甲": "yang",
    "乙": "yin",
    "丙": "yang",
    "丁": "yin",
    "戊": "yang",
    "己": "yin",
    "庚": "yang",
    "辛": "yin",
    "壬": "yang",
    "癸": "yin",
}
STEM_ELEMENTS = {
    "甲": "木",
    "乙": "木",
    "丙": "火",
    "丁": "火",
    "戊": "土",
    "己": "土",
    "庚": "金",
    "辛": "金",
    "壬": "水",
    "癸": "水",
}
BRANCH_ELEMENTS = {
    "子": "水",
    "丑": "土",
    "寅": "木",
    "卯": "木",
    "辰": "土",
    "巳": "火",
    "午": "火",
    "未": "土",
    "申": "金",
    "酉": "金",
    "戌": "土",
    "亥": "水",
}
HIDDEN_STEMS = {
    "子": [{"stem": "癸", "role": "main", "weight": 100}],
    "丑": [
        {"stem": "己", "role": "main", "weight": 60},
        {"stem": "癸", "role": "middle", "weight": 30},
        {"stem": "辛", "role": "residual", "weight": 10},
    ],
    "寅": [
        {"stem": "甲", "role": "main", "weight": 60},
        {"stem": "丙", "role": "middle", "weight": 30},
        {"stem": "戊", "role": "residual", "weight": 10},
    ],
    "卯": [{"stem": "乙", "role": "main", "weight": 100}],
    "辰": [
        {"stem": "戊", "role": "main", "weight": 60},
        {"stem": "乙", "role": "middle", "weight": 30},
        {"stem": "癸", "role": "residual", "weight": 10},
    ],
    "巳": [
        {"stem": "丙", "role": "main", "weight": 60},
        {"stem": "戊", "role": "middle", "weight": 30},
        {"stem": "庚", "role": "residual", "weight": 10},
    ],
    "午": [
        {"stem": "丁", "role": "main", "weight": 70},
        {"stem": "己", "role": "middle", "weight": 30},
    ],
    "未": [
        {"stem": "己", "role": "main", "weight": 60},
        {"stem": "丁", "role": "middle", "weight": 30},
        {"stem": "乙", "role": "residual", "weight": 10},
    ],
    "申": [
        {"stem": "庚", "role": "main", "weight": 60},
        {"stem": "壬", "role": "middle", "weight": 30},
        {"stem": "戊", "role": "residual", "weight": 10},
    ],
    "酉": [{"stem": "辛", "role": "main", "weight": 100}],
    "戌": [
        {"stem": "戊", "role": "main", "weight": 60},
        {"stem": "辛", "role": "middle", "weight": 30},
        {"stem": "丁", "role": "residual", "weight": 10},
    ],
    "亥": [
        {"stem": "壬", "role": "main", "weight": 70},
        {"stem": "甲", "role": "middle", "weight": 30},
    ],
}
ELEMENT_GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
ELEMENT_CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
STEM_COMBINES = {"甲": "己", "乙": "庚", "丙": "辛", "丁": "壬", "戊": "癸"}
STEM_CLASHES = {"甲": "庚", "乙": "辛", "丙": "壬", "丁": "癸"}
BRANCH_CLASHES = {"子": "午", "丑": "未", "寅": "申", "卯": "酉", "辰": "戌", "巳": "亥"}
BRANCH_HARMONIES = {"子": "丑", "寅": "亥", "卯": "戌", "辰": "酉", "巳": "申", "午": "未"}
RELATION_LABELS = {"combine": "合", "clash": "沖", "harmony": "合"}


def _sexagenary(index: int) -> str:
    return HEAVENLY_STEMS[index % 10] + EARTHLY_BRANCHES[index % 12]


def _year_pillar(birth_date: date) -> str:
    return _sexagenary(birth_date.year - 1984)


def _month_pillar(birth_date: date) -> str:
    year_stem_index = (birth_date.year - 1984) % 10
    first_month_stem_index = ((year_stem_index % 5) * 2 + 2) % 10
    branch_index = (birth_date.month + 1) % 12
    stem_index = (first_month_stem_index + birth_date.month - 1) % 10
    return HEAVENLY_STEMS[stem_index] + EARTHLY_BRANCHES[branch_index]


def _day_pillar(birth_date: date) -> str:
    base_day = date(1900, 1, 31)
    return _sexagenary((birth_date - base_day).days)


def _hour_pillar(day_pillar: str, birth_time: time) -> str:
    hour = birth_time.hour
    branch_index = ((hour + 1) // 2) % 12
    day_stem_index = HEAVENLY_STEMS.index(day_pillar[0])
    first_hour_stem_index = (day_stem_index % 5) * 2
    return HEAVENLY_STEMS[(first_hour_stem_index + branch_index) % 10] + EARTHLY_BRANCHES[branch_index]


def _lunar_python_pillars(birth_date: date, birth_time: time) -> dict[str, str] | None:
    try:
        from lunar_python import Solar
    except ImportError:
        return None

    solar = Solar.fromYmdHms(
        birth_date.year,
        birth_date.month,
        birth_date.day,
        birth_time.hour,
        birth_time.minute,
        birth_time.second,
    )
    eight_char = solar.getLunar().getEightChar()
    return {
        "year": eight_char.getYear(),
        "month": eight_char.getMonth(),
        "day": eight_char.getDay(),
        "hour": eight_char.getTime(),
    }


def _calendar_pillars(birth_date: date, birth_time: time) -> tuple[dict[str, str], dict[str, Any]]:
    try:
        provider_pillars = _lunar_python_pillars(birth_date, birth_time)
    except Exception as error:
        provider_pillars = None
        provider_error = type(error).__name__
    else:
        provider_error = None

    if provider_pillars:
        return provider_pillars, {
            "provider": "lunar-python",
            "provider_status": "active",
            "algorithm_level": "calendar_provider_lunar_python_rules_mvp",
            "notice": "四柱由 lunar-python 產出；藏干、十神、合沖與大運仍由 Pantheon rules layer 計算。",
            "policies": {
                "month_boundary": "solar_term_by_provider",
                "day_boundary": "provider_default",
                "true_solar_time": "not_applied",
            },
        }

    day = _day_pillar(birth_date)
    fallback_pillars = {
        "year": _year_pillar(birth_date),
        "month": _month_pillar(birth_date),
        "day": day,
        "hour": _hour_pillar(day, birth_time),
    }
    notice = "目前使用內建 MVP 曆法骨架；尚未啟用 lunar-python，月柱不是正式節氣換月。"
    if provider_error:
        notice = f"{notice} lunar-python adapter error: {provider_error}."
    return fallback_pillars, {
        "provider": "pantheon-internal",
        "provider_status": "fallback",
        "algorithm_level": "mvp_scaffold",
        "notice": notice,
        "policies": {
            "month_boundary": "calendar_month_mvp",
            "day_boundary": "clock_date_mvp",
            "true_solar_time": "not_applied",
        },
    }


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def _parse_time(value: Any) -> time:
    if isinstance(value, time):
        return value
    return time.fromisoformat(str(value))


def _parse_utc_offset(value: Any) -> float:
    text = str(value or "+08:00").strip()
    sign = -1 if text.startswith("-") else 1
    parts = text.lstrip("+-").split(":")
    hours = int(parts[0] or 0)
    minutes = int(parts[1] or 0) if len(parts) > 1 else 0
    return sign * (hours + minutes / 60)


def _true_solar_time(user_data: dict[str, Any], birth_date: date, birth_time: time) -> dict[str, Any]:
    longitude = user_data.get("longitude")
    if longitude in {None, ""}:
        return {"status": "missing_longitude", "applied": False}
    try:
        longitude_value = float(longitude)
    except (TypeError, ValueError):
        return {"status": "invalid_longitude", "applied": False}
    utc_offset = _parse_utc_offset(user_data.get("utc_offset"))
    standard_meridian = utc_offset * 15
    day_of_year = birth_date.timetuple().tm_yday
    angle = 2 * math.pi * (day_of_year - 81) / 364
    equation_of_time = 9.87 * math.sin(2 * angle) - 7.53 * math.cos(angle) - 1.5 * math.sin(angle)
    longitude_correction = 4 * (longitude_value - standard_meridian)
    total_correction = longitude_correction + equation_of_time
    local_dt = datetime.combine(birth_date, birth_time)
    adjusted = local_dt + timedelta(minutes=total_correction)
    return {
        "status": "computed",
        "applied": bool(user_data.get("use_true_solar_time")),
        "local_time": local_dt.isoformat(timespec="seconds"),
        "true_solar_time": adjusted.isoformat(timespec="seconds"),
        "longitude": longitude_value,
        "standard_meridian": standard_meridian,
        "equation_of_time_minutes": round(equation_of_time, 2),
        "longitude_correction_minutes": round(longitude_correction, 2),
        "total_correction_minutes": round(total_correction, 2),
        "policy": "computed_but_not_applied_by_default",
    }


def _element_scores(pillars: dict[str, str]) -> dict[str, int]:
    scores = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for pillar in pillars.values():
        scores[STEM_ELEMENTS[pillar[0]]] += 2
        scores[BRANCH_ELEMENTS[pillar[1]]] += 3
        for hidden in HIDDEN_STEMS[pillar[1]]:
            scores[STEM_ELEMENTS[hidden["stem"]]] += max(1, hidden["weight"] // 50)
    return scores


def _relation_pairs(values: list[str], mapping: dict[str, str], label: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for left in values:
        right = mapping.get(left)
        if right and right in values:
            relation_name = RELATION_LABELS.get(label, label)
            found.append({"type": label, "name": f"{left}{right}{relation_name}", "left": left, "right": right})
    return found


def _ten_god(day_stem: str, target_stem: str) -> str:
    day_element = STEM_ELEMENTS[day_stem]
    target_element = STEM_ELEMENTS[target_stem]
    same_polarity = STEM_POLARITY[day_stem] == STEM_POLARITY[target_stem]
    if target_element == day_element:
        return "比肩" if same_polarity else "劫財"
    if ELEMENT_GENERATES[day_element] == target_element:
        return "食神" if same_polarity else "傷官"
    if ELEMENT_CONTROLS[day_element] == target_element:
        return "偏財" if same_polarity else "正財"
    if ELEMENT_CONTROLS[target_element] == day_element:
        return "七殺" if same_polarity else "正官"
    if ELEMENT_GENERATES[target_element] == day_element:
        return "偏印" if same_polarity else "正印"
    return "未知"


def _hidden_stems(day_stem: str, pillars: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    hidden_by_pillar: dict[str, list[dict[str, Any]]] = {}
    for palace, pillar in pillars.items():
        branch = pillar[1]
        hidden_by_pillar[palace] = [
            {
                **hidden,
                "god": _ten_god(day_stem, hidden["stem"]),
                "element": STEM_ELEMENTS[hidden["stem"]],
                "polarity": STEM_POLARITY[hidden["stem"]],
                "source_branch": branch,
            }
            for hidden in HIDDEN_STEMS[branch]
        ]
    return hidden_by_pillar


def _ten_gods(day_stem: str, pillars: dict[str, str]) -> dict[str, dict[str, str]]:
    hidden_by_pillar = _hidden_stems(day_stem, pillars)
    return {
        palace: {
            "stem": pillar[0],
            "god": _ten_god(day_stem, pillar[0]),
            "element": STEM_ELEMENTS[pillar[0]],
            "polarity": STEM_POLARITY[pillar[0]],
            "hidden_stems": hidden_by_pillar[palace],
        }
        for palace, pillar in pillars.items()
    }


def _notable_patterns(
    pillars: dict[str, str],
    scores: dict[str, int],
    day_master: str,
    relations: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    patterns: list[dict[str, str]] = []
    high_element = max(scores, key=scores.get)
    low_element = min(scores, key=scores.get)
    patterns.append(
        {
            "id": f"bazi.pattern.{high_element}.high",
            "name": f"{high_element}旺",
            "basis": "五行最高分",
            "meaning": f"{high_element}能量是此盤目前最突出的五行訊號。",
        }
    )
    patterns.append(
        {
            "id": f"bazi.pattern.{low_element}.low",
            "name": f"{low_element}弱",
            "basis": "五行最低分",
            "meaning": f"{low_element}能量是此盤目前最需要補位的五行訊號。",
        }
    )
    day_strength = "日主偏強" if scores[STEM_ELEMENTS[day_master]] >= 7 else "日主偏弱"
    patterns.append(
        {
            "id": "bazi.pattern.day_master_strength",
            "name": day_strength,
            "basis": "日主五行支持分",
            "meaning": "日主強弱用來判斷自我核心是偏能扛、偏主動，還是需要借環境補力。",
        }
    )
    for relation in relations["stem"] + relations["branch"]:
        patterns.append(
            {
                "id": f"bazi.pattern.relation.{relation['left']}.{relation['right']}.{relation['type']}",
                "name": relation["name"],
                "basis": "天干地支關係",
                "meaning": f"{relation['name']}代表命盤內部有互相牽動的關係訊號。",
            }
        )
    return patterns


def _annual_relations(annual_pillar: str, pillars: dict[str, str]) -> dict[str, list[dict[str, str]]]:
    stems = [annual_pillar[0], *[pillar[0] for pillar in pillars.values()]]
    branches = [annual_pillar[1], *[pillar[1] for pillar in pillars.values()]]
    return {
        "stem": _relation_pairs(stems, STEM_COMBINES, "combine")
        + _relation_pairs(stems, STEM_CLASHES, "clash"),
        "branch": _relation_pairs(branches, BRANCH_HARMONIES, "harmony")
        + _relation_pairs(branches, BRANCH_CLASHES, "clash"),
    }


def _luck_cycles(
    birth_date: date,
    target_year: int,
    month_pillar: str,
    day_master: str,
    pillars: dict[str, str],
    birth_time: time,
    gender: str | None = None,
) -> dict[str, Any]:
    provider_luck = _lunar_python_luck_cycles(birth_date, birth_time, target_year, day_master, gender)
    if provider_luck:
        provider_luck["annual"]["flow_months"] = _flow_months(target_year, day_master)
        return provider_luck

    age = max(0, target_year - birth_date.year)
    current_phase = age // 10
    month_index = HEAVENLY_STEMS.index(month_pillar[0]) % 10
    branch_index = EARTHLY_BRANCHES.index(month_pillar[1]) % 12
    direction = _luck_direction(pillars["year"][0], gender)
    direction_step = 1 if direction == "forward" else -1
    decade_cycles = []
    for phase in range(8):
        pillar = (
            HEAVENLY_STEMS[(month_index + direction_step * (phase + 1)) % 10]
            + EARTHLY_BRANCHES[(branch_index + direction_step * (phase + 1)) % 12]
        )
        decade_cycles.append(
            {
                "age_start": phase * 10,
                "age_end": phase * 10 + 9,
                "pillar": pillar,
                "ten_god": _ten_god(day_master, pillar[0]),
                "theme": _decade_theme(_ten_god(day_master, pillar[0])),
                "direction": direction,
            }
        )
    annual_pillar = _year_pillar(date(target_year, 1, 1))
    annual_ten_god = _ten_god(day_master, annual_pillar[0])
    annual_relations = _annual_relations(annual_pillar, pillars)
    return {
        "algorithm_level": "mvp_age_decade_not_qiyun",
        "notice": "目前已依年干陰陽與性別判斷大運順逆，但尚未用精確節氣時計算起運歲數；十年段仍為 MVP 定位。",
        "qiyun": {
            "status": "pending_solar_term_time",
            "direction": direction,
            "direction_label": "順行" if direction == "forward" else "逆行",
            "start_age_years": None,
            "basis": "年干陰陽 + 性別；精準起運需出生前後節氣時間。",
        },
        "target_year": target_year,
        "nominal_age": age,
        "decade_cycles": decade_cycles,
        "current_decade": decade_cycles[min(current_phase, len(decade_cycles) - 1)],
        "annual": {
            "year": target_year,
            "pillar": annual_pillar,
            "zodiac": ZODIACS[annual_pillar[1]],
            "ten_god": annual_ten_god,
            "theme": _annual_theme(annual_ten_god, annual_relations),
            "interaction_summary": _interaction_summary(annual_relations),
            "relations": annual_relations,
            "flow_months": _flow_months(target_year, day_master),
        },
    }


def _lunar_python_luck_cycles(
    birth_date: date,
    birth_time: time,
    target_year: int,
    day_master: str,
    gender: str | None,
) -> dict[str, Any] | None:
    try:
        from lunar_python import Solar
    except ImportError:
        return None
    gender_code = 1 if (gender or "").lower() == "male" else 0
    try:
        lunar = Solar.fromYmdHms(
            birth_date.year,
            birth_date.month,
            birth_date.day,
            birth_time.hour,
            birth_time.minute,
            birth_time.second,
        ).getLunar()
        yun = lunar.getEightChar().getYun(gender_code)
        da_yun = yun.getDaYun()
    except Exception:
        return None
    decade_cycles = []
    current_decade = None
    for item in da_yun:
        pillar = item.getGanZhi()
        if not pillar:
            continue
        ten_god = _ten_god(day_master, pillar[0])
        cycle = {
            "index": item.getIndex(),
            "start_year": item.getStartYear(),
            "end_year": item.getEndYear(),
            "age_start": item.getStartAge(),
            "age_end": item.getEndAge(),
            "pillar": pillar,
            "ten_god": ten_god,
            "theme": _decade_theme(ten_god),
            "direction": "forward" if yun.isForward() else "reverse",
        }
        decade_cycles.append(cycle)
        if item.getStartYear() <= target_year <= item.getEndYear():
            current_decade = cycle
    annual_pillar = _provider_year_pillar(target_year)
    annual_ten_god = _ten_god(day_master, annual_pillar[0])
    annual_relations = _annual_relations(annual_pillar, {
        "year": lunar.getYearInGanZhi(),
        "month": lunar.getMonthInGanZhi(),
        "day": lunar.getDayInGanZhi(),
        "hour": lunar.getTimeInGanZhi(),
    })
    return {
        "algorithm_level": "lunar_python_qiyun_dayun",
        "notice": "起運歲數與大運由 lunar-python Yun/DaYun 產出；真太陽時是否套用由 policy 控制。",
        "qiyun": {
            "status": "computed",
            "direction": "forward" if yun.isForward() else "reverse",
            "direction_label": "順行" if yun.isForward() else "逆行",
            "start_age_years": yun.getStartYear(),
            "start_age_months": yun.getStartMonth(),
            "start_age_days": yun.getStartDay(),
            "start_age_hours": yun.getStartHour(),
            "start_solar": str(yun.getStartSolar()),
            "basis": "lunar-python EightChar.getYun(gender).getDaYun()",
        },
        "target_year": target_year,
        "nominal_age": max(0, target_year - birth_date.year),
        "decade_cycles": decade_cycles,
        "current_decade": current_decade or (decade_cycles[0] if decade_cycles else {}),
        "annual": {
            "year": target_year,
            "pillar": annual_pillar,
            "zodiac": ZODIACS[annual_pillar[1]],
            "ten_god": annual_ten_god,
            "theme": _annual_theme(annual_ten_god, annual_relations),
            "interaction_summary": _interaction_summary(annual_relations),
            "relations": annual_relations,
        },
    }


def _provider_year_pillar(target_year: int) -> str:
    try:
        from lunar_python import Solar
    except ImportError:
        return _year_pillar(date(target_year, 1, 1))
    return Solar.fromYmdHms(target_year, 7, 1, 12, 0, 0).getLunar().getYearInGanZhi()


def _flow_months(target_year: int, day_master: str) -> list[dict[str, Any]]:
    months = []
    for month in range(1, 13):
        try:
            from lunar_python import Solar
            pillar = Solar.fromYmdHms(target_year, month, 15, 12, 0, 0).getLunar().getMonthInGanZhi()
            basis = "lunar-python mid-month representative solar-term month"
        except Exception:
            pillar = _month_pillar(date(target_year, month, 15))
            basis = "pantheon fallback calendar month"
        months.append(
            {
                "month": month,
                "representative_date": f"{target_year}-{month:02d}-15",
                "pillar": pillar,
                "ten_god": _ten_god(day_master, pillar[0]),
                "basis": basis,
            }
        )
    return months


def _luck_direction(year_stem: str, gender: str | None) -> str:
    is_yang_year = STEM_POLARITY[year_stem] == "yang"
    normalized_gender = (gender or "").lower()
    if normalized_gender == "male":
        return "forward" if is_yang_year else "reverse"
    if normalized_gender == "female":
        return "reverse" if is_yang_year else "forward"
    return "forward" if is_yang_year else "reverse"


def _cycle_theme(ten_god: str) -> str:
    return {
        "比肩": "自我定位、同儕競爭、主動爭取",
        "劫財": "資源分配、合作摩擦、界線感",
        "食神": "作品輸出、教學分享、穩定表達",
        "傷官": "突破規則、表現欲、創新與衝撞",
        "偏財": "機會流動、業務資源、彈性變現",
        "正財": "穩定收入、責任承擔、務實累積",
        "七殺": "壓力挑戰、速度、競爭與決斷",
        "正官": "秩序規範、職涯責任、名聲位置",
        "偏印": "研究洞察、非典型學習、內在轉向",
        "正印": "支持系統、學習沉澱、保護與修復",
    }.get(ten_god, "年度主題待補")


def _decade_theme(ten_god: str) -> str:
    return {
        "比肩": "十年主軸是建立自我位置，練習從同儕競爭中長出自己的路線。",
        "劫財": "十年主軸是資源與合作界線，重點在合夥、分配與風險控管。",
        "食神": "十年主軸是穩定輸出，把才華、作品與教學累積成可持續資產。",
        "傷官": "十年主軸是突破舊框架，適合創新，但要避免長期跟制度硬碰硬。",
        "偏財": "十年主軸是機會與流動資源，適合拓展市場、人脈與副收入。",
        "正財": "十年主軸是穩定累積，把責任、現金流與生活秩序慢慢墊高。",
        "七殺": "十年主軸是承壓與升級，會反覆遇到競爭、速度與決斷力的訓練。",
        "正官": "十年主軸是職涯名分與規範，適合建立位置、信用與可被信任的角色。",
        "偏印": "十年主軸是研究與轉向，適合沉澱特殊知識、技術或非典型路線。",
        "正印": "十年主軸是補養與學習，適合建立支持系統、資格、知識與保護層。",
    }.get(ten_god, "十年主題待補")


def _annual_theme(ten_god: str, relations: dict[str, list[dict[str, str]]]) -> str:
    base = {
        "比肩": "今年容易被推去爭取主導權，適合明確表態與重新排定位。",
        "劫財": "今年要特別看資源分配與合作邊界，避免人情壓過規則。",
        "食神": "今年適合把長期累積做成作品、內容或可交付成果。",
        "傷官": "今年容易想突破限制，適合創新，但要注意說話和制度衝突。",
        "偏財": "今年機會流動較強，適合談合作、開新案、測試變現路徑。",
        "正財": "今年重點在穩定現金流與責任分配，適合整理財務和承諾。",
        "七殺": "今年會把壓力事件推到眼前，適合快速決斷，但不宜硬衝到底。",
        "正官": "今年重點在規範、職位、名聲與責任，適合做可被檢驗的承諾。",
        "偏印": "今年適合研究、修正方向與建立新的理解框架。",
        "正印": "今年適合補課、取得支持、修復狀態，不宜過度消耗。",
    }.get(ten_god, "今年主題待補")
    interaction = _interaction_summary(relations)
    return f"{base} 本命互動：{interaction}。"


def _interaction_summary(relations: dict[str, list[dict[str, str]]]) -> str:
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


def _strength_analysis(pillars: dict[str, str], scores: dict[str, int], day_master: str) -> dict[str, Any]:
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


class BaziCalculator(BaseDivination):
    """八字 MVP 算力接口，後續可替換為授權確認後的完整演算法。"""

    name = "bazi"

    def calculate(self, user_data: dict[str, Any]) -> dict[str, Any]:
        birth_date = _parse_date(user_data["birth_date"])
        birth_time = _parse_time(user_data["birth_time"])
        solar_time = _true_solar_time(user_data, birth_date, birth_time)
        calculation_dt = (
            datetime.fromisoformat(solar_time["true_solar_time"])
            if solar_time.get("applied") and solar_time.get("true_solar_time")
            else datetime.combine(birth_date, birth_time)
        )
        pillars, calendar_engine = _calendar_pillars(calculation_dt.date(), calculation_dt.time())
        year = pillars["year"]
        month = pillars["month"]
        day = pillars["day"]
        stems = [pillar[0] for pillar in pillars.values()]
        branches = [pillar[1] for pillar in pillars.values()]
        scores = _element_scores(pillars)
        day_master = day[0]
        day_master_element = STEM_ELEMENTS[day_master]
        supporting_score = scores[day_master_element]
        relations = {
            "stem": _relation_pairs(stems, STEM_COMBINES, "combine")
            + _relation_pairs(stems, STEM_CLASHES, "clash"),
            "branch": _relation_pairs(branches, BRANCH_HARMONIES, "harmony")
            + _relation_pairs(branches, BRANCH_CLASHES, "clash"),
        }

        return {
            "system": self.name,
            "version": self.version,
            "algorithm_level": calendar_engine["algorithm_level"],
            "notice": calendar_engine["notice"],
            "calendar_engine": calendar_engine,
            "solar_time": solar_time,
            "ruleset_version": "pantheon-bazi-rules-mvp-0.2",
            "pillars": pillars,
            "zodiac": {
                "branch": year[1],
                "animal": ZODIACS[year[1]],
                "label": f"{year[1]}{ZODIACS[year[1]]}",
            },
            "day_master": {
                "stem": day_master,
                "element": day_master_element,
                "supporting_score": supporting_score,
                "strength": "strong" if supporting_score >= 7 else "weak",
            },
            "hidden_stems": _hidden_stems(day_master, pillars),
            "ten_gods": _ten_gods(day_master, pillars),
            "elements": scores,
            "relations": relations,
            "strength_analysis": _strength_analysis(pillars, scores, day_master),
            "notable_patterns": _notable_patterns(pillars, scores, day_master, relations),
            "luck_cycles": _luck_cycles(
                calculation_dt.date(),
                int(user_data.get("target_year") or 2026),
                month,
                day_master,
                pillars,
                calculation_dt.time(),
                str(user_data.get("gender") or ""),
            ),
        }
