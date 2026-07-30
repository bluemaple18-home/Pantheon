import * as THREE from "three";
import { PANTHEON_IDENTITY_MACRO_BASELINE } from "./pantheonSurfaceIdentityPresets.ts";

export type IdentityPhase = 1 | 2 | 3;
export type IdentityDebugMode =
  | "beauty"
  | "roughness"
  | "normal"
  | "brush";

type IdentityMaterialControls = {
  phase: IdentityPhase;
  mesoStrength: number;
  microNormalStrength: number;
  roughnessVariation: number;
  reliefDepth: number;
  reliefDensity: number;
  brushScale: number;
  brushIrregularity: number;
  polishedZoneStrength: number;
  oxidizedZoneStrength: number;
  noMicro: boolean;
  noRelief: boolean;
  monochrome: boolean;
  debugMode: IdentityDebugMode;
};

const DEBUG_MODE: Record<IdentityDebugMode, number> = {
  beauty: 0,
  roughness: 1,
  normal: 2,
  brush: 3,
};

export async function createPantheonIdentityMaterial(
  environmentMap: THREE.Texture,
) {
  const loader = new THREE.TextureLoader();
  const [maskAtlas, normalAtlas] = await Promise.all([
    loader.loadAsync("/material-identity/pantheon-identity-mask-atlas.png"),
    loader.loadAsync("/material-identity/pantheon-identity-normal-atlas.png"),
  ]);
  maskAtlas.colorSpace = THREE.NoColorSpace;
  normalAtlas.colorSpace = THREE.NoColorSpace;
  maskAtlas.wrapS = THREE.ClampToEdgeWrapping;
  maskAtlas.wrapT = THREE.ClampToEdgeWrapping;
  normalAtlas.wrapS = THREE.ClampToEdgeWrapping;
  normalAtlas.wrapT = THREE.ClampToEdgeWrapping;
  normalAtlas.repeat.set(1, 0.5);
  normalAtlas.offset.set(0, 0);

  const controls: IdentityMaterialControls = {
    phase: 3,
    mesoStrength: 1,
    microNormalStrength: 1,
    roughnessVariation: 1,
    reliefDepth: 1,
    reliefDensity: 1,
    brushScale: 1,
    brushIrregularity: 0,
    polishedZoneStrength: 1,
    oxidizedZoneStrength: 1,
    noMicro: false,
    noRelief: false,
    monochrome: true,
    debugMode: "beauty",
  };
  const uniforms = {
    uMesoStrength: { value: controls.mesoStrength },
    uRoughnessVariation: { value: controls.roughnessVariation },
    uNormalStrength: { value: controls.microNormalStrength },
    uBrushScale: { value: controls.brushScale },
    uBrushIrregularity: { value: controls.brushIrregularity },
    uPolishedZoneStrength: { value: controls.polishedZoneStrength },
    uOxidizedZoneStrength: { value: controls.oxidizedZoneStrength },
    uMonochrome: { value: 1 },
    uDebugMode: { value: 0 },
    uSelectedIdentity: { value: -1 },
    uGrayStart: {
      value: new THREE.Color(PANTHEON_IDENTITY_MACRO_BASELINE.baseColor),
    },
    uGrayEnd: {
      value: new THREE.Color(PANTHEON_IDENTITY_MACRO_BASELINE.secondaryColor),
    },
  };

  const material = new THREE.MeshPhysicalMaterial({
    color: "#ffffff",
    metalness: PANTHEON_IDENTITY_MACRO_BASELINE.metalness,
    roughness: PANTHEON_IDENTITY_MACRO_BASELINE.roughness,
    clearcoat: PANTHEON_IDENTITY_MACRO_BASELINE.clearcoat,
    envMap: environmentMap,
    envMapIntensity: PANTHEON_IDENTITY_MACRO_BASELINE.envMapIntensity,
    roughnessMap: maskAtlas,
    normalMap: normalAtlas,
    normalScale: new THREE.Vector2(1, 1),
    side: THREE.FrontSide,
  });
  material.name = "PantheonIdentitySharedPhysicalMaterial";
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace(
        "void main() {",
        `
attribute float aIdentity;
attribute float aBandV;
attribute vec3 aThemeColor;
varying float vPantheonIdentity;
varying float vPantheonBandV;
varying vec3 vPantheonThemeColor;
void main() {
  vPantheonIdentity = aIdentity;
  vPantheonBandV = aBandV;
  vPantheonThemeColor = aThemeColor;
`,
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "void main() {",
        `
uniform float uMesoStrength;
uniform float uRoughnessVariation;
uniform float uNormalStrength;
uniform float uBrushScale;
uniform float uBrushIrregularity;
uniform float uPolishedZoneStrength;
uniform float uOxidizedZoneStrength;
uniform float uMonochrome;
uniform float uDebugMode;
uniform float uSelectedIdentity;
uniform vec3 uGrayStart;
uniform vec3 uGrayEnd;
varying float vPantheonIdentity;
varying float vPantheonBandV;
varying vec3 vPantheonThemeColor;
void main() {
  if (
    uSelectedIdentity > -0.5 &&
    abs(vPantheonIdentity - uSelectedIdentity) > 0.25
  ) discard;
`,
      )
      .replace(
        "#include <color_fragment>",
        `
#include <color_fragment>
vec3 pantheonGray = mix(uGrayStart, uGrayEnd, smoothstep(0.08, 0.92, vPantheonBandV));
diffuseColor.rgb *= mix(vPantheonThemeColor, pantheonGray, uMonochrome);
`,
      )
      .replace(
        "#include <roughnessmap_fragment>",
        `
float roughnessFactor = roughness;
#ifdef USE_ROUGHNESSMAP
  float pantheonTile = floor(vPantheonIdentity + 0.5);
  float pantheonLocalU = fract(vRoughnessMapUv.x * 5.0);
  pantheonLocalU = fract(
    (pantheonLocalU - 0.5) * uBrushScale + 0.5 +
    sin(vRoughnessMapUv.y * 37.0 + pantheonTile * 2.3) *
    uBrushIrregularity * 0.018
  );
  vec2 pantheonMaskUv = vec2(
    (pantheonTile + pantheonLocalU) / 5.0,
    vRoughnessMapUv.y
  );
  vec4 pantheonIdentityMask = texture2D(roughnessMap, pantheonMaskUv);
  float roughnessDelta =
    (pantheonIdentityMask.g - 0.5) * 0.5 +
    pantheonIdentityMask.a * 0.16 * uOxidizedZoneStrength -
    pantheonIdentityMask.b * 0.18 * uPolishedZoneStrength;
  roughnessFactor = clamp(
    roughness + roughnessDelta * uRoughnessVariation * uMesoStrength,
    0.18,
    0.78
  );
#endif
`,
      )
      .replace(
        "#include <normal_fragment_maps>",
        `
#ifdef USE_NORMALMAP_TANGENTSPACE
  float pantheonNormalTile = floor(vPantheonIdentity + 0.5);
  float pantheonNormalLocalU = fract(vNormalMapUv.x * 5.0);
  pantheonNormalLocalU = fract(
    (pantheonNormalLocalU - 0.5) * uBrushScale + 0.5 +
    sin(vNormalMapUv.y * 37.0 + pantheonNormalTile * 2.3) *
    uBrushIrregularity * 0.018
  );
  vec2 pantheonNormalUv = vec2(
    (pantheonNormalTile + pantheonNormalLocalU) / 5.0,
    vNormalMapUv.y
  );
  vec3 mapN = texture2D(normalMap, pantheonNormalUv).xyz * 2.0 - 1.0;
  mapN.xy *= normalScale * uNormalStrength;
  normal = normalize(tbn * mapN);
#endif
`,
      )
      .replace(
        "#include <opaque_fragment>",
        `
#include <opaque_fragment>
if (uDebugMode > 0.5) {
  float debugTile = floor(vPantheonIdentity + 0.5);
  float debugLocalU = fract(vRoughnessMapUv.x * 5.0);
  vec2 debugUv = vec2((debugTile + debugLocalU) / 5.0, vRoughnessMapUv.y);
  vec4 identityMaskDebug = texture2D(roughnessMap, debugUv);
  if (uDebugMode < 1.5) {
    gl_FragColor.rgb = vec3(1.0 - identityMaskDebug.g);
  } else if (uDebugMode < 2.5) {
    gl_FragColor.rgb = texture2D(normalMap, vNormalMapUv).xyz;
  } else {
    gl_FragColor.rgb = vec3(identityMaskDebug.r);
  }
}
`,
      );
    material.userData.shader = shader;
  };
  material.customProgramCacheKey = () => "pantheon-identity-material-v1";

  const sync = () => {
    const normalEnabled =
      controls.phase >= 2 && !controls.noMicro
        ? controls.microNormalStrength
        : 0;
    const combinedRelief = controls.phase >= 3 && !controls.noRelief;
    normalAtlas.offset.y = combinedRelief ? 0.5 : 0;
    uniforms.uMesoStrength.value = controls.mesoStrength;
    uniforms.uRoughnessVariation.value = controls.roughnessVariation;
    uniforms.uNormalStrength.value =
      normalEnabled *
      (combinedRelief ? controls.reliefDepth * controls.reliefDensity : 1);
    uniforms.uBrushScale.value = controls.brushScale;
    uniforms.uBrushIrregularity.value = controls.brushIrregularity;
    uniforms.uPolishedZoneStrength.value = controls.polishedZoneStrength;
    uniforms.uOxidizedZoneStrength.value = controls.oxidizedZoneStrength;
    uniforms.uMonochrome.value = controls.monochrome ? 1 : 0;
    uniforms.uDebugMode.value = DEBUG_MODE[controls.debugMode];
  };

  const setControls = (patch: Partial<IdentityMaterialControls>) => {
    Object.assign(controls, patch);
    sync();
  };
  sync();

  return {
    material,
    maskAtlas,
    normalAtlas,
    controls,
    setControls,
    setSelectedIdentity: (identity: number | null) => {
      uniforms.uSelectedIdentity.value = identity ?? -1;
    },
    snapshot: () => ({
      ...controls,
      materialInstances: 1,
      addedTextureSamples: {
        phase1: 1,
        phase2: 2,
        phase3: 2,
      },
      atlas: {
        mask: [1024, 256],
        normal: [1024, 512],
        regions: 5,
      },
    }),
    dispose: () => {
      material.dispose();
      maskAtlas.dispose();
      normalAtlas.dispose();
    },
  };
}
