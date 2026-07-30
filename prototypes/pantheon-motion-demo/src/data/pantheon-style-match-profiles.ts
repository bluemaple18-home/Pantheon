import type { PantheonThemeId } from "./pantheon-theme-config.ts";

export type StyleMatchCandidateId =
  | "visual-target-v1"
  | "reference-match"
  | "soft-metal"
  | "soft-illustration"
  | "reflection-v1";

export type PantheonStyleMatchProfile = {
  id: StyleMatchCandidateId;
  label: string;
  enabled: boolean;
  wrap: number;
  wrapStrength: number;
  viewGradientStrength: number;
  rimStrength: number;
  specularTintStrength: number;
  colorLift: number;
  emissiveLift: number;
  gradientStrength: number;
  backBrightness: number;
  roughnessOffset: number;
  metalnessScale: number;
  envMapIntensity: number;
  coreEmissive: number;
  coreRoughness: number;
  coreColor: string;
  coreEmissiveColor: string;
  coreMetalness: number;
  themeBalance: Record<PantheonThemeId, PantheonThemeBalance>;
};

export type PantheonThemeBalance = {
  brightness: number;
  saturation: number;
  roughness?: number;
  metalness?: number;
  roughnessOffset: number;
  metalnessScale: number;
  highlightStrength: number;
  gradientStrength: number;
  depthBackBrightness: number;
  bevelBrightness: number;
};

export const PANTHEON_STYLE_GRADIENTS: Record<
  PantheonThemeId,
  { start: string; end: string }
> = {
  constellation: {
    start: "#132b50",
    end: "#667fa3",
  },
  tarot: {
    start: "#762d40",
    end: "#b55f70",
  },
  mbti: {
    start: "#245f5b",
    end: "#5b918a",
  },
  "human-design": {
    start: "#96a4a3",
    end: "#becbc8",
  },
  "ziwei-bazi": {
    start: "#774a30",
    end: "#b77d4d",
  },
};

const CLOSEST_CURRENT_BALANCE: Record<
  PantheonThemeId,
  PantheonThemeBalance
> = {
  constellation: {
    brightness: 0.96,
    saturation: 0.9,
    roughnessOffset: 0,
    metalnessScale: 1,
    highlightStrength: 0.92,
    gradientStrength: 0.42,
    depthBackBrightness: 0.78,
    bevelBrightness: 1.05,
  },
  tarot: {
    brightness: 0.97,
    saturation: 0.92,
    roughnessOffset: 0,
    metalnessScale: 0.96,
    highlightStrength: 0.92,
    gradientStrength: 0.42,
    depthBackBrightness: 0.82,
    bevelBrightness: 1.05,
  },
  mbti: {
    brightness: 0.92,
    saturation: 0.9,
    roughnessOffset: 0.03,
    metalnessScale: 0.94,
    highlightStrength: 0.88,
    gradientStrength: 0.38,
    depthBackBrightness: 0.86,
    bevelBrightness: 1.04,
  },
  "human-design": {
    brightness: 0.98,
    saturation: 0.72,
    roughnessOffset: -0.04,
    metalnessScale: 0.9,
    highlightStrength: 0.9,
    gradientStrength: 0.14,
    depthBackBrightness: 0.84,
    bevelBrightness: 1.08,
  },
  "ziwei-bazi": {
    brightness: 0.95,
    saturation: 0.88,
    roughnessOffset: -0.01,
    metalnessScale: 0.94,
    highlightStrength: 0.9,
    gradientStrength: 0.4,
    depthBackBrightness: 0.81,
    bevelBrightness: 1.05,
  },
};

const BALANCED_THEME_BALANCE: Record<
  PantheonThemeId,
  PantheonThemeBalance
