import { normalizeOptionalNumber } from "./utils.js";

export function buildPredictionPayload(form) {
  const data = Object.fromEntries(new FormData(form));
  normalizeOptionalNumber(data, "latitude");
  normalizeOptionalNumber(data, "longitude");
  normalizeOptionalNumber(data, "target_year");
  data.use_true_solar_time = Boolean(form.querySelector("[name='use_true_solar_time']")?.checked);
  data.include_reserved_plugins = false;
  return data;
}

export function buildPersonalityPayload(form) {
  return {
    personality_answers: collectPersonalityAnswers(form),
  };
}

function collectPersonalityAnswers(form) {
  return [...form.querySelectorAll("[data-mbti-question]")]
    .map((group) => {
      const selected = group.querySelector("input[type='radio']:checked");
      if (!selected) return null;
      return {
        question_id: group.dataset.questionId,
        dimension: group.dataset.dimension,
        direction: group.dataset.direction,
        value: Number(selected.value),
      };
    })
    .filter(Boolean);
}

export async function fetchPrediction(payload) {
  const response = await fetch("/api/v1/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

export async function fetchPersonality(payload) {
  const response = await fetch("/api/v1/personality", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}
