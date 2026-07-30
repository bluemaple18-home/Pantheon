import type { PantheonThemeId } from "./pantheon-theme-config.ts";

export const PANTHEON_EFFECTS_VERSION = "Pantheon Effects v1" as const;

export const BAND_RUNE_SURFACE_CONFIG = {
  system: "pantheon-theme-raised-metal-relief-v1",
  reliefModel: "shallow-cast-raised-metal",
  fixedToBandUv: true,
  independentMotion: false,
  emissive: false,
  cellCount: 24,
  minimumGlyphClusters: 20,
  idleMarkOpacity: 0.58,
  hoveredMarkOpacity: 0.72,
  selectedMarkOpacity: 0.84,
  backgroundMarkOpacity: 0.42,
  reliefDepth: 0.078,
  reliefEdgeSharpness: 0.61,
  contactShadowStrength: 0.052,
  edgeHighlightStrength: 0.072,
  roughnessTopDelta: -0.018,
  roughnessEdgeDelta: 0.012,
  metalnessDelta: 0,
} as const;

export interface SurfaceEnergyConfig {
  cycleSeconds: number;
  pulseCount: number;
  intensity: number;
  direction: 1 | -1;
  rhythmWarp: number;
}

export const SURFACE_ENERGY_CONFIG: Record<
  PantheonThemeId,
  SurfaceEnergyConfig
> = {
  constellation: {
    cycleSeconds: 18,
    pulseCount: 2,
    intensity: 0.36,
    direction: 1,
    rhythmWarp: 0.16,
  },
  tarot: {
    cycleSeconds: 13,
    pulseCount: 1,
    intensity: 0.46,
    direction: -1,
    rhythmWarp: 0.3,
  },
  mbti: {
    cycleSeconds: 16,
    pulseCount: 2,
    intensity: 0.34,
    direction: 1,
    rhythmWarp: 0.08,
  },
  "human-design": {
    cycleSeconds: 12,
    pulseCount: 1,
    intensity: 0.32,
    direction: -1,
    rhythmWarp: 0.22,
  },
  "ziwei-bazi": {
    cycleSeconds: 20,
    pulseCount: 1,
    intensity: 0.42,
    direction: 1,
    rhythmWarp: 0.36,
  },
};

export const HOVER_EFFECT_CONFIG = {
  idleMarkOpacity: BAND_RUNE_SURFACE_CONFIG.idleMarkOpacity,
  hoveredMarkOpacity: BAND_RUNE_SURFACE_CONFIG.hoveredMarkOpacity,
  sweepDurationSeconds: 0,
  sweepIntensity: 0,
} as const;

export const SELF_CORE_EFFECT_CONFIG = {
  reflectionFrequencyHz: 0.42,
  normalStrength: 0.032,
  roughnessVariation: 0.028,
} as const;

export const CORE_RUNE_RELATIONSHIP_CONFIG = {
  projectionInnerRadius: 0.012,
  projectionOuterRadius: 0.14,
  proximityCalibrationSamples: 72,
  proximityCalibrationIntervalFrames: 12,
  hysteresis: 0.035,
  enterDurationSeconds: 0.34,
  exitDurationSeconds: 0.62,
  maximumInfluence: 0.92,
  stateInfluence: {
    Idle: 0.72,
    Hovered: 0.8,
    Selected: 0.9,
    Background: 0.56,
  },
  themeColors: {
    constellation: "#4f78b3",
    tarot: "#b6556c",
    mbti: "#47a89b",
    "human-design": "#c0d3d5",
    "ziwei-bazi": "#c7854c",
  },
} as const;
