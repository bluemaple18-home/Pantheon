import {
  PANTHEON_THEME_CONFIGS,
  type PantheonThemeId,
} from "../data/pantheon-theme-config.ts";
import { RIBBON_PROGRESS } from "../data/pantheon-material-config.ts";

export type OrbitVisualState =
  | "Idle"
  | "Hovered"
  | "Selected"
  | "Background";

export interface OrbitInteractionState {
  hoveredTheme: PantheonThemeId | null;
  selectedTheme: PantheonThemeId | null;
  geometryLocked: true;
  autoRotate: boolean;
  reducedMotion: boolean;
  transitionProgress: number;
  ribbonProgress: Record<PantheonThemeId, number>;
  mobiusTwistProgress: Record<PantheonThemeId, number>;
  runeFlowProgress: Record<PantheonThemeId, number>;
  brightness: Record<PantheonThemeId, number>;
  saturation: Record<PantheonThemeId, number>;
}

export const INTERACTION_TIMING = {
  hoverMs: 500,
  selectedMs: 650,
  corePulseMs: 760,
} as const;

const themeIds = PANTHEON_THEME_CONFIGS.map(({ id }) => id);

function recordWith(value: number): Record<PantheonThemeId, number> {
  return Object.fromEntries(themeIds.map((id) => [id, value])) as Record<
    PantheonThemeId,
    number
  >;
}

export function createPantheonInteractionState(): OrbitInteractionState {
  return {
    hoveredTheme: null,
    selectedTheme: null,
    geometryLocked: true,
    autoRotate: true,
    reducedMotion: false,
    transitionProgress: 1,
    ribbonProgress: recordWith(RIBBON_PROGRESS.idle),
    mobiusTwistProgress: recordWith(0),
    runeFlowProgress: recordWith(0),
    brightness: recordWith(1),
    saturation: recordWith(1),
  };
}

export function resolveOrbitVisualState(
  state: OrbitInteractionState,
  themeId: PantheonThemeId,
): OrbitVisualState {
  if (state.selectedTheme === themeId) return "Selected";
  if (state.selectedTheme) return "Background";
  if (state.hoveredTheme === themeId) return "Hovered";
  return "Idle";
}

export function visualTargets(visualState: OrbitVisualState) {
  // Final Balance：互動只做克制的材質權重變化，Geometry 永遠不變。
  return {
    ribbon:
      visualState === "Selected"
        ? RIBBON_PROGRESS.selected
        : visualState === "Hovered"
          ? RIBBON_PROGRESS.hover
          : RIBBON_PROGRESS.idle,
    brightness:
      visualState === "Selected"
        ? 1.08
        : visualState === "Hovered"
          ? 1.04
          : visualState === "Background"
            ? 0.8
            : 1,
    saturation:
      visualState === "Selected"
        ? 1.05
        : visualState === "Hovered"
          ? 1.03
          : visualState === "Background"
            ? 0.8
            : 1,
    opacity: 1,
  };
}

export function smoothToward(
  current: number,
  target: number,
  deltaSeconds: number,
  durationMs: number,
) {
  if (durationMs <= 0) return target;
  const alpha = 1 - Math.exp((-deltaSeconds * 1000 * 4.6) / durationMs);
  return current + (target - current) * alpha;
}
