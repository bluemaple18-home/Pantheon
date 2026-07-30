import * as THREE from "three";
import {
  DESKTOP_RIBBON_WIDTHS,
  MOBILE_RIBBON_WIDTHS,
  PANTHEON_MATERIAL_CONFIGS,
  type RibbonWidthProfile,
} from "../data/pantheon-material-config.ts";
import {
  PANTHEON_THEME_CONFIGS,
  type PantheonThemeId,
} from "../data/pantheon-theme-config.ts";
import {
  DEFAULT_REFLECTION_CANDIDATE,
  PANTHEON_REFLECTION_CANDIDATES,
  REFLECTION_CORE_SUPPRESSION,
  type ReflectionCandidateId,
} from "../data/pantheon-reflection-profiles.ts";
import {
  DEFAULT_STYLE_MATCH_CANDIDATE,
  PANTHEON_STYLE_GRADIENTS,
  PANTHEON_STYLE_LIGHT_DIRECTION,
  PANTHEON_STYLE_MATCH_CANDIDATES,
  type StyleMatchCandidateId,
} from "../data/pantheon-style-match-profiles.ts";
import {
  BAND_RUNE_SURFACE_CONFIG,
  HOVER_EFFECT_CONFIG,
  PANTHEON_EFFECTS_VERSION,
  SURFACE_ENERGY_CONFIG,
} from "../data/pantheon-effects-config.ts";
import {
  createPantheonInteractionState,
  INTERACTION_TIMING,
  resolveOrbitVisualState,
  smoothToward,
  visualTargets,
} from "../interaction/createPantheonInteractionState.ts";
import {
  RIBBON_PHASE_DEGREES,
} from "../generated/createPantheonStarOrbits.ts";
import type {
  StarOrbitId,
  getPantheonStarOrbitRuntime,
} from "../generated/createPantheonStarOrbits.ts";

type OrbitRuntime = ReturnType<typeof getPantheonStarOrbitRuntime>;

export type DirectSpecularCompressionCandidateId =
  | "baseline"
  | "candidate-a"
  | "candidate-b";

export type StyleColorLiftCandidateId =
  | "baseline"
  | "candidate-a"
  | "candidate-b";

export type HumanDesignIndirectSpecularCandidateId =
  | "baseline"
  | "candidate-a"
  | "candidate-b";

export type MetalColorDensityCandidateId =
  | "baseline"
  | "candidate-a"
  | "candidate-b"
  | "visual-target-v1";

type MetalColorDensityProfile = Record<
  PantheonThemeId,
  {
    baseColor: string;
    gradientStart: string;
    gradientEnd: string;
    saturation: number;
  }
>;

const METAL_COLOR_DENSITY_CANDIDATES: Record<
  MetalColorDensityCandidateId,
  MetalColorDensityProfile
> = {
  "visual-target-v1": {
    constellation: {
      baseColor: "#204a7a",
      gradientStart: "#14335a",
      gradientEnd: "#486b94",
      saturation: 1,
    },
    tarot: {
      baseColor: "#702638",
      gradientStart: "#3d121f",
      gradientEnd: "#9f4a5d",
      saturation: 1,
    },
    mbti: {
      baseColor: "#0f5a61",
      gradientStart: "#07373d",
      gradientEnd: "#367e86",
      saturation: 1,
    },
    "human-design": {
      baseColor: "#8d989d",
      gradientStart: "#5d686f",
      gradientEnd: "#d0d6d7",
      saturation: 0.6,
    },
    "ziwei-bazi": {
      baseColor: "#70411f",
      gradientStart: "#40230f",
      gradientEnd: "#ad7440",
      saturation: 0.98,
    },
  },
  baseline: {
    constellation: {
      baseColor: "#294f87",
      gradientStart: "#132b50",
      gradientEnd: "#667fa3",
      saturation: 0.86,
    },
    tarot: {
      baseColor: "#8a3b4a",
      gradientStart: "#762d40",
      gradientEnd: "#b55f70",
      saturation: 0.9,
    },
    mbti: {
      baseColor: "#2d756f",
      gradientStart: "#245f5b",
      gradientEnd: "#5b918a",
      saturation: 0.86,
    },
    "human-design": {
      baseColor: "#a8b4b3",
      gradientStart: "#96a4a3",
      gradientEnd: "#becbc8",
      saturation: 0.68,
    },
    "ziwei-bazi": {
      baseColor: "#8f5c3e",
      gradientStart: "#774a30",
      gradientEnd: "#b77d4d",
      saturation: 0.82,
    },
  },
  "candidate-a": {
    constellation: {
      baseColor: "#234a82",
      gradientStart: "#102846",
      gradientEnd: "#55749e",
      saturation: 0.96,
    },
    tarot: {
      baseColor: "#873044",
      gradientStart: "#652337",
      gradientEnd: "#b34e68",
      saturation: 1,
    },
    mbti: {
      baseColor: "#236f68",
      gradientStart: "#175752",
      gradientEnd: "#4d9187",
      saturation: 0.9288,
    },
    "human-design": {
      baseColor: "#9aa9ac",
      gradientStart: "#7e9095",
      gradientEnd: "#bac9cc",
      saturation: 0.74,
    },
    "ziwei-bazi": {
      baseColor: "#925535",
      gradientStart: "#6c3c25",
      gradientEnd: "#be7841",
      saturation: 0.902,
    },
  },
  "candidate-b": {
    constellation: {
      baseColor: "#284f88",
      gradientStart: "#132c4a",
      gradientEnd: "#6280a8",
      saturation: 0.912,
    },
    tarot: {
      baseColor: "#8f364b",
      gradientStart: "#762c42",
      gradientEnd: "#b65d74",
      saturation: 0.95,
    },
    mbti: {
      baseColor: "#28766e",
      gradientStart: "#1c5f5a",
      gradientEnd: "#509389",
      saturation: 0.88236,
    },
    "human-design": {
      baseColor: "#a7b3b6",
      gradientStart: "#95a3a7",
      gradientEnd: "#bdcbcd",
      saturation: 0.703,
    },
    "ziwei-bazi": {
      baseColor: "#95593a",
      gradientStart: "#7d472d",
      gradientEnd: "#bc7b47",
      saturation: 0.8569,
    },
  },
};

const HUMAN_DESIGN_INDIRECT_SPECULAR_CANDIDATES: Record<
  HumanDesignIndirectSpecularCandidateId,
  { pivot: number; contrast: number }
> = {
  baseline: { pivot: 0.18, contrast: 1 },
  "candidate-a": { pivot: 0.18, contrast: 1.3 },
  "candidate-b": { pivot: 0.18, contrast: 1.5 },
};

const STYLE_COLOR_LIFT_CANDIDATES: Record<
  StyleColorLiftCandidateId,
  number
> = {
  baseline: 0.11,
  "candidate-a": 0.05,
  "candidate-b": 0.03,
};

const DIRECT_SPECULAR_COMPRESSION_SHOULDERS: Record<
  DirectSpecularCompressionCandidateId,
  Partial<Record<PantheonThemeId, number>>
> = {
  baseline: {},
  "candidate-a": {
    constellation: 2.4,
    tarot: 1.4,
  },
  "candidate-b": {
    constellation: 1.9,
    tarot: 1,
  },
};

interface ThemeBinding {
  id: PantheonThemeId;
  orbitId: StarOrbitId;
  line: THREE.Mesh;
  ribbon: THREE.Mesh;
  rune: THREE.Mesh;
  lineMaterial: THREE.MeshStandardMaterial;
  ribbonMaterial: THREE.MeshPhysicalMaterial;
  bevelMaterial: THREE.MeshPhysicalMaterial;
  edgeMaterial: THREE.MeshPhysicalMaterial;
  ribbonUniforms: RibbonUniforms;
  runeUniforms: RuneUniforms;
  baseColor: THREE.Color;
  accentColor: THREE.Color;
  opacity: number;
}

interface RibbonUniforms {
  width: { value: number };
  thickness: { value: number };
  twist: { value: number };
  debugMode: { value: number };
  markOpacity: { value: number };
  markDepth: { value: number };
  markRoughnessDelta: { value: number };
  markMetalnessDelta: { value: number };
  markEmissive: { value: number };
  flow: { value: number };
  flowIntensity: { value: number };
  energyPulseCount: { value: number };
  energyDirection: { value: number };
  hoverSweep: { value: number };
  hoverSweepIntensity: { value: number };
  markStyle: { value: number };
  markColor: { value: THREE.Color };
  reflectionEnabled: { value: number };
  highlightOffset: { value: number };
  highlightWidth: { value: number };
  highlightStrength: { value: number };
  specularGain: { value: number };
  grazingGain: { value: number };
  darkSideLift: { value: number };
  centerSuppression: { value: number };
  coreSuppressInner: { value: number };
  coreSuppressOuter: { value: number };
  grazingPower: { value: number };
  specularShoulder: { value: number };
  directSpecularCompressionShoulder: { value: number };
  indirectSpecularContrast: { value: number };
  indirectSpecularPivot: { value: number };
  reflectionTintAmount: { value: number };
  reflectionRotation: { value: number };
  profileColor: { value: THREE.Color };
  styleEnabled: { value: number };
  styleGradientStart: { value: THREE.Color };
  styleGradientEnd: { value: THREE.Color };
  styleGradientStrength: { value: number };
  styleWrap: { value: number };
  styleWrapStrength: { value: number };
  styleViewGradientStrength: { value: number };
  styleRimStrength: { value: number };
  styleSpecularTintStrength: { value: number };
  styleColorLift: { value: number };
  styleEmissiveLift: { value: number };
  styleBackBrightness: { value: number };
  styleThemeBrightness: { value: number };
  styleThemeSaturation: { value: number };
  styleHighlightStrength: { value: number };
  styleLightDirection: { value: THREE.Vector3 };
}

interface RuneUniforms {
  width: { value: number };
  thickness: { value: number };
  twist: { value: number };
  debugMode: { value: number };
  flow: { value: number };
  opacity: { value: number };
  color: { value: THREE.Color };
}

const PREBUILT_MAX_RIBBON_WIDTH = 0.23;
const RIBBON_THICKNESS = 0.02;
const BAND_BEVEL_WIDTH = 0.0024;
const BAND_BEVEL_SEGMENTS = 2;
const MOBILE_STUDIO_METAL_TINT = new THREE.Color(0xb9b4aa);

const VALIDATION_MODE = {
  "flat-pbr": 0,
  "front-back": 1,
  normal: 2,
  tangent: 3,
  edge: 4,
  uv: 5,
  roughness: 6,
  metalness: 7,
  marks: 8,
  flow: 9,
  bevel: 10,
  "outer-isolation": 8,
  "outer-intersections": 9,
  "over-under": 1,
  "mark-density": 8,
  engraving: 8,
  emissive: 9,
  "background-weight": 0,
  "brushed-metal": 6,
  "engraving-reveal": 8,
  "luxury-metal": 0,
  "material-v2": 0,
  "material-v3": 0,
  "physical-specular": 11,
  "highlight-mask": 12,
  "core-suppression": 13,
  "grazing-response": 14,
  "dark-side-lift": 15,
  "reflection-rotation": 16,
  "luminance-heatmap": 17,
  "overexposure-mask": 18,
  "reflection-profile": 19,
  "baseline-linked-compare": 20,
} as const;

export const DEFAULT_METAL_HIGHLIGHT_STRENGTH = 1;
export const PANTHEON_BAND_ENVIRONMENT_BASELINE = Object.freeze({
  topBottom: 1.288,
  bevel: 1.365,
  edge: 1.133,
});

function applyBandEnvironmentRotation(
  material: THREE.MeshPhysicalMaterial,
  reflectionRotationDegrees: number,
) {
  const rotation = THREE.MathUtils.degToRad(
    reflectionRotationDegrees,
  );
  material.envMapRotation.set(
    rotation * 0.42,
    rotation,
    rotation * -0.28,
    "XYZ",
  );
}