> = {
  constellation: {
    brightness: 0.92,
    saturation: 0.86,
    roughness: 0.46,
    metalness: 0.8645,
    roughnessOffset: 0,
    metalnessScale: 1,
    highlightStrength: 0.82,
    gradientStrength: 0.4,
    depthBackBrightness: 0.72,
    bevelBrightness: 1.06,
  },
  tarot: {
    brightness: 0.72,
    saturation: 0.9,
    roughness: 0.44,
    metalness: 0.8126,
    roughnessOffset: 0,
    metalnessScale: 0.94,
    highlightStrength: 0.38,
    gradientStrength: 0.42,
    depthBackBrightness: 0.82,
    bevelBrightness: 1.06,
  },
  mbti: {
    brightness: 0.88,
    saturation: 0.86,
    roughness: 0.44,
    metalness: 0.82,
    roughnessOffset: 0.05,
    metalnessScale: 0.9,
    highlightStrength: 0.66,
    gradientStrength: 0.36,
    depthBackBrightness: 0.86,
    bevelBrightness: 1.04,
  },
  "human-design": {
    brightness: 0.68,
    saturation: 0.68,
    roughness: 0.48,
    metalness: 0.84,
    roughnessOffset: -0.04,
    metalnessScale: 0.9,
    highlightStrength: 0.48,
    gradientStrength: 0.16,
    depthBackBrightness: 0.72,
    bevelBrightness: 1.1,
  },
  "ziwei-bazi": {
    brightness: 0.9,
    saturation: 0.82,
    roughness: 0.39,
    metalness: 0.86,
    roughnessOffset: -0.01,
    metalnessScale: 0.92,
    highlightStrength: 0.62,
    gradientStrength: 0.4,
    depthBackBrightness: 0.87,
    bevelBrightness: 1.06,
  },
};

const ORIGINAL_SITE_BALANCE: Record<
  PantheonThemeId,
  PantheonThemeBalance
> = {
  constellation: {
    ...BALANCED_THEME_BALANCE.constellation,
    brightness: 0.94,
    gradientStrength: 0.5,
    depthBackBrightness: 0.76,
  },
  tarot: {
    ...BALANCED_THEME_BALANCE.tarot,
    brightness: 0.97,
    gradientStrength: 0.5,
  },
  mbti: {
    ...BALANCED_THEME_BALANCE.mbti,
    brightness: 0.92,
    saturation: 0.9,
    gradientStrength: 0.46,
  },
  "human-design": {
    ...BALANCED_THEME_BALANCE["human-design"],
    brightness: 1,
    gradientStrength: 0.18,
  },
  "ziwei-bazi": {
    ...BALANCED_THEME_BALANCE["ziwei-bazi"],
    brightness: 0.96,
    saturation: 0.86,
    gradientStrength: 0.48,
  },
};

const VISUAL_TARGET_V1_BALANCE: Record<
  PantheonThemeId,
  PantheonThemeBalance
> = {
  constellation: {
    brightness: 0.94,
    saturation: 1,
    roughness: 0.34,
    metalness: 0.92,
    roughnessOffset: 0,
    metalnessScale: 1,
    highlightStrength: 0.84,
    gradientStrength: 0.34,
    depthBackBrightness: 0.8,
    bevelBrightness: 1.12,
  },
  tarot: {
    brightness: 0.86,
    saturation: 1,
    roughness: 0.36,
    metalness: 0.9,
    roughnessOffset: 0,
    metalnessScale: 1,
    highlightStrength: 0.72,
    gradientStrength: 0.32,
    depthBackBrightness: 0.72,
    bevelBrightness: 1.12,
  },
  mbti: {
    brightness: 0.87,
    saturation: 1,
    roughness: 0.37,
    metalness: 0.9,
    roughnessOffset: 0,
    metalnessScale: 1,
    highlightStrength: 0.72,
    gradientStrength: 0.3,
    depthBackBrightness: 0.72,
    bevelBrightness: 1.1,
  },
  "human-design": {
    brightness: 0.9,
    saturation: 0.58,
    roughness: 0.35,
    metalness: 0.91,
    roughnessOffset: 0,
    metalnessScale: 1,
    highlightStrength: 0.7,
    gradientStrength: 0.24,
    depthBackBrightness: 0.74,
    bevelBrightness: 1.14,
  },
  "ziwei-bazi": {
    brightness: 0.86,
    saturation: 0.96,
    roughness: 0.36,
    metalness: 0.92,
    roughnessOffset: 0,
    metalnessScale: 1,
    highlightStrength: 0.78,
    gradientStrength: 0.32,
    depthBackBrightness: 0.72,
    bevelBrightness: 1.13,
  },
};

export const PANTHEON_STYLE_MATCH_CANDIDATES: Record<
  StyleMatchCandidateId,
  PantheonStyleMatchProfile
