export const ELEMENT_ORDER = ["木", "火", "土", "金", "水"];

export const RADAR_AXIS = [
  { key: "木", label: "成長" },
  { key: "火", label: "表達" },
  { key: "土", label: "穩定" },
  { key: "金", label: "判斷" },
  { key: "水", label: "觀察" },
];

export function normalizeOptionalNumber(data, key) {
  if (data[key] === "") {
    delete data[key];
    return;
  }
  if (data[key] !== undefined) {
    data[key] = Number(data[key]);
  }
}

export function strongestElement(elements = {}) {
  const entries = Object.entries(elements);
  if (!entries.length) return "未知";
  const [name, value] = entries.sort((a, b) => b[1] - a[1])[0];
  return `${name}旺 ${value}`;
}

export function polygonPoints(count, center, radius) {
  return Array.from({ length: count }, (_, index) => {
    const angle = -Math.PI / 2 + (index / count) * Math.PI * 2;
    return `${center + Math.cos(angle) * radius},${center + Math.sin(angle) * radius}`;
  }).join(" ");
}

export function formatBirth(input = {}) {
  const place = input.location ? `｜${input.location}` : "";
  return `${input.birth_date || ""} ${input.birth_time || ""}${place}`.trim();
}

export function formatDecade(decade = {}) {
  if (!decade.pillar) return "待補";
  return `${decade.age_start}-${decade.age_end}歲 ${decade.pillar}`;
}

export function formatAnnual(annual = {}) {
  if (!annual.pillar) return "待補";
  return `${annual.year} ${annual.pillar}年 ${annual.zodiac || ""}`.trim();
}

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
