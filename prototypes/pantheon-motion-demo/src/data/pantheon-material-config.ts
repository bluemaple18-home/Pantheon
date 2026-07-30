import type { PantheonThemeId } from "./pantheon-theme-config.ts";

export interface PantheonMaterialConfig {
  id: string;
  themeId: PantheonThemeId;
  color: string;
  accent: string;
  metalness: number;
  roughness: number;
  clearcoat: number;
  clearcoatRoughness: number;
  anisotropy: number;
  envMapIntensity: number;
  markStyle: number;
}

export const PANTHEON_MATERIAL_CONFIGS: Record<
  PantheonThemeId,
  PantheonMaterialConfig
> = {
  constellation: {
    id: "material.constellation",
    themeId: "constellation",
    color: "#294f87",
    accent: "#c7a96a",
    metalness: 0.91,
    roughness: 0.56,
    clearcoat: 0,
    clearcoatRoughness: 0.28,
    anisotropy: 0.42,
    envMapIntensity: 0.66,
    markStyle: 0,
  },
  tarot: {
    id: "material.tarot",
    themeId: "tarot",
    color: "#8a3b4a",
    accent: "#d1a06f",
    metalness: 0.91,
    roughness: 0.54,
    clearcoat: 0,
    clearcoatRoughness: 0.27,
    anisotropy: 0.38,
    envMapIntensity: 0.67,
    markStyle: 1,
  },
  mbti: {
    id: "material.mbti",
    themeId: "mbti",
    color: "#2d756f",
    accent: "#d1b274",
    metalness: 0.89,
    roughness: 0.58,
    clearcoat: 0,
    clearcoatRoughness: 0.3,
    anisotropy: 0.36,
    envMapIntensity: 0.64,
    markStyle: 2,
  },
  "human-design": {
    id: "material.human-design",
    themeId: "human-design",
    color: "#a8b4b3",
    accent: "#afc5ce",
    metalness: 0.91,
    roughness: 0.55,
    clearcoat: 0,
    clearcoatRoughness: 0.29,
    anisotropy: 0.34,
    envMapIntensity: 0.66,
    markStyle: 3,
  },
  "ziwei-bazi": {
    id: "material.ziwei-bazi",
    themeId: "ziwei-bazi",
    color: "#8f5c3e",
    accent: "#d8ae67",
    metalness: 0.92,
    roughness: 0.56,
    clearcoat: 0,
    clearcoatRoughness: 0.28,
    anisotropy: 0.44,
    envMapIntensity: 0.68,
    markStyle: 4,
  },
};

export interface RibbonWidthProfile {
  idle: number;
  hover: number;
  selected: number;
}

export const DESKTOP_RIBBON_WIDTHS: RibbonWidthProfile = {
  idle: 0.22,
  hover: 0.22,
  selected: 0.22,
};

export const MOBILE_RIBBON_WIDTHS: RibbonWidthProfile = {
  idle: 0.2,
  hover: 0.2,
  selected: 0.2,
};

export const DESKTOP_BAND_WIDTH = 0.22;
export const MOBILE_BAND_WIDTH = 0.2;
export type BandWidthProfile = RibbonWidthProfile;
export const DESKTOP_BAND_WIDTHS = DESKTOP_RIBBON_WIDTHS;
export const MOBILE_BAND_WIDTHS = MOBILE_RIBBON_WIDTHS;

export const RIBBON_PROGRESS = {
  idle: 0.22,
  hover: 0.5,
  selected: 1,
} as const;

function smoothStep(value: number) {
  const clamped = Math.max(0, Math.min(1, value));
  return clamped * clamped * (3 - 2 * clamped);
}

export function ribbonWidthAt(
  progress: number,
  profile: RibbonWidthProfile = DESKTOP_RIBBON_WIDTHS,
): number {
  const value = Math.max(RIBBON_PROGRESS.idle, Math.min(1, progress));
  if (value <= RIBBON_PROGRESS.hover) {
    const ratio = smoothStep(
      (value - RIBBON_PROGRESS.idle) /
        (RIBBON_PROGRESS.hover - RIBBON_PROGRESS.idle),
    );
    return profile.idle + (profile.hover - profile.idle) * ratio;
  }
  const ratio = smoothStep(
    (value - RIBBON_PROGRESS.hover) /
      (RIBBON_PROGRESS.selected - RIBBON_PROGRESS.hover),
  );
  return (
    profile.hover + (profile.selected - profile.hover) * ratio
  );
}
