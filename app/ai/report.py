from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Signal(BaseModel):
    id: str
    system: str
    category: str
    label: str
    value: str | int | float | bool
    polarity: Literal["low", "neutral", "high", "present"] = "present"
    basis: str
    plain_meaning: str


class ComboCard(BaseModel):
    id: str
    title: str
    evidence_ids: list[str]
    formula: str
    because: str
    therefore: str
    suitable: list[str] = Field(default_factory=list)
    unsuitable: list[str] = Field(default_factory=list)
    advice: str


class ReadingBlock(BaseModel):
    topic: str
    title: str
    source_card_ids: list[str]
    summary: str
    reasoning: str
    actions: list[str]


class UnifiedReport(BaseModel):
    syntax_version: str = "0.2"
    narrative_strategy: str = "evidence_chain"
    signals: list[Signal]
    combo_cards: list[ComboCard]
    reading_blocks: list[ReadingBlock]


ELEMENT_MEANINGS = {
    "木": "木代表成長、規劃、學習、創造與向外延展",
    "火": "火代表表達、熱情、審美、現場感與反應速度",
    "土": "土代表穩定、承接、信任、管理與長期累積",
    "金": "金代表規則、判斷、效率、邊界與決斷力",
    "水": "水代表觀察、流動、思考、溝通與資訊敏感度",
}
ELEMENT_IDS = {"木": "wood", "火": "fire", "土": "earth", "金": "metal", "水": "water"}
PATTERN_ID_SLUGS = {"木": "wood", "火": "fire", "土": "earth", "金": "metal", "水": "water"}


def build_unified_report(charts: dict[str, Any]) -> UnifiedReport:
    bazi = charts.get("bazi", {})
    ziwei = charts.get("ziwei", {})
    mbti = charts.get("mbti", {})
    signals = _build_signals(bazi, ziwei, mbti)
    combo_cards = _build_combo_cards(signals, bazi, ziwei, mbti)
    reading_blocks = _build_reading_blocks(combo_cards)
    return UnifiedReport(signals=signals, combo_cards=combo_cards, reading_blocks=reading_blocks)


