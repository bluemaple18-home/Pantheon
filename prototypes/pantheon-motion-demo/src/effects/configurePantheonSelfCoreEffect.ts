import * as THREE from "three";
import {
  CORE_RUNE_RELATIONSHIP_CONFIG,
  PANTHEON_EFFECTS_VERSION,
  SELF_CORE_EFFECT_CONFIG,
} from "../data/pantheon-effects-config.ts";
import type { PantheonThemeId } from "../data/pantheon-theme-config.ts";
import {
  DEFAULT_SELF_CORE_ARTIFACT_CANDIDATE,
  getPantheonSelfCoreArtifactPreset,
  type PantheonSelfCoreCandidateId,
} from "../data/pantheon-self-core-artifact.ts";

export interface SelfCoreEffectController {
  update: (
    elapsedSeconds: number,
    motionOff: boolean,
    deltaSeconds?: number,
  ) => void;
  setStyle: (style: {
    color: string;
    emissiveColor: string;
    emissiveIntensity: number;
    metalness: number;
    roughness: number;
    clearcoat?: number;
    clearcoatRoughness?: number;
    envMapIntensity?: number;
  }) => void;
  setRelationshipTarget: (target: {
    themeId: PantheonThemeId | null;
    color: string;
    influence: number;
  }) => void;
  setArtifactCandidate: (
    candidateId: PantheonSelfCoreCandidateId,
  ) => {
    candidateId: PantheonSelfCoreCandidateId;
    radiusScale: number;
  };
  snapshot: () => {
    version: typeof PANTHEON_EFFECTS_VERSION;
    reflectionFrequencyHz: number;
    normalStrength: number;
    roughnessVariation: number;
    scaleAnimation: false;
    emissive: boolean;
    emissiveIntensity: number;
    color: string;
    emissiveColor: string;
    metalness: number;
    roughness: number;
    clearcoat: number;
    clearcoatRoughness: number;
    envMapIntensity: number;
    materialEnvMapIntensity: number;
    gpuEnvMapIntensity: number | null;
    envMapUuid: string | null;
    explicitEnvironmentMap: boolean;
    relationship: {
      activeTheme: PantheonThemeId | null;
      targetInfluence: number;
      currentInfluence: number;
      targetColor: string;
      currentColor: string;
      displayColor: string;
    };
    artifact: {
      candidateId: PantheonSelfCoreCandidateId;
      radiusScale: number;
      surfaceStrength: number;
      ringFrequency: number;
      latitudeFrequency: number;
      wearStrength: number;
      roughnessVariation: number;
      timeVariation: number;
      maximumWarmth: {
        hueDegrees: 1;
        saturation: 0.02;
        luminance: 0.03;
      };
      rotationAnimation: false;
      pulseAnimation: false;
      breathingAnimation: false;
    };
    bloom: false;
  };
}

