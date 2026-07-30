import type { StarOrbitId } from "../generated/createPantheonStarOrbits.ts";

export type PantheonThemeId =
  | "constellation"
  | "tarot"
  | "mbti"
  | "human-design"
  | "ziwei-bazi";

export interface PantheonThemeConfig {
  id: PantheonThemeId;
  orbitId: StarOrbitId;
  materialId: string;
  runeTextureId: string;
  label: string;
  shortLabel: string;
  symbol: string;
  description: string;
  action: string;
  runeFlowSpeed: number;
  runePhase: number;
}

export const PANTHEON_THEME_CONFIGS: readonly PantheonThemeConfig[] = [
  {
    id: "constellation",
    orbitId: "Constellation",
    materialId: "material.constellation",
    runeTextureId: "runes.constellation",
    label: "星座",
    shortLabel: "星座",
    symbol: "✦",
    description: "從天體節律，閱讀你此刻的生命座標。",
    action: "進入星座解讀",
    runeFlowSpeed: 0.01,
    runePhase: 0.07,
  },
  {
    id: "tarot",
    orbitId: "Tarot",
    materialId: "material.tarot",
    runeTextureId: "runes.tarot",
    label: "塔羅",
    shortLabel: "塔羅",
    symbol: "◇",
    description: "讓圖像與直覺，映照問題背後的選擇。",
    action: "展開塔羅牌陣",
    runeFlowSpeed: 0.014,
    runePhase: 0.23,
  },
  {
    id: "mbti",
    orbitId: "MBTI",
    materialId: "material.mbti",
    runeTextureId: "runes.mbti",
    label: "MBTI",
    shortLabel: "MBTI",
    symbol: "⊹",
    description: "理解你的認知偏好，以及與世界互動的方式。",
    action: "查看人格功能",
    runeFlowSpeed: 0.012,
    runePhase: 0.41,
  },
  {
    id: "human-design",
    orbitId: "HumanDesign",
    materialId: "material.human-design",
    runeTextureId: "runes.human-design",
    label: "人類圖",
    shortLabel: "人類圖",
    symbol: "⬡",
    description: "沿著能量中心與通道，辨識適合你的運作策略。",
    action: "閱讀人類圖",
    runeFlowSpeed: 0.011,
    runePhase: 0.59,
  },
  {
    id: "ziwei-bazi",
    orbitId: "ZiweiBazi",
    materialId: "material.ziwei-bazi",
    runeTextureId: "runes.ziwei-bazi",
    label: "紫微八字",
    shortLabel: "紫微八字",
    symbol: "辰",
    description: "以干支、星曜與宮位，觀察生命結構與時運。",
    action: "查看命盤",
    runeFlowSpeed: 0.009,
    runePhase: 0.77,
  },
] as const;

export const PANTHEON_THEME_BY_ID = Object.fromEntries(
  PANTHEON_THEME_CONFIGS.map((theme) => [theme.id, theme]),
) as Record<PantheonThemeId, PantheonThemeConfig>;

export const PANTHEON_THEME_BY_ORBIT = Object.fromEntries(
  PANTHEON_THEME_CONFIGS.map((theme) => [theme.orbitId, theme]),
) as Record<StarOrbitId, PantheonThemeConfig>;
