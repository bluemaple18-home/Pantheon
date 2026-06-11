import { ELEMENT_ORDER, RADAR_AXIS, escapeHtml, polygonPoints, strongestElement } from "./utils.js";

export function renderDashboard(result, targets) {
  const bazi = result.charts.bazi;
  const ziwei = result.charts.ziwei;
  const mbti = result.charts.mbti;
  const nameology = result.charts.nameology;
  const report = result.report;
  renderIdentity(bazi, ziwei, mbti, nameology, targets.identityStrip);
  renderPillarCards(bazi, targets.pillarCards);
  renderDestinyWheel(bazi, ziwei, targets.destinyWheel);
  renderElementBars(bazi.elements, targets.elementBars);
  renderRadar(bazi.elements, targets.radarChart);
  renderTenGodBoard(bazi, targets.tenGodBoard);
  renderTimingBoard(bazi, targets.timingBoard);
  renderComboCards(report.combo_cards, targets.comboCards);
  renderReadingBlocks(report.reading_blocks, targets.readingBlocks);
  renderSignals(report.signals, result.metadata?.school_policy, targets.signalsTable);
}

function renderIdentity(bazi, ziwei, mbti, nameology, container) {
  const dayMaster = bazi.day_master || {};
  const pillars = bazi.pillars || {};
  const zodiac = bazi.zodiac || {};
  const calendarEngine = bazi.calendar_engine || {};
  const solarTime = bazi.solar_time || {};
  const items = [
    ["生肖", zodiac.label || "未知", "年支民俗身份"],
    ["日主", `${dayMaster.stem || "未知"}${dayMaster.element || ""}`, `四柱 ${Object.values(pillars).join(" ")}`],
    ["主能量", strongestElement(bazi.elements), "五行最高分"],
    ["八字引擎", calendarEngine.provider || "未知", calendarEngine.provider_status || "未標示"],
    ["命宮", ziwei.life_palace || "未知", "紫微人格主軸"],
  ];
  if (solarTime.status === "computed") {
    items.push([
      "真太陽時",
      solarTime.applied ? "已套用" : "未套用",
      `${solarTime.total_correction_minutes > 0 ? "+" : ""}${solarTime.total_correction_minutes} 分`,
    ]);
  }
  if (mbti?.status === "scored") {
    items.push(["MBTI", mbti.type || "未定", "個人自評偏好"]);
  }
  if (nameology?.name) {
    const nameologyValue = nameology.matched_count > 0
      ? `${nameology.matched_count}/${nameology.name.length}`
      : "待輸入中文";
    items.push([
      "姓名學",
      nameologyValue,
      nameology.provider || "康熙筆畫",
    ]);
  }
  container.innerHTML = items
    .map(([label, value, helper]) => `
      <div class="identity-item">
        <p class="identity-label">${escapeHtml(label)}</p>
        <p class="identity-value">${escapeHtml(value)}</p>
        <p class="fine-print">${escapeHtml(helper)}</p>
      </div>
    `)
    .join("");
}

function renderPillarCards(bazi, container) {
  if (!container) return;
  const pillars = bazi.pillars || {};
  const tenGods = bazi.ten_gods || {};
  const labels = { year: "年柱", month: "月柱", day: "日柱", hour: "時柱" };
  container.innerHTML = ["year", "month", "day", "hour"]
    .map((key) => {
      const pillar = pillars[key] || "未知";
      const tenGod = tenGods[key] || {};
      return `
        <article class="pillar-card ${key === "day" ? "focus" : ""}">
          <span>${escapeHtml(labels[key])}</span>
          <strong>${escapeHtml(pillar)}</strong>
          <em>${escapeHtml(tenGod.god || "十神待補")}</em>
          <small>${escapeHtml(tenGod.element || "五行")}｜${escapeHtml(tenGod.polarity || "陰陽")}</small>
        </article>
      `;
    })
    .join("");
}

