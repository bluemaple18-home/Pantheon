import { buildPersonalityPayload, fetchPersonality } from "./api.js";
import { escapeHtml } from "./utils.js";

const dom = {
  form: document.querySelector("#personality-form"),
  questions: document.querySelector("#mbti-questions"),
  progressText: document.querySelector("#mbti-progress-text"),
  answerStatus: document.querySelector("#mbti-answer-status"),
  progressFill: document.querySelector("#mbti-progress-fill"),
  prev: document.querySelector("#mbti-prev"),
  next: document.querySelector("#mbti-next"),
  submit: document.querySelector("#personality-submit"),
  result: document.querySelector("#personality-result"),
};

const MBTI_QUESTIONS = [
  ["mbti.ei.01", "EI", "E", "朋友臨時揪一個不熟的小聚，我多半會覺得去看看也不錯。"],
  ["mbti.ei.02", "EI", "I", "同一天連續好幾個邀約，我會開始想把其中一個改期。"],
  ["mbti.ei.03", "EI", "E", "卡在一件事上時，我常是講著講著才知道自己在想什麼。"],
  ["mbti.ei.04", "EI", "I", "忙完一整天後，我最想要的是一段不用回應任何人的時間。"],
  ["mbti.ei.05", "EI", "E", "群組冷掉時，我常會丟一個話題讓它重新動起來。"],
  ["mbti.ei.06", "EI", "I", "我比較常在很熟的人面前，才把真正的想法講完整。"],
  ["mbti.ei.07", "EI", "E", "想到一個有趣的東西，我會想先丟出去看大家反應。"],
  ["mbti.ei.08", "EI", "I", "被突然問到複雜問題時，我常希望晚點再好好回。"],
  ["mbti.sn.01", "SN", "S", "餐廳評價寫得很漂亮，我還是會先看照片、菜單和實際評論。"],
  ["mbti.sn.02", "SN", "N", "看一個新工具時，我很快會想到它還可以被拿來做什麼。"],
  ["mbti.sn.03", "SN", "S", "如果只聽到願景，沒有看到操作方式，我會先保留。"],
  ["mbti.sn.04", "SN", "N", "聊天聊到一半，我常會突然想到另一個領域的類似例子。"],
  ["mbti.sn.05", "SN", "S", "有人推薦方法時，我會想知道他自己是不是真的用過。"],
  ["mbti.sn.06", "SN", "N", "我常會被一個還很粗糙、但很有想像空間的概念吸住。"],
  ["mbti.sn.07", "SN", "S", "看文件或畫面時，我容易先看到錯字、格式或漏掉的欄位。"],
  ["mbti.sn.08", "SN", "N", "學新東西時，只背步驟會讓我煩，我想先知道它為什麼這樣設計。"],
  ["mbti.tf.01", "TF", "T", "兩個人各說各話時，我會想先把時間線和責任切清楚。"],
  ["mbti.tf.02", "TF", "F", "要拒絕別人時，我會想很久怎麼說比較不讓對方難受。"],
  ["mbti.tf.03", "TF", "T", "別人直接挑出漏洞，只要不是亂罵，我通常會先聽內容。"],
  ["mbti.tf.04", "TF", "F", "就算我覺得自己有理，也會避開讓對方太難堪的講法。"],
  ["mbti.tf.05", "TF", "T", "同一件事今天可以、明天不行，我會想知道規則到底在哪。"],
  ["mbti.tf.06", "TF", "F", "聚會裡有人突然安靜，我常會注意到。"],
  ["mbti.tf.07", "TF", "T", "如果新資料推翻我原本的看法，我會比較願意重算一次。"],
  ["mbti.tf.08", "TF", "F", "事情表面解決了，但有人心裡卡著，我會覺得還沒真的結束。"],
  ["mbti.jp.01", "JP", "J", "出門旅行前，我會想先把幾個關鍵時間點定下來。"],
  ["mbti.jp.02", "JP", "P", "旅行排得太滿時，我會覺得少了遇到驚喜的空間。"],
  ["mbti.jp.03", "JP", "J", "桌面或待辦一亂，我會想先整理一下再繼續。"],
  ["mbti.jp.04", "JP", "P", "原本的安排突然變了，我通常能很快換一個玩法。"],
  ["mbti.jp.05", "JP", "J", "訊息一直未讀、事情一直未定，會讓我心裡掛著。"],
  ["mbti.jp.06", "JP", "P", "買重要東西前，我常會多逛幾輪，看看有沒有更好的選項。"],
  ["mbti.jp.07", "JP", "J", "接到一件大任務，我會想先拆出今天能做的第一塊。"],
  ["mbti.jp.08", "JP", "P", "做到一半冒出新方向時，我不一定會急著把它按回原路。"],
  ["mbti.ao.01", "AO", "A", "事情出包時，我多半能先穩住，心裡知道還有辦法收拾。"],
  ["mbti.ao.02", "AO", "O", "送出重要訊息後，我有時會回頭看好幾次自己有沒有講錯。"],
  ["mbti.ao.03", "AO", "A", "別人一時不認同，我不太會立刻懷疑整個方向。"],
  ["mbti.ao.04", "AO", "O", "對方回覆慢一點，我可能會開始猜是不是哪裡出了問題。"],
  ["mbti.ao.05", "AO", "A", "我可以先把東西交出去，再用下一版慢慢修。"],
  ["mbti.ao.06", "AO", "O", "我常在最後一刻又想多檢查一次，怕漏掉什麼。"],
  ["mbti.ao.07", "AO", "A", "被打槍之後，我通常會先想下一步能怎麼調。"],
  ["mbti.ao.08", "AO", "O", "就算成果被稱讚，我還是容易看到那些可以更好的地方。"],
  ["mbti.hc.01", "HC", "H", "有人在桌上被開玩笑開過頭，我會想把話題帶走。"],
  ["mbti.hc.02", "HC", "C", "現場情緒很滿時，我通常不會立刻跟著升溫。"],
  ["mbti.hc.03", "HC", "H", "一群人裡有人插不上話，我常會想把他拉進來。"],
  ["mbti.hc.04", "HC", "C", "別人急著要我表態時，我還是會想先把界線說清楚。"],
  ["mbti.hc.05", "HC", "H", "大家都各退一步就能過的事，我會想推它往那邊走。"],
  ["mbti.hc.06", "HC", "C", "吵到很熱時，我比較想先暫停一下，不急著當場分勝負。"],
  ["mbti.hc.07", "HC", "H", "兩邊其實都不是壞意時，我會想幫他們把話翻得好懂一點。"],
  ["mbti.hc.08", "HC", "C", "越多人情緒上來，我越想先問：現在具體要處理哪一件事？"],
];

