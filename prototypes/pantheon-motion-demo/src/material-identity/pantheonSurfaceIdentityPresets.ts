export type PantheonSurfaceIdentityId =
  | "constellation"
  | "tarot"
  | "mbti"
  | "human-design"
  | "ziwei-bazi";

export type BandSurfaceIdentity = {
  id: PantheonSurfaceIdentityId;
  label: string;
  process: string;
  brushDirection:
    | "longitudinal"
    | "radial-arc"
    | "segmented-u"
    | "bead-channel"
    | "cross-hand";
  brushScale: number;
  brushAspect: number;
  brushIrregularity: number;
  brushStrength: number;
  roughnessBaseOffset: number;
  roughnessVariation: number;
  roughnessPatternScale: number;
  microNormalStrength: number;
  microNormalScale: number;
  reliefDepth: number;
  reliefDensity: number;
  reliefEdgeSharpness: number;
  polishedZoneStrength: number;
  oxidizedZoneStrength: number;
  surfaceAtlasRegion: [number, number, number, number];
};

const ATLAS_TILE_WIDTH = 0.2;

export const PANTHEON_SURFACE_IDENTITIES: readonly BandSurfaceIdentity[] =
  Object.freeze([
    {
      id: "constellation",
      label: "星座",
      process: "Blued steel · long precision brushing",
      brushDirection: "longitudinal",
      brushScale: 0.72,
      brushAspect: 0.18,
      brushIrregularity: 0.12,
      brushStrength: 0.34,
      roughnessBaseOffset: -0.025,
      roughnessVariation: 0.15,
      roughnessPatternScale: 0.62,
      microNormalStrength: 0.31,
      microNormalScale: 0.72,
      reliefDepth: 0.16,
      reliefDensity: 0.12,
      reliefEdgeSharpness: 0.76,
      polishedZoneStrength: 0.48,
      oxidizedZoneStrength: 0.08,
      surfaceAtlasRegion: [0, 0, ATLAS_TILE_WIDTH, 1],
    },
    {
      id: "tarot",
      label: "塔羅",
      process: "Oxidized metal · radial ritual framing",
      brushDirection: "radial-arc",
      brushScale: 0.48,
      brushAspect: 0.42,
      brushIrregularity: 0.16,
      brushStrength: 0.4,
      roughnessBaseOffset: 0.035,
      roughnessVariation: 0.28,
      roughnessPatternScale: 0.46,
      microNormalStrength: 0.42,
      microNormalScale: 0.52,
      reliefDepth: 0.42,
      reliefDensity: 0.3,
      reliefEdgeSharpness: 0.86,
      polishedZoneStrength: 0.72,
      oxidizedZoneStrength: 0.38,
      surfaceAtlasRegion: [ATLAS_TILE_WIDTH, 0, ATLAS_TILE_WIDTH, 1],
    },
    {
      id: "mbti",
      label: "MBTI",
      process: "Anodized alloy · segmented precision milling",
      brushDirection: "segmented-u",
      brushScale: 0.58,
      brushAspect: 0.24,
      brushIrregularity: 0.04,
      brushStrength: 0.45,
      roughnessBaseOffset: -0.005,
      roughnessVariation: 0.24,
      roughnessPatternScale: 0.58,
      microNormalStrength: 0.38,
      microNormalScale: 0.6,
      reliefDepth: 0.28,
      reliefDensity: 0.42,
      reliefEdgeSharpness: 0.92,
      polishedZoneStrength: 0.56,
      oxidizedZoneStrength: 0,
      surfaceAtlasRegion: [ATLAS_TILE_WIDTH * 2, 0, ATLAS_TILE_WIDTH, 1],
    },
    {
      id: "human-design",
      label: "人類圖",
      process: "Bead-blasted titanium · polished channels",
      brushDirection: "bead-channel",
      brushScale: 0.86,
      brushAspect: 0.92,
      brushIrregularity: 0.09,
      brushStrength: 0.26,
      roughnessBaseOffset: 0.055,
      roughnessVariation: 0.3,
      roughnessPatternScale: 0.72,
      microNormalStrength: 0.5,
      microNormalScale: 0.86,
      reliefDepth: 0.22,
      reliefDensity: 0.2,
      reliefEdgeSharpness: 0.66,
      polishedZoneStrength: 0.8,
      oxidizedZoneStrength: 0,
      surfaceAtlasRegion: [ATLAS_TILE_WIDTH * 3, 0, ATLAS_TILE_WIDTH, 1],
    },
    {
      id: "ziwei-bazi",
      label: "紫微八字",
      process: "Aged bronze · cross-hand brushing",
      brushDirection: "cross-hand",
      brushScale: 0.4,
      brushAspect: 0.34,
      brushIrregularity: 0.38,
      brushStrength: 0.52,
      roughnessBaseOffset: 0.025,
      roughnessVariation: 0.34,
      roughnessPatternScale: 0.38,
      microNormalStrength: 0.46,
      microNormalScale: 0.44,
      reliefDepth: 0.38,
      reliefDensity: 0.34,
      reliefEdgeSharpness: 0.7,
      polishedZoneStrength: 0.62,
      oxidizedZoneStrength: 0.58,
      surfaceAtlasRegion: [ATLAS_TILE_WIDTH * 4, 0, ATLAS_TILE_WIDTH, 1],
    },
  ]);

export const PANTHEON_IDENTITY_MACRO_BASELINE = Object.freeze({
  baseColor: "#8f9699",
  secondaryColor: "#b1b7b8",
  metalness: 0.8,
  roughness: 0.42,
  clearcoat: 0,
  envMapIntensity: 1.288,
});