def _build_signals(bazi: dict[str, Any], ziwei: dict[str, Any], mbti: dict[str, Any] | None = None) -> list[Signal]:
    signals: list[Signal] = []
    elements = bazi.get("elements", {})
    if elements:
        max_score = max(elements.values())
        min_score = min(elements.values())
        for element, score in elements.items():
            polarity: Literal["low", "neutral", "high", "present"] = "neutral"
            if score == max_score:
                polarity = "high"
            elif score == min_score:
                polarity = "low"
            signals.append(
                Signal(
                    id=f"bazi.element.{ELEMENT_IDS.get(element, str(element))}",
                    system="bazi",
                    category="element",
                    label=element,
                    value=score,
                    polarity=polarity,
                    basis="五行分數",
                    plain_meaning=ELEMENT_MEANINGS.get(element, "五行能量訊號"),
                )
            )

    day_master = bazi.get("day_master", {})
    if day_master:
        stem = day_master.get("stem", "未知")
        element = day_master.get("element", "未知")
        signals.append(
            Signal(
                id="bazi.day_master",
                system="bazi",
                category="identity",
                label=f"{stem}{element}",
                value=stem,
                polarity="present",
                basis="日主",
                plain_meaning=f"日主代表自我核心；{element}日主會影響使用者理解世界與行動的方式",
            )
        )

    zodiac = bazi.get("zodiac", {})
    if zodiac:
        signals.append(
            Signal(
                id="bazi.zodiac",
                system="bazi",
                category="zodiac",
                label=str(zodiac.get("label", "未知")),
                value=str(zodiac.get("animal", "未知")),
                polarity="present",
                basis="生肖",
                plain_meaning="生肖是年支轉出的民俗身份訊號，適合放在命盤身份卡作為入口。",
            )
        )

    for palace, item in bazi.get("ten_gods", {}).items():
        signals.append(
            Signal(
                id=f"bazi.ten_god.{palace}",
                system="bazi",
                category="ten_god",
                label=str(item.get("god", "未知")),
                value=str(item.get("stem", "未知")),
                polarity="present",
                basis=f"{_pillar_label(palace)}十神",
                plain_meaning=f"{item.get('god', '未知')}是以日主對照{_pillar_label(palace)}天干得出的十神名稱。",
            )
        )

    for index, pattern in enumerate(bazi.get("notable_patterns", [])):
        signals.append(
            Signal(
                id=_stable_pattern_id("bazi", pattern, index),
                system="bazi",
                category="pattern",
                label=str(pattern.get("name", "未知格局")),
                value=str(pattern.get("basis", "格局訊號")),
                polarity="present",
                basis=str(pattern.get("basis", "格局訊號")),
                plain_meaning=str(pattern.get("meaning", "此訊號需要進一步解讀。")),
            )
        )

    luck_cycles = bazi.get("luck_cycles", {})
    current_decade = luck_cycles.get("current_decade", {})
    if current_decade:
        signals.append(
            Signal(
                id="bazi.luck.current_decade",
                system="bazi",
                category="luck_cycle",
                label=f"{current_decade.get('age_start')}-{current_decade.get('age_end')}歲 {current_decade.get('pillar')}",
                value=str(current_decade.get("pillar", "未知")),
                polarity="present",
                basis="大運階段",
                plain_meaning=f"目前以年齡十年段估算大運主題：{current_decade.get('theme', '待補')}。",
            )
        )
    annual = luck_cycles.get("annual", {})
    if annual:
        signals.append(
            Signal(
                id="bazi.luck.annual",
                system="bazi",
                category="annual_luck",
                label=f"{annual.get('year')} {annual.get('pillar')}年",
                value=str(annual.get("pillar", "未知")),
                polarity="present",
                basis="年度流年",
                plain_meaning=f"年度干支與日主形成{annual.get('ten_god', '未知')}主題：{annual.get('theme', '待補')}。",
            )
        )

    life_palace = ziwei.get("life_palace")
    if life_palace:
        signals.append(
            Signal(
                id="ziwei.life_palace",
                system="ziwei",
                category="palace",
                label=str(life_palace),
                value=str(life_palace),
                polarity="present",
                basis="命宮",
                plain_meaning="命宮代表人格底色、外在呈現與人生主軸",
            )
        )

    body_palace = ziwei.get("body_palace")
    if body_palace:
        signals.append(
            Signal(
                id="ziwei.body_palace",
                system="ziwei",
                category="palace",
                label=str(body_palace),
                value=str(body_palace),
                polarity="present",
                basis="身宮",
                plain_meaning="身宮代表後天行動模式與實際投入的生活重心",
            )
        )

    for star in ziwei.get("life_palace_stars", []):
        signals.append(
            Signal(
                id=f"ziwei.life_star.{_slug(star)}",
                system="ziwei",
                category="star",
                label=str(star),
                value=str(star),
                polarity="present",
                basis="命宮星曜",
                plain_meaning=f"{star}出現在命宮訊號中，用來輔助解讀人格主軸。",
            )
        )

    for index, pattern in enumerate(ziwei.get("notable_patterns", [])):
        signals.append(
            Signal(
                id=_stable_pattern_id("ziwei", pattern, index),
                system="ziwei",
                category="pattern",
                label=str(pattern.get("name", "未知格局")),
                value=str(pattern.get("basis", "格局訊號")),
                polarity="present",
                basis=str(pattern.get("basis", "格局訊號")),
                plain_meaning=str(pattern.get("meaning", "此紫微訊號需要進一步解讀。")),
            )
        )

    if mbti and mbti.get("status") in {"scored", "scored_core"}:
        for dimension, item in mbti.get("dimensions", {}).items():
            confidence = str(item.get("confidence", "primary"))
            preferred = str(item.get("preferred", "未知"))
            preferred_label = str(item.get("preferred_label", "自評偏好"))
            score = float(item.get("score", 0))
            polarity: Literal["low", "neutral", "high", "present"] = "present"
            if confidence == "low_margin":
                polarity = "neutral"
            elif score > 0:
                polarity = "high"
            elif score < 0:
                polarity = "low"
            meaning = f"自評問卷目前偏向{preferred_label}（{preferred}）"
            if confidence == "low_margin":
                meaning = f"自評問卷在{dimension} 接近中線，較適合視為彈性偏好，不宜寫成固定人格"
            signals.append(
                Signal(
                    id=f"mbti.dimension.{dimension.lower()}",
                    system="mbti",
                    category="personality_dimension",
                    label=f"{dimension}:{preferred}",
                    value=round(score, 3),
                    polarity=polarity,
                    basis="MBTI 自評問卷",
                    plain_meaning=meaning,
                )
            )

    return signals


