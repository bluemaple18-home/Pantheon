export type PantheonSelfCoreCandidateId =
  | "baseline"
  | "candidate-a"
  | "candidate-b"
  | "visual-target-v1";

export type PantheonSelfCoreArtifactPreset = {
  id: PantheonSelfCoreCandidateId;
  label: string;
  radiusScale: number;
  color: string;
  emissiveColor: string;
  emissiveIntensity: number;
  metalness: number;
  roughness: number;
  clearcoat: number;
  clearcoatRoughness: number;
  envMapIntensity: number;
  surface: {
    strength: number;
    ringFrequency: number;
    latitudeFrequency: number;
    wearStrength: number;
    roughnessVariation: number;
    timeVariation: number;
  };
};

export const DEFAULT_SELF_CORE_ARTIFACT_CANDIDATE =
  "visual-target-v1" satisfies PantheonSelfCoreCandidateId;

export const PANTHEON_SELF_CORE_ARTIFACT_PRESETS = Object.freeze({
  baseline: Object.freeze({
    id: "baseline",
    label: "Baseline — Metal Sphere",
    radiusScale: 1,
    color: "#c9a154",
    emissiveColor: "#52370d",
    emissiveIntensity: 0.07,
    metalness: 0.76,
    roughness: 0.3,
    clearcoat: 0,
    clearcoatRoughness: 0.28,
    envMapIntensity: 0.9,
    surface: Object.freeze({
      strength: 0,
      ringFrequency: 0,
      latitudeFrequency: 0,
      wearStrength: 0,
      roughnessVariation: 0,
      timeVariation: 0,
    }),
  }),
  "candidate-a": Object.freeze({
    id: "candidate-a",
    label: "Candidate A — Quiet Artifact",
    radiusScale: 0.9,
    color: "#936b35",
    emissiveColor: "#000000",
    emissiveIntensity: 0,
    metalness: 0.84,
    roughness: 0.4,
    clearcoat: 0.04,
    clearcoatRoughness: 0.42,
    envMapIntensity: 0.9,
    surface: Object.freeze({
      strength: 0.018,
      ringFrequency: 30,
      latitudeFrequency: 9,
      wearStrength: 0.035,
      roughnessVariation: 0.022,
      timeVariation: 0.008,
    }),
  }),
  "candidate-b": Object.freeze({
    id: "candidate-b",
    label: "Candidate B — Time-Worn Artifact",
    radiusScale: 0.85,
    color: "#865f2f",
    emissiveColor: "#000000",
    emissiveIntensity: 0,
    metalness: 0.82,
    roughness: 0.43,
    clearcoat: 0.025,
    clearcoatRoughness: 0.48,
    envMapIntensity: 0.9,
    surface: Object.freeze({
      strength: 0.028,
      ringFrequency: 36,
      latitudeFrequency: 11,
      wearStrength: 0.055,
      roughnessVariation: 0.032,
      timeVariation: 0.01,
    }),
  }),
  "visual-target-v1": Object.freeze({
    id: "visual-target-v1",
    label: "Visual Target — Ancient Gold Artifact",
    radiusScale: 0.96,
    color: "#754315",
    emissiveColor: "#190c02",
    emissiveIntensity: 0.012,
    metalness: 0.9,
    roughness: 0.25,
    clearcoat: 0.045,
    clearcoatRoughness: 0.24,
    envMapIntensity: 1.02,
    surface: Object.freeze({
      strength: 0.01,
      ringFrequency: 28,
      latitudeFrequency: 7,
      wearStrength: 0.018,
      roughnessVariation: 0.012,
      timeVariation: 0.005,
    }),
  }),
} satisfies Record<
  PantheonSelfCoreCandidateId,
  Readonly<PantheonSelfCoreArtifactPreset>
>);

export function getPantheonSelfCoreArtifactPreset(
  candidateId: PantheonSelfCoreCandidateId,
) {
  return PANTHEON_SELF_CORE_ARTIFACT_PRESETS[candidateId];
}