function renderDestinyWheel(bazi, ziwei, container) {
  if (!container) return;
  const pillars = bazi.pillars || {};
  const dayMaster = bazi.day_master || {};
  const annual = bazi.luck_cycles?.annual || {};
  const palaces = ziwei.palaces || [];
  const palaceRing = palaces.slice(0, 12).map((palace, index) => `
    <span class="wheel-palace p${index} ${palace.is_life_palace ? "life" : ""} ${palace.is_body_palace ? "body" : ""}">
      ${escapeHtml(palace.name)}
    </span>
  `).join("");
  container.innerHTML = `
    <div class="destiny-wheel" aria-label="命盤輪">
      ${palaceRing}
      <div class="wheel-ring outer"></div>
      <div class="wheel-ring middle"></div>
      <div class="wheel-core">
        <span>日主</span>
        <strong>${escapeHtml(`${dayMaster.stem || "?"}${dayMaster.element || ""}`)}</strong>
      </div>
    </div>
    <div class="wheel-meta">
      <div><span>四柱</span><strong>${escapeHtml(Object.values(pillars).join(" ") || "待補")}</strong></div>
      <div><span>命宮</span><strong>${escapeHtml(ziwei.life_palace || "未知")}</strong></div>
      <div><span>流年</span><strong>${escapeHtml(annual.pillar || "待補")}</strong></div>
    </div>
  `;
}

function renderTenGodBoard(bazi, container) {
  if (!container) return;
  const tenGods = bazi.ten_gods || {};
  const strength = bazi.strength_analysis || {};
  const labels = { year: "年柱", month: "月柱", day: "日柱", hour: "時柱" };
  container.innerHTML = `
    <section class="detail-board">
      <div class="section-heading">
        <p class="eyebrow">Ten Gods</p>
        <h2>十神結構</h2>
      </div>
      <div class="detail-grid">
        ${["year", "month", "day", "hour"].map((key) => {
          const item = tenGods[key] || {};
          const hidden = (item.hidden_stems || [])
            .map((stem) => `${stem.stem}${stem.god || ""}`)
            .join("、");
          return `
            <article class="detail-card">
              <span>${escapeHtml(labels[key])}</span>
              <strong>${escapeHtml(item.god || "待補")}</strong>
              <p>${escapeHtml(item.stem || "?")}｜${escapeHtml(item.element || "五行")}｜${escapeHtml(item.polarity || "陰陽")}</p>
              <small>${escapeHtml(hidden ? `藏干：${hidden}` : "藏干待補")}</small>
            </article>
          `;
        }).join("")}
      </div>
      <p class="detail-note">十神已含四柱天干與地支藏干；權重依 Pantheon MVP 規則表，派別可於後續版本切換。</p>
      <div class="detail-grid timing-detail-grid">
        <article class="detail-card emphasis">
          <span>旺衰候選</span>
          <strong>${escapeHtml(strengthLabel(strength.label))}</strong>
          <p>${escapeHtml(`support ${strength.support_score ?? "?"}｜pressure ${strength.pressure_score ?? "?"}`)}</p>
          <small>${escapeHtml(strength.caution || "旺衰不可單獨定用神。")}</small>
        </article>
      </div>
    </section>
  `;
}