def _build_combo_cards(
    signals: list[Signal],
    bazi: dict[str, Any],
    ziwei: dict[str, Any],
    mbti: dict[str, Any] | None = None,
) -> list[ComboCard]:
    signal_by_id = {signal.id: signal for signal in signals}
    high_elements = [signal for signal in signals if signal.category == "element" and signal.polarity == "high"]
    low_elements = [signal for signal in signals if signal.category == "element" and signal.polarity == "low"]
    cards: list[ComboCard] = []

    if high_elements:
        high = high_elements[0]
        evidence = [high.id]
        if "ziwei.life_palace" in signal_by_id:
            evidence.append("ziwei.life_palace")
        cards.append(
            ComboCard(
                id="combo.primary_drive",
                title=f"{high.label}旺主能量",
                evidence_ids=evidence,
                formula=f"{high.label}旺 + 命宮訊號",
                because=f"因為五行裡{high.label}能量最高，並且命宮提供人格主軸",
                therefore=f"所以解讀要先從{high.plain_meaning}展開，再連到個性、職涯與關係建議",
                suitable=_suitable_for_element(str(high.label)),
                unsuitable=_unsuitable_for_element(str(high.label)),
                advice=_advice_for_element(str(high.label)),
            )
        )

    ten_god_signals = [signal for signal in signals if signal.category == "ten_god"]
    officer_or_output = [
        signal for signal in ten_god_signals if signal.label in {"正官", "七殺", "食神", "傷官"}
    ]
    life_star_signals = [signal for signal in signals if signal.category == "star" and signal.basis == "命宮星曜"]
    if officer_or_output or life_star_signals:
        evidence = [signal.id for signal in officer_or_output[:2] + life_star_signals[:2]]
        cards.append(
            ComboCard(
                id="combo.named_basis_stack",
                title="命名依據組合",
                evidence_ids=evidence,
                formula="十神 + 命宮星曜",
                because="因為命盤已經抓到十神名稱與命宮星曜名稱",
                therefore="所以前端可以先展示依據名稱，再展開白話解讀與建議，而不是直接給結論",
                suitable=["依據先行的報告", "可展開的組合牌", "命理名詞教學"],
                unsuitable=["沒有依據的 AI 斷語", "只給性格標籤不說來源"],
                advice="報告每一段先列出十神、星曜或格局名，再接白話翻譯。",
            )
        )

    if low_elements:
        low = low_elements[0]
        cards.append(
            ComboCard(
                id="combo.energy_gap",
                title=f"{low.label}弱補強牌",
                evidence_ids=[low.id],
                formula=f"{low.label}弱",
                because=f"因為五行裡{low.label}能量最低",
                therefore=f"所以這一塊不適合被包裝成天生強項，而應該變成環境選擇與習慣補強",
                suitable=[f"用制度或他人合作補足{low.label}的不足"],
                unsuitable=[f"長期把{low.label}相關能力當成唯一成功路徑"],
                advice=f"先承認{low.label}是需要補位的能量，不要把所有壓力都放在這個面向。",
            )
        )

    day_master = bazi.get("day_master", {})
    if day_master and "bazi.day_master" in signal_by_id:
        evidence = ["bazi.day_master"]
        if high_elements:
            evidence.append(high_elements[0].id)
        cards.append(
            ComboCard(
                id="combo.identity_to_action",
                title="日主行動牌",
                evidence_ids=evidence,
                formula="日主 + 主五行能量",
                because=f"因為日主是{day_master.get('stem')}，五行屬{day_master.get('element')}",
                therefore="所以報告不能只說個性，而要把自我核心連到可執行選擇",
                suitable=["能保留自主判斷的選擇", "能逐步累積作品或成果的路線"],
                unsuitable=["完全被動等待安排", "沒有回饋也沒有成長感的環境"],
                advice="把自我核心翻成一個短期可驗證的行動，不要只停在命理標籤。",
            )
        )

    if ziwei.get("life_palace") and ziwei.get("body_palace"):
        cards.append(
            ComboCard(
                id="combo.palace_axis",
                title="命身宮軸線",
                evidence_ids=["ziwei.life_palace", "ziwei.body_palace"],
                formula="命宮 + 身宮",
                because=f"因為命宮在{ziwei.get('life_palace')}，身宮在{ziwei.get('body_palace')}",
                therefore="所以紫微段落要同時區分人格底色與後天行動重心",
                suitable=["先看人格主軸，再看實際行動落點"],
                unsuitable=["只用單一宮位直接下結論"],
                advice="紫微解讀要把命宮當起點，身宮當落地方式。",
            )
        )

    mbti_signals = [signal for signal in signals if signal.system == "mbti"]
    if mbti and mbti.get("status") in {"scored", "scored_core"} and mbti_signals:
        mbti_type = mbti.get("type") or mbti.get("core_type") or "未定型"
        low_margin = [
            signal for signal in mbti_signals if signal.polarity == "neutral"
        ]
        cards.append(
            ComboCard(
                id="combo.mbti_self_report",
                title=f"64 分支人格自評 {mbti_type}",
                evidence_ids=[signal.id for signal in mbti_signals],
                formula="MBTI 四維 + A/O + H/C",
                because="因為使用者完成了個人自評問卷，系統已取得核心人格與分支人格維度",
                therefore="所以報告可以把 64 分支人格當成使用者自我敘述的語言，輔助命盤解讀與後續追問",
                suitable=["自我理解", "溝通偏好整理", "報告後續追問", "AI 顧問語氣校準"],
                unsuitable=["心理診斷", "單憑人格代碼決定人生方向", "覆蓋八字或紫微原始訊號"],
                advice=_mbti_advice(low_margin),
            )
        )

    luck_signals = [signal for signal in signals if signal.category in {"luck_cycle", "annual_luck"}]
    if luck_signals:
        cards.append(
            ComboCard(
                id="combo.luck_timing",
                title="大運流年牌",
                evidence_ids=[signal.id for signal in luck_signals],
                formula="十年大運 + 年度流年",
                because="因為命盤已經產生目前十年階段與年度干支訊號",
                therefore="所以時間解讀先看長週期，再看年度主題，不細分到流月以避免假精準",
                suitable=["年度規劃", "職涯節奏判斷", "重大決策前的自我檢查"],
                unsuitable=["逐月鐵口直斷", "每日吉凶判定", "忽略出生時間可信度的精算"],
                advice="先用大運看人生階段，再用流年看今年重點；流月需等曆法與起運校準後再做。",
            )
        )

    return cards


