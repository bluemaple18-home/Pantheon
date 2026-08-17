import type { StarOrbitId } from "../generated/createPantheonStarOrbits.ts";

export const PANTHEON_BAND_MOTION_LOOP_SECONDS = 60;

const TAU = Math.PI * 2;

const BAND_SELF_ROTATION = Object.freeze({
  Constellation: { direction: 1, rhythmAmplitude: 0.1, rhythmPhase: 0.2 },
  Tarot: { direction: -1, rhythmAmplitude: 0.14, rhythmPhase: 1.4 },
  MBTI: { direction: 1, rhythmAmplitude: 0.16, rhythmPhase: 2.6 },
  HumanDesign: { direction: -1, rhythmAmplitude: 0.08, rhythmPhase: 3.8 },
  ZiweiBazi: { direction: 1, rhythmAmplitude: 0.12, rhythmPhase: 5.0 },
} satisfies Record<
  StarOrbitId,
  { direction: 1 | -1; rhythmAmplitude: number; rhythmPhase: number }
>);

export function pantheonMotionLoopProgress(elapsedSeconds: number) {
  const wrapped =
    ((elapsedSeconds % PANTHEON_BAND_MOTION_LOOP_SECONDS) +
      PANTHEON_BAND_MOTION_LOOP_SECONDS) %
    PANTHEON_BAND_MOTION_LOOP_SECONDS;
  return wrapped / PANTHEON_BAND_MOTION_LOOP_SECONDS;
}

export function resolvePantheonSystemMotion(elapsedSeconds: number) {
  const progress = pantheonMotionLoopProgress(elapsedSeconds);
  const phase = progress * TAU;
  return {
    revolutionY: phase,
    swayZ: Math.sin(phase) * 0.006,
  };
}

export function resolvePantheonBandSelfRotation(
  orbitId: StarOrbitId,
  elapsedSeconds: number,
) {
  const progress = pantheonMotionLoopProgress(elapsedSeconds);
  const phase = progress * TAU;
  const config = BAND_SELF_ROTATION[orbitId];
  const rhythmOffset =
    config.rhythmAmplitude *
    (Math.sin(phase + config.rhythmPhase) -
      Math.sin(config.rhythmPhase));
  return config.direction * phase + rhythmOffset;
}