function renderTimingBoard(bazi, container) {
  if (!container) return;
  const luck = bazi.luck_cycles || {};
  const decade = luck.current_decade || {};
  const annual = luck.annual || {};
  const qiyun = luck.qiyun || {};
  const flowMonths = annual.flow_months || [];
const qiyunAge = qiyun.status === "computed"
    ? `${qiyun.start_age_years ?? "?"}年${qiyun.start_age_months ?? "?"}月${qiyun.start_age_days ?? "?"}日起運`
    : "起運歲數待精確節氣";
  const qiyunText = qiyun.direction_label
    ? `${qiyun.direction_label}｜${qiyunAge}`
    : "起運資料待補";
  container.innerHTML = `
    <section class="detail-board">
      <div class="section-heading">
        <p class="eyebrow">Timing</p>
        <h2>大運流年</h2>
      </div>
      <div class="detail-grid timing-detail-grid">
        <article class="detail-card emphasis">
          <span>目前大運</span>
          <strong>${escapeHtml(decade.pillar || "待補")}</strong>
          <p>${escapeHtml(`${decade.age_start ?? "?"}-${decade.age_end ?? "?"} 歲｜${decade.ten_god || "十神待補"}`)}</p>
          <small>${escapeHtml(decade.theme || "十年主題待補。")}</small>
        </article>
        <article class="detail-card">
          <span>起運規則</span>
          <strong>${escapeHtml(qiyunText)}</strong>
          <p>${escapeHtml(qiyun.basis || "精準起運需節氣時間。")}</p>
          <small>${escapeHtml(qiyun.status || "pending")}</small>
        </article>
        <article class="detail-card emphasis">
          <span>今年流年</span>
          <strong>${escapeHtml(annual.pillar || "待補")}</strong>
          <p>${escapeHtml(`${annual.year || ""}｜${annual.ten_god || "十神待補"}`)}</p>
          <small>${escapeHtml(annual.theme || "年度主題待補。")}</small>
        </article>
      </div>
      <div class="detail-grid">
        ${flowMonths.slice(0, 6).map((month) => `
          <article class="detail-card compact">
            <span>${escapeHtml(`${month.month} 月`)}</span>
            <strong>${escapeHtml(month.pillar || "待補")}</strong>
            <p>${escapeHtml(month.ten_god || "十神待補")}</p>
          </article>
        `).join("")}
      </div>
      <p class="detail-note">${escapeHtml(luck.notice || "精準起運、流月與真太陽時待接正式演算法。")}</p>
    </section>
  `;
}

function strengthLabel(value) {
  return {
    strong_candidate: "日主偏強候選",
    weak_candidate: "日主偏弱候選",
    balanced_candidate: "日主中和候選",
  }[value] || value || "待補";
}

function renderElementBars(elements = {}, container) {
  const max = Math.max(...Object.values(elements), 1);
  container.innerHTML = ELEMENT_ORDER
    .map((name) => {
      const value = Number(elements[name] || 0);
      const width = Math.max(4, Math.round((value / max) * 100));
      const state = value === max ? "high" : value === 0 ? "low" : "";
      return `
        <div class="element-row">
          <span class="element-name">${name}</span>
          <span class="bar-track"><span class="bar-fill ${state}" style="width:${width}%"></span></span>
          <span class="element-score">${value}</span>
        </div>
      `;
    })
    .join("");
}

function renderRadar(elements = {}, container) {
  const size = 320;
  const center = size / 2;
  const radius = 104;
  const max = Math.max(...Object.values(elements), 1);
  const axisPoints = RADAR_AXIS.map((axis, index) => {
    const angle = -Math.PI / 2 + (index / RADAR_AXIS.length) * Math.PI * 2;
    const raw = Number(elements[axis.key] || 0);
    const distance = (raw / max) * radius;
    return {
      label: axis.label,
      x: center + Math.cos(angle) * distance,
      y: center + Math.sin(angle) * distance,
      lx: center + Math.cos(angle) * (radius + 28),
      ly: center + Math.sin(angle) * (radius + 28),
      ax: center + Math.cos(angle) * radius,
      ay: center + Math.sin(angle) * radius,
    };
  });
  const rings = [0.25, 0.5, 0.75, 1]
    .map((scale) => polygonPoints(RADAR_AXIS.length, center, radius * scale))
    .map((points) => `<polygon points="${points}" fill="none" stroke="#d9dfdc" stroke-width="1" />`)
    .join("");
  const axes = axisPoints
    .map((point) => `<line x1="${center}" y1="${center}" x2="${point.ax}" y2="${point.ay}" stroke="#d9dfdc" />`)
    .join("");
  const labels = axisPoints
    .map((point) => `<text x="${point.lx}" y="${point.ly}" text-anchor="middle" dominant-baseline="middle">${point.label}</text>`)
    .join("");
  const shape = axisPoints.map((point) => `${point.x},${point.y}`).join(" ");
  container.innerHTML = `
    <svg viewBox="0 0 ${size} ${size}" role="img" aria-label="五行特質雷達圖">
      ${rings}
      ${axes}
      <polygon points="${shape}" fill="rgba(23,109,99,.25)" stroke="#176d63" stroke-width="3" />
      ${axisPoints.map((point) => `<circle cx="${point.x}" cy="${point.y}" r="4" fill="#b54a35" />`).join("")}
      ${labels}
    </svg>
  `;
}

