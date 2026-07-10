import { ELEMENT_ORDER, escapeHtml, formatAnnual, formatBirth, formatDecade } from "./utils.js";

export function renderFortunePaper(result, container) {
  const bazi = result.charts.bazi || {};
  const ziwei = result.charts.ziwei || {};
  const nameology = result.charts.nameology || {};
  const report = result.report || {};
  const input = result.input || {};
  const policy = result.metadata?.school_policy || {};
  const pillars = bazi.pillars || {};
  const tenGods = bazi.ten_gods || {};
  const combos = report.combo_cards || [];
  const signals = report.signals || [];
  const elementRows = ELEMENT_ORDER.map((element) => [element, Number((bazi.elements || {})[element] || 0)]);
  const baziPatterns = signals.filter((signal) => signal.system === "bazi" && signal.category === "pattern").slice(0, 5);
  const ziweiSignals = signals.filter((signal) => signal.system === "ziwei").slice(0, 5);
  const mainCombo = combos[0] || {};
  const timingCombo = combos.find((combo) => combo.id === "combo.luck_timing") || {};
  const secondaryCombos = combos.filter((combo) => combo.id !== mainCombo.id && combo.id !== timingCombo.id).slice(0, 2);
  const luck = bazi.luck_cycles || {};
  const qiyun = luck.qiyun || {};
  const currentDecade = luck.current_decade || {};
  const annual = luck.annual || {};
  const readingBlocks = report.reading_blocks || [];
  const strength = bazi.strength_analysis || {};
  const solarTime = bazi.solar_time || {};
  const flowMonths = annual.flow_months || [];
  const baziItems = bazi.calculated_items || {};
  const ziweiItems = ziwei.calculated_items || {};
  const growthStates = baziItems.growth_states || [];
  const specialForces = baziItems.special_forces || [];
  const shensha = {
    bazi: baziItems.shensha || [],
    ziwei: ziweiItems.support_stars || [],
    note: buildShenshaNote(baziItems.shensha || []),
  };
  const destinyProfile = buildDestinyProfile(bazi, ziwei, nameology, combos, readingBlocks, growthStates, specialForces);
  const careerReading = deriveCareerReading(bazi, ziwei, mainCombo, timingCombo);
  const yearlyNotes = deriveYearlyNotes(bazi, destinyProfile);

  container.innerHTML = `
    <article class="paper-sheet">
      <div class="paper-mark top-left">命書</div>
      <div class="paper-mark top-right">合參</div>
      <header class="paper-header">
        <div class="vertical-title">
          <span>命</span><span>書</span><span>報</span><span>告</span>
        </div>
        <div class="paper-name">
          <p>本次命主</p>
          <h2>${escapeHtml(input.name || "未填姓名")}</h2>
          <span>${escapeHtml(formatBirth(input))}</span>
        </div>
        <div class="paper-id-block">
          <div><strong>${escapeHtml((bazi.zodiac || {}).label || "未知")}</strong><span>生肖</span></div>
          <div><strong>${escapeHtml(`${(bazi.day_master || {}).stem || "?"}${(bazi.day_master || {}).element || ""}`)}</strong><span>日主</span></div>
          <div><strong>${escapeHtml(ziwei.life_palace || "未知")}</strong><span>命宮</span></div>
        </div>
      </header>

      <section class="paper-flow">
        <section class="paper-section">
          ${renderSectionHeading("01", "姓名合參", "名字先作入口，但不壓過本命盤")}
          ${renderNameology(nameology, bazi)}
        </section>

        <section class="paper-section">
          ${renderSectionHeading("02", "本命底色", "先講這個人的核心氣質")}
          <div class="paper-grid-map summary-grid">
            ${renderSummaryPanel("四柱", Object.values(pillars).join(" ") || "待補", destinyProfile.core)}
            ${renderSummaryPanel("日主", `${(bazi.day_master || {}).stem || "?"}${(bazi.day_master || {}).element || ""}`, destinyProfile.dayMaster)}
            ${renderSummaryPanel("旺衰候選", strengthLabel(strength.label), strength.caution || "旺衰只是候選，不直接定用神。")}
          </div>
        </section>

        <section class="paper-section">
          ${renderSectionHeading("03", "五行怎麼用", "不只列數字，直接翻成工作與風險")}
          <div class="paper-grid-map element-meaning-grid">
            <div class="paper-panel element-panel">
              <h3>五行分數</h3>
              <div class="paper-elements">
                ${elementRows.map(([name, value]) => `
                  <div>
                    <span>${escapeHtml(name)}</span>
                    <strong>${value}</strong>
                  </div>
                `).join("")}
              </div>
              <p>${escapeHtml(`support ${strength.support_score ?? "?"}｜pressure ${strength.pressure_score ?? "?"}`)}</p>
            </div>
            ${renderNarrativePanel("強項怎麼用", destinyProfile.elementUse)}
            ${renderNarrativePanel("缺口怎麼補", destinyProfile.elementRisk)}
          </div>
        </section>

        <section class="paper-section">
          ${renderSectionHeading("04", "十神", "只講盤裡有的，並標出最明顯的工作用法")}
          <div class="paper-grid-map ten-god-grid">
            <div class="paper-panel pillars-panel">
              <h3>四柱十神</h3>
              <div class="pillar-grid">
                ${["year", "month", "day", "hour"].map((key) => renderPillarCell(key, pillars[key], tenGods[key])).join("")}
              </div>
            </div>
            ${renderListPanel("明顯十神", listProminentTenGods(tenGods))}
            ${renderListPanel("藏干補充", listHiddenTenGods(tenGods))}
            ${renderNarrativePanel("十神用法", destinyProfile.tenGodUse)}
          </div>
        </section>

        <section class="paper-section">
          ${renderSectionHeading("05", "十二長生 / 祿刃", "看能量是怎麼發動，不和十神混在一起")}
          <div class="paper-grid-map force-grid">
            ${renderListPanel("十二長生", growthStates.map(formatGrowthState))}
            ${renderListPanel("祿刃與特殊氣", specialForces.map(formatCalculatedItem))}
            ${renderNarrativePanel("力量怎麼用", destinyProfile.forceUse)}
          </div>
        </section>

        <section class="paper-section">
          ${renderSectionHeading("06", "神煞", "目前是規則補判，只列有命中的項目")}
          <div class="paper-grid-map shensha-grid">
            ${renderListPanel("八字神煞", shensha.bazi.map(formatCalculatedItem))}
            ${renderListPanel("紫微輔星", shensha.ziwei.map(formatCalculatedItem))}
            ${renderNarrativePanel("神煞提醒", shensha.note)}
          </div>
        </section>

        <section class="paper-section">
          ${renderSectionHeading("07", "紫微星曜", "命宮看底色，身宮與官祿看工作落點")}
          <div class="paper-grid-map ziwei-grid">
            ${renderZiweiPanel("命宮", ziwei.life_palace, ziwei.life_palace_stars, destinyProfile.lifePalace)}
            ${renderZiweiPanel("身宮 / 官祿", ziwei.body_palace, ziwei.body_palace_stars, destinyProfile.bodyPalace)}
            ${renderZiweiPanel("財帛", "財帛", findPalaceStars(ziwei, "財帛"), destinyProfile.moneyPalace)}
          </div>
        </section>

        <section class="paper-section timing-section">
          ${renderSectionHeading("08", "今年工作運", "大運定階段，流年定今年的觸發")}
          <div class="timing-grid">
            <div class="paper-panel timing-panel decade-panel">
              <h3>${escapeHtml(formatDecade(currentDecade))}</h3>
              <p class="timing-theme">${escapeHtml(currentDecade.theme || "十年主題待補。")}</p>
              <div class="palace-line"><span>干支</span><strong>${escapeHtml(currentDecade.pillar || "待補")}</strong></div>
              <div class="palace-line"><span>十神</span><strong>${escapeHtml(currentDecade.ten_god || "待補")}</strong></div>
              <div class="palace-line"><span>起運</span><strong>${escapeHtml(formatQiyun(qiyun))}</strong></div>
            </div>
            <div class="paper-panel timing-panel annual-panel">
              <h3>${escapeHtml(formatAnnual(annual))}</h3>
              <p class="timing-theme">${escapeHtml(careerReading.work)}</p>
              <div class="palace-line"><span>十神</span><strong>${escapeHtml(annual.ten_god || "待補")}</strong></div>
              <div class="palace-line"><span>打法</span><strong>${escapeHtml(careerReading.strategy)}</strong></div>
            </div>
          </div>
          <div class="advice-grid">
            <div class="paper-panel">
              <h3>適合</h3>
              ${renderTagList(collectUnique([mainCombo.suitable, ...secondaryCombos.map((combo) => combo.suitable)]), "tag")}
            </div>
            <div class="paper-panel">
              <h3>不適合</h3>
              ${renderTagList(collectUnique([mainCombo.unsuitable, ...secondaryCombos.map((combo) => combo.unsuitable)]), "tag warn")}
            </div>
            <div class="paper-panel advice-panel">
              <h3>落地建議</h3>
              ${renderAdviceList(readingBlocks, combos)}
            </div>
          </div>
          ${renderFlowMonths(flowMonths)}
        </section>

        <section class="paper-section">
          ${renderSectionHeading("09", "今年財務、健康、人際", "把流年風險翻成可執行提醒")}
          <div class="paper-grid-map yearly-grid">
            ${renderNarrativePanel("財務", yearlyNotes.finance)}
            ${renderNarrativePanel("健康", yearlyNotes.health)}
            ${renderNarrativePanel("人際", yearlyNotes.relationship)}
          </div>
        </section>

        <section class="paper-section">
          ${renderSectionHeading("10", "算法依據", "把能算與不能算的部分講清楚")}
          <div class="paper-grid-map policy-grid">
            <div class="paper-panel"><h3>八字</h3>${renderPolicyChips(policy.bazi)}</div>
            <div class="paper-panel"><h3>姓名</h3>${renderPolicyChips(policy.nameology)}</div>
            <div class="paper-panel"><h3>AI</h3>${renderPolicyChips(policy.ai)}</div>
          </div>
        </section>
      </section>

      <footer class="paper-footer">
        <span>依據：姓名、四柱、五行、十神、長生祿刃、神煞補判、紫微星曜、大運流年</span>
        <span>未啟用項目會保留標示，不做假精準</span>
      </footer>
    </article>
  `;
}

