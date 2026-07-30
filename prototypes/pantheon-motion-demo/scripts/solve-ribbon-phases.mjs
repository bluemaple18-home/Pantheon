import * as THREE from "three";
import geometryLock from "../geometry/pantheon-orbits-v1.json" with {
  type: "json",
};

const PHASE_STEP = 5;
const SAMPLE_COUNT = 180;
const NATURAL_ROLL_AMPLITUDE = 8;
const VIEWS = {
  front: new THREE.Vector3(0, 0, 1).normalize(),
  "front-left": new THREE.Vector3(-2.85, 0.65, 3.2).normalize(),
  side: new THREE.Vector3(1, 0, 0).normalize(),
};
const ROLL_PHASES = {
  Constellation: 18,
  Tarot: 91,
  MBTI: 157,
  HumanDesign: 229,
  ZiweiBazi: 307,
};

function orientationFromConfig(config) {
  const azimuth = new THREE.Quaternion().setFromAxisAngle(
    new THREE.Vector3(0, 0, 1),
    THREE.MathUtils.degToRad(config.azimuth),
  );
  const inclination = new THREE.Quaternion().setFromAxisAngle(
    new THREE.Vector3(1, 0, 0),
    THREE.MathUtils.degToRad(config.inclination),
  );
  const roll = new THREE.Quaternion().setFromAxisAngle(
    new THREE.Vector3(0, 0, 1),
    THREE.MathUtils.degToRad(config.roll),
  );
  return azimuth.multiply(inclination).multiply(roll).normalize();
}

function frameSamples(config, phaseDegrees, naturalRoll) {
  const orientation = orientationFromConfig(config);
  const rollPhase = THREE.MathUtils.degToRad(ROLL_PHASES[config.id]);
  return Array.from({ length: SAMPLE_COUNT }, (_, index) => {
    const t = index / SAMPLE_COUNT;
    const angle = t * Math.PI * 2 + config.phase;
    const point = new THREE.Vector3(
      config.semiMajorAxis * Math.cos(angle),
      config.semiMinorAxis * Math.sin(angle),
      0,
    );
    const tangent = new THREE.Vector3(
      -config.semiMajorAxis * Math.sin(angle),
      config.semiMinorAxis * Math.cos(angle),
      0,
    ).normalize();
    const side = point
      .clone()
      .addScaledVector(tangent, -point.dot(tangent))
      .normalize();
    const roll =
      THREE.MathUtils.degToRad(phaseDegrees) +
      (naturalRoll
        ? THREE.MathUtils.degToRad(NATURAL_ROLL_AMPLITUDE) *
          Math.sin(t * Math.PI * 2 + rollPhase)
        : 0);
    side.applyAxisAngle(tangent, roll).normalize();
    const normal = new THREE.Vector3()
      .crossVectors(tangent, side)
      .normalize();
    return {
      point: point.applyQuaternion(orientation),
      tangent: tangent.applyQuaternion(orientation),
      side: side.applyQuaternion(orientation),
      normal: normal.applyQuaternion(orientation),
    };
  });
}

function viewMetrics(samples, viewDirection) {
  const visible = samples.map(({ normal }) =>
    Math.abs(normal.dot(viewDirection)),
  );
  const mean =
    visible.reduce((sum, value) => sum + value, 0) / visible.length;
  const variance =
    visible.reduce(
      (sum, value) => sum + (value - mean) ** 2,
      0,
    ) / visible.length;
  const edgeOnRatio =
    visible.filter((value) => value < 0.16).length / visible.length;
  const faceOnRatio =
    visible.filter((value) => value > 0.93).length / visible.length;
  const selfCoreOcclusion =
    samples.reduce((sum, { point }, index) => {
      const depth = point.dot(viewDirection);
      const projectedRadius = point
        .clone()
        .addScaledVector(viewDirection, -depth)
        .length();
      return (
        sum +
        (projectedRadius < 0.18 ? 0.3 + visible[index] * 0.7 : 0)
      );
    }, 0) / samples.length;
  return {
    edgeOnRatio,
    faceOnRatio,
    projectedWidthVariance: variance,
    meanVisibleWidth: mean,
    selfCoreOcclusion,
  };
}

function individualScore(metricsByView) {
  const metrics = Object.values(metricsByView);
  const worstEdge = Math.max(...metrics.map((value) => value.edgeOnRatio));
  return metrics.reduce(
    (score, value) =>
      score +
      value.edgeOnRatio * 2.2 +
      value.faceOnRatio * 0.45 +
      value.projectedWidthVariance * 1.35 +
      Math.max(0, 0.42 - value.meanVisibleWidth) * 6 +
      value.selfCoreOcclusion * 0.35,
    worstEdge * 1.2,
  );
}

function candidate(config, phaseDegrees, naturalRoll) {
  const samples = frameSamples(config, phaseDegrees, naturalRoll);
  const views = Object.fromEntries(
    Object.entries(VIEWS).map(([name, direction]) => [
      name,
      viewMetrics(samples, direction),
    ]),
  );
  return {
    phaseDegrees,
    naturalRoll,
    rollAmplitudeDegrees: naturalRoll ? NATURAL_ROLL_AMPLITUDE : 0,
    rollPhaseDegrees: ROLL_PHASES[config.id],
    score: individualScore(views),
    views,
  };
}

function phaseSearch(config, naturalRoll) {
  return Array.from(
    { length: 180 / PHASE_STEP },
    (_, index) => candidate(config, index * PHASE_STEP, naturalRoll),
  ).sort((left, right) => left.score - right.score);
}

const result = {
  version: "Ribbon Frame v2",
  geometrySignature: geometryLock.centerlineSignature,
  phaseStepDegrees: PHASE_STEP,
  views: Object.keys(VIEWS),
  naturalRollAmplitudeDegrees: NATURAL_ROLL_AMPLITUDE,
  orbits: geometryLock.orbits.map((config) => {
    const fixed = phaseSearch(config, false);
    const natural = phaseSearch(config, true);
    const best = natural[0].score < fixed[0].score ? natural[0] : fixed[0];
    return {
      id: config.id,
      selected: best,
      fixedBest: fixed[0],
      naturalRollBest: natural[0],
      candidates: natural.slice(0, 5),
    };
  }),
};

process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