const QUESTION_ORDER = [
  "mbti.sn.01", "mbti.ei.03", "mbti.hc.01", "mbti.jp.02", "mbti.tf.05", "mbti.ao.04", "mbti.ei.06", "mbti.sn.08",
  "mbti.jp.01", "mbti.hc.04", "mbti.ao.01", "mbti.tf.02", "mbti.ei.01", "mbti.jp.06", "mbti.sn.04", "mbti.hc.06",
  "mbti.tf.07", "mbti.ao.02", "mbti.ei.08", "mbti.sn.05", "mbti.jp.04", "mbti.tf.04", "mbti.hc.03", "mbti.ao.07",
  "mbti.sn.02", "mbti.ei.04", "mbti.jp.07", "mbti.tf.01", "mbti.hc.08", "mbti.ao.05", "mbti.ei.05", "mbti.sn.07",
  "mbti.jp.03", "mbti.tf.08", "mbti.hc.02", "mbti.ao.06", "mbti.ei.02", "mbti.sn.03", "mbti.jp.08", "mbti.tf.03",
  "mbti.hc.05", "mbti.ao.03", "mbti.ei.07", "mbti.sn.06", "mbti.jp.05", "mbti.tf.06", "mbti.hc.07", "mbti.ao.08",
];

const QUESTIONS_PER_PAGE = 8;
let currentQuestionPage = 0;
let orderedQuestions = [];

renderQuestions();
dom.prev.addEventListener("click", () => setQuestionPage(currentQuestionPage - 1));
dom.next.addEventListener("click", () => setQuestionPage(currentQuestionPage + 1));
dom.questions.addEventListener("change", updateProgress);
dom.form.addEventListener("submit", submitPersonality);

function renderQuestions() {
  const questionById = new Map(MBTI_QUESTIONS.map((question) => [question[0], question]));
  orderedQuestions = QUESTION_ORDER.map((id) => questionById.get(id)).filter(Boolean);
  dom.questions.innerHTML = orderedQuestions.map(([id, dimension, direction, text], index) => `
    <fieldset
      class="mbti-question"
      data-mbti-question
      data-question-id="${id}"
      data-dimension="${dimension}"
      data-direction="${direction}"
      data-question-page="${Math.floor(index / QUESTIONS_PER_PAGE)}"
    >
      <legend><span>${index + 1}</span>${text}</legend>
      <div class="likert-row" aria-label="${text}">
        ${[1, 2, 3, 4, 5].map((value) => `
          <label>
            <input type="radio" name="${id}" value="${value}" />
            <span>${value}</span>
          </label>
        `).join("")}
      </div>
    </fieldset>
  `).join("");
  updateProgress();
}