def _build_reading_blocks(cards: list[ComboCard]) -> list[ReadingBlock]:
    card_by_id = {card.id: card for card in cards}
    blocks: list[ReadingBlock] = []

    primary = card_by_id.get("combo.primary_drive")
    if primary:
        blocks.append(
            ReadingBlock(
                topic="overview",
                title="人生總覽",
                source_card_ids=[primary.id],
                summary=primary.therefore,
                reasoning=f"{primary.because}，{primary.therefore}。",
                actions=[primary.advice],
            )
        )
        blocks.append(
            ReadingBlock(
                topic="career",
                title="職涯適配",
                source_card_ids=[primary.id],
                summary=f"適合：{'、'.join(primary.suitable)}；不適合：{'、'.join(primary.unsuitable)}。",
                reasoning=f"{primary.formula} 會優先影響使用者適合的工作環境與輸出方式。",
                actions=[primary.advice],
            )
        )

    gap = card_by_id.get("combo.energy_gap")
    if gap:
        blocks.append(
            ReadingBlock(
                topic="risk",
                title="能量短板",
                source_card_ids=[gap.id],
                summary=gap.therefore,
                reasoning=f"{gap.because}，所以不要把這個面向寫成天生強項。",
                actions=[gap.advice],
            )
        )

    palace = card_by_id.get("combo.palace_axis")
    if palace:
        blocks.append(
            ReadingBlock(
                topic="ziwei",
                title="紫微命身軸線",
                source_card_ids=[palace.id],
                summary=palace.therefore,
                reasoning=f"{palace.because}，{palace.therefore}。",
                actions=[palace.advice],
            )
        )

    mbti = card_by_id.get("combo.mbti_self_report")
    if mbti:
        blocks.append(
            ReadingBlock(
                topic="personality",
                title="MBTI 自評偏好",
                source_card_ids=[mbti.id],
                summary=mbti.therefore,
                reasoning=f"{mbti.because}，{mbti.therefore}。",
                actions=[mbti.advice],
            )
        )

    return blocks