function configureRibbonMaterial(
  material: THREE.MeshPhysicalMaterial,
  uniforms: RibbonUniforms,
) {
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, {
      uRibbonWidth: uniforms.width,
      uRibbonThickness: uniforms.thickness,
      uMobiusTwist: uniforms.twist,
      uRibbonDebugMode: uniforms.debugMode,
      uMarkOpacity: uniforms.markOpacity,
      uMarkDepth: uniforms.markDepth,
      uMarkRoughnessDelta: uniforms.markRoughnessDelta,
      uMarkMetalnessDelta: uniforms.markMetalnessDelta,
      uMarkEmissive: uniforms.markEmissive,
      uBandFlow: uniforms.flow,
      uFlowIntensity: uniforms.flowIntensity,
      uEnergyPulseCount: uniforms.energyPulseCount,
      uEnergyDirection: uniforms.energyDirection,
      uHoverSweep: uniforms.hoverSweep,
      uHoverSweepIntensity: uniforms.hoverSweepIntensity,
      uMarkStyle: uniforms.markStyle,
      uMarkColor: uniforms.markColor,
      uReflectionEnabled: uniforms.reflectionEnabled,
      uHighlightOffset: uniforms.highlightOffset,
      uHighlightWidth: uniforms.highlightWidth,
      uHighlightStrength: uniforms.highlightStrength,
      uSpecularGain: uniforms.specularGain,
      uGrazingGain: uniforms.grazingGain,
      uDarkSideLift: uniforms.darkSideLift,
      uCenterSuppression: uniforms.centerSuppression,
      uCoreSuppressInner: uniforms.coreSuppressInner,
      uCoreSuppressOuter: uniforms.coreSuppressOuter,
      uGrazingPower: uniforms.grazingPower,
      uSpecularShoulder: uniforms.specularShoulder,
      uDirectSpecularCompressionShoulder:
        uniforms.directSpecularCompressionShoulder,
      uIndirectSpecularContrast:
        uniforms.indirectSpecularContrast,
      uIndirectSpecularPivot: uniforms.indirectSpecularPivot,
      uReflectionTintAmount: uniforms.reflectionTintAmount,
      uReflectionRotation: uniforms.reflectionRotation,
      uProfileColor: uniforms.profileColor,
      uStyleEnabled: uniforms.styleEnabled,
      uStyleGradientStart: uniforms.styleGradientStart,
      uStyleGradientEnd: uniforms.styleGradientEnd,
      uStyleGradientStrength: uniforms.styleGradientStrength,
      uStyleWrap: uniforms.styleWrap,
      uStyleWrapStrength: uniforms.styleWrapStrength,
      uStyleViewGradientStrength: uniforms.styleViewGradientStrength,
      uStyleRimStrength: uniforms.styleRimStrength,
      uStyleSpecularTintStrength: uniforms.styleSpecularTintStrength,
      uStyleColorLift: uniforms.styleColorLift,
      uStyleEmissiveLift: uniforms.styleEmissiveLift,
      uStyleBackBrightness: uniforms.styleBackBrightness,
      uStyleThemeBrightness: uniforms.styleThemeBrightness,
      uStyleThemeSaturation: uniforms.styleThemeSaturation,
      uStyleHighlightStrength: uniforms.styleHighlightStrength,
      uStyleLightDirection: uniforms.styleLightDirection,
    });
    shader.vertexShader = shader.vertexShader
      .replace(
        "void main() {",
        `attribute vec3 aCenterline;
attribute vec3 aWidthOffset;
attribute vec3 aThicknessOffset;
attribute vec3 aTangent;
attribute float aOrbitProgress;
attribute float aFaceType;
uniform float uRibbonWidth;
uniform float uRibbonThickness;
uniform float uMobiusTwist;
varying vec2 vRibbonUv;
varying float vRibbonFaceType;
varying vec3 vRibbonTangent;
varying vec3 vRibbonSide;
varying vec3 vRibbonSurfaceNormal;
varying vec3 vBandWorldPosition;
void main() {`,
      )
      .replace(
        "#include <begin_vertex>",
        `float twistAngle = 3.14159265359 * uMobiusTwist * aOrbitProgress;
vec3 widthDirection =
  aWidthOffset * cos(twistAngle) +
  aThicknessOffset * sin(twistAngle);
vec3 thicknessDirection =
  aThicknessOffset * cos(twistAngle) -
  aWidthOffset * sin(twistAngle);
vec3 transformed =
  aCenterline +
  widthDirection * (uRibbonWidth * 0.5) +
  thicknessDirection * (uRibbonThickness * 0.5);
vRibbonUv = uv;
vRibbonFaceType = aFaceType;
vRibbonTangent = normalize(normalMatrix * aTangent);
vRibbonSide = normalize(normalMatrix * aWidthOffset);
vRibbonSurfaceNormal = normalize(normalMatrix * aThicknessOffset);
vBandWorldPosition = (modelMatrix * vec4(transformed, 1.0)).xyz;`,
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "void main() {",
        `uniform float uRibbonDebugMode;
uniform float uMarkOpacity;
uniform float uMarkDepth;
uniform float uMarkRoughnessDelta;
uniform float uMarkMetalnessDelta;
uniform float uMarkEmissive;
uniform float uBandFlow;
uniform float uFlowIntensity;
uniform float uEnergyPulseCount;
uniform float uEnergyDirection;
uniform float uHoverSweep;
uniform float uHoverSweepIntensity;
uniform float uMarkStyle;
uniform vec3 uMarkColor;
uniform float uReflectionEnabled;
uniform float uHighlightOffset;
uniform float uHighlightWidth;
uniform float uHighlightStrength;
uniform float uSpecularGain;
uniform float uGrazingGain;
uniform float uDarkSideLift;
uniform float uCenterSuppression;
uniform float uCoreSuppressInner;
uniform float uCoreSuppressOuter;
uniform float uGrazingPower;
uniform float uSpecularShoulder;
uniform float uDirectSpecularCompressionShoulder;
uniform float uIndirectSpecularContrast;
uniform float uIndirectSpecularPivot;
uniform float uReflectionTintAmount;
uniform float uReflectionRotation;
uniform vec3 uProfileColor;
uniform float uStyleEnabled;
uniform vec3 uStyleGradientStart;
uniform vec3 uStyleGradientEnd;
uniform float uStyleGradientStrength;
uniform float uStyleWrap;
uniform float uStyleWrapStrength;
uniform float uStyleViewGradientStrength;
uniform float uStyleRimStrength;
uniform float uStyleSpecularTintStrength;
uniform float uStyleColorLift;
uniform float uStyleEmissiveLift;
uniform float uStyleBackBrightness;
uniform float uStyleThemeBrightness;
uniform float uStyleThemeSaturation;
uniform float uStyleHighlightStrength;
uniform vec3 uStyleLightDirection;
varying vec2 vRibbonUv;
varying float vRibbonFaceType;
varying vec3 vRibbonTangent;
varying vec3 vRibbonSide;
varying vec3 vRibbonSurfaceNormal;
varying vec3 vBandWorldPosition;
float bandLine(float value, float width) {
  return 1.0 - smoothstep(width, width * 1.8, abs(value));
}
float bandZone(float u, float center, float width) {
  float distanceToCenter = abs(fract(u - center + 0.5) - 0.5);
  return 1.0 - smoothstep(width, width * 1.35, distanceToCenter);
}
float bandSegment(
  vec2 point,
  vec2 start,
  vec2 end,
  float width
) {
  width *= 2.05;
  vec2 segment = end - start;
  float projection = clamp(
    dot(point - start, segment) / max(dot(segment, segment), 0.0001),
    0.0,
    1.0
  );
  float distanceToSegment =
    length(point - (start + segment * projection));
  return 1.0 - smoothstep(width, width * 1.65, distanceToSegment);
}
float bandRing(vec2 point, float radius, float width) {
  return bandLine(length(point) - radius, width * 2.05);
}
float bandBox(vec2 point, vec2 halfSize, float width) {
  vec2 distanceToEdge = abs(abs(point) - halfSize);
  float inside =
    step(abs(point.x), halfSize.x + width) *
    step(abs(point.y), halfSize.y + width);
  return (1.0 - smoothstep(width, width * 1.75, min(distanceToEdge.x, distanceToEdge.y))) * inside;
}
float bandDot(vec2 point, float radius) {
  return 1.0 - smoothstep(radius, radius * 1.65, length(point));
}
float constellationGlyph(vec2 point, float variant) {
  float glyph = 0.0;
  if (variant < 0.5) {
    // 稀疏三節點星圖。
    glyph = max(
      bandDot(point - vec2(-0.12, 0.045), 0.012),
      bandDot(point - vec2(0.0, -0.018), 0.009)
    );
    glyph = max(
      glyph,
      bandDot(point - vec2(0.12, 0.035), 0.013)
    );
    glyph = max(
      glyph,
      bandSegment(point, vec2(-0.108, 0.039), vec2(-0.01, -0.013), 0.0035)
    );
    glyph = max(
      glyph,
      bandSegment(point, vec2(0.01, -0.013), vec2(0.107, 0.031), 0.0035)
    );
  } else if (variant < 1.5) {
    // 天體座標十字與冷靜刻點。
    glyph = max(
      bandRing(point, 0.032, 0.0035),
      bandSegment(point, vec2(-0.09, 0.0), vec2(0.09, 0.0), 0.003)
    );
    glyph = max(
      glyph,
      bandSegment(point, vec2(0.0, -0.075), vec2(0.0, 0.075), 0.003)
    );
  } else if (variant < 2.5) {
    // 雙星與精密座標連線。
    glyph = max(
      bandDot(point - vec2(-0.09, -0.025), 0.011),
      bandDot(point - vec2(0.095, 0.03), 0.014)
    );
    glyph = max(
      glyph,
      bandSegment(point, vec2(-0.078, -0.021), vec2(0.08, 0.025), 0.0033)
    );
    glyph = max(
      glyph,
      bandSegment(point, vec2(0.0, -0.06), vec2(0.0, 0.058), 0.0028)
    );
  } else if (variant < 3.5) {
    // 極簡四向星芒。
    glyph = max(
      bandSegment(point, vec2(-0.11, 0.0), vec2(0.11, 0.0), 0.0032),
      bandSegment(point, vec2(0.0, -0.082), vec2(0.0, 0.082), 0.0032)
    );
    glyph = max(
      glyph,
      bandDot(point, 0.012)
    );
  } else if (variant < 4.5) {
    // 座標刻度。
    glyph = max(
      bandSegment(point, vec2(-0.13, 0.0), vec2(0.13, 0.0), 0.0032),
      bandSegment(point, vec2(-0.08, -0.035), vec2(-0.08, 0.035), 0.003)
    );
    glyph = max(
      glyph,
      bandSegment(point, vec2(0.0, -0.05), vec2(0.0, 0.05), 0.003)
    );
    glyph = max(
      glyph,
      bandSegment(point, vec2(0.08, -0.035), vec2(0.08, 0.035), 0.003)
    );
  } else {
    // 星圖菱形節點。
    glyph = max(
      bandSegment(point, vec2(0.0, 0.07), vec2(0.075, 0.0), 0.0038),
      bandSegment(point, vec2(0.075, 0.0), vec2(0.0, -0.07), 0.0038)
    );
    glyph = max(
      glyph,
      bandSegment(point, vec2(0.0, -0.07), vec2(-0.075, 0.0), 0.0038)
    );
    glyph = max(
      glyph,
      bandSegment(point, vec2(-0.075, 0.0), vec2(0.0, 0.07), 0.0038)
    );
    glyph = max(glyph, bandDot(point, 0.011));
  }
  return clamp(glyph, 0.0, 1.0);
}
float tarotGlyph(vec2 point, float variant) {
  float glyph = 0.0;
  if (variant < 0.5) {
    // 雙層牌框。
    glyph = max(
      bandBox(point, vec2(0.115, 0.082), 0.0045),
      bandBox(point, vec2(0.085, 0.058), 0.0035)
    );
  } else if (variant < 1.5) {
    // 羅馬數字 II。
    glyph = max(
      bandSegment(point, vec2(-0.035, -0.07), vec2(-0.035, 0.07), 0.006),
      bandSegment(point, vec2(0.035, -0.07), vec2(0.035, 0.07), 0.006)
    );
  } else if (variant < 2.5) {
    // 眼形中央徽記。
    glyph = max(
      bandSegment(point, vec2(-0.12, 0.0), vec2(0.0, 0.055), 0.0045),
      bandSegment(point, vec2(0.0, 0.055), vec2(0.12, 0.0), 0.0045)
    );
    glyph = max(
      glyph,
      bandSegment(point, vec2(-0.12, 0.0), vec2(0.0, -0.055), 0.0045)
    );
    glyph = max(
      glyph,
      bandSegment(point, vec2(0.0, -0.055), vec2(0.12, 0.0), 0.0045)
    );
    glyph = max(glyph, bandDot(point, 0.018));
  } else if (variant < 3.5) {
    // 儀式太陽徽記。
    glyph = max(bandRing(point, 0.034, 0.0045), bandDot(point, 0.012));
    glyph = max(
      glyph,
      bandSegment(point, vec2(-0.095, 0.0), vec2(-0.052, 0.0), 0.004)
    );
    glyph = max(
      glyph,
      bandSegment(point, vec2(0.052, 0.0), vec2(0.095, 0.0), 0.004)
    );
    glyph = max(
      glyph,
      bandSegment(point, vec2(0.0, -0.082), vec2(0.0, -0.052), 0.004)
    );
    glyph = max(
      glyph,
      bandSegment(point, vec2(0.0, 0.052), vec2(0.0, 0.082), 0.004)
    );
  } else if (variant < 4.5) {
    // Major Arcana 抽象三角徽記。
    glyph = max(
      bandSegment(point, vec2(0.0, 0.078), vec2(0.095, -0.068), 0.005),
      bandSegment(point, vec2(0.095, -0.068), vec2(-0.095, -0.068), 0.005)
    );
    glyph = max(
      glyph,
      bandSegment(point, vec2(-0.095, -0.068), vec2(0.0, 0.078), 0.005)
    );
    glyph = max(glyph, bandDot(point - vec2(0.0, -0.016), 0.012));
  } else {
    // 中央儀式菱形。
    glyph = max(
      bandSegment(point, vec2(0.0, 0.082), vec2(0.09, 0.0), 0.005),
      bandSegment(point, vec2(0.09, 0.0), vec2(0.0, -0.082), 0.005)
    );
    glyph = max(
      glyph,
      bandSegment(point, vec2(0.0, -0.082), vec2(-0.09, 0.0), 0.005)
    );
    glyph = max(
      glyph,
      bandSegment(point, vec2(-0.09, 0.0), vec2(0.0, 0.082), 0.005)
    );
    glyph = max(glyph, bandRing(point, 0.024, 0.004));
  }
  return clamp(glyph, 0.0, 1.0);
}
float mbtiGlyph(vec2 point, float variant) {
  float glyph = 0.0;
  if (variant < 0.5) {
    // E：三條規則橫槽。
    glyph = bandSegment(point, vec2(-0.075, -0.072), vec2(-0.075, 0.072), 0.006);
    glyph = max(glyph, bandSegment(point, vec2(-0.075, 0.07), vec2(0.08, 0.07), 0.006));
    glyph = max(glyph, bandSegment(point, vec2(-0.075, 0.0), vec2(0.055, 0.0), 0.006));
    glyph = max(glyph, bandSegment(point, vec2(-0.075, -0.07), vec2(0.08, -0.07), 0.006));
  } else if (variant < 1.5) {
    // I 與節點。
    glyph = bandSegment(point, vec2(0.0, -0.072), vec2(0.0, 0.072), 0.006);
    glyph = max(glyph, bandSegment(point, vec2(-0.06, 0.072), vec2(0.06, 0.072), 0.006));
    glyph = max(glyph, bandSegment(point, vec2(-0.06, -0.072), vec2(0.06, -0.072), 0.006));
  } else if (variant < 2.5) {
    // N／S：對立維度成對出現。
    glyph = max(
      bandSegment(point, vec2(-0.14, -0.065), vec2(-0.14, 0.065), 0.0048),
      bandSegment(point, vec2(-0.035, -0.065), vec2(-0.035, 0.065), 0.0048)
    );
    glyph = max(glyph, bandSegment(point, vec2(-0.14, 0.065), vec2(-0.035, -0.065), 0.0048));
    glyph = max(glyph, bandSegment(point, vec2(0.025, 0.06), vec2(0.135, 0.06), 0.0048));
    glyph = max(glyph, bandSegment(point, vec2(0.025, 0.06), vec2(0.025, 0.0), 0.0048));
    glyph = max(glyph, bandSegment(point, vec2(0.025, 0.0), vec2(0.135, 0.0), 0.0048));
    glyph = max(glyph, bandSegment(point, vec2(0.135, 0.0), vec2(0.135, -0.06), 0.0048));
    glyph = max(glyph, bandSegment(point, vec2(0.025, -0.06), vec2(0.135, -0.06), 0.0048));
  } else if (variant < 3.5) {
    // T／F：判斷維度。
    glyph = max(
      bandSegment(point, vec2(-0.15, 0.065), vec2(-0.035, 0.065), 0.005),
      bandSegment(point, vec2(-0.092, 0.065), vec2(-0.092, -0.065), 0.005)
    );
    glyph = max(glyph, bandSegment(point, vec2(0.035, -0.065), vec2(0.035, 0.065), 0.005));
    glyph = max(glyph, bandSegment(point, vec2(0.035, 0.065), vec2(0.145, 0.065), 0.005));
    glyph = max(glyph, bandSegment(point, vec2(0.035, 0.0), vec2(0.12, 0.0), 0.005));
  } else if (variant < 4.5) {
    // J／P：生活方式維度。
    glyph = bandSegment(point, vec2(-0.1, 0.065), vec2(-0.1, -0.04), 0.005);
    glyph = max(glyph, bandSegment(point, vec2(-0.1, -0.04), vec2(-0.14, -0.065), 0.005));
    glyph = max(glyph, bandSegment(point, vec2(-0.14, -0.065), vec2(-0.17, -0.035), 0.005));
    glyph = max(glyph, bandSegment(point, vec2(0.02, -0.065), vec2(0.02, 0.065), 0.005));
    glyph = max(glyph, bandSegment(point, vec2(0.02, 0.065), vec2(0.115, 0.065), 0.005));
    glyph = max(glyph, bandSegment(point, vec2(0.115, 0.065), vec2(0.145, 0.025), 0.005));
    glyph = max(glyph, bandSegment(point, vec2(0.145, 0.025), vec2(0.115, -0.012), 0.005));
    glyph = max(glyph, bandSegment(point, vec2(0.115, -0.012), vec2(0.02, -0.012), 0.005));
  } else {
    // 模組節點。
    glyph = max(
      bandBox(point - vec2(-0.075, 0.0), vec2(0.03, 0.03), 0.0045),
      bandBox(point - vec2(0.075, 0.0), vec2(0.03, 0.03), 0.0045)
    );
    glyph = max(glyph, bandSegment(point, vec2(-0.04, 0.0), vec2(0.04, 0.0), 0.004));
  }
  return clamp(glyph, 0.0, 1.0);
}
float humanDesignGlyph(vec2 point, float variant) {
  float glyph = 0.0;
  if (variant < 0.5) {
    // Gate 點位與連續 Channel。
    glyph = max(
      bandRing(point - vec2(-0.105, 0.0), 0.019, 0.004),
      bandRing(point - vec2(0.105, 0.0), 0.019, 0.004)
    );
    glyph = max(glyph, bandSegment(point, vec2(-0.083, 0.0), vec2(0.083, 0.0), 0.004));
  } else if (variant < 1.5) {
    // 九中心抽象菱形。
    glyph = max(
      bandSegment(point, vec2(0.0, 0.075), vec2(0.075, 0.0), 0.004),
      bandSegment(point, vec2(0.075, 0.0), vec2(0.0, -0.075), 0.004)
    );
    glyph = max(glyph, bandSegment(point, vec2(0.0, -0.075), vec2(-0.075, 0.0), 0.004));
    glyph = max(glyph, bandSegment(point, vec2(-0.075, 0.0), vec2(0.0, 0.075), 0.004));
    glyph = max(glyph, bandDot(point, 0.012));
  } else if (variant < 2.5) {
    // 三中心能量路徑。
    glyph = max(
      bandRing(point - vec2(-0.1, 0.04), 0.016, 0.0038),
      bandRing(point - vec2(0.0, -0.04), 0.016, 0.0038)
    );
    glyph = max(glyph, bandRing(point - vec2(0.1, 0.04), 0.016, 0.0038));
    glyph = max(glyph, bandSegment(point, vec2(-0.083, 0.033), vec2(-0.015, -0.033), 0.0038));
    glyph = max(glyph, bandSegment(point, vec2(0.015, -0.033), vec2(0.083, 0.033), 0.0038));
  } else if (variant < 3.5) {
    // Channel 雙線。
    glyph = max(
      bandSegment(point, vec2(-0.13, 0.028), vec2(0.13, 0.028), 0.0036),
      bandSegment(point, vec2(-0.13, -0.028), vec2(0.13, -0.028), 0.0036)
    );
    glyph = max(glyph, bandDot(point - vec2(-0.13, 0.0), 0.011));
    glyph = max(glyph, bandDot(point - vec2(0.13, 0.0), 0.011));
  } else if (variant < 4.5) {
    // 幾何中心節點。
    glyph = max(
      bandBox(point, vec2(0.075, 0.055), 0.004),
      bandDot(point, 0.013)
    );
    glyph = max(glyph, bandSegment(point, vec2(-0.075, 0.0), vec2(0.075, 0.0), 0.0035));
  } else {
    // 交會能量路徑。
    glyph = max(
      bandSegment(point, vec2(-0.13, -0.055), vec2(0.0, 0.0), 0.004),
      bandSegment(point, vec2(-0.13, 0.055), vec2(0.0, 0.0), 0.004)
    );
    glyph = max(glyph, bandSegment(point, vec2(0.0, 0.0), vec2(0.13, 0.0), 0.004));
    glyph = max(glyph, bandRing(point, 0.018, 0.004));
  }
  return clamp(glyph, 0.0, 1.0);
}
float ziweiGlyph(vec2 point, float variant) {
  float glyph = 0.0;
  if (variant < 0.5) {
    // 印章式框線。
    glyph = bandBox(point, vec2(0.105, 0.075), 0.0055);
    glyph = max(glyph, bandSegment(point, vec2(-0.055, -0.04), vec2(0.055, 0.04), 0.005));
  } else if (variant < 1.5) {
    // 宮位刻度。
    glyph = bandSegment(point, vec2(-0.13, 0.0), vec2(0.13, 0.0), 0.0045);
    glyph = max(glyph, bandSegment(point, vec2(-0.09, -0.055), vec2(-0.09, 0.055), 0.0045));
    glyph = max(glyph, bandSegment(point, vec2(0.0, -0.075), vec2(0.0, 0.075), 0.0045));
    glyph = max(glyph, bandSegment(point, vec2(0.09, -0.055), vec2(0.09, 0.055), 0.0045));
  } else if (variant < 2.5) {
    // 五行抽象節點。
    glyph = bandRing(point, 0.05, 0.005);
    glyph = max(glyph, bandSegment(point, vec2(-0.11, 0.0), vec2(0.11, 0.0), 0.004));
    glyph = max(glyph, bandSegment(point, vec2(0.0, -0.082), vec2(0.0, 0.082), 0.004));
  } else if (variant < 3.5) {
    // 天干地支式粗細節奏。
    glyph = max(
      bandSegment(point, vec2(-0.1, 0.055), vec2(0.1, 0.055), 0.0055),
      bandSegment(point, vec2(-0.075, 0.0), vec2(0.075, 0.0), 0.0045)
    );
    glyph = max(glyph, bandSegment(point, vec2(0.0, 0.075), vec2(0.0, -0.075), 0.0055));
    glyph = max(glyph, bandSegment(point, vec2(-0.1, -0.055), vec2(0.1, -0.055), 0.0055));
  } else if (variant < 4.5) {
    // 時序節點。
    glyph = max(
      bandDot(point - vec2(-0.1, 0.0), 0.016),
      bandDot(point, 0.016)
    );
    glyph = max(glyph, bandDot(point - vec2(0.1, 0.0), 0.016));
    glyph = max(glyph, bandSegment(point, vec2(-0.082, 0.0), vec2(-0.018, 0.0), 0.004));
    glyph = max(glyph, bandSegment(point, vec2(0.018, 0.0), vec2(0.082, 0.0), 0.004));
  } else {
    // 宮盤同心框。
    glyph = max(
      bandBox(point, vec2(0.105, 0.075), 0.0045),
      bandBox(point, vec2(0.06, 0.042), 0.004)
    );
    glyph = max(glyph, bandDot(point, 0.011));
  }
  return clamp(glyph, 0.0, 1.0);
}
float bandThemeGlyph(vec2 point, float variant, float style) {
  if (style < 0.5) return constellationGlyph(point, variant);
  if (style < 1.5) return tarotGlyph(point, variant);
  if (style < 2.5) return mbtiGlyph(point, variant);
  if (style < 3.5) return humanDesignGlyph(point, variant);
  return ziweiGlyph(point, variant);
}
float bandMarks(vec2 uv, float style) {
  float u = fract(uv.x);
  float lane = uv.y - 0.5;
  float cellCount = 24.0;
  float shiftedU = fract(u + style * 0.009);
  float cellIndex = floor(shiftedU * cellCount);
  float localU = fract(shiftedU * cellCount) - 0.5;
  float randomValue = fract(
    sin((cellIndex + style * 17.0) * 12.9898) * 43758.5453
  );
  float densityThreshold =
    style < 0.5 ? 0.14 :
    style < 1.5 ? 0.12 :
    style < 2.5 ? 0.06 :
    style < 3.5 ? 0.1 :
    0.08;
  float sparseSlot = step(densityThreshold, randomValue);
  float variant = floor(
    fract(sin((cellIndex + style * 7.0) * 8.173) * 15731.743) * 6.0
  );
  vec2 glyphPoint = vec2(localU * 0.88, lane * 0.78);
  float glyph = bandThemeGlyph(glyphPoint, variant, style);
  float connectorThreshold =
    style < 0.5 ? 0.72 :
    style < 1.5 ? 0.88 :
    style < 2.5 ? 0.58 :
    style < 3.5 ? 0.46 :
    0.64;
  float connectorWeight =
    style < 0.5 ? 0.34 :
    style < 1.5 ? 0.18 :
    style < 2.5 ? 0.42 :
    style < 3.5 ? 0.5 :
    0.28;
  float connector =
    bandLine(lane, style < 2.5 ? 0.0048 : 0.0058) *
    step(connectorThreshold, randomValue) *
    (1.0 - smoothstep(0.36, 0.48, abs(localU)));
  return clamp(
    max(glyph * sparseSlot, connector * connectorWeight),
    0.0,
    1.0
  );
}
float bandFlowMask(float u, float flow) {
  float distanceToPulse = abs(fract(u - flow + 0.5) - 0.5);
  return 1.0 - smoothstep(0.035, 0.14, distanceToPulse);
}
float bandSymbolChaseMask(float u, float flow, float direction) {
  float cellCount = 24.0;
  float symbolCenter =
    (floor(fract(u) * cellCount) + 0.5) / cellCount;
  float signedDistance = fract(
    (symbolCenter - flow) * direction + 0.5
  ) - 0.5;
  float fadeIn = 1.0 - smoothstep(
    0.012,
    0.075,
    signedDistance
  );
  float fadeOut = 1.0 - smoothstep(
    0.025,
    0.19,
    -signedDistance
  );
  return fadeIn * fadeOut;
}
float bandEnergyMask(
  float u,
  float flow,
  float pulseCount,
  float direction
) {
  float energy = bandSymbolChaseMask(u, flow, direction);
  if (pulseCount > 1.5) {
    energy = max(
      energy,
      bandSymbolChaseMask(u, flow + 0.5, direction)
    );
  }
  if (pulseCount > 2.5) {
    energy = max(
      energy,
      bandSymbolChaseMask(u, flow + 0.337, direction)
    );
  }
  if (pulseCount > 3.5) {
    energy = max(
      energy,
      bandSymbolChaseMask(u, flow + 0.581, direction)
    );
  }
  if (pulseCount > 4.5) {
    energy = max(
      energy,
      bandSymbolChaseMask(u, flow + 0.793, direction)
    );
  }
  return energy;
}
void main() {`,
      )
      .replace(
        "#include <roughnessmap_fragment>",
        `#include <roughnessmap_fragment>
roughnessFactor = clamp(
  roughnessFactor +
    pantheonMark * uMarkRoughnessDelta * (0.65 + uMarkDepth) +
    pantheonReliefEdge * 0.018 -
    pantheonLitMark * uFlowIntensity * 3.2 -
    pantheonMark * pantheonHoverSweep * uHoverSweepIntensity * 3.4,
  0.12,
  1.0
);`,
      )
      .replace(
        "#include <color_fragment>",
        `#include <color_fragment>
float pantheonStyleWidthRamp = smoothstep(
  0.04,
  0.96,
  clamp(vRibbonUv.y, 0.0, 1.0)
);
float pantheonStyleOrbitRamp =
  0.5 +
  0.5 * sin(vRibbonUv.x * 6.28318530718 + 0.72);
float pantheonStyleGradientPhase = clamp(
  mix(pantheonStyleWidthRamp, pantheonStyleOrbitRamp, 0.22),
  0.0,
  1.0
);
vec3 pantheonStyleGradient = mix(
  uStyleGradientStart,
  uStyleGradientEnd,
  pantheonStyleGradientPhase
);
diffuseColor.rgb = mix(
  diffuseColor.rgb,
  pantheonStyleGradient,
  uStyleGradientStrength * uStyleEnabled
);
float pantheonStyleLuma = dot(
  diffuseColor.rgb,
  vec3(0.2126, 0.7152, 0.0722)
);
diffuseColor.rgb = mix(
  diffuseColor.rgb,
  mix(
    vec3(pantheonStyleLuma),
    diffuseColor.rgb,
    uStyleThemeSaturation
  ) * uStyleThemeBrightness,
  uStyleEnabled
);
float pantheonMarkPattern = vRibbonFaceType < 1.5
  ? bandMarks(vRibbonUv, uMarkStyle)
  : 0.0;
float pantheonMark = pantheonMarkPattern * uMarkOpacity;
float pantheonEnergy = vRibbonFaceType < 1.5
  ? bandEnergyMask(
      vRibbonUv.x,
      uBandFlow,
      uEnergyPulseCount,
      uEnergyDirection
    )
  : 0.0;
float pantheonHoverSweep = vRibbonFaceType < 1.5
  ? bandFlowMask(vRibbonUv.x, uHoverSweep)
  : 0.0;
float pantheonLitMark = pantheonMarkPattern * pantheonEnergy;
vec2 pantheonReliefOffset = vec2(0.0011, 0.01);
float pantheonReliefLight = vRibbonFaceType < 1.5
  ? max(
      bandMarks(
        vRibbonUv - pantheonReliefOffset,
        uMarkStyle
      ) - pantheonMarkPattern,
      0.0
    ) * uMarkOpacity
  : 0.0;
float pantheonReliefShadow = vRibbonFaceType < 1.5
  ? max(
      bandMarks(
        vRibbonUv + pantheonReliefOffset,
        uMarkStyle
      ) - pantheonMarkPattern,
      0.0
    ) * uMarkOpacity
  : 0.0;
float pantheonReliefEdge = max(
  pantheonReliefLight,
  pantheonReliefShadow
);
vec3 pantheonBandMetalColor = diffuseColor.rgb;
vec3 pantheonReliefTopColor = mix(
  pantheonBandMetalColor,
  uMarkColor,
  0.1
);
float pantheonReliefTopMix = pantheonMark * 0.54;
diffuseColor.rgb = mix(
  diffuseColor.rgb,
  pantheonReliefTopColor,
  pantheonReliefTopMix
);
float pantheonMovingLightWeight = clamp(
  pantheonLitMark * uFlowIntensity * 2.8,
  0.0,
  0.82
);
vec3 pantheonMovingLightColor = mix(
  pantheonBandMetalColor,
  uMarkColor,
  0.16
);
diffuseColor.rgb = mix(
  diffuseColor.rgb,
  pantheonMovingLightColor,
  pantheonMovingLightWeight
);
vec3 pantheonReliefHighlightColor = mix(
  pantheonBandMetalColor,
  uMarkColor,
  0.1
);
diffuseColor.rgb +=
  pantheonReliefHighlightColor * pantheonReliefLight * 0.072;
diffuseColor.rgb *=
  1.0 - pantheonReliefShadow * 0.052;`,
      )
      .replace(
        "#include <normal_fragment_maps>",
        `#include <normal_fragment_maps>
if (vRibbonFaceType < 1.5 && uMarkDepth > 0.0) {
  float pantheonDu = 0.001;
  float pantheonDv = 0.0065;
  float pantheonGradientU =
    bandMarks(
      vRibbonUv + vec2(pantheonDu, 0.0),
      uMarkStyle
    ) -
    bandMarks(
      vRibbonUv - vec2(pantheonDu, 0.0),
      uMarkStyle
    );
  float pantheonGradientV =
    bandMarks(
      vRibbonUv + vec2(0.0, pantheonDv),
      uMarkStyle
    ) -
    bandMarks(
      vRibbonUv - vec2(0.0, pantheonDv),
      uMarkStyle
    );
  vec3 pantheonReliefNormal =
    vRibbonTangent * pantheonGradientU +
    vRibbonSide * pantheonGradientV;
  normal = normalize(
    normal - pantheonReliefNormal * uMarkDepth * 5.0
  );
}`,
      )
      .replace(
        "#include <metalnessmap_fragment>",
        `#include <metalnessmap_fragment>
metalnessFactor = clamp(
  metalnessFactor + pantheonMark * uMarkMetalnessDelta,
  0.0,
  1.0
);`,
      )
      .replace(
        "#include <emissivemap_fragment>",
        `#include <emissivemap_fragment>
totalEmissiveRadiance +=
  uMarkColor * pantheonMark * uMarkEmissive;
totalEmissiveRadiance +=
  pantheonStyleGradient *
  uStyleEmissiveLift *
  uStyleEnabled;`,
      )
      .replace(
        "#include <lights_fragment_end>",
        `#include <lights_fragment_end>
float pantheonSurfaceLightMask =
  pantheonMarkPattern * (
    pantheonEnergy * uFlowIntensity +
    pantheonHoverSweep * uHoverSweepIntensity
  );
vec3 pantheonSurfaceLightColor = mix(
  diffuseColor.rgb,
  uMarkColor,
  0.68
);
reflectedLight.directDiffuse +=
  pantheonSurfaceLightColor * pantheonSurfaceLightMask * 0.46;
reflectedLight.indirectSpecular +=
  pantheonSurfaceLightColor * pantheonSurfaceLightMask * 0.54;
vec3 pantheonPhysicalSpecular =
  reflectedLight.directSpecular + reflectedLight.indirectSpecular;
float pantheonWrappedDistance = abs(
  fract(vRibbonUv.x - uHighlightOffset + 0.5) - 0.5
);
float pantheonHighlightMask = exp(
  -pow(
    pantheonWrappedDistance / max(uHighlightWidth, 0.001),
    2.0
  )
);
float pantheonCoreDistance = length(vBandWorldPosition);
float pantheonCoreProximity =
  1.0 - smoothstep(
    uCoreSuppressInner,
    uCoreSuppressOuter,
    pantheonCoreDistance
  );
float pantheonSpecularSuppression =
  1.0 - pantheonCoreProximity * uCenterSuppression;
float pantheonNdotV = abs(
  dot(normalize(normal), normalize(vViewPosition))
);
float pantheonGrazing = pow(
  clamp(1.0 - pantheonNdotV, 0.0, 1.0),
  uGrazingPower
);
float pantheonHighlightResponse = mix(
  0.28,
  1.0 + uHighlightStrength,
  pantheonHighlightMask
);
float pantheonGrazingResponse =
  mix(1.0, uGrazingGain, pantheonGrazing);
float pantheonSpecularScale =
  uSpecularGain *
  pantheonHighlightResponse *
  pantheonSpecularSuppression *
  pantheonGrazingResponse;
float pantheonBasePeak = max(
  diffuseColor.r,
  max(diffuseColor.g, diffuseColor.b)
);
vec3 pantheonBaseHue =
  diffuseColor.rgb / max(pantheonBasePeak, 0.001);
vec3 pantheonStudioWhite = vec3(0.98, 0.985, 1.0);
vec3 pantheonTintedReflection = mix(
  pantheonStudioWhite,
  pantheonBaseHue,
  0.72
);
vec3 pantheonSpecularTint = mix(
  pantheonStudioWhite,
  pantheonTintedReflection,
  uReflectionTintAmount
);
vec3 pantheonLinkedDirect =
  reflectedLight.directSpecular *
  pantheonSpecularScale *
  pantheonSpecularTint;
vec3 pantheonLinkedIndirect =
  reflectedLight.indirectSpecular *
  pantheonSpecularScale *
  pantheonSpecularTint;
vec3 pantheonLinkedSpecular =
  pantheonLinkedDirect + pantheonLinkedIndirect;
float pantheonLinkedLuminance = dot(
  pantheonLinkedSpecular,
  vec3(0.2126, 0.7152, 0.0722)
);
float pantheonCompressedLuminance =
  pantheonLinkedLuminance /
  (1.0 + uSpecularShoulder * pantheonLinkedLuminance);
float pantheonCompressionScale =
  pantheonCompressedLuminance /
  max(pantheonLinkedLuminance, 0.0001);
pantheonLinkedDirect *= pantheonCompressionScale;
pantheonLinkedIndirect *= pantheonCompressionScale;
pantheonLinkedSpecular =
  pantheonLinkedDirect + pantheonLinkedIndirect;
reflectedLight.directSpecular = mix(
  reflectedLight.directSpecular,
  pantheonLinkedDirect,
  uReflectionEnabled
);
reflectedLight.indirectSpecular = mix(
  reflectedLight.indirectSpecular,
  pantheonLinkedIndirect,
  uReflectionEnabled
);
float pantheonDarkResponse =
  uDarkSideLift *
  (0.62 + 0.22 * pantheonGrazing) *
  uReflectionEnabled;
vec3 pantheonDarkSideContribution =
  diffuseColor.rgb * pantheonDarkResponse;
reflectedLight.indirectDiffuse +=
  pantheonDarkSideContribution;

vec3 pantheonStyleNormal = normalize(normal);
vec3 pantheonStyleView = normalize(vViewPosition);
float pantheonStyleNdotL = dot(
  pantheonStyleNormal,
  normalize(uStyleLightDirection)
);
float pantheonStyleWrapDiffuse = clamp(
  (pantheonStyleNdotL + uStyleWrap) /
    (1.0 + uStyleWrap),
  0.0,
  1.0
);
float pantheonStyleFacing = abs(
  dot(pantheonStyleNormal, pantheonStyleView)
);
float pantheonStyleFaceRamp = smoothstep(
  0.08,
  0.92,
  pantheonStyleFacing
);
float pantheonStyleGrazing = pow(
  clamp(1.0 - pantheonStyleFacing, 0.0, 1.0),
  2.2
);
float pantheonStyleDepth = smoothstep(
  -0.82,
  0.82,
  dot(
    vBandWorldPosition,
    normalize(cameraPosition)
  )
);
float pantheonStyleDepthBrightness = mix(
  uStyleBackBrightness,
  1.0,
  pantheonStyleDepth
);
float pantheonStyleViewTone = mix(
  1.0 - uStyleViewGradientStrength,
  1.0 + uStyleViewGradientStrength * 0.34,
  pantheonStyleFaceRamp
);
float pantheonStyleBackFaceTone =
  gl_FrontFacing ? 1.0 : 0.94;
float pantheonStyleBrightness =
  mix(
    1.0,
    pantheonStyleDepthBrightness *
      pantheonStyleViewTone *
      pantheonStyleBackFaceTone,
    uStyleEnabled
  );
reflectedLight.directDiffuse *= pantheonStyleBrightness;
reflectedLight.indirectDiffuse *= pantheonStyleBrightness;
reflectedLight.directDiffuse *= mix(
  1.0,
  mix(0.92, 1.0, uStyleHighlightStrength),
  uStyleEnabled
);
reflectedLight.directSpecular *= mix(
  1.0,
  mix(0.94, 1.0, pantheonStyleDepthBrightness),
  uStyleEnabled
);
reflectedLight.indirectSpecular *= mix(
  1.0,
  mix(0.92, 1.0, pantheonStyleDepthBrightness),
  uStyleEnabled
);
vec3 pantheonStyleSpecularTint = mix(
  vec3(1.0),
  pantheonStyleGradient,
  uStyleSpecularTintStrength
);
reflectedLight.directSpecular *= mix(
  vec3(1.0),
  pantheonStyleSpecularTint,
  uStyleEnabled
);
reflectedLight.indirectSpecular *= mix(
  vec3(1.0),
  pantheonStyleSpecularTint,
  uStyleEnabled
);
float pantheonIndirectSpecularLuma = dot(
  reflectedLight.indirectSpecular,
  vec3(0.2126, 0.7152, 0.0722)
);
if (
  uIndirectSpecularContrast > 1.0001 &&
  pantheonIndirectSpecularLuma > 0.0
) {
  float pantheonIndirectCentered =
    pantheonIndirectSpecularLuma - uIndirectSpecularPivot;
  float pantheonIndirectExpandedLinear =
    uIndirectSpecularPivot +
    pantheonIndirectCentered * uIndirectSpecularContrast;
  float pantheonIndirectToeWidth =
    max(uIndirectSpecularPivot * 0.18, 0.02);
  float pantheonIndirectExpandedToe =
    0.5 * (
      pantheonIndirectExpandedLinear +
      sqrt(
        pantheonIndirectExpandedLinear *
        pantheonIndirectExpandedLinear +
        pantheonIndirectToeWidth *
        pantheonIndirectToeWidth *
        0.04
      )
    );
  float pantheonIndirectToeGate = smoothstep(
    0.0,
    uIndirectSpecularPivot * 0.45,
    pantheonIndirectSpecularLuma
  );
  float pantheonIndirectExpanded =
    pantheonIndirectExpandedToe * pantheonIndirectToeGate;
  float pantheonIndirectShoulder = smoothstep(
    uIndirectSpecularPivot * 1.8,
    uIndirectSpecularPivot * 4.5,
    pantheonIndirectSpecularLuma
  );
  pantheonIndirectExpanded = mix(
    pantheonIndirectExpanded,
    pantheonIndirectSpecularLuma +
      (
        pantheonIndirectExpanded -
        pantheonIndirectSpecularLuma
      ) * 0.55,
    pantheonIndirectShoulder
  );
  reflectedLight.indirectSpecular *=
    pantheonIndirectExpanded /
    max(pantheonIndirectSpecularLuma, 1e-5);
}
float pantheonDirectSpecularLuma = dot(
  reflectedLight.directSpecular,
  vec3(0.2126, 0.7152, 0.0722)
);
if (
  uDirectSpecularCompressionShoulder > 0.0 &&
  pantheonDirectSpecularLuma > 0.0
) {
  float pantheonCompressedDirectSpecularLuma =
    pantheonDirectSpecularLuma /
    (
      1.0 +
      pantheonDirectSpecularLuma /
      uDirectSpecularCompressionShoulder
    );
  reflectedLight.directSpecular *=
    pantheonCompressedDirectSpecularLuma /
    max(pantheonDirectSpecularLuma, 1e-5);
}
vec3 pantheonStyleSoftLight =
  pantheonStyleGradient *
  (
    pantheonStyleWrapDiffuse * uStyleWrapStrength +
    uStyleColorLift * (0.72 + pantheonStyleFaceRamp * 0.28) +
    pantheonStyleGrazing * uStyleRimStrength
  ) *
  pantheonStyleDepthBrightness *
  uStyleEnabled *
  0.62;
reflectedLight.indirectDiffuse += pantheonStyleSoftLight;`,
      )
      .replace(
        "#include <tonemapping_fragment>",
        `#include <tonemapping_fragment>`,
      )
      .replace(
        "#include <dithering_fragment>",
        `if (uRibbonDebugMode > 0.5) {
  vec3 debugColor = diffuseColor.rgb;
  if (uRibbonDebugMode < 1.5) {
    debugColor = gl_FrontFacing
      ? vec3(0.18, 0.78, 0.42)
      : vec3(0.58, 0.28, 0.82);
  } else if (uRibbonDebugMode < 2.5) {
    debugColor = abs(normalize(vNormal));
  } else if (uRibbonDebugMode < 3.5) {
    debugColor =
      abs(normalize(vRibbonTangent)) * 0.45 +
      abs(normalize(vRibbonSide)) * 0.35 +
      abs(normalize(vRibbonSurfaceNormal)) * 0.20;
  } else if (uRibbonDebugMode < 4.5) {
    debugColor = vRibbonFaceType < 1.5
      ? vec3(0.18, 0.62, 0.82)
      : vRibbonFaceType < 1.5
        ? vec3(0.92, 0.76, 0.22)
        : vec3(0.92, 0.38, 0.18);
  } else if (uRibbonDebugMode < 5.5) {
    vec2 grid = floor(vRibbonUv * vec2(24.0, 6.0));
    float checker = mod(grid.x + grid.y, 2.0);
    debugColor = mix(
      vec3(0.12, 0.16, 0.20),
      vec3(0.78, 0.84, 0.88),
      checker
    );
  } else if (uRibbonDebugMode < 6.5) {
    debugColor = vec3(roughnessFactor);
  } else if (uRibbonDebugMode < 7.5) {
    debugColor = vec3(metalnessFactor);
  } else if (uRibbonDebugMode < 8.5) {
    debugColor = mix(vec3(0.025), uMarkColor, pantheonMark);
  } else if (uRibbonDebugMode < 9.5) {
    float pantheonFlowDebugMask = smoothstep(
      0.035,
      0.30,
      pantheonMarkPattern * (
        pantheonEnergy + pantheonHoverSweep
      )
    );
    debugColor = mix(
      vec3(0.008),
      mix(uMarkColor, vec3(1.0), 0.22),
      pantheonFlowDebugMask
    );
  } else if (uRibbonDebugMode < 10.5) {
    debugColor = vRibbonFaceType > 0.5 && vRibbonFaceType < 1.5
      ? vec3(0.92, 0.76, 0.22)
      : vec3(0.10);
  } else if (uRibbonDebugMode < 11.5) {
    debugColor = pantheonLinkedSpecular;
  } else if (uRibbonDebugMode < 12.5) {
    debugColor = vec3(pantheonHighlightMask);
  } else if (uRibbonDebugMode < 13.5) {
    debugColor = vec3(
      pantheonCoreProximity,
      pantheonSpecularSuppression,
      0.08
    );
  } else if (uRibbonDebugMode < 14.5) {
    debugColor = mix(
      vec3(0.025, 0.04, 0.08),
      vec3(0.2, 0.72, 0.96),
      pantheonGrazing
    );
  } else if (uRibbonDebugMode < 15.5) {
    debugColor =
      pantheonBaseHue * min(1.0, pantheonDarkResponse * 4.0);
  } else if (uRibbonDebugMode < 16.5) {
    float rotationPhase = fract(
      uReflectionRotation / 6.28318530718 + 0.5
    );
    debugColor = mix(
      uProfileColor * 0.34,
      uProfileColor,
      rotationPhase
    );
  } else if (uRibbonDebugMode < 17.5) {
    float displayLuminance = dot(
      gl_FragColor.rgb,
      vec3(0.2126, 0.7152, 0.0722)
    );
    debugColor =
      displayLuminance < 0.5
        ? mix(
            vec3(0.02, 0.04, 0.16),
            vec3(0.05, 0.82, 0.72),
            displayLuminance * 2.0
          )
        : mix(
            vec3(0.05, 0.82, 0.72),
            vec3(1.0, 0.08, 0.02),
            (displayLuminance - 0.5) * 2.0
          );
  } else if (uRibbonDebugMode < 18.5) {
    float displayLuminance = dot(
      gl_FragColor.rgb,
      vec3(0.2126, 0.7152, 0.0722)
    );
    debugColor = displayLuminance > 0.86
      ? vec3(1.0, 0.02, 0.0)
      : vec3(0.015);
  } else if (uRibbonDebugMode < 19.5) {
    debugColor = mix(
      uProfileColor * 0.22,
      uProfileColor,
      pantheonHighlightMask
    );
  } else {
    debugColor = vRibbonUv.y < 0.5
      ? pantheonPhysicalSpecular
      : pantheonLinkedSpecular;
  }
  gl_FragColor = vec4(debugColor, 1.0);
}
#include <dithering_fragment>`,
      );
    material.userData.shader = shader;
  };
  material.customProgramCacheKey = () => "pantheon-band-material-v3";
}