function renderSectionHeading(number, title, helper) {
  return `
    <div class="paper-section-heading">
      <span>${escapeHtml(number)}</span>
      <div>
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(helper)}</p>
      </div>
    </div>
  `;
}

function renderSummaryPanel(label, value, helper) {
  return `
    <div class="paper-panel summary-panel">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      <p>${escapeHtml(helper)}</p>
    </div>
  `;
}

function renderNarrativePanel(title, body) {
  return `
    <div class="paper-panel narrative-panel">
      <h3>${escapeHtml(title)}</h3>
      <p>${escapeHtml(body || "資料待補。")}</p>
    </div>
  `;
}

function renderListPanel(title, items = []) {
  const rows = items.filter(Boolean);
  return `
    <div class="paper-panel list-panel">
      <h3>${escapeHtml(title)}</h3>
      ${rows.length ? `<ul>${rows.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : "<p>未見明顯命中。</p>"}
    </div>
  `;
}

function renderZiweiPanel(title, palace, stars = [], note = "") {
  return `
    <div class="paper-panel ziwei-panel">
      <h3>${escapeHtml(title)}</h3>
      <div class="palace-line"><span>宮位</span><strong>${escapeHtml(palace || "未知")}</strong></div>
      <div class="palace-line"><span>星曜</span><strong>${escapeHtml((stars || []).join("、") || "未知")}</strong></div>
      <p>${escapeHtml(note || "紫微星曜用來輔助工作、人際與財務落點。")}</p>
    </div>
  `;
}

function strengthLabel(value) {
  return {
    strong_candidate: "日主偏強候選",
    weak_candidate: "日主偏弱候選",
    balanced_candidate: "日主中和候選",
  }[value] || value || "待補";
}

function formatSolarTime(solarTime = {}) {
  if (solarTime.status !== "computed") return "未計算";
  const correction = Number(solarTime.total_correction_minutes || 0);
  const sign = correction > 0 ? "+" : "";
  return `${solarTime.applied ? "已套用" : "未套用"} ${sign}${correction} 分`;
}

function formatQiyun(qiyun = {}) {
  if (qiyun.status !== "computed") return "起運待補";
  return `${qiyun.direction_label || "順逆待補"}｜${qiyun.start_age_years ?? "?"}年${qiyun.start_age_months ?? "?"}月${qiyun.start_age_days ?? "?"}日`;
}

function renderFlowMonths(months = []) {
  if (!months.length) return `<p class="fine-note">流月資料待補。</p>`;
  return `
    <div class="flow-month-grid">
      ${months.slice(0, 12).map((month) => `
        <div>
          <span>${escapeHtml(`${month.month} 月`)}</span>
          <strong>${escapeHtml(month.pillar || "待補")}</strong>
          <em>${escapeHtml(month.ten_god || "十神待補")}</em>
        </div>
      `).join("")}
    </div>
  `;
}

function renderNameology(nameology = {}, bazi = {}) {
  if (!nameology.name) {
    return `
      <div class="paper-panel nameology-empty">
        <h3>尚未啟用</h3>
        <p>姓名留空，因此本次不做康熙筆畫、五格與三才合參。</p>
      </div>
    `;
  }
  const strokes = nameology.characters || [];
  const grids = nameology.five_grid || {};
  const talents = nameology.three_talents || {};
  return `
    <div class="paper-grid-map nameology-grid">
      <div class="paper-panel">
        <h3>姓名筆畫</h3>
        <div class="stroke-grid">
          ${strokes.map((item) => `
            <div>
              <span>${escapeHtml(item.char || "?")}</span>
              <strong>${escapeHtml(item.strokes ?? "缺")}</strong>
            </div>
          `).join("") || "<p>查無筆畫資料。</p>"}
        </div>
      </div>
      <div class="paper-panel">
        <h3>五格</h3>
        ${renderFiveGrid(grids)}
      </div>
      <div class="paper-panel">
        <h3>三才</h3>
        ${renderThreeTalents(talents)}
      </div>
      <div class="paper-panel">
        <h3>姓名與本命</h3>
        <p>${escapeHtml(nameologyNarrative(nameology, bazi))}</p>
      </div>
    </div>
  `;
}

function renderFiveGrid(grid = {}) {
  const values = grid.values || {};
  const elements = grid.elements || {};
  const entries = [
    ["天格", "heaven"],
    ["人格", "person"],
    ["地格", "earth"],
    ["外格", "outer"],
    ["總格", "total"],
  ].filter(([, key]) => values[key] !== null && values[key] !== undefined);
  if (!entries.length) return `<p>${escapeHtml(grid.status || "資料待補。")}</p>`;
  return `
    <div class="kv-list">
      ${entries.map(([label, key]) => `
        <div><span>${escapeHtml(label)}</span><strong>${escapeHtml(`${values[key]} ${elements[key] || ""}`.trim())}</strong></div>
      `).join("")}
    </div>
    <p class="fine-note">${escapeHtml(grid.formula_note || "五格只輸出數字與元素，不輸出吉凶表。")}</p>
  `;
}

function renderThreeTalents(talents = {}) {
  const sequence = talents.sequence || [];
  const elements = talents.elements || [];
  if (!sequence.length && !elements.length) return `<p>${escapeHtml(talents.status || "資料待補。")}</p>`;
  return `
    <div class="kv-list">
      <div><span>數序</span><strong>${escapeHtml(sequence.join(" / ") || "待補")}</strong></div>
      <div><span>三才</span><strong>${escapeHtml(elements.join(" / ") || "待補")}</strong></div>
    </div>
    <p class="fine-note">${escapeHtml(talents.notice || "三才只標示元素序列，不輸出吉凶表。")}</p>
  `;
}

function renderPolicyChips(policy = {}) {
  const entries = Object.entries(policy || {})
    .filter(([, value]) => value !== null && value !== undefined && typeof value !== "object")
    .slice(0, 5);
  if (!entries.length) return `<p>本次無額外設定。</p>`;
  return `
    <div class="policy-chip-list">
      ${entries.map(([key, value]) => `<span>${escapeHtml(key)}：${escapeHtml(value)}</span>`).join("")}
    </div>
  `;
}

function formatGrowthState(item = {}) {
  const branches = item.branches || (item.branch ? [item.branch] : []);
  const branchText = branches.join("、") || "未標支";
  return `${item.label || "長生狀態"}：${branchText}${item.count > 1 ? ` x${item.count}` : ""}`;
}

function formatCalculatedItem(item = {}) {
  if (!item.label) return "";
  return `${item.label}：${item.note || item.basis || "已命中"}`;
}

function buildShenshaNote(items = []) {
  return items.length ? "神煞只作輔助，不壓過本命五行、十神與流年。" : "本次未見需要特別標出的八字神煞。";
}

function buildDestinyProfile(bazi = {}, ziwei = {}, nameology = {}, combos = [], blocks = [], growthStates = [], specialForces = []) {
  const day = bazi.day_master || {};
  const elements = bazi.elements || {};
  const strongest = topElement(elements);
  const weakest = lowElement(elements);
  const annual = bazi.luck_cycles?.annual || {};
  const currentDecade = bazi.luck_cycles?.current_decade || {};
  const mainCombo = combos[0] || {};
  const careerBlock = blocks.find((block) => block.topic === "career") || {};
  const dayText = `${day.stem || "?"}${day.element || ""}`;
  return {
    core: `這盤以 ${dayText} 為核心，${strongest.name || "五行"}最明顯；不是只看單一標籤，要看能量怎麼落到工作和選擇。`,
    dayMaster: day.element === "火"
      ? "火日主重表達、速度、曝光與主導；能量太滿時要靠規則與交付收住。"
      : day.element === "土"
        ? "土日主重承接、責任、信任與穩定；壓力大時容易自己扛住。"
        : `${day.element || "日主"}代表此盤的核心行動方式。`,
    elementUse: elementUseText(strongest.name, mainCombo.therefore || careerBlock.summary),
    elementRisk: elementRiskText(weakest.name),
    tenGodUse: tenGodUseText(listProminentTenGods(bazi.ten_gods || {})),
    forceUse: forceUseText(growthStates, specialForces),
    lifePalace: ziweiLifeText(ziwei.life_palace_stars || []),
    bodyPalace: ziweiBodyText(ziwei.body_palace_stars || []),
    moneyPalace: ziweiMoneyText(findPalaceStars(ziwei, "財帛")),
    annual: annual.theme || `${annual.year || "今年"}以 ${annual.ten_god || "流年十神"} 為主。`,
    decade: currentDecade.theme || "大運主題待補。",
    nameology: nameologyNarrative(nameology, bazi),
  };
}

function elementUseText(element, fallback = "") {
  const table = {
    木: "木強適合用在規劃、成長、學習、內容架構與開新路線。",
    火: "火強適合用在表達、曝光、品牌、內容、顧問、產品推廣與舞台感。",
    土: "土強適合用在管理、承接、服務品質、長期經營與可信任的交付。",
    金: "金強適合用在規則、判斷、流程、品質、金融法務與效率設計。",
    水: "水強適合用在資訊、溝通、流動資源、策略觀察與跨界整合。",
  };
  return table[element] || fallback || "強項要轉成工作中的可交付能力。";
}

function elementRiskText(element) {
  const table = {
    木: "木弱要補規劃、學習節奏與長線成長，不要只靠當下反應。",
    火: "火弱要補曝光、表達與行動速度，不要長期只在幕後消耗。",
    土: "土弱要補穩定、承接、規則與收尾，避免東西做散。",
    金: "金弱要補邊界、判斷、品質標準與流程，不要只有感覺沒有規格。",
    水: "水弱要補冷靜、睡眠、現金流、合約、數據與復盤，避免一直硬燒。",
  };
  return table[element] || "低分五行代表現實上需要用制度與環境補位。";
}

function tenGodUseText(gods = []) {
  if (gods.includes("偏財") && gods.includes("傷官")) return "傷官加偏財，適合把想法、表達、產品感與商業機會接起來，但合作和分帳要寫清楚。";
  if (gods.includes("食神") && gods.includes("正官")) return "食神加官星，適合把專業、服務、整理能力落到穩定職務和可信任成果。";
  if (gods.includes("食神")) return "食神明顯，重點是輸出、作品、服務、教學、整理與可持續產出。";
  if (gods.includes("比肩")) return "比肩明顯，主體性強，適合爭取位置，但要避免硬碰硬。";
  return "十神要看哪些最明顯，再轉成工作上的輸出方式。";
}

function forceUseText(growthStates = [], specialForces = []) {
  const growthLabels = growthStates.map((item) => item.label).filter(Boolean);
  const forceLabels = specialForces.map((item) => item.label).filter(Boolean);
  const labels = [...new Set([...growthLabels, ...forceLabels])];
  if (!labels.length) return "本次沒有明確命中的長生、帝旺、祿或羊刃，不額外放大這段。";
  if (labels.includes("帝旺") && labels.includes("羊刃")) return "帝旺和羊刃同時命中時，主導與爆發力會被放大；要用規則和交付把力道收住。";
  if (labels.includes("祿")) return "命中祿地，重點是把能力變成穩定位置、資源和可被市場接受的交付。";
  if (labels.includes("長生")) return "命中長生，代表這股能量有起勢和生發感，適合放在學習、開局和新方向。";
  return `本次命中 ${labels.join("、")}，只作能量狀態輔助，不取代五行與十神主判。`;
}

function ziweiLifeText(stars = []) {
  if (hasStar(stars, "天機")) return "命宮天機重策略、變動、工具與方法；適合做會動腦和調整系統的事。";
  if (hasStar(stars, "天同") || hasStar(stars, "天梁")) return "命宮天同天梁重服務、照顧、原則與信任感；不適合太冷硬的環境。";
  return "命宮星曜是人格底色，先看主星再看輔星加成。";
}

function ziweiBodyText(stars = []) {
  if (hasStar(stars, "文昌") || hasStar(stars, "文曲")) return "身宮/官祿見文昌文曲，適合寫、講、企劃、內容、顧問、文件與產品邏輯。";
  if (hasStar(stars, "天機")) return "身宮/官祿見天機，工作容易變動，也適合靠規劃、系統與解法吃飯。";
  return "身宮代表後天行動重心；落到官祿時，事業會是長期主軸。";
}

function ziweiMoneyText(stars = []) {
  if (hasStar(stars, "太陰") || hasStar(stars, "天同")) return "財帛見太陰/天同，錢較適合靠信任、服務感、長期客戶、內容溫度或細膩需求累積。";
  if (hasStar(stars, "天魁") || hasStar(stars, "天鉞")) return "財帛見貴人星，資源和機會常來自關鍵支持者或合作方。";
  return "財帛宮看收入方式，不單獨當作財富保證。";
}

function deriveCareerReading(bazi = {}, ziwei = {}, mainCombo = {}, timingCombo = {}) {
  const annual = bazi.luck_cycles?.annual || {};
  const decade = bazi.luck_cycles?.current_decade || {};
  const tenGod = annual.ten_god || "";
  if (tenGod === "比肩") {
    return {
      work: "今年主題是自己出來、自己主導、自己定位置。越等別人給舞台，越容易卡。",
      strategy: "拿作品、產品、方案、案例出來測市場。",
    };
  }
  if (tenGod === "偏印" || decade.ten_god === "偏印") {
    return {
      work: "今年主題是重新學習、整理方向、修正定位，不是單純硬衝。",
      strategy: "先整理能力和方向，再穩定轉換位置。",
    };
  }
  return {
    work: annual.theme || mainCombo.therefore || "今年工作要先看大運，再看流年觸發。",
    strategy: timingCombo.advice || "先用大運看階段，再用流年看今年重點。",
  };
}

function deriveYearlyNotes(bazi = {}, profile = {}) {
  const annual = bazi.luck_cycles?.annual || {};
  const strongest = topElement(bazi.elements || {}).name;
  const weakest = lowElement(bazi.elements || {}).name;
  const tenGod = annual.ten_god || "";
  return {
    finance: tenGod === "比肩"
      ? "比肩年容易爭資源、談合作、拉位置；大額支出和合作分帳要先寫規則。"
      : "今年財務重點在穩定節奏與風險控管；有變動時先整理現金流和最壞情境。",
    health: strongest === "火"
      ? "火旺要注意睡眠、眼睛、心火、發炎、焦躁、血壓與過勞。"
      : weakest === "水"
        ? "水弱要注意睡眠、壓力流動、焦慮、疲勞與身體恢復。"
        : "健康重點是規律作息和不要長期用壓力硬撐。",
    relationship: tenGod === "比肩"
      ? "今年主導感強，人際上要避免太急、太硬；把規則說清楚比臨場硬碰硬好。"
      : "今年情緒容易往內收，人際上要提早講，不要等壓力滿了才一次爆開。",
  };
}

function listProminentTenGods(tenGods = {}) {
  const values = Object.values(tenGods || {}).map((item) => item.god);
  return [...new Set(values.filter(Boolean))];
}

function listHiddenTenGods(tenGods = {}) {
  const values = Object.values(tenGods || {}).flatMap((item) => [
    ...(item.hidden_stems || []).map((hidden) => hidden.god),
  ]);
  const visible = new Set(listProminentTenGods(tenGods));
  return [...new Set(values.filter((value) => value && !visible.has(value)))];
}

function findPalaceStars(ziwei = {}, palaceName) {
  return (ziwei.palaces || []).find((palace) => palace.name === palaceName)?.stars || [];
}

function hasStar(stars = [], name) {
  return stars.some((star) => String(star).includes(name));
}

function nameologyNarrative(nameology = {}, bazi = {}) {
  if (!nameology.name) return "姓名留空，這段不參與判斷。";
  const elements = nameology.five_grid?.elements || {};
  const nameElements = Object.values(elements);
  const strongestName = mostFrequent(nameElements);
  const weakest = lowElement(bazi.elements || {}).name;
  const totalElement = elements.total;
  const base = strongestName ? `名字五格以${strongestName}氣較明顯` : "名字五格資料已列出";
  if (weakest && nameElements.includes(weakest)) return `${base}，並有補到本命較弱的${weakest}；可視為外顯氣質上的輔助。`;
  if (totalElement && totalElement === weakest) return `${base}，總格帶${totalElement}，對本命低分五行有一點補位，但仍要靠現實習慣落實。`;
  return `${base}，主要加強外顯形象與做事方式；沒有補到的五行仍要用生活和制度補。`;
}

function topElement(elements = {}) {
  return sortedElements(elements)[0] || { name: "", value: 0 };
}

function lowElement(elements = {}) {
  const rows = sortedElements(elements).filter((item) => Number.isFinite(item.value));
  return rows[rows.length - 1] || { name: "", value: 0 };
}

function sortedElements(elements = {}) {
  return ELEMENT_ORDER
    .map((name) => ({ name, value: Number(elements[name] ?? 0) }))
    .sort((a, b) => b.value - a.value);
}

function mostFrequent(values = []) {
  const counts = values.reduce((acc, value) => {
    if (value) acc[value] = (acc[value] || 0) + 1;
    return acc;
  }, {});
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || "";
}

function renderComboProofCard(card = {}, fallbackTitle) {
  return `
    <article class="paper-panel combo-proof-card">
      <h3>${escapeHtml(card.title || fallbackTitle)}</h3>
      <p class="combo-large">${escapeHtml(card.formula || "主訊號未定")}</p>
      <dl class="because-therefore">
        <div>
          <dt>因為</dt>
          <dd>${escapeHtml(stripLeadingCue(card.because, "因為") || "尚未取得足夠命盤依據。")}</dd>
        </div>
        <div>
          <dt>所以</dt>
          <dd>${escapeHtml(stripLeadingCue(card.therefore, "所以") || "等待命盤訊號產生組合解讀。")}</dd>
        </div>
      </dl>
    </article>
  `;
}

function stripLeadingCue(value = "", cue) {
  return String(value || "").replace(new RegExp(`^${cue}`), "").trim();
}

function renderSignalList(signals = []) {
  if (!signals.length) return `<p>尚無格局或星曜摘錄。</p>`;
  return `
    <ul>
      ${signals.map((signal) => `<li>${escapeHtml(signal.label)}<span>${escapeHtml(signal.basis)}</span></li>`).join("")}
    </ul>
  `;
}

function renderTagList(items = [], className) {
  if (!items.length) return `<p>待更多命盤訊號補足。</p>`;
  return `<div class="paper-tag-list">${items.map((item) => `<span class="${className}">${escapeHtml(item)}</span>`).join("")}</div>`;
}

function renderAdviceList(blocks = [], cards = []) {
  const actions = collectUnique([
    blocks.flatMap((block) => block.actions || []),
    cards.map((card) => card.advice).filter(Boolean),
  ]).slice(0, 5);
  if (!actions.length) return `<p>尚無批語。</p>`;
  return `
    <ol class="advice-list">
      ${actions.map((action) => `<li>${escapeHtml(action)}</li>`).join("")}
    </ol>
  `;
}

function collectUnique(groups = []) {
  const values = groups.flat().filter(Boolean);
  return [...new Set(values)];
}

function renderPillarCell(key, pillar = "未知", tenGod = {}) {
  const labels = { year: "年", month: "月", day: "日", hour: "時" };
  return `
    <div class="pillar-cell">
      <span>${labels[key]}</span>
      <strong>${escapeHtml(pillar)}</strong>
      <em>${escapeHtml(tenGod.god || "十神")}</em>
    </div>
  `;
}
