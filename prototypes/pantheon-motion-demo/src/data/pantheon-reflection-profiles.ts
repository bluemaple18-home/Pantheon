import type { PantheonThemeId } from "./pantheon-theme-config.ts";

export type ReflectionCandidateId =
  | "baseline"
  | "conservative"
  | "editorial"
  | "dramatic";

export type BandReflectionProfile = {
  reflectionRotation: number;
  highlightOffset: number;
  highlightWidth: number;
  highlightStrength: number;
  specularGain: number;
  grazingGain: number;
  darkSideLift: number;
  centerSuppression: number;
};

type ReflectionCandidate = {
  id: ReflectionCandidateId;
  label: string;
  enabled: boolean;
  shoulder: number;
  tintAmount: number;
  profiles: Record<PantheonThemeId, BandReflectionProfile>;
};

const EDITORIAL_PROFILES: Record<
  PantheonThemeId,
  BandReflectionProfile
> = {
  constellation: {
    reflectionRotation: -18,
    highlightOffset: 0.12,
    highlightWidth: 0.22,
    highlightStrength: 0.7,
    specularGain: 0.82,
    grazingGain: 1.12,
    darkSideLift: 0.18,
    centerSuppression: 0.28,
  },
  tarot: {
    reflectionRotation: 24,
    highlightOffset: 0.34,
    highlightWidth: 0.18,
    highlightStrength: 0.76,
    specularGain: 0.78,
    grazingGain: 1,
    darkSideLift: 0.14,
    centerSuppression: 0.34,
  },
  mbti: {
    reflectionRotation: -36,
    highlightOffset: 0.58,
    highlightWidth: 0.16,
    highlightStrength: 0.68,
    specularGain: 0.72,
    grazingGain: 0.96,
    darkSideLift: 0.16,
    centerSuppression: 0.38,
  },
  "human-design": {
    reflectionRotation: 42,
    highlightOffset: 0.76,
    highlightWidth: 0.17,
    highlightStrength: 0.72,
    specularGain: 0.76,
    grazingGain: 1.04,
    darkSideLift: 0.17,
    centerSuppression: 0.32,
  },
  "ziwei-bazi": {
    reflectionRotation: 8,
    highlightOffset: 0.9,
    highlightWidth: 0.2,
    highlightStrength: 0.74,
    specularGain: 0.8,
    grazingGain: 1.08,
    darkSideLift: 0.15,
    centerSuppression: 0.3,
  },
};

function mapProfiles(
  transform: (
    profile: BandReflectionProfile,
  ) => BandReflectionProfile,
) {
  return Object.fromEntries(
    Object.entries(EDITORIAL_PROFILES).map(([id, profile]) => [
      id,
      transform(profile),
    ]),
  ) as Record<PantheonThemeId, BandReflectionProfile>;
}

export const PANTHEON_REFLECTION_CANDIDATES: Record<
  ReflectionCandidateId,
  ReflectionCandidate
> = {
  baseline: {
    id: "baseline",
    label: "Baseline · Shared Reflection",
    enabled: false,
    shoulder: 0,
    tintAmount: 0,
    profiles: EDITORIAL_PROFILES,
  },
  conservative: {
    id: "conservative",
    label: "Candidate A · Conservative",
    enabled: true,
    shoulder: 0.72,
    tintAmount: 0.3,
    profiles: mapProfiles((profile) => ({
      ...profile,
      highlightWidth: Math.min(0.25, profile.highlightWidth * 1.08),
      highlightStrength: profile.highlightStrength * 0.82,
      specularGain: profile.specularGain * 0.94,
      grazingGain: Math.max(1, profile.grazingGain),
      darkSideLift: Math.min(0.2, profile.darkSideLift + 0.025),
      centerSuppression: Math.min(
        0.4,
        profile.centerSuppression + 0.035,
      ),
    })),
  },
  editorial: {
    id: "editorial",
    label: "Candidate B · Editorial",
    enabled: true,
    shoulder: 0.58,
    tintAmount: 0.24,
    profiles: EDITORIAL_PROFILES,
  },
  dramatic: {
    id: "dramatic",
    label: "Candidate C · Dramatic",
    enabled: true,
    shoulder: 0.46,
    tintAmount: 0.2,
    profiles: mapProfiles((profile) => ({
      ...profile,
      highlightWidth: Math.max(0.13, profile.highlightWidth * 0.82),
      highlightStrength: Math.min(
        0.88,
        profile.highlightStrength * 1.12,
      ),
      specularGain: Math.min(0.9, profile.specularGain * 1.06),
      grazingGain: profile.grazingGain * 1.04,
      darkSideLift: Math.max(0.12, profile.darkSideLift - 0.02),
      centerSuppression: Math.min(
        0.4,
        profile.centerSuppression + 0.02,
      ),
    })),
  },
};

export const DEFAULT_REFLECTION_CANDIDATE: ReflectionCandidateId =
  "editorial";

export const REFLECTION_CORE_SUPPRESSION = {
  inner: 0.18,
  outer: 0.52,
  grazingPower: 2.7,
} as const;