function createRuneMaterial(
  color: THREE.Color,
  phase: number,
): { material: THREE.ShaderMaterial; uniforms: RuneUniforms } {
  const uniforms: RuneUniforms = {
    width: { value: 0 },
    thickness: { value: RIBBON_THICKNESS + 0.0012 },
    twist: { value: 0 },
    debugMode: { value: 0 },
    flow: { value: phase },
    opacity: { value: 0 },
    color: { value: color.clone() },
  };
  const material = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    uniforms: {
      uRibbonWidth: uniforms.width,
      uRibbonThickness: uniforms.thickness,
      uMobiusTwist: uniforms.twist,
      uRuneFlow: uniforms.flow,
      uRuneOpacity: uniforms.opacity,
      uRuneColor: uniforms.color,
    },
    vertexShader: `
      attribute vec3 aCenterline;
      attribute vec3 aWidthOffset;
      attribute vec3 aThicknessOffset;
      attribute vec3 aTangent;
      attribute float aOrbitProgress;
      uniform float uRibbonWidth;
      uniform float uRibbonThickness;
      uniform float uMobiusTwist;
      varying float vOrbitProgress;
      varying float vWidthSide;
      void main() {
        float twistAngle =
          3.14159265359 * uMobiusTwist * aOrbitProgress;
        vec3 widthDirection =
          aWidthOffset * cos(twistAngle) +
          aThicknessOffset * sin(twistAngle);
        vec3 thicknessDirection =
          aThicknessOffset * cos(twistAngle) -
          aWidthOffset * sin(twistAngle);
        vec3 transformed =
          aCenterline +
          widthDirection * (uRibbonWidth * 0.5) +
          thicknessDirection * (uRibbonThickness * 0.5);
        vOrbitProgress = aOrbitProgress;
        vWidthSide = aWidthOffset.x + aWidthOffset.y + aWidthOffset.z;
        gl_Position =
          projectionMatrix * modelViewMatrix * vec4(transformed, 1.0);
      }
    `,
    fragmentShader: `
      uniform float uRuneFlow;
      uniform float uRuneOpacity;
      uniform vec3 uRuneColor;
      varying float vOrbitProgress;
      varying float vWidthSide;
      void main() {
        float lane = fract(vOrbitProgress * 24.0 - uRuneFlow);
        float bar = 1.0 - smoothstep(0.16, 0.28, abs(lane - 0.5));
        float notch =
          smoothstep(0.02, 0.14, abs(fract(vOrbitProgress * 48.0) - 0.5));
        float edge = smoothstep(0.02, 0.12, abs(vWidthSide));
        float alpha = bar * notch * edge * uRuneOpacity;
        if (alpha < 0.015) discard;
        gl_FragColor = vec4(uRuneColor, alpha);
      }
    `,
  });
  return { material, uniforms };
}