> = {
  "visual-target-v1": {
    id: "visual-target-v1",
    label: "Pantheon Visual Target v1",
    enabled: true,
    wrap: 0.42,
    wrapStrength: 0.18,
    viewGradientStrength: 0.12,
    rimStrength: 0.035,
    specularTintStrength: 0.82,
    colorLift: 0.025,
    emissiveLift: 0.018,
    gradientStrength: 0.34,
    backBrightness: 0.64,
    roughnessOffset: 0,
    metalnessScale: 1,
    envMapIntensity: 1,
    coreEmissive: 0.065,
    coreRoughness: 0.26,
    coreColor: "#bd8f3e",
    coreEmissiveColor: "#4a2d08",
    coreMetalness: 0.88,
    themeBalance: VISUAL_TARGET_V1_BALANCE,
  },
  "reference-match": {
    id: "reference-match",
    label: "Candidate A · Closest to Current",
    enabled: true,
    wrap: 0.48,
    wrapStrength: 0.2,
    viewGradientStrength: 0.17,
    rimStrength: 0.052,
    specularTintStrength: 0.28,
    colorLift: 0.045,
    emissiveLift: 0.045,
    gradientStrength: 0.46,
    backBrightness: 0.82,
    roughnessOffset: 0.01,
    metalnessScale: 0.78,
    envMapIntensity: 0.44,
    coreEmissive: 0.045,
    coreRoughness: 0.35,
    coreColor: "#b78a3d",
    coreEmissiveColor: "#3a2609",
    coreMetalness: 0.82,
    themeBalance: CLOSEST_CURRENT_BALANCE,
  },
  "soft-metal": {
    id: "soft-metal",
    label: "Candidate B · Balanced",
    enabled: true,
    wrap: 0.48,
    wrapStrength: 0.34,
    viewGradientStrength: 0.17,
    rimStrength: 0.052,
    specularTintStrength: 0.28,
    colorLift: 0.11,
    emissiveLift: 0.045,
    gradientStrength: 0.46,
    backBrightness: 0.9,
    roughnessOffset: -0.1,
    metalnessScale: 0.95,
    envMapIntensity: 0.92,
    coreEmissive: 0.07,
    coreRoughness: 0.3,
    coreColor: "#c9a154",
    coreEmissiveColor: "#52370d",
    coreMetalness: 0.76,
    themeBalance: BALANCED_THEME_BALANCE,
  },
  "soft-illustration": {
    id: "soft-illustration",
    label: "Candidate C · Closest to Original Site",
    enabled: true,
    wrap: 0.52,
    wrapStrength: 0.24,
    viewGradientStrength: 0.2,
    rimStrength: 0.05,
    specularTintStrength: 0.28,
    colorLift: 0.06,
    emissiveLift: 0.055,
    gradientStrength: 0.58,
    backBrightness: 0.83,
    roughnessOffset: 0.02,
    metalnessScale: 0.72,
    envMapIntensity: 0.42,
    coreEmissive: 0.035,
    coreRoughness: 0.36,
    coreColor: "#98712f",
    coreEmissiveColor: "#322108",
    coreMetalness: 0.86,
    themeBalance: ORIGINAL_SITE_BALANCE,
  },
  "reflection-v1": {
    id: "reflection-v1",
    label: "Archive · Reflection v1",
    enabled: false,
    wrap: 0,
    wrapStrength: 0,
    viewGradientStrength: 0,
    rimStrength: 0,
    specularTintStrength: 0,
    colorLift: 0,
    emissiveLift: 0,
    gradientStrength: 0,
    backBrightness: 1,
    roughnessOffset: 0,
    metalnessScale: 1,
    envMapIntensity: 0.86,
    coreEmissive: 0,
    coreRoughness: 0.24,
    coreColor: "#8a6528",
    coreEmissiveColor: "#000000",
    coreMetalness: 0.92,
    themeBalance: CLOSEST_CURRENT_BALANCE,
  },
};

export const DEFAULT_STYLE_MATCH_CANDIDATE: StyleMatchCandidateId =
  "visual-target-v1";

export const PANTHEON_STYLE_LIGHT_DIRECTION = [
  -0.48,
  0.66,
  0.58,
] as const;

export const PANTHEON_STYLE_BACKGROUND = {
  center: "#10243a",
  edge: "#06101d",
  solidFallback: "#091522",
} as const;
