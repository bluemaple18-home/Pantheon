import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { astro } from "iztro";

const require = createRequire(import.meta.url);
const packageMeta = require("iztro/package.json");

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      data += chunk;
    });
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
}

function timeIndexFromClock(value) {
  const [hourText = "0"] = String(value || "00:00").split(":");
  const hour = Number(hourText);
  if (!Number.isFinite(hour)) return 0;
  return Math.floor((hour + 1) / 2) % 12;
}

function genderLabel(value) {
  return String(value || "").toLowerCase() === "male" ? "男" : "女";
}

function starLabel(star) {
  return star.brightness ? `${star.name}(${star.brightness})` : star.name;
}

function normalizePalace(palace) {
  const majorStars = (palace.majorStars || []).map(starLabel);
  const minorStars = (palace.minorStars || []).map(starLabel);
  const adjectiveStars = (palace.adjectiveStars || []).map(starLabel);
  return {
    name: palace.name,
    index: palace.index,
    heavenly_stem: palace.heavenlyStem,
    earthly_branch: palace.earthlyBranch,
    is_life_palace: palace.name === "命宮",
    is_body_palace: Boolean(palace.isBodyPalace),
    stars: [...majorStars, ...minorStars, ...adjectiveStars],
    major_stars: majorStars,
    minor_stars: minorStars,
    adjective_stars: adjectiveStars,
    decadal: palace.decadal || null,
    ages: palace.ages || [],
  };
}

function fallbackVersion() {
  try {
    const raw = readFileSync(require.resolve("iztro/package.json"), "utf8");
    return JSON.parse(raw).version || packageMeta.version;
  } catch {
    return packageMeta.version;
  }
}

const input = JSON.parse(await readStdin());
const birthDate = String(input.birth_date);
const timeIndex = Number.isInteger(input.time_index)
  ? input.time_index
  : timeIndexFromClock(input.birth_time);
const chart = astro.bySolar(birthDate, timeIndex, genderLabel(input.gender), true, "zh-TW");
const palaces = chart.palaces.map(normalizePalace);
const lifePalace = palaces.find((palace) => palace.is_life_palace) || palaces[0];
const bodyPalace = palaces.find((palace) => palace.is_body_palace) || lifePalace;

process.stdout.write(
  JSON.stringify({
    provider: "iztro",
    provider_status: "active",
    provider_version: fallbackVersion(),
    algorithm_level: "iztro_provider",
    notice: "紫微斗數由 iztro 產出；Pantheon 只做 normalization 與解讀規則，不自行編造星曜。",
    solar_date: chart.solarDate,
    lunar_date: chart.lunarDate,
    chinese_date: chart.chineseDate,
    time_index: timeIndex,
    time_range: chart.timeRange,
    sign: chart.sign,
    zodiac: chart.zodiac,
    soul: chart.soul,
    body: chart.body,
    five_elements_class: chart.fiveElementsClass,
    earthly_branch_of_life_palace: chart.earthlyBranchOfSoulPalace,
    earthly_branch_of_body_palace: chart.earthlyBranchOfBodyPalace,
    life_palace: lifePalace.name,
    body_palace: bodyPalace.name,
    life_palace_stars: lifePalace.stars,
    body_palace_stars: bodyPalace.stars,
    palaces,
  }),
);