function renderComboCards(cards = [], container) {
  container.innerHTML = cards.length
    ? cards
        .map((card) => `
          <article class="combo-card">
            <h3>${escapeHtml(card.title)}</h3>
            <span class="combo-formula">${escapeHtml(card.formula)}</span>
            <p>${escapeHtml(card.because)}，${escapeHtml(card.therefore)}。</p>
            <div class="tag-list">${card.suitable.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("")}</div>
            <div class="tag-list">${card.unsuitable.map((item) => `<span class="tag warn">${escapeHtml(item)}</span>`).join("")}</div>
          </article>
        `)
        .join("")
    : `<div class="empty">尚未產生組合牌</div>`;
}

function renderReadingBlocks(blocks = [], container) {
  container.innerHTML = blocks.length
    ? blocks
        .map((block) => `
          <article class="reading-card">
            <p class="eyebrow">${escapeHtml(block.topic)}</p>
            <h3>${escapeHtml(block.title)}</h3>
            <p>${escapeHtml(block.reasoning)}</p>
            <ul class="action-line">${block.actions.map((action) => `<li>${escapeHtml(action)}</li>`).join("")}</ul>
          </article>
        `)
        .join("")
    : `<div class="empty">尚未產生主題報告</div>`;
}

function renderSignals(signals = [], schoolPolicy = {}, container) {
  const policyRows = Object.entries(schoolPolicy || {})
    .map(([name, policy]) => `
      <div class="signal-row policy-row">
        <span class="signal-id">policy.${escapeHtml(name)}</span>
        <strong>${escapeHtml(policyTitle(name, policy))}</strong>
        <span>${escapeHtml(policySubtitle(name, policy))}</span>
        <span>${escapeHtml(policySummary(name, policy))}</span>
      </div>
    `)
    .join("");
  const signalRows = signals
    .map((signal) => `
      <div class="signal-row">
        <span class="signal-id">${escapeHtml(signal.id)}</span>
        <strong>${escapeHtml(signal.basis)}</strong>
        <span>${escapeHtml(signal.label)} / ${escapeHtml(signal.polarity)}</span>
        <span>${escapeHtml(signal.plain_meaning)}</span>
      </div>
    `)
    .join("");
  container.innerHTML = `${policyRows}${signalRows}`;
}

function policyTitle(name, policy) {
  if (name === "bazi") return policy.calendar_provider || "八字設定";
  if (name === "ai") return "AI 解讀邊界";
  return policy.provider || policy.role || "設定";
}

function policySubtitle(name, policy) {
  if (name === "bazi") return policy.dayun_method || "";
  if (name === "ai") return policy.role || "";
  return policy.algorithm_level || policy.school || policy.stroke_source || "";
}

function policySummary(name, policy) {
  if (name === "ai") return "只解讀 charts / signals / combo_cards / school_policy，不自行重排命盤。";
  if (name === "bazi" && policy.true_solar_time) {
    const solar = policy.true_solar_time.applied ? "真太陽時已套用" : "真太陽時未套用";
    return `${solar}；${policy.caution || ""}`;
  }
  return policy.caution || "本次算法設定已記錄。";
}
