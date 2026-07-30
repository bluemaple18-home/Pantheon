import * as THREE from "three";
import {
  CORE_RUNE_RELATIONSHIP_CONFIG,
} from "../data/pantheon-effects-config.ts";
import {
  PANTHEON_THEME_CONFIGS,
  type PantheonThemeId,
} from "../data/pantheon-theme-config.ts";
import type {
  SelfCoreEffectController,
} from "./configurePantheonSelfCoreEffect.ts";

type VisualState = "Idle" | "Hovered" | "Selected" | "Background";

type MaterialSnapshot = {
  visuals: Record<
    PantheonThemeId,
    {
      state: VisualState;
      energyPhase: number;
      energyPulseCount: number;
    }
  >;
};

type InfluenceSnapshot = {
  energyPositions: number[];
  projectedDistance: number;
  orbitClosestDistance: number;
  relativeProjectedDistance: number;
  influence: number;
};

const DEFAULT_CORE_COLOR = "#c49a4a";
const PULSE_OFFSETS = [0, 0.5, 0.337, 0.581, 0.793] as const;
const interpolationPoint = new THREE.Vector3();

function smoothstep(edge0: number, edge1: number, value: number) {
  const ratio = THREE.MathUtils.clamp(
    (value - edge0) / (edge1 - edge0),
    0,
    1,
  );
  return ratio * ratio * (3 - 2 * ratio);
}

function pointAtProgress(
  samples: readonly [number, number, number][],
  progress: number,
  target: THREE.Vector3,
) {
  const wrapped = ((progress % 1) + 1) % 1;
  const scaled = wrapped * samples.length;
  const index = Math.floor(scaled) % samples.length;
  const next = (index + 1) % samples.length;
  return target
    .fromArray(samples[index])
    .lerp(
      interpolationPoint.fromArray(samples[next]),
      scaled - index,
    );
}