export function configurePantheonSelfCoreEffect(
  core: THREE.Mesh,
  options: {
    environmentMap?: THREE.Texture;
  } = {},
): SelfCoreEffectController {
  if (!(core.material instanceof THREE.MeshPhysicalMaterial)) {
    throw new Error("Self Core 必須使用 MeshPhysicalMaterial");
  }

  const material = core.material;
  material.envMap = options.environmentMap ?? null;
  const uniforms = {
    time: { value: 0 },
    motion: { value: 1 },
    surfaceStrength: { value: 0 },
    ringFrequency: { value: 0 },
    latitudeFrequency: { value: 0 },
    wearStrength: { value: 0 },
    roughnessVariation: { value: 0 },
    timeVariation: { value: 0 },
  };
  let styleEmissiveIntensity = 0.085;
  let styleColor = new THREE.Color("#c49a4a");
  let styleEmissiveColor = new THREE.Color("#432c0a");
  let styleMetalness = 0.78;
  let styleRoughness = 0.3;
  let styleClearcoat = 0.65;
  let styleClearcoatRoughness = 0.14;
  let styleEnvMapIntensity = 0.9;
  let relationshipTheme: PantheonThemeId | null = null;
  let relationshipTargetInfluence = 0;
  let relationshipCurrentInfluence = 0;
  const relationshipTargetColor = styleColor.clone();
  const relationshipCurrentColor = styleColor.clone();
  const displayColor = styleColor.clone();
  const displayEmissiveColor = styleEmissiveColor.clone();
  const relationshipEmissiveColor = styleEmissiveColor.clone();
  const warmArtifactColor = styleColor.clone();
  let artifactCandidateId: PantheonSelfCoreCandidateId =
    DEFAULT_SELF_CORE_ARTIFACT_CANDIDATE;
  let artifactRadiusScale = 1;

  material.color.copy(styleColor);
  material.emissive.copy(styleEmissiveColor);
  material.emissiveIntensity = styleEmissiveIntensity;
  material.metalness = styleMetalness;
  material.roughness = styleRoughness;
  material.onBeforeCompile = (shader) => {
    material.userData.shader = shader;
    Object.assign(shader.uniforms, {
      uPantheonCoreTime: uniforms.time,
      uPantheonCoreMotion: uniforms.motion,
      uPantheonCoreSurfaceStrength: uniforms.surfaceStrength,
      uPantheonCoreRingFrequency: uniforms.ringFrequency,
      uPantheonCoreLatitudeFrequency: uniforms.latitudeFrequency,
      uPantheonCoreWearStrength: uniforms.wearStrength,
      uPantheonCoreRoughnessVariation: uniforms.roughnessVariation,
      uPantheonCoreTimeVariation: uniforms.timeVariation,
    });
    shader.vertexShader = shader.vertexShader
      .replace(
        "void main() {",
        `varying vec3 vPantheonCorePosition;
void main() {`,
      )
      .replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>
vPantheonCorePosition = position;`,
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "void main() {",
        `uniform float uPantheonCoreTime;
uniform float uPantheonCoreMotion;
uniform float uPantheonCoreSurfaceStrength;
uniform float uPantheonCoreRingFrequency;
uniform float uPantheonCoreLatitudeFrequency;
uniform float uPantheonCoreWearStrength;
uniform float uPantheonCoreRoughnessVariation;
uniform float uPantheonCoreTimeVariation;
varying vec3 vPantheonCorePosition;
void main() {`,
      )
      .replace(
        "#include <normal_fragment_maps>",
        `#include <normal_fragment_maps>
vec3 pantheonCoreDirection = normalize(vPantheonCorePosition);
float pantheonCoreRing =
  sin(pantheonCoreDirection.y * uPantheonCoreRingFrequency);
float pantheonCoreLatitude =
  sin(
    atan(pantheonCoreDirection.z, pantheonCoreDirection.x) *
    uPantheonCoreLatitudeFrequency
  );
float pantheonCoreMachining =
  pantheonCoreRing * 0.74 + pantheonCoreLatitude * 0.26;
vec3 pantheonCoreArtifactNormal = vec3(
  pantheonCoreLatitude * 0.35,
  pantheonCoreRing,
  -pantheonCoreLatitude * 0.35
);
normal = normalize(
  normal +
  pantheonCoreArtifactNormal * uPantheonCoreSurfaceStrength
);`,
      )
      .replace(
        "#include <roughnessmap_fragment>",
        `#include <roughnessmap_fragment>
vec3 pantheonCoreRoughnessDirection = normalize(vPantheonCorePosition);
float pantheonCoreRings =
  sin(pantheonCoreRoughnessDirection.y * uPantheonCoreRingFrequency);
float pantheonCoreWear =
  smoothstep(
    0.25,
    0.92,
    abs(pantheonCoreRoughnessDirection.x * 0.62 +
        pantheonCoreRoughnessDirection.z * 0.38)
  );
float pantheonCoreSlowMaterialDrift =
  sin(uPantheonCoreTime * 0.34) *
  uPantheonCoreTimeVariation *
  uPantheonCoreMotion;
roughnessFactor = clamp(
  roughnessFactor +
    pantheonCoreRings * uPantheonCoreRoughnessVariation +
    pantheonCoreWear * uPantheonCoreWearStrength +
    pantheonCoreSlowMaterialDrift,
  0.26,
  0.52
);`,
      );
  };
  material.customProgramCacheKey = () =>
    "pantheon-self-core-artifact-v1";
  material.needsUpdate = true;
  core.userData.effectsVersion = PANTHEON_EFFECTS_VERSION;

  const controller: SelfCoreEffectController = {
    update(elapsedSeconds, motionOff, deltaSeconds = 1 / 60) {
      uniforms.motion.value = motionOff ? 0 : 1;
      if (!motionOff) uniforms.time.value = elapsedSeconds;
      if (motionOff) {
        relationshipTheme = null;
        relationshipTargetInfluence = 0;
        relationshipCurrentInfluence = 0;
        relationshipTargetColor.copy(styleColor);
        relationshipCurrentColor.copy(styleColor);
      } else {
        const duration =
          relationshipTargetInfluence > relationshipCurrentInfluence
            ? CORE_RUNE_RELATIONSHIP_CONFIG.enterDurationSeconds
            : CORE_RUNE_RELATIONSHIP_CONFIG.exitDurationSeconds;
        const influenceAlpha =
          1 - Math.exp((-3 * deltaSeconds) / duration);
        relationshipCurrentInfluence = THREE.MathUtils.lerp(
          relationshipCurrentInfluence,
          relationshipTargetInfluence,
          influenceAlpha,
        );
        const colorAlpha =
          1 -
          Math.exp(
            (-3 * deltaSeconds) /
              CORE_RUNE_RELATIONSHIP_CONFIG.enterDurationSeconds,
          );
        relationshipCurrentColor.lerp(
          relationshipTargetColor,
          colorAlpha,
        );
      }
      const baseHsl = { h: 0, s: 0, l: 0 };
      styleColor.getHSL(baseHsl);
      warmArtifactColor.setHSL(
        (baseHsl.h - 1 / 360 + 1) % 1,
        THREE.MathUtils.clamp(baseHsl.s + 0.02, 0, 1),
        THREE.MathUtils.clamp(baseHsl.l + 0.03, 0, 1),
      );
      displayColor
        .copy(styleColor)
        .lerp(
          warmArtifactColor,
          relationshipCurrentInfluence,
        );
      relationshipEmissiveColor
        .copy(relationshipCurrentColor)
        .multiplyScalar(0.62);
      displayEmissiveColor
        .copy(styleEmissiveColor)
        .lerp(
          relationshipEmissiveColor,
          relationshipCurrentInfluence,
        );
      material.color.copy(displayColor);
      material.emissive.copy(displayEmissiveColor);
      material.emissiveIntensity = styleEmissiveIntensity;
      material.metalness = styleMetalness;
      material.roughness =
        styleRoughness *
        (1 - relationshipCurrentInfluence * 0.01);
      material.clearcoat = styleClearcoat;
      material.clearcoatRoughness = styleClearcoatRoughness;
      material.envMapIntensity = styleEnvMapIntensity;
    },
    setRelationshipTarget(target) {
      relationshipTheme = target.themeId;
      relationshipTargetInfluence = THREE.MathUtils.clamp(
        target.influence,
        0,
        CORE_RUNE_RELATIONSHIP_CONFIG.maximumInfluence,
      );
      relationshipTargetColor.set(target.color);
    },
    setArtifactCandidate(candidateId) {
      const preset = getPantheonSelfCoreArtifactPreset(candidateId);
      artifactCandidateId = candidateId;
      artifactRadiusScale = preset.radiusScale;
      uniforms.surfaceStrength.value = preset.surface.strength;
      uniforms.ringFrequency.value = preset.surface.ringFrequency;
      uniforms.latitudeFrequency.value =
        preset.surface.latitudeFrequency;
      uniforms.wearStrength.value = preset.surface.wearStrength;
      uniforms.roughnessVariation.value =
        preset.surface.roughnessVariation;
      uniforms.timeVariation.value = preset.surface.timeVariation;
      controller.setStyle(preset);
      core.userData.selfCoreArtifactCandidate = candidateId;
      return {
        candidateId,
        radiusScale: artifactRadiusScale,
      };
    },
    setStyle(style) {
      styleColor = new THREE.Color(style.color);
      styleEmissiveColor = new THREE.Color(style.emissiveColor);
      styleEmissiveIntensity = THREE.MathUtils.clamp(
        style.emissiveIntensity,
        0,
        0.12,
      );
      styleMetalness = THREE.MathUtils.clamp(
        style.metalness,
        0.68,
        0.92,
      );
      styleRoughness = THREE.MathUtils.clamp(
        style.roughness,
        0.2,
        0.38,
      );
      styleClearcoat = THREE.MathUtils.clamp(
        style.clearcoat ?? styleClearcoat,
        0,
        1,
      );
      styleClearcoatRoughness = THREE.MathUtils.clamp(
        style.clearcoatRoughness ?? styleClearcoatRoughness,
        0,
        1,
      );
      styleEnvMapIntensity = THREE.MathUtils.clamp(
        style.envMapIntensity ?? styleEnvMapIntensity,
        0,
        1.5,
      );
      material.color.copy(styleColor);
      material.emissive.copy(styleEmissiveColor);
      material.emissiveIntensity = styleEmissiveIntensity;
      material.metalness = styleMetalness;
      material.roughness = styleRoughness;
      material.clearcoat = styleClearcoat;
      material.clearcoatRoughness = styleClearcoatRoughness;
      material.envMapIntensity = styleEnvMapIntensity;
    },
    snapshot() {
      return {
        version: PANTHEON_EFFECTS_VERSION,
        ...SELF_CORE_EFFECT_CONFIG,
        scaleAnimation: false,
        emissive: styleEmissiveIntensity > 0,
        emissiveIntensity: styleEmissiveIntensity,
        color: `#${styleColor.getHexString()}`,
        emissiveColor: `#${styleEmissiveColor.getHexString()}`,
        metalness: styleMetalness,
        roughness: styleRoughness,
        clearcoat: styleClearcoat,
        clearcoatRoughness: styleClearcoatRoughness,
        envMapIntensity: styleEnvMapIntensity,
        materialEnvMapIntensity: material.envMapIntensity,
        gpuEnvMapIntensity:
          material.userData.shader?.uniforms?.envMapIntensity?.value ??
          null,
        envMapUuid: material.envMap?.uuid ?? null,
        explicitEnvironmentMap: material.envMap !== null,
        relationship: {
          activeTheme: relationshipTheme,
          targetInfluence: relationshipTargetInfluence,
          currentInfluence: relationshipCurrentInfluence,
          targetColor: `#${relationshipTargetColor.getHexString()}`,
          currentColor: `#${relationshipCurrentColor.getHexString()}`,
          displayColor: `#${displayColor.getHexString()}`,
        },
        artifact: {
          candidateId: artifactCandidateId,
          radiusScale: artifactRadiusScale,
          surfaceStrength: uniforms.surfaceStrength.value,
          ringFrequency: uniforms.ringFrequency.value,
          latitudeFrequency: uniforms.latitudeFrequency.value,
          wearStrength: uniforms.wearStrength.value,
          roughnessVariation: uniforms.roughnessVariation.value,
          timeVariation: uniforms.timeVariation.value,
          maximumWarmth: {
            hueDegrees: 1,
            saturation: 0.02,
            luminance: 0.03,
          },
          rotationAnimation: false,
          pulseAnimation: false,
          breathingAnimation: false,
        },
        bloom: false,
      };
    },
  };
  controller.setArtifactCandidate(
    DEFAULT_SELF_CORE_ARTIFACT_CANDIDATE,
  );
  return controller;
}