def _suitable_for_element(element: str) -> list[str]:
    return {
        "木": ["教育", "策劃", "產品", "內容企劃", "顧問", "長期成長型工作"],
        "火": ["內容", "品牌", "教學", "顧問", "社群", "表演型工作"],
        "土": ["營運", "管理", "客戶成功", "專案管理", "服務業", "長期經營"],
        "金": ["策略", "法務", "金融分析", "流程設計", "品質控管", "決策型工作"],
        "水": ["研究", "溝通", "資料分析", "交易", "跨域協作", "資訊流工作"],
    }.get(element, ["需要進一步解讀的方向"])


def _unsuitable_for_element(element: str) -> list[str]:
    return {
        "木": ["完全沒有成長空間", "只做短期消耗", "不能學習的環境"],
        "火": ["高度重複", "完全照 SOP", "不能表達", "沒有回饋的環境"],
        "土": ["長期混亂", "承諾反覆變動", "沒有信任基礎的環境"],
        "金": ["規則模糊", "邊界不清", "只靠人情不看標準的環境"],
        "水": ["資訊封閉", "不能交流", "節奏僵硬", "只靠單一路徑的環境"],
    }.get(element, ["需要進一步避開的方向"])


def _advice_for_element(element: str) -> str:
    return {
        "木": "把想法拆成可持續成長的計畫，避免只停在靈感階段。",
        "火": "先累積可展示作品，不要只停留在靈感或口才。",
        "土": "建立穩定節奏與可交付成果，讓信任感變成你的資產。",
        "金": "把判斷標準寫清楚，讓你的決斷力不變成過度挑剔。",
        "水": "保留資訊流動與交流空間，讓觀察力轉成具體選擇。",
    }.get(element, "先把命盤訊號轉成一個可驗證的小行動。")


def _mbti_advice(low_margin: list[Signal]) -> str:
    if low_margin:
        labels = "、".join(signal.label.split(":")[0] for signal in low_margin)
        return f"{labels} 維度接近中線，先把它當成情境彈性，而不是固定人格標籤。"
    return "把 MBTI 當成自我描述語言，用來校準溝通與行動建議，不要讓四字母取代具體證據。"


def _pillar_label(palace: str) -> str:
    return {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "時柱"}.get(palace, palace)


def _stable_pattern_id(system: str, pattern: dict[str, Any], index: int) -> str:
    raw = str(pattern.get("id") or pattern.get("name") or index)
    return f"{system}.pattern.{_slug(raw)}"


def _slug(value: str) -> str:
    return "".join(ch if ch.isascii() and ch.isalnum() else "_" for ch in value).strip("_") or "signal"