function setQuestionPage(page) {
  const totalPages = Math.ceil(orderedQuestions.length / QUESTIONS_PER_PAGE);
  currentQuestionPage = Math.max(0, Math.min(page, totalPages - 1));
  updateProgress();
}

function updateProgress() {
  const questions = [...dom.questions.querySelectorAll("[data-mbti-question]")];
  const totalPages = Math.ceil(orderedQuestions.length / QUESTIONS_PER_PAGE);
  const answered = questions.filter((question) => question.querySelector("input:checked")).length;
  const percent = orderedQuestions.length ? Math.round((answered / orderedQuestions.length) * 100) : 0;

  questions.forEach((question) => {
    question.classList.toggle("answered", Boolean(question.querySelector("input:checked")));
    question.hidden = Number(question.dataset.questionPage) !== currentQuestionPage;
  });

  dom.progressText.textContent = `段落 ${currentQuestionPage + 1} / ${totalPages}`;
  dom.answerStatus.textContent = answered ? `已答 ${answered} / ${orderedQuestions.length} 題` : "尚未作答";
  dom.progressFill.style.width = `${percent}%`;
  dom.prev.disabled = currentQuestionPage === 0;
  dom.next.disabled = currentQuestionPage === totalPages - 1;
  dom.submit.disabled = answered < orderedQuestions.length;
  dom.submit.textContent = answered < orderedQuestions.length ? "完成後產生結果" : "產生人格結果";
}

async function submitPersonality(event) {
  event.preventDefault();
  renderPending("計算中");
  try {
    const result = await fetchPersonality(buildPersonalityPayload(dom.form));
    renderResult(result);
  } catch (error) {
    renderPending("人格測驗 API error");
    console.error(error);
  }
}

function renderPending(text) {
  dom.result.innerHTML = `
    <p class="eyebrow">Result</p>
    <h2>${escapeHtml(text)}</h2>
    <p>完成後會在這裡顯示核心型、分支碼與六軸偏好。</p>
  `;
}

function renderResult(result) {
  const chart = result.chart || {};
  const ai = result.ai || {};
  const dimensions = chart.dimensions || {};
  const rows = Object.entries(dimensions).map(([key, item]) => `
    <div class="personality-dimension-row">
      <span>${escapeHtml(key)}</span>
      <strong>${escapeHtml(item.preferred || "未定")}</strong>
      <em>${escapeHtml(item.preferred_label || "自評偏好")}</em>
    </div>
  `).join("");
  const aiSections = Array.isArray(ai.sections) ? ai.sections.map((section) => `
    <article class="personality-ai-section">
      <h3>${escapeHtml(section.title || "解讀")}</h3>
      <p>${escapeHtml(section.body || "")}</p>
    </article>
  `).join("") : "";
  const advice = Array.isArray(ai.advice) ? ai.advice.map((item) => `
    <li>${escapeHtml(item)}</li>
  `).join("") : "";
  const aiMode = ai.mode === "gemini" ? `Gemini ${ai.model || ""}` : "本地備援";

  dom.result.innerHTML = `
    <p class="eyebrow">Result</p>
    <h2>${escapeHtml(chart.type || "結果待補")}</h2>
    <p>${escapeHtml(chart.notice || "此結果只作自我探索，不作心理診斷。")}</p>
    <div class="personality-result-grid">
      <div><span>核心型</span><strong>${escapeHtml(chart.core_type || "未定")}</strong></div>
      <div><span>分支碼</span><strong>${escapeHtml(chart.branch_code || "未定")}</strong></div>
    </div>
    <div class="personality-dimensions">${rows}</div>
    <div class="personality-ai-reading">
      <div class="personality-ai-header">
        <span>AI 顧問解讀</span>
        <em>${escapeHtml(aiMode)}</em>
      </div>
      <p>${escapeHtml(ai.summary || "目前沒有足夠訊號產生解讀。")}</p>
      <div class="personality-ai-sections">${aiSections}</div>
      ${advice ? `<ul class="personality-ai-advice">${advice}</ul>` : ""}
      <small>${escapeHtml(ai.limitations || "此結果為自我探索，不是心理診斷。")}</small>
    </div>
  `;
}