function displayColor(
  base: THREE.Color,
  brightness: number,
  saturation: number,
  monochrome: boolean,
) {
  if (monochrome) {
    return new THREE.Color(0xf2f1ec).multiplyScalar(brightness * 0.82);
  }
  const result = base.clone();
  const hsl = { h: 0, s: 0, l: 0 };
  result.getHSL(hsl);
  result.setHSL(
    hsl.h,
    THREE.MathUtils.clamp(hsl.s * saturation, 0, 1),
    THREE.MathUtils.clamp(hsl.l * brightness, 0.03, 0.88),
  );
  return result;
}

export function createPantheonMaterialPrototype(
  runtime: OrbitRuntime,
  options: {
    mobileQuality?: boolean;
    environmentMap?: THREE.Texture;
  } = {},
) {
  runtime.updateRibbonPrototype(
    PREBUILT_MAX_RIBBON_WIDTH,
    RIBBON_THICKNESS,
  );
  runtime.setMaterialInteractionMode();
  const nodes = runtime.getThemeNodes();
  const state = createPantheonInteractionState();
  const bindings = new Map<PantheonThemeId, ThemeBinding>();
  let monochrome = false;
  let paused = false;
  let reducedMotionPreview = false;
  let mobileQualityPreview = Boolean(options.mobileQuality);
  let environmentIntensity: number =
    PANTHEON_BAND_ENVIRONMENT_BASELINE.topBottom;
  let surfaceEnergyTime = 0;
  let reflectionCandidateId: ReflectionCandidateId =
    DEFAULT_REFLECTION_CANDIDATE;
  let styleMatchCandidateId: StyleMatchCandidateId =
    DEFAULT_STYLE_MATCH_CANDIDATE;
  let directSpecularCompressionCandidateId:
    DirectSpecularCompressionCandidateId = "candidate-a";
  let styleColorLiftCandidateId: StyleColorLiftCandidateId =
    "candidate-a";
  let humanDesignIndirectSpecularCandidateId:
    HumanDesignIndirectSpecularCandidateId = "candidate-a";
  let metalColorDensityCandidateId:
    MetalColorDensityCandidateId = "visual-target-v1";
  const desktopWidths = { ...DESKTOP_RIBBON_WIDTHS };
  const mobileWidths = { ...MOBILE_RIBBON_WIDTHS };
  const debug = {
    ribbonProgress: null as number | null,
    opacity: 1,
    speed: 1,
    brightness: 1,
    saturation: 1,
    showUV: false,
    showFrame: false,
    showSeam: false,
    showTubeLine: false,
    showRibbon: true,
    showBand: true,
    showCore: true,
    showPhase: false,
    validationMode: "material-v3" as keyof typeof VALIDATION_MODE,
    enableRunes: false,
    markOpacity: 1,
    markDepth: BAND_RUNE_SURFACE_CONFIG.reliefDepth,
    markRoughnessDelta: BAND_RUNE_SURFACE_CONFIG.roughnessTopDelta,
    markMetalnessDelta: BAND_RUNE_SURFACE_CONFIG.metalnessDelta,
    markEmissive: 0,
    flowIntensity: 1,
    metalHighlightStrength: DEFAULT_METAL_HIGHLIGHT_STRENGTH,
    edgeBrightness: 0.91,
    edgeRoughness: 0.1,
    flatMaterial: false,
    showTopBottom: true,
    showEdges: true,
    showBevel: true,
  };

  PANTHEON_THEME_CONFIGS.forEach((theme) => {
    const line = nodes.meshes.get(theme.orbitId)!;
    const ribbon = nodes.ribbonMeshes.get(theme.orbitId)!;
    const materialConfig = PANTHEON_MATERIAL_CONFIGS[theme.id];
    const reflectionCandidate =
      PANTHEON_REFLECTION_CANDIDATES[reflectionCandidateId];
    const reflectionProfile = reflectionCandidate.profiles[theme.id];
    const styleCandidate =
      PANTHEON_STYLE_MATCH_CANDIDATES[styleMatchCandidateId];
    const metalColorProfile =
      METAL_COLOR_DENSITY_CANDIDATES[
        metalColorDensityCandidateId
      ][theme.id];
    const baseColor = new THREE.Color(metalColorProfile.baseColor);
    const accentColor = new THREE.Color(materialConfig.accent);
    const lineMaterial = new THREE.MeshStandardMaterial({
      color: baseColor,
      emissive: baseColor,
      emissiveIntensity: 0,
      metalness: materialConfig.metalness,
      roughness: materialConfig.roughness,
      transparent: false,
      opacity: 1,
    });
    line.material = lineMaterial;

    const ribbonUniforms: RibbonUniforms = {
      width: {
        value: mobileQualityPreview
          ? MOBILE_RIBBON_WIDTHS.idle
          : DESKTOP_RIBBON_WIDTHS.idle,
      },
      thickness: { value: RIBBON_THICKNESS },
      twist: { value: 0 },
      debugMode: { value: 0 },
      markOpacity: {
        value: BAND_RUNE_SURFACE_CONFIG.idleMarkOpacity,
      },
      markDepth: { value: BAND_RUNE_SURFACE_CONFIG.reliefDepth },
      markRoughnessDelta: {
        value: BAND_RUNE_SURFACE_CONFIG.roughnessTopDelta,
      },
      markMetalnessDelta: {
        value: BAND_RUNE_SURFACE_CONFIG.metalnessDelta,
      },
      markEmissive: { value: 0 },
      flow: { value: theme.runePhase },
      flowIntensity: { value: 0 },
      energyPulseCount: {
        value: SURFACE_ENERGY_CONFIG[theme.id].pulseCount,
      },
      energyDirection: {
        value: SURFACE_ENERGY_CONFIG[theme.id].direction,
      },
      hoverSweep: { value: 1 },
      hoverSweepIntensity: { value: 0 },
      markStyle: { value: materialConfig.markStyle },
      markColor: { value: accentColor.clone() },
      reflectionEnabled: {
        value:
          !styleCandidate.enabled && reflectionCandidate.enabled ? 1 : 0,
      },
      highlightOffset: { value: reflectionProfile.highlightOffset },
      highlightWidth: { value: reflectionProfile.highlightWidth },
      highlightStrength: {
        value: reflectionProfile.highlightStrength,
      },
      specularGain: { value: reflectionProfile.specularGain },
      grazingGain: { value: reflectionProfile.grazingGain },
      darkSideLift: { value: reflectionProfile.darkSideLift },
      centerSuppression: {
        value: reflectionProfile.centerSuppression,
      },
      coreSuppressInner: {
        value: REFLECTION_CORE_SUPPRESSION.inner,
      },
      coreSuppressOuter: {
        value: REFLECTION_CORE_SUPPRESSION.outer,
      },
      grazingPower: {
        value: REFLECTION_CORE_SUPPRESSION.grazingPower,
      },
      specularShoulder: { value: reflectionCandidate.shoulder },
      directSpecularCompressionShoulder: {
        value:
          DIRECT_SPECULAR_COMPRESSION_SHOULDERS[
            directSpecularCompressionCandidateId
          ][theme.id] ?? 0,
      },
      indirectSpecularContrast: {
        value:
          theme.id === "human-design"
            ? HUMAN_DESIGN_INDIRECT_SPECULAR_CANDIDATES[
                humanDesignIndirectSpecularCandidateId
              ].contrast
            : 1,
      },
      indirectSpecularPivot: {
        value:
          HUMAN_DESIGN_INDIRECT_SPECULAR_CANDIDATES[
            humanDesignIndirectSpecularCandidateId
          ].pivot,
      },
      reflectionTintAmount: {
        value: reflectionCandidate.tintAmount,
      },
      reflectionRotation: {
        value: THREE.MathUtils.degToRad(
          reflectionProfile.reflectionRotation,
        ),
      },
      profileColor: { value: baseColor.clone() },
      styleEnabled: { value: styleCandidate.enabled ? 1 : 0 },
      styleGradientStart: {
        value: new THREE.Color(metalColorProfile.gradientStart),
      },
      styleGradientEnd: {
        value: new THREE.Color(metalColorProfile.gradientEnd),
      },
      styleGradientStrength: {
        value: styleCandidate.gradientStrength,
      },
      styleWrap: { value: styleCandidate.wrap },
      styleWrapStrength: { value: styleCandidate.wrapStrength },
      styleViewGradientStrength: {
        value: styleCandidate.viewGradientStrength,
      },
      styleRimStrength: { value: styleCandidate.rimStrength },
      styleSpecularTintStrength: {
        value: styleCandidate.specularTintStrength,
      },
      styleColorLift: {
        value: STYLE_COLOR_LIFT_CANDIDATES[styleColorLiftCandidateId],
      },
      styleEmissiveLift: { value: styleCandidate.emissiveLift },
      styleBackBrightness: {
        value:
          styleCandidate.themeBalance[theme.id].depthBackBrightness,
      },
      styleThemeBrightness: {
        value: styleCandidate.themeBalance[theme.id].brightness,
      },
      styleThemeSaturation: {
        value: metalColorProfile.saturation,
      },
      styleHighlightStrength: {
        value:
          styleCandidate.themeBalance[theme.id].highlightStrength,
      },
      styleLightDirection: {
        value: new THREE.Vector3(
          ...PANTHEON_STYLE_LIGHT_DIRECTION,
        ).normalize(),
      },
    };
    const ribbonMaterial = new THREE.MeshPhysicalMaterial({
      color: baseColor,
      emissive: baseColor,
      emissiveIntensity: 0,
      metalness: materialConfig.metalness,
      roughness: materialConfig.roughness,
      clearcoat: materialConfig.clearcoat,
      clearcoatRoughness: materialConfig.clearcoatRoughness,
      anisotropy: mobileQualityPreview ? 0 : materialConfig.anisotropy,
      anisotropyRotation: Math.PI / 2,
      envMap: options.environmentMap ?? null,
      envMapIntensity: materialConfig.envMapIntensity,
      transparent: false,
      opacity: 1,
      depthTest: true,
      depthWrite: true,
      side: THREE.DoubleSide,
    });
    const bevelMaterial = new THREE.MeshPhysicalMaterial({
      color: baseColor,
      emissive: baseColor,
      emissiveIntensity: 0,
      metalness: materialConfig.metalness,
      roughness: Math.max(0.18, materialConfig.roughness - 0.055),
      clearcoat: materialConfig.clearcoat,
      clearcoatRoughness: materialConfig.clearcoatRoughness,
      anisotropy: mobileQualityPreview ? 0 : materialConfig.anisotropy * 0.7,
      anisotropyRotation: Math.PI / 2,
      envMap: options.environmentMap ?? null,
      envMapIntensity: materialConfig.envMapIntensity * 1.08,
      transparent: false,
      opacity: 1,
      depthTest: true,
      depthWrite: true,
      side: THREE.DoubleSide,
    });
    const edgeMaterial = new THREE.MeshPhysicalMaterial({
      color: baseColor.clone().multiplyScalar(0.88),
      emissive: baseColor,
      emissiveIntensity: 0,
      metalness: materialConfig.metalness,
      roughness: Math.min(1, materialConfig.roughness + 0.09),
      clearcoat: materialConfig.clearcoat * 0.5,
      clearcoatRoughness: materialConfig.clearcoatRoughness,
      anisotropy: 0,
      envMap: options.environmentMap ?? null,
      envMapIntensity: materialConfig.envMapIntensity * 0.9,
      transparent: false,
      opacity: 1,
      depthTest: true,
      depthWrite: true,
      side: THREE.DoubleSide,
      polygonOffset: true,
      polygonOffsetFactor: 0.15,
      polygonOffsetUnits: 0.15,
    });
    for (const material of [
      ribbonMaterial,
      bevelMaterial,
      edgeMaterial,
    ]) {
      if (styleCandidate.enabled) {
        material.envMapRotation.set(0, 0, 0);
      } else {
        applyBandEnvironmentRotation(
          material,
          reflectionProfile.reflectionRotation,
        );
      }
    }
    configureRibbonMaterial(ribbonMaterial, ribbonUniforms);
    configureRibbonMaterial(bevelMaterial, ribbonUniforms);
    configureRibbonMaterial(edgeMaterial, ribbonUniforms);
    ribbon.material = [ribbonMaterial, bevelMaterial, edgeMaterial];
    ribbon.name = `PantheonBand.${theme.orbitId}`;
    ribbon.userData.publicRole = "pantheon-band";
    ribbon.visible = false;

    const runePrototype = createRuneMaterial(
      accentColor,
      theme.runePhase,
    );
    const rune = new THREE.Mesh(ribbon.geometry, runePrototype.material);
    rune.name = `RuneFlow.${theme.orbitId}`;
    rune.quaternion.copy(ribbon.quaternion);
    rune.scale.copy(ribbon.scale);
    rune.position.copy(ribbon.position);
    rune.visible = false;
    nodes.ribbonGroup.add(rune);

    bindings.set(theme.id, {
      id: theme.id,
      orbitId: theme.orbitId,
      line,
      ribbon,
      rune,
      lineMaterial,
      ribbonMaterial,
      bevelMaterial,
      edgeMaterial,
      ribbonUniforms,
      runeUniforms: runePrototype.uniforms,
      baseColor,
      accentColor,
      opacity: 0.82,
    });
  });

  function setHoveredTheme(themeId: PantheonThemeId | null) {
    state.hoveredTheme = state.selectedTheme ? null : themeId;
    state.transitionProgress = 0;
  }

  function selectTheme(themeId: PantheonThemeId | null) {
    state.selectedTheme = themeId;
    state.hoveredTheme = null;
    state.transitionProgress = 0;
  }

  function update(deltaSeconds: number) {
    if (!reducedMotionPreview && !paused) {
      surfaceEnergyTime += deltaSeconds * debug.speed;
    }
    const durationScale =
      reducedMotionPreview || paused ? 0 : INTERACTION_TIMING.hoverMs;
    state.transitionProgress = smoothToward(
      state.transitionProgress,
      1,
      deltaSeconds,
      durationScale,
    );
    PANTHEON_THEME_CONFIGS.forEach((theme) => {
      const binding = bindings.get(theme.id)!;
      const visualState = resolveOrbitVisualState(state, theme.id);
      const targets = visualTargets(visualState);
      const duration =
        reducedMotionPreview || paused
          ? 0
          : visualState === "Selected"
            ? INTERACTION_TIMING.selectedMs
            : visualState === "Hovered"
              ? INTERACTION_TIMING.hoverMs
              : INTERACTION_TIMING.selectedMs;
      state.ribbonProgress[theme.id] = smoothToward(
        state.ribbonProgress[theme.id],
        1,
        deltaSeconds,
        duration,
      );
      state.brightness[theme.id] = smoothToward(
        state.brightness[theme.id],
        targets.brightness * debug.brightness,
        deltaSeconds,
        duration,
      );
      state.saturation[theme.id] = smoothToward(
        state.saturation[theme.id],
        targets.saturation * debug.saturation,
        deltaSeconds,
        duration,
      );
      binding.opacity = smoothToward(
        binding.opacity,
        targets.opacity * debug.opacity,
        deltaSeconds,
        duration,
      );

      const widthProfile = mobileQualityPreview
        ? mobileWidths
        : desktopWidths;
      const width = widthProfile.idle;
      const selected = visualState === "Selected";
      const hovered = visualState === "Hovered";
      const markOpacity = debug.flatMaterial
        ? 0
        : debug.validationMode === "marks" ||
            debug.validationMode === "flow" ||
            debug.validationMode === "engraving-reveal"
          ? 0.82
          : selected
            ? BAND_RUNE_SURFACE_CONFIG.selectedMarkOpacity
            : hovered
              ? BAND_RUNE_SURFACE_CONFIG.hoveredMarkOpacity
              : visualState === "Background"
                ? BAND_RUNE_SURFACE_CONFIG.backgroundMarkOpacity
                : BAND_RUNE_SURFACE_CONFIG.idleMarkOpacity;
      binding.ribbonUniforms.width.value = width;
      binding.ribbonUniforms.thickness.value = RIBBON_THICKNESS;
      binding.ribbonUniforms.twist.value = 0;
      binding.ribbonUniforms.debugMode.value =
        VALIDATION_MODE[debug.validationMode];
      binding.ribbonUniforms.markOpacity.value =
        markOpacity * debug.markOpacity;
      binding.ribbonUniforms.markDepth.value = debug.markDepth;
      binding.ribbonUniforms.markRoughnessDelta.value =
        debug.markRoughnessDelta;
      binding.ribbonUniforms.markMetalnessDelta.value =
        debug.markMetalnessDelta;
      // 流水只逐個照亮凸起符文；不可讓整套符文一起變成 LED。
      binding.ribbonUniforms.markEmissive.value = 0;
      const energy = SURFACE_ENERGY_CONFIG[theme.id];
      const linearEnergyPhase =
        energy.cycleSeconds > 0
          ? (surfaceEnergyTime / energy.cycleSeconds) % 1
          : 0;
      const rhythmPhase =
        linearEnergyPhase +
        Math.sin(linearEnergyPhase * Math.PI * 2) *
          (energy.rhythmWarp / (Math.PI * 2));
      const energyStateWeight =
        visualState === "Background"
          ? 0.72
          : selected
            ? 1.18
            : hovered
              ? 1.1
              : 1;
      binding.ribbonUniforms.flowIntensity.value =
        reducedMotionPreview || paused
          ? 0
          : energy.intensity *
            energyStateWeight *
            (mobileQualityPreview ? 0.82 : 1) *
            debug.flowIntensity *
            0.4;
      binding.ribbonUniforms.energyPulseCount.value =
        reducedMotionPreview || paused ? 0 : energy.pulseCount;
      binding.ribbonUniforms.energyDirection.value = energy.direction;
      binding.ribbonUniforms.hoverSweep.value = 1;
      binding.ribbonUniforms.hoverSweepIntensity.value = 0;
      binding.ribbon.visible = debug.showBand;
      binding.ribbonMaterial.visible = debug.showTopBottom;
      binding.bevelMaterial.visible = debug.showBevel;
      binding.edgeMaterial.visible = debug.showEdges;
      binding.ribbonMaterial.opacity = 1;

      binding.runeUniforms.width.value = width;
      binding.runeUniforms.twist.value =
        state.mobiusTwistProgress[theme.id];
      binding.runeUniforms.opacity.value = 0;
      binding.rune.visible = false;
      // 符文固定黏在 Band UV；移動的是局部照明，不是圖樣本身。
      binding.runeUniforms.flow.value = theme.runePhase;
      binding.ribbonUniforms.flow.value =
        ((theme.runePhase + rhythmPhase * energy.direction) % 1 + 1) %
        1;

      const color = displayColor(
        binding.baseColor,
        state.brightness[theme.id] * (mobileQualityPreview ? 1.42 : 1),
        state.saturation[theme.id],
        monochrome,
      );
      if (mobileQualityPreview) {
        color.lerp(MOBILE_STUDIO_METAL_TINT, 0.05);
      }
      binding.lineMaterial.color.copy(color);
      binding.ribbonMaterial.color.copy(color);
      binding.bevelMaterial.color
        .copy(color)
        .lerp(binding.accentColor, 0.18);
      binding.edgeMaterial.color
        .copy(color)
        .lerp(binding.accentColor, 0.22)
        .multiplyScalar(debug.edgeBrightness);
      binding.lineMaterial.emissive.copy(binding.baseColor);
      binding.ribbonMaterial.emissive.copy(binding.baseColor);
      binding.bevelMaterial.emissive.copy(binding.baseColor);
      binding.edgeMaterial.emissive.copy(binding.baseColor);
      binding.lineMaterial.emissiveIntensity = 0;
      binding.ribbonMaterial.emissiveIntensity = 0;
      binding.bevelMaterial.emissiveIntensity = 0;
      binding.edgeMaterial.emissiveIntensity = 0;
      binding.edgeMaterial.roughness = Math.min(
        1,
        PANTHEON_MATERIAL_CONFIGS[binding.id].roughness +
          debug.edgeRoughness,
      );
      const materialConfig = PANTHEON_MATERIAL_CONFIGS[binding.id];
      const reflectionCandidate =
        PANTHEON_REFLECTION_CANDIDATES[reflectionCandidateId];
      const reflectionProfile =
        reflectionCandidate.profiles[binding.id];
      const styleCandidate =
        PANTHEON_STYLE_MATCH_CANDIDATES[styleMatchCandidateId];
      const metalColorProfile =
        METAL_COLOR_DENSITY_CANDIDATES[
          metalColorDensityCandidateId
        ][binding.id];
      const themeBalance =
        styleCandidate.themeBalance[binding.id];
      binding.bevelMaterial.color.multiplyScalar(
        styleCandidate.enabled
          ? themeBalance.bevelBrightness
          : 1,
      );
      binding.ribbonUniforms.reflectionEnabled.value =
        !styleCandidate.enabled && reflectionCandidate.enabled ? 1 : 0;
      binding.ribbonUniforms.highlightOffset.value =
        reflectionProfile.highlightOffset;
      binding.ribbonUniforms.highlightWidth.value =
        reflectionProfile.highlightWidth;
      binding.ribbonUniforms.highlightStrength.value =
        reflectionProfile.highlightStrength;
      binding.ribbonUniforms.specularGain.value =
        reflectionProfile.specularGain;
      binding.ribbonUniforms.grazingGain.value =
        reflectionProfile.grazingGain;
      binding.ribbonUniforms.darkSideLift.value =
        reflectionProfile.darkSideLift;
      binding.ribbonUniforms.centerSuppression.value =
        reflectionProfile.centerSuppression;
      binding.ribbonUniforms.specularShoulder.value =
        reflectionCandidate.shoulder;
      binding.ribbonUniforms.directSpecularCompressionShoulder.value =
        DIRECT_SPECULAR_COMPRESSION_SHOULDERS[
          directSpecularCompressionCandidateId
        ][binding.id] ?? 0;
      const humanDesignIndirectSpecular =
        HUMAN_DESIGN_INDIRECT_SPECULAR_CANDIDATES[
          humanDesignIndirectSpecularCandidateId
        ];
      binding.ribbonUniforms.indirectSpecularContrast.value =
        binding.id === "human-design"
          ? humanDesignIndirectSpecular.contrast
          : 1;
      binding.ribbonUniforms.indirectSpecularPivot.value =
        humanDesignIndirectSpecular.pivot;
      binding.ribbonUniforms.reflectionTintAmount.value =
        reflectionCandidate.tintAmount;
      binding.ribbonUniforms.reflectionRotation.value =
        THREE.MathUtils.degToRad(
          reflectionProfile.reflectionRotation,
        );
      binding.ribbonUniforms.profileColor.value.copy(
        binding.baseColor,
      );
      binding.ribbonUniforms.styleEnabled.value =
        styleCandidate.enabled ? 1 : 0;
      binding.ribbonUniforms.styleGradientStart.value.set(
        monochrome ? "#787c80" : metalColorProfile.gradientStart,
      );
      binding.ribbonUniforms.styleGradientEnd.value.set(
        monochrome ? "#f0eee7" : metalColorProfile.gradientEnd,
      );
      binding.ribbonUniforms.styleGradientStrength.value =
        styleCandidate.enabled
          ? themeBalance.gradientStrength
          : styleCandidate.gradientStrength;
      binding.ribbonUniforms.styleWrap.value = styleCandidate.wrap;
      binding.ribbonUniforms.styleWrapStrength.value =
        styleCandidate.wrapStrength;
      binding.ribbonUniforms.styleViewGradientStrength.value =
        styleCandidate.viewGradientStrength;
      binding.ribbonUniforms.styleRimStrength.value =
        styleCandidate.rimStrength;
      binding.ribbonUniforms.styleSpecularTintStrength.value =
        styleCandidate.specularTintStrength;
      binding.ribbonUniforms.styleColorLift.value =
        styleMatchCandidateId === "soft-metal"
          ? STYLE_COLOR_LIFT_CANDIDATES[styleColorLiftCandidateId]
          : styleCandidate.colorLift;
      binding.ribbonUniforms.styleEmissiveLift.value =
        styleCandidate.emissiveLift;
      binding.ribbonUniforms.styleBackBrightness.value =
        styleCandidate.enabled
          ? themeBalance.depthBackBrightness
          : styleCandidate.backBrightness;
      binding.ribbonUniforms.styleThemeBrightness.value =
        styleCandidate.enabled ? themeBalance.brightness : 1;
      binding.ribbonUniforms.styleThemeSaturation.value =
        styleCandidate.enabled ? metalColorProfile.saturation : 1;
      binding.ribbonUniforms.styleHighlightStrength.value =
        styleCandidate.enabled
          ? themeBalance.highlightStrength
          : 1;
      for (const material of [
        binding.ribbonMaterial,
        binding.bevelMaterial,
        binding.edgeMaterial,
      ]) {
        if (styleCandidate.enabled) {
          material.envMapRotation.set(0, 0, 0);
        } else {
          applyBandEnvironmentRotation(
            material,
            reflectionProfile.reflectionRotation,
          );
        }
      }
      const qualityEnvironmentBoost = mobileQualityPreview ? 1.22 : 1;
      binding.ribbonMaterial.envMapIntensity =
        environmentIntensity *
        qualityEnvironmentBoost *
        debug.metalHighlightStrength;
      binding.bevelMaterial.envMapIntensity =
        environmentIntensity *
        (PANTHEON_BAND_ENVIRONMENT_BASELINE.bevel /
          PANTHEON_BAND_ENVIRONMENT_BASELINE.topBottom) *
        qualityEnvironmentBoost *
        debug.metalHighlightStrength;
      binding.edgeMaterial.envMapIntensity =
        environmentIntensity *
        (PANTHEON_BAND_ENVIRONMENT_BASELINE.edge /
          PANTHEON_BAND_ENVIRONMENT_BASELINE.topBottom) *
        qualityEnvironmentBoost *
        debug.metalHighlightStrength;
      binding.ribbonMaterial.roughness =
        styleCandidate.enabled && themeBalance.roughness !== undefined
          ? themeBalance.roughness
          : THREE.MathUtils.clamp(
              materialConfig.roughness +
                (styleCandidate.enabled
                  ? styleCandidate.roughnessOffset +
                    themeBalance.roughnessOffset
                  : 0),
              0.42,
              0.6,
            );
      binding.bevelMaterial.roughness = THREE.MathUtils.clamp(
        binding.ribbonMaterial.roughness - 0.035,
        0.18,
        0.36,
      );
      binding.edgeMaterial.roughness = THREE.MathUtils.clamp(
        binding.ribbonMaterial.roughness + debug.edgeRoughness,
        0.28,
        0.5,
      );
      const styleMetalnessScale = styleCandidate.enabled
        ? styleCandidate.metalnessScale *
          themeBalance.metalnessScale
        : 1;
      const bandMetalness =
        styleCandidate.enabled && themeBalance.metalness !== undefined
          ? themeBalance.metalness
          : materialConfig.metalness * styleMetalnessScale;
      binding.ribbonMaterial.metalness = bandMetalness;
      binding.bevelMaterial.metalness = bandMetalness;
      binding.edgeMaterial.metalness = bandMetalness;
      binding.runeUniforms.color.value.copy(
        monochrome ? new THREE.Color(0xf5f5f2) : binding.accentColor,
      );
    });
    nodes.orbitGroup.visible = debug.showTubeLine;
    nodes.ribbonGroup.visible = debug.showBand;
    nodes.core.visible = debug.showCore;
  }

  function getSnapshot() {
    return {
      state: JSON.parse(JSON.stringify(state)),
      visuals: Object.fromEntries(
        [...bindings.entries()].map(([id, binding]) => [
          id,
          {
            state: resolveOrbitVisualState(state, id),
            width: binding.ribbonUniforms.width.value,
            bandWidth: binding.ribbonUniforms.width.value,
            bandThickness: binding.ribbonUniforms.thickness.value,
            opacity: binding.opacity,
            ribbonVisible: binding.ribbon.visible,
            bandVisible: binding.ribbon.visible,
            runeVisible: binding.rune.visible,
            markOpacity: binding.ribbonUniforms.markOpacity.value,
            flowIntensity: binding.ribbonUniforms.flowIntensity.value,
            energyPhase: binding.ribbonUniforms.flow.value,
            energyPulseCount:
              binding.ribbonUniforms.energyPulseCount.value,
            energyCycleSeconds:
              SURFACE_ENERGY_CONFIG[id].cycleSeconds,
            hoverSweepProgress:
              binding.ribbonUniforms.hoverSweep.value,
            hoverSweepIntensity:
              binding.ribbonUniforms.hoverSweepIntensity.value,
            baseColor: `#${binding.baseColor.getHexString()}`,
            displayColor: `#${binding.ribbonMaterial.color.getHexString()}`,
            stateBrightness: state.brightness[id],
            stateSaturation: state.saturation[id],
            emissiveIntensity: binding.ribbonMaterial.emissiveIntensity,
            metalness: binding.ribbonMaterial.metalness,
            roughness: binding.ribbonMaterial.roughness,
            clearcoat: binding.ribbonMaterial.clearcoat,
            clearcoatRoughness:
              binding.ribbonMaterial.clearcoatRoughness,
            anisotropy: binding.ribbonMaterial.anisotropy,
            envMapIntensity: binding.ribbonMaterial.envMapIntensity,
            envMapRotationDegrees:
              THREE.MathUtils.radToDeg(
                binding.ribbonMaterial.envMapRotation.y,
              ),
            envMapRotationEulerDegrees: [
              THREE.MathUtils.radToDeg(
                binding.ribbonMaterial.envMapRotation.x,
              ),
              THREE.MathUtils.radToDeg(
                binding.ribbonMaterial.envMapRotation.y,
              ),
              THREE.MathUtils.radToDeg(
                binding.ribbonMaterial.envMapRotation.z,
              ),
            ],
            reflectionProfile: {
              ...PANTHEON_REFLECTION_CANDIDATES[
                reflectionCandidateId
              ].profiles[id],
            },
            styleGradient: {
              start:
                METAL_COLOR_DENSITY_CANDIDATES[
                  metalColorDensityCandidateId
                ][id].gradientStart,
              end:
                METAL_COLOR_DENSITY_CANDIDATES[
                  metalColorDensityCandidateId
                ][id].gradientEnd,
            },
            styleEmissiveLift:
              binding.ribbonUniforms.styleEmissiveLift.value,
            styleDepthBrightness:
              binding.ribbonUniforms.styleBackBrightness.value,
            styleThemeBrightness:
              binding.ribbonUniforms.styleThemeBrightness.value,
            styleThemeSaturation:
              binding.ribbonUniforms.styleThemeSaturation.value,
            styleHighlightStrength:
              binding.ribbonUniforms.styleHighlightStrength.value,
            directSpecularCompressionShoulder:
              binding.ribbonUniforms.directSpecularCompressionShoulder
                .value,
            indirectSpecularContrast:
              binding.ribbonUniforms.indirectSpecularContrast.value,
            indirectSpecularPivot:
              binding.ribbonUniforms.indirectSpecularPivot.value,
            styleGradientStrength:
              binding.ribbonUniforms.styleGradientStrength.value,
            bevelBrightness:
              PANTHEON_STYLE_MATCH_CANDIDATES[
                styleMatchCandidateId
              ].themeBalance[id].bevelBrightness,
            frontBackSameBaseColor: true,
            frontBackSamePbr: true,
            edgeColorScale: 0.88,
            flowSpeed: PANTHEON_THEME_CONFIGS.find(
              (theme) => theme.id === id,
            )!.runeFlowSpeed,
          },
        ]),
      ),
      geometryBuilds: 1,
      materialVersion:
        "Pantheon Style Match Final Balance Pass v1",
      styleMatch: {
        version: "Pantheon Style Match Final Balance Pass v1",
        candidate: styleMatchCandidateId,
        candidateLabel:
          PANTHEON_STYLE_MATCH_CANDIDATES[styleMatchCandidateId]
            .label,
        sourceVisual:
          "artifacts/pantheon_sphere_phase2/pantheon-sphere-reference-crop-v2.jpeg",
        sharedShadingModel:
          PANTHEON_STYLE_MATCH_CANDIDATES[styleMatchCandidateId]
            .enabled,
        perBandReflectionProfilesActive:
          !PANTHEON_STYLE_MATCH_CANDIDATES[styleMatchCandidateId]
            .enabled,
        profile: {
          ...PANTHEON_STYLE_MATCH_CANDIDATES[
            styleMatchCandidateId
          ],
        },
        gradients: { ...PANTHEON_STYLE_GRADIENTS },
        wrapDiffuse: true,
        viewGradient: true,
        cameraDepthLayering: true,
        bloom: false,
        particles: false,
        halo: false,
      },
      directSpecularCompression: {
        version:
          "Pantheon Constellation–Tarot Highlight Compression Pass v1",
        candidate: directSpecularCompressionCandidateId,
        shoulders: {
          ...DIRECT_SPECULAR_COMPRESSION_SHOULDERS[
            directSpecularCompressionCandidateId
          ],
        },
        scope: ["constellation", "tarot"],
        affectsDirectSpecularOnly: true,
      },
      styleColorLiftRecovery: {
        version: "Pantheon Dark Reflection Recovery Pass v1",
        candidate: styleColorLiftCandidateId,
        value: STYLE_COLOR_LIFT_CANDIDATES[styleColorLiftCandidateId],
        sharedAcrossThemes: true,
        styleSoftLightWeight: 0.62,
        wrapDiffuseChanged: false,
        rimLiftChanged: false,
        emissiveLiftChanged: false,
      },
      humanDesignIndirectSpecularContrast: {
        version:
          "Pantheon Human Design Indirect Specular Contrast Pass v1",
        candidate: humanDesignIndirectSpecularCandidateId,
        ...HUMAN_DESIGN_INDIRECT_SPECULAR_CANDIDATES[
          humanDesignIndirectSpecularCandidateId
        ],
        scope: ["human-design"],
        affectsIndirectSpecularOnly: true,
      },
      metalColorDensityRecovery: {
        version: "Pantheon Metal Color Density Recovery Pass v1",
        candidate: metalColorDensityCandidateId,
        profiles: JSON.parse(
          JSON.stringify(
            METAL_COLOR_DENSITY_CANDIDATES[
              metalColorDensityCandidateId
            ],
          ),
        ),
        affectsBaseColorGradientAndSaturationOnly: true,
      },
      reflectionArtDirection: {
        version: "Pantheon Reflection Art Direction Pass v1",
        status:
          styleMatchCandidateId === "reflection-v1"
            ? "archive-active"
            : "debug-archive",
        candidate: reflectionCandidateId,
        candidateLabel:
          PANTHEON_REFLECTION_CANDIDATES[reflectionCandidateId].label,
        enabled:
          styleMatchCandidateId === "reflection-v1" &&
          PANTHEON_REFLECTION_CANDIDATES[reflectionCandidateId]
            .enabled,
        implementation: "material-envMapRotation-plus-physical-specular-shaping",
        sharedPmrem: true,
        environmentCopies: 1,
        hardHighlightCeiling: false,
        bloom: false,
        emissiveReflection: false,
        coreSuppressInner: REFLECTION_CORE_SUPPRESSION.inner,
        coreSuppressOuter: REFLECTION_CORE_SUPPRESSION.outer,
        grazingPower: REFLECTION_CORE_SUPPRESSION.grazingPower,
        shoulder:
          PANTHEON_REFLECTION_CANDIDATES[reflectionCandidateId]
            .shoulder,
        tintAmount:
          PANTHEON_REFLECTION_CANDIDATES[reflectionCandidateId]
            .tintAmount,
        profiles: Object.fromEntries(
          PANTHEON_THEME_CONFIGS.map(({ id }) => [
            id,
            {
              ...PANTHEON_REFLECTION_CANDIDATES[
                reflectionCandidateId
              ].profiles[id],
            },
          ]),
        ),
      },
      effectsVersion: PANTHEON_EFFECTS_VERSION,
      effects: {
        geometryAttachedOnly: true,
        surfaceEnergy: {
          minimumCycleSeconds: Math.min(
            ...Object.values(SURFACE_ENERGY_CONFIG).map(
              ({ cycleSeconds }) => cycleSeconds,
            ),
          ),
          maximumCycleSeconds: Math.max(
            ...Object.values(SURFACE_ENERGY_CONFIG).map(
              ({ cycleSeconds }) => cycleSeconds,
            ),
          ),
          minimumPulseCount: Math.min(
            ...Object.values(SURFACE_ENERGY_CONFIG).map(
              ({ pulseCount }) => pulseCount,
            ),
          ),
          maximumPulseCount: Math.max(
            ...Object.values(SURFACE_ENERGY_CONFIG).map(
              ({ pulseCount }) => pulseCount,
            ),
          ),
          perBandRhythm: Object.fromEntries(
            Object.entries(SURFACE_ENERGY_CONFIG).map(
              ([id, config]) => [
                id,
                {
                  cycleSeconds: config.cycleSeconds,
                  pulseCount: config.pulseCount,
                  intensity: config.intensity,
                  direction: config.direction,
                  rhythmWarp: config.rhythmWarp,
                },
              ],
            ),
          ),
        },
        hover: {
          idleMarkOpacity: HOVER_EFFECT_CONFIG.idleMarkOpacity,
          hoveredMarkOpacity:
            HOVER_EFFECT_CONFIG.hoveredMarkOpacity,
          sweepDurationSeconds:
            HOVER_EFFECT_CONFIG.sweepDurationSeconds,
          singlePass: false,
        },
        forbiddenEffects: {
          particles: false,
          bloom: false,
          halo: false,
          lensFlare: false,
          floatingObjects: false,
        },
      },
      surfaceMarks: {
        system: BAND_RUNE_SURFACE_CONFIG.system,
        themeSpecificGlyphs: true,
        renderedSurfaces: ["top", "bottom"],
        samePatternOnBothSurfaces: true,
        fixedToBandUv: BAND_RUNE_SURFACE_CONFIG.fixedToBandUv,
        independentMotion:
          BAND_RUNE_SURFACE_CONFIG.independentMotion,
        idleVisible: true,
        idleMarkOpacity: BAND_RUNE_SURFACE_CONFIG.idleMarkOpacity,
        illuminatedUsesSameMarks: true,
        illuminationAddsToIdleBaseline: true,
        cellCount: BAND_RUNE_SURFACE_CONFIG.cellCount,
        minimumGlyphClusters:
          BAND_RUNE_SURFACE_CONFIG.minimumGlyphClusters,
        idleCoverage: 0.31,
        hoveredCoverage: 0.36,
        selectedCoverage: 0.4,
        maximumEmissive: 0,
        maximumSimultaneousFlowMarks: Math.max(
          ...Object.values(SURFACE_ENERGY_CONFIG).map(
            ({ pulseCount }) => pulseCount,
          ),
        ),
        wholeTextureTranslation: false,
        localRaisedReliefRevealOnly: true,
        localEngravingRevealOnly: false,
        reliefModel: BAND_RUNE_SURFACE_CONFIG.reliefModel,
        metalReflectionOnly: false,
        marksRemainFixedWhileLightMoves: true,
        strokeScale: 2.05,
        reliefNormalStrength: debug.markDepth * 5,
        reliefDepth: BAND_RUNE_SURFACE_CONFIG.reliefDepth,
        reliefEdgeSharpness:
          BAND_RUNE_SURFACE_CONFIG.reliefEdgeSharpness,
        contactShadowStrength:
          BAND_RUNE_SURFACE_CONFIG.contactShadowStrength,
        edgeHighlightStrength:
          BAND_RUNE_SURFACE_CONFIG.edgeHighlightStrength,
        roughnessTopDelta:
          BAND_RUNE_SURFACE_CONFIG.roughnessTopDelta,
        roughnessEdgeDelta:
          BAND_RUNE_SURFACE_CONFIG.roughnessEdgeDelta,
        metalnessDelta:
          BAND_RUNE_SURFACE_CONFIG.metalnessDelta,
        bevelHighlight: true,
        contactShadow: true,
        addedGeometry: false,
        brushedRoughnessPattern: "anisotropy-only",
        periodicRoughness: false,
        metalHighlightCeiling: null,
      },
      wholeBandInteraction: {
        brightnessShift: false,
        saturationShift: false,
        colorShift: false,
        roughnessShift: false,
        environmentShift: false,
        widthShift: false,
        emissiveShift: false,
      },
      backgroundMinimumBrightness: 1.08,
      runeCycles: 0,
      runeSeamContinuous: true,
      ribbonThickness: RIBBON_THICKNESS,
      bandThickness: RIBBON_THICKNESS,
      bandDimensions: {
        locked: true,
        desktopWidth: DESKTOP_RIBBON_WIDTHS.idle,
        mobileWidth: MOBILE_RIBBON_WIDTHS.idle,
        thickness: RIBBON_THICKNESS,
        bevelWidth: BAND_BEVEL_WIDTH,
        bevelSegments: BAND_BEVEL_SEGMENTS,
        invariantAcrossStates: true,
      },
      widthProfile: {
        desktop: { ...desktopWidths },
        mobile: { ...mobileWidths },
        active: {
          ...(mobileQualityPreview ? mobileWidths : desktopWidths),
        },
      },
      prebuiltMaxRibbonWidth: PREBUILT_MAX_RIBBON_WIDTH,
      prebuiltBandWidth: PREBUILT_MAX_RIBBON_WIDTH,
      ribbonPhases: { ...RIBBON_PHASE_DEGREES },
      validationMode: debug.validationMode,
      mobileQualityPreview,
      reducedMotionPreview,
      paused,
      monochrome,
      debug: { ...debug },
    };
  }

  return {
    state,
    bindings,
    update,
    setHoveredTheme,
    selectTheme,
    setTwist(themeId: PantheonThemeId, value: number) {
      // Geometry v1.1 永久凍結；保留 API 只為相容舊驗收呼叫。
      void value;
      state.mobiusTwistProgress[themeId] = 0;
    },
    setMonochrome(value: boolean) {
      monochrome = value;
    },
    setPaused(value: boolean) {
      paused = value;
      state.autoRotate = !value;
    },
    setReducedMotionPreview(value: boolean) {
      reducedMotionPreview = value;
      state.reducedMotion = value;
    },
    setMobileQualityPreview(value: boolean) {
      mobileQualityPreview = value;
      bindings.forEach((binding) => {
        const config = PANTHEON_MATERIAL_CONFIGS[binding.id];
        binding.ribbonMaterial.anisotropy = value
          ? 0
          : config.anisotropy;
        binding.bevelMaterial.anisotropy = value
          ? 0
          : config.anisotropy * 0.7;
        binding.ribbonMaterial.clearcoat = value
          ? config.clearcoat * 0.45
          : config.clearcoat;
        binding.bevelMaterial.clearcoat = value
          ? config.clearcoat * 0.45
          : config.clearcoat;
      });
    },
    setReflectionCandidate(candidateId: ReflectionCandidateId) {
      if (!(candidateId in PANTHEON_REFLECTION_CANDIDATES)) {
        return getSnapshot();
      }
      reflectionCandidateId = candidateId;
      update(0);
      return getSnapshot();
    },
    setStyleMatchCandidate(candidateId: StyleMatchCandidateId) {
      if (!(candidateId in PANTHEON_STYLE_MATCH_CANDIDATES)) {
        return getSnapshot();
      }
      styleMatchCandidateId = candidateId;
      update(0);
      return getSnapshot();
    },
    setDirectSpecularCompressionCandidate(
      candidateId: DirectSpecularCompressionCandidateId,
    ) {
      if (!(candidateId in DIRECT_SPECULAR_COMPRESSION_SHOULDERS)) {
        return getSnapshot();
      }
      directSpecularCompressionCandidateId = candidateId;
      update(0);
      return getSnapshot();
    },
    setStyleColorLiftCandidate(
      candidateId: StyleColorLiftCandidateId,
    ) {
      if (!(candidateId in STYLE_COLOR_LIFT_CANDIDATES)) {
        return getSnapshot();
      }
      styleColorLiftCandidateId = candidateId;
      update(0);
      return getSnapshot();
    },
    setHumanDesignIndirectSpecularCandidate(
      candidateId: HumanDesignIndirectSpecularCandidateId,
    ) {
      if (
        !(
          candidateId in
          HUMAN_DESIGN_INDIRECT_SPECULAR_CANDIDATES
        )
      ) {
        return getSnapshot();
      }
      humanDesignIndirectSpecularCandidateId = candidateId;
      update(0);
      return getSnapshot();
    },
    setMetalColorDensityCandidate(
      candidateId: MetalColorDensityCandidateId,
    ) {
      if (!(candidateId in METAL_COLOR_DENSITY_CANDIDATES)) {
        return getSnapshot();
      }
      metalColorDensityCandidateId = candidateId;
      const profile =
        METAL_COLOR_DENSITY_CANDIDATES[candidateId];
      for (const [themeId, binding] of bindings) {
        binding.baseColor.set(profile[themeId].baseColor);
      }
      update(0);
      return getSnapshot();
    },
    setEnvironmentIntensity(value: number) {
      environmentIntensity = THREE.MathUtils.clamp(value, 0, 1.5);
      update(0);
      return getSnapshot();
    },
    setThemeMaterial(
      themeId: PantheonThemeId,
      patch: Partial<{
        baseColor: string;
        metalness: number;
        roughness: number;
        clearcoat: number;
        clearcoatRoughness: number;
        anisotropy: number;
        envMapIntensity: number;
      }>,
    ) {
      const binding = bindings.get(themeId);
      if (!binding) return getSnapshot();
      if (patch.baseColor) {
        binding.baseColor.set(patch.baseColor);
      }
      for (const material of [
        binding.ribbonMaterial,
        binding.bevelMaterial,
        binding.edgeMaterial,
      ]) {
        if (patch.metalness !== undefined) {
          material.metalness = patch.metalness;
        }
        if (patch.roughness !== undefined) {
          material.roughness = patch.roughness;
        }
        if (patch.clearcoat !== undefined) {
          material.clearcoat = patch.clearcoat;
        }
        if (patch.clearcoatRoughness !== undefined) {
          material.clearcoatRoughness = patch.clearcoatRoughness;
        }
        if (patch.envMapIntensity !== undefined) {
          material.envMapIntensity = patch.envMapIntensity;
        }
      }
      if (patch.anisotropy !== undefined) {
        binding.ribbonMaterial.anisotropy = patch.anisotropy;
        binding.bevelMaterial.anisotropy = patch.anisotropy * 0.7;
      }
      return getSnapshot();
    },
    setWidthProfile(
      target: "desktop" | "mobile",
      patch: Partial<RibbonWidthProfile>,
    ) {
      // 僅供 Material Lab 預覽；不回寫 Geometry 或正式尺寸設定。
      const profile = target === "mobile" ? mobileWidths : desktopWidths;
      const requestedWidth =
        patch.idle ?? patch.hover ?? patch.selected ?? profile.idle;
      const width = THREE.MathUtils.clamp(requestedWidth, 0.06, 0.36);
      Object.assign(profile, {
        idle: width,
        hover: width,
        selected: width,
      });
      return {
        desktop: { ...desktopWidths },
        mobile: { ...mobileWidths },
      };
    },
    setDebugOverrides(
      patch: Partial<typeof debug>,
    ) {
      Object.assign(debug, patch);
      if ("showRibbon" in patch && !("showBand" in patch)) {
        debug.showBand = Boolean(patch.showRibbon);
      }
      if ("showBand" in patch && !("showRibbon" in patch)) {
        debug.showRibbon = Boolean(patch.showBand);
      }
      bindings.forEach((binding) => {
        binding.ribbonMaterial.wireframe = debug.showFrame;
        binding.bevelMaterial.wireframe = debug.showFrame;
        binding.edgeMaterial.wireframe = debug.showFrame;
        binding.lineMaterial.wireframe = debug.showSeam;
      });
    },
    getSnapshot,
    dispose() {
      bindings.forEach((binding) => {
        binding.lineMaterial.dispose();
        binding.ribbonMaterial.dispose();
        binding.bevelMaterial.dispose();
        binding.edgeMaterial.dispose();
        (binding.rune.material as THREE.Material).dispose();
        binding.rune.removeFromParent();
      });
    },
  };
}