export function configurePantheonCoreRuneRelationship(options: {
  root: THREE.Object3D;
  core: THREE.Object3D;
  camera: THREE.Camera;
  viewport: HTMLElement;
  centerlineSamples: Record<
    string,
    [number, number, number][]
  >;
  coreEffect: SelfCoreEffectController;
}) {
  const {
    root,
    core,
    camera,
    viewport,
    centerlineSamples,
    coreEffect,
  } = options;
  const localPoint = new THREE.Vector3();
  const projectedPoint = new THREE.Vector3();
  const coreProjected = new THREE.Vector3();
  let activeTheme: PantheonThemeId | null = null;
  let forceTheme: PantheonThemeId | null = null;
  let frameIndex = 0;
  const orbitClosestDistances = {} as Record<PantheonThemeId, number>;
  let influences = {} as Record<PantheonThemeId, InfluenceSnapshot>;

  function update(
    snapshot: MaterialSnapshot,
    motionOff: boolean,
  ) {
    if (motionOff) {
      activeTheme = null;
      influences = Object.fromEntries(
        PANTHEON_THEME_CONFIGS.map(({ id }) => [
          id,
          {
            energyPositions: [],
            projectedDistance: Number.POSITIVE_INFINITY,
            orbitClosestDistance: Number.POSITIVE_INFINITY,
            relativeProjectedDistance: Number.POSITIVE_INFINITY,
            influence: 0,
          },
        ]),
      ) as unknown as Record<PantheonThemeId, InfluenceSnapshot>;
      coreEffect.setRelationshipTarget({
        themeId: null,
        color: DEFAULT_CORE_COLOR,
        influence: 0,
      });
      return;
    }

    root.updateMatrixWorld(true);
    camera.updateMatrixWorld(true);
    core.getWorldPosition(coreProjected).project(camera);
    const width = Math.max(1, viewport.clientWidth);
    const height = Math.max(1, viewport.clientHeight);
    const normalization = Math.max(1, Math.min(width, height));
    const shouldCalibrate =
      frameIndex %
        CORE_RUNE_RELATIONSHIP_CONFIG
          .proximityCalibrationIntervalFrames ===
        0 ||
      PANTHEON_THEME_CONFIGS.some(
        ({ id }) => !Number.isFinite(orbitClosestDistances[id]),
      );
    frameIndex += 1;

    if (shouldCalibrate) {
      PANTHEON_THEME_CONFIGS.forEach((theme) => {
        const samples = centerlineSamples[theme.orbitId];
        const stride = Math.max(
          1,
          Math.floor(
            samples.length /
              CORE_RUNE_RELATIONSHIP_CONFIG
                .proximityCalibrationSamples,
          ),
        );
        let closestDistance = Number.POSITIVE_INFINITY;
        for (let index = 0; index < samples.length; index += stride) {
          localPoint
            .fromArray(samples[index])
            .applyMatrix4(root.matrixWorld);
          projectedPoint.copy(localPoint).project(camera);
          if (projectedPoint.z < -1 || projectedPoint.z > 1) continue;
          const pixelDistance = Math.hypot(
            (projectedPoint.x - coreProjected.x) * width * 0.5,
            (projectedPoint.y - coreProjected.y) * height * 0.5,
          );
          closestDistance = Math.min(
            closestDistance,
            pixelDistance / normalization,
          );
        }
        orbitClosestDistances[theme.id] = closestDistance;
      });
    }

    influences = Object.fromEntries(
      PANTHEON_THEME_CONFIGS.map((theme) => {
        const visual = snapshot.visuals[theme.id];
        const samples = centerlineSamples[theme.orbitId];
        const pulseCount = Math.max(
          0,
          Math.min(PULSE_OFFSETS.length, visual.energyPulseCount),
        );
        const energyPositions = PULSE_OFFSETS.slice(0, pulseCount).map(
          (offset) => ((visual.energyPhase + offset) % 1 + 1) % 1,
        );
        let minimumDistance = Number.POSITIVE_INFINITY;
        energyPositions.forEach((energyPosition) => {
          pointAtProgress(samples, energyPosition, localPoint)
            .applyMatrix4(root.matrixWorld);
          projectedPoint.copy(localPoint).project(camera);
          if (projectedPoint.z < -1 || projectedPoint.z > 1) return;
          const pixelDistance = Math.hypot(
            (projectedPoint.x - coreProjected.x) * width * 0.5,
            (projectedPoint.y - coreProjected.y) * height * 0.5,
          );
          minimumDistance = Math.min(
            minimumDistance,
            pixelDistance / normalization,
          );
        });
        const orbitClosestDistance =
          orbitClosestDistances[theme.id] ??
          Number.POSITIVE_INFINITY;
        const relativeProjectedDistance = Math.max(
          0,
          minimumDistance - orbitClosestDistance,
        );
        const proximity =
          1 -
          smoothstep(
            CORE_RUNE_RELATIONSHIP_CONFIG.projectionInnerRadius,
            CORE_RUNE_RELATIONSHIP_CONFIG.projectionOuterRadius,
            relativeProjectedDistance,
          );
        const stateWeight =
          CORE_RUNE_RELATIONSHIP_CONFIG.stateInfluence[visual.state];
        return [
          theme.id,
          {
            energyPositions,
            projectedDistance: minimumDistance,
            orbitClosestDistance,
            relativeProjectedDistance,
            influence: proximity * stateWeight,
          },
        ];
      }),
    ) as Record<PantheonThemeId, InfluenceSnapshot>;

    if (forceTheme) {
      activeTheme = forceTheme;
      coreEffect.setRelationshipTarget({
        themeId: forceTheme,
        color:
          CORE_RUNE_RELATIONSHIP_CONFIG.themeColors[forceTheme],
        influence: CORE_RUNE_RELATIONSHIP_CONFIG.maximumInfluence,
      });
      return;
    }

    const ranked = PANTHEON_THEME_CONFIGS.map(({ id }) => ({
      id,
      influence: influences[id].influence,
    })).sort((a, b) => b.influence - a.influence);
    const challenger = ranked[0];
    if (
      activeTheme &&
      influences[activeTheme].influence +
        CORE_RUNE_RELATIONSHIP_CONFIG.hysteresis >=
        challenger.influence
    ) {
      // 保留目前主題，避免兩條 Band 接近時逐幀搶占。
    } else {
      activeTheme =
        challenger.influence > 0.015 ? challenger.id : null;
    }
    const influence = activeTheme
      ? influences[activeTheme].influence
      : 0;
    if (influence <= 0.01) activeTheme = null;
    coreEffect.setRelationshipTarget({
      themeId: activeTheme,
      color: activeTheme
        ? CORE_RUNE_RELATIONSHIP_CONFIG.themeColors[activeTheme]
        : DEFAULT_CORE_COLOR,
      influence,
    });
  }

  return {
    update,
    setForceTheme(themeId: PantheonThemeId | null) {
      forceTheme = themeId;
    },
    snapshot() {
      return {
        mode: "screen-space-relative-proximity",
        sharesSurfaceEnergyProgress: true,
        activeTheme,
        forceTheme,
        influences,
        projectionInnerRadius:
          CORE_RUNE_RELATIONSHIP_CONFIG.projectionInnerRadius,
        projectionOuterRadius:
          CORE_RUNE_RELATIONSHIP_CONFIG.projectionOuterRadius,
        hysteresis: CORE_RUNE_RELATIONSHIP_CONFIG.hysteresis,
        themeColors: {
          ...CORE_RUNE_RELATIONSHIP_CONFIG.themeColors,
        },
      };
    },
  };
}
