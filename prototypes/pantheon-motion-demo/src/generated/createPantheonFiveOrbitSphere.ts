import * as THREE from "three";

export type OrbitId =
  | "Constellation"
  | "Tarot"
  | "MBTI"
  | "HumanDesign"
  | "ZiweiBazi";

export type OrbitCurveProfile =
  | "stable"
  | "dramatic"
  | "balanced"
  | "channel"
  | "cyclic";

export type OrbitPresentationMode =
  | "final-occluded"
  | "xray"
  | "monochrome-occluded"
  | "monochrome-xray";

export interface OrbitConfig {
  id: OrbitId;
  label: string;
  curveProfile: OrbitCurveProfile;
  color: string;
  baseRadius: number;
  coreApproachRadius: number;
  pathPhase: number;
  inclination: number;
  azimuth: number;
  latitudeBias: number;
  latitudeAmplitude: number;
  tubeRadius: number;
  visible: boolean;
  lineToRibbonProgress: number;
}

interface OrbitBasis {
  u: THREE.Vector3;
  v: THREE.Vector3;
  n: THREE.Vector3;
}

interface OrbitTrackStats {
  controlPointCount: number;
  minRadius: number;
  maxRadius: number;
  averageRadius: number;
  maxCurvature: number;
  minBendRadius: number;
  hasLocalLoop: boolean;
  frontProjectedSelfIntersections: number;
  nonPlanarOffset: number;
  extentX: number;
  extentY: number;
  extentZ: number;
  minY: number;
  maxY: number;
}

export interface OrbitSphereMetrics {
  trackCount: number;
  sampleCountPerTrack: number;
  minRadius: number;
  maxRadius: number;
  averageRadius: number;
  extentX: number;
  extentY: number;
  extentZ: number;
  extentRatio: number;
  directionalCoverage: {
    front: number;
    back: number;
    left: number;
    right: number;
    top: number;
    bottom: number;
  };
  nearestTrackDistance: number;
  nearestTrackPair: [OrbitId, OrbitId];
  nearestCoreSurfaceDistance: number;
  frontProjectedCrossings: number;
  visibleFinalCrossings: number;
  coreVisibleRatioEstimate: number;
  withoutTrackExtentRatios: Record<OrbitId, number>;
  withoutTrackExtents: Record<
    OrbitId,
    { x: number; y: number; z: number; ratio: number }
  >;
  tracks: Record<OrbitId, OrbitTrackStats>;
}

type Disposable = THREE.BufferGeometry | THREE.Material;

export const PANTHEON_FIVE_ORBIT_PARAMS = {
  sphereRadius: 1,
  coreRadius: 0.18,
  innerOcclusionRadius: 0.8,
  apertureRadius: 0.166,
  debugSphereOpacity: 0.11,
  tubularSegments: 224,
  radialSegments: 8,
  metricSamples: 384,
  rotationSeconds: 52,
  lineToRibbonProgress: 0,
} as const;

export const RECOMMENDED_ORBIT_CONFIGS: readonly OrbitConfig[] = [
  {
    id: "Constellation",
    label: "星座",
    curveProfile: "stable",
    color: "#244f86",
    baseRadius: 0.985,
    coreApproachRadius: 0.9,
    pathPhase: 0.18,
    inclination: 25,
    azimuth: 12,
    latitudeBias: 0.015,
    latitudeAmplitude: 0.13,
    tubeRadius: 0.0103,
    visible: true,
    lineToRibbonProgress: 0,
  },
  {
    id: "Tarot",
    label: "塔羅",
    curveProfile: "dramatic",
    color: "#8f3349",
    baseRadius: 0.995,
    coreApproachRadius: 0.46,
    pathPhase: 0.56,
    inclination: 82,
    azimuth: 28,
    latitudeBias: -0.01,
    latitudeAmplitude: 0.23,
    tubeRadius: 0.0108,
    visible: true,
    lineToRibbonProgress: 0,
  },
  {
    id: "MBTI",
    label: "MBTI",
    curveProfile: "balanced",
    color: "#3b9689",
    baseRadius: 0.97,
    coreApproachRadius: 0.53,
    pathPhase: 1.04,
    inclination: -50,
    azimuth: -22,
    latitudeBias: 0.01,
    latitudeAmplitude: 0.17,
    tubeRadius: 0.0095,
    visible: true,
    lineToRibbonProgress: 0,
  },
  {
    id: "HumanDesign",
    label: "人類圖",
    curveProfile: "channel",
    color: "#d8d4c8",
    baseRadius: 0.98,
    coreApproachRadius: 0.48,
    pathPhase: 2.09,
    inclination: 82,
    azimuth: 72,
    latitudeBias: 0.02,
    latitudeAmplitude: 0.25,
    tubeRadius: 0.0083,
    visible: true,
    lineToRibbonProgress: 0,
  },
  {
    id: "ZiweiBazi",
    label: "紫微八字",
    curveProfile: "cyclic",
    color: "#b77a42",
    baseRadius: 0.975,
    coreApproachRadius: 0.55,
    pathPhase: 2.3,
    inclination: -42,
    azimuth: 125,
    latitudeBias: -0.02,
    latitudeAmplitude: 0.22,
    tubeRadius: 0.0108,
    visible: true,
    lineToRibbonProgress: 0,
  },
] as const;

function cloneConfigs(configs: readonly OrbitConfig[]): OrbitConfig[] {
  return configs.map((config) => ({ ...config }));
}

function createBasis(config: OrbitConfig): OrbitBasis {
  const n = new THREE.Vector3(0, 1, 0)
    .applyAxisAngle(
      new THREE.Vector3(1, 0, 0),
      THREE.MathUtils.degToRad(config.inclination),
    )
    .applyAxisAngle(
      new THREE.Vector3(0, 1, 0),
      THREE.MathUtils.degToRad(config.azimuth),
    )
    .normalize();
  const helper =
    Math.abs(n.dot(new THREE.Vector3(0, 0, 1))) > 0.92
      ? new THREE.Vector3(1, 0, 0)
      : new THREE.Vector3(0, 0, 1);
  const u = helper.clone().cross(n).normalize();
  const v = n.clone().cross(u).normalize();
  return { u, v, n };
}

interface ArtDirectionPoint {
  latitude: number;
  inset: number;
  phaseNudge: number;
}

const ART_DIRECTION_PATTERNS: Record<
  OrbitCurveProfile,
  readonly ArtDirectionPoint[]
> = {
  stable: [
    { latitude: 0.15, inset: 0, phaseNudge: 0 },
    { latitude: 0.62, inset: 0.04, phaseNudge: -0.01 },
    { latitude: 1, inset: 0.08, phaseNudge: 0 },
    { latitude: 0.62, inset: 0.04, phaseNudge: 0.01 },
    { latitude: 0.08, inset: 0, phaseNudge: 0 },
    { latitude: -0.5, inset: 0.03, phaseNudge: -0.01 },
    { latitude: -0.88, inset: 0.08, phaseNudge: 0 },
    { latitude: -0.55, inset: 0.04, phaseNudge: 0.01 },
    { latitude: -0.05, inset: 0, phaseNudge: 0 },
    { latitude: 0.28, inset: 0, phaseNudge: 0 },
  ],
  dramatic: [
    { latitude: 0.08, inset: 0, phaseNudge: 0 },
    { latitude: 0.48, inset: 0.04, phaseNudge: -0.015 },
    { latitude: 0.86, inset: 0.18, phaseNudge: -0.02 },
    { latitude: 1, inset: 0.55, phaseNudge: 0 },
    { latitude: 0.82, inset: 1, phaseNudge: 0.02 },
    { latitude: 0.42, inset: 0.6, phaseNudge: 0.015 },
    { latitude: -0.08, inset: 0.22, phaseNudge: 0 },
    { latitude: -0.5, inset: 0.05, phaseNudge: -0.01 },
    { latitude: -0.84, inset: 0, phaseNudge: 0 },
    { latitude: -0.96, inset: 0, phaseNudge: 0.01 },
    { latitude: -0.7, inset: 0, phaseNudge: 0.01 },
    { latitude: -0.28, inset: 0, phaseNudge: 0 },
  ],
  balanced: [
    { latitude: 0, inset: 0, phaseNudge: 0 },
    { latitude: 0.5, inset: 0.04, phaseNudge: -0.01 },
    { latitude: 0.86, inset: 0.28, phaseNudge: 0 },
    { latitude: 1, inset: 0.68, phaseNudge: 0.01 },
    { latitude: 0.86, inset: 1, phaseNudge: 0 },
    { latitude: 0.5, inset: 0.68, phaseNudge: -0.01 },
    { latitude: 0, inset: 0.28, phaseNudge: 0 },
    { latitude: -0.5, inset: 0.04, phaseNudge: 0.01 },
    { latitude: -0.86, inset: 0, phaseNudge: 0 },
    { latitude: -1, inset: 0, phaseNudge: -0.01 },
    { latitude: -0.86, inset: 0, phaseNudge: 0 },
    { latitude: -0.5, inset: 0, phaseNudge: 0.01 },
  ],
  channel: [
    { latitude: 0, inset: 0, phaseNudge: 0 },
    { latitude: 0.58, inset: 0, phaseNudge: -0.01 },
    { latitude: 1, inset: 0.08, phaseNudge: 0 },
    { latitude: 0.78, inset: 0.28, phaseNudge: 0.01 },
    { latitude: 0.32, inset: 0.7, phaseNudge: 0 },
    { latitude: -0.22, inset: 1, phaseNudge: -0.01 },
    { latitude: -0.72, inset: 0.62, phaseNudge: 0 },
    { latitude: -1, inset: 0, phaseNudge: 0.01 },
    { latitude: -0.78, inset: 0.06, phaseNudge: 0 },
    { latitude: -0.3, inset: 0, phaseNudge: -0.01 },
    { latitude: 0.2, inset: 0, phaseNudge: 0 },
    { latitude: 0.56, inset: 0, phaseNudge: 0.01 },
  ],
  cyclic: [
    { latitude: -0.1, inset: 0, phaseNudge: 0 },
    { latitude: 0.32, inset: 0, phaseNudge: -0.01 },
    { latitude: 0.68, inset: 0.08, phaseNudge: 0 },
    { latitude: 0.9, inset: 0.3, phaseNudge: 0.015 },
    { latitude: 0.78, inset: 0.68, phaseNudge: 0.01 },
    { latitude: 0.38, inset: 1, phaseNudge: 0 },
    { latitude: -0.1, inset: 0.62, phaseNudge: -0.01 },
    { latitude: -0.52, inset: 0.25, phaseNudge: -0.015 },
    { latitude: -0.82, inset: 0.05, phaseNudge: 0 },
    { latitude: -0.9, inset: 0, phaseNudge: 0.01 },
    { latitude: -0.68, inset: 0, phaseNudge: 0.01 },
    { latitude: -0.38, inset: 0, phaseNudge: 0 },
  ],
};

function createArtDirectedControlPoints(
  config: OrbitConfig,
  basis: OrbitBasis,
): THREE.Vector3[] {
  const pattern = ART_DIRECTION_PATTERNS[config.curveProfile];
  return pattern.map((point, index) => {
    const progress = index / pattern.length + point.phaseNudge;
    const angle = progress * Math.PI * 2 + config.pathPhase;
    const latitude =
      config.latitudeBias + config.latitudeAmplitude * point.latitude;
    const radius = THREE.MathUtils.lerp(
      config.baseRadius,
      config.coreApproachRadius,
      point.inset,
    );
    return basis.u
      .clone()
      .multiplyScalar(Math.cos(angle))
      .addScaledVector(basis.v, Math.sin(angle))
      .addScaledVector(basis.n, latitude)
      .normalize()
      .multiplyScalar(radius);
  });
}

export class ArtDirectedOrbitCurve extends THREE.CatmullRomCurve3 {
  readonly config: OrbitConfig;
  readonly basis: OrbitBasis;
  readonly artControlPoints: THREE.Vector3[];

  constructor(config: OrbitConfig) {
    const basis = createBasis(config);
    const points = createArtDirectedControlPoints(config, basis);
    super(points, true, "centripetal", 0.42);
    this.config = { ...config };
    this.basis = basis;
    this.artControlPoints = points;
  }
}

function sampleCurve(
  curve: THREE.Curve<THREE.Vector3>,
  count: number,
): THREE.Vector3[] {
  return Array.from({ length: count }, (_, index) =>
    curve.getPoint(index / count),
  );
}

function calculateCurvatures(points: readonly THREE.Vector3[]): number[] {
  return points.map((point, index) => {
    const previous =
      points[(index - 1 + points.length) % points.length];
    const next = points[(index + 1) % points.length];
    const incoming = point.clone().sub(previous);
    const outgoing = next.clone().sub(point);
    const chord = next.clone().sub(previous);
    const denominator =
      incoming.length() * outgoing.length() * chord.length();
    if (denominator < 1e-8) return 0;
    return (
      (2 * incoming.clone().cross(outgoing).length()) / denominator
    );
  });
}

function cross2d(
  ax: number,
  ay: number,
  bx: number,
  by: number,
): number {
  return ax * by - ay * bx;
}

interface FrontIntersection {
  t: number;
  u: number;
  x: number;
  y: number;
  leftZ: number;
  rightZ: number;
}

function getFrontIntersection(
  a: THREE.Vector3,
  b: THREE.Vector3,
  c: THREE.Vector3,
  d: THREE.Vector3,
): FrontIntersection | null {
  const abx = b.x - a.x;
  const aby = b.y - a.y;
  const cdx = d.x - c.x;
  const cdy = d.y - c.y;
  const denominator = cross2d(abx, aby, cdx, cdy);
  if (Math.abs(denominator) < 1e-7) return null;
  const acx = c.x - a.x;
  const acy = c.y - a.y;
  const t = cross2d(acx, acy, cdx, cdy) / denominator;
  const u = cross2d(acx, acy, abx, aby) / denominator;
  if (!(t > 0.002 && t < 0.998 && u > 0.002 && u < 0.998)) {
    return null;
  }
  return {
    t,
    u,
    x: THREE.MathUtils.lerp(a.x, b.x, t),
    y: THREE.MathUtils.lerp(a.y, b.y, t),
    leftZ: THREE.MathUtils.lerp(a.z, b.z, t),
    rightZ: THREE.MathUtils.lerp(c.z, d.z, u),
  };
}

function segmentsIntersectFront(
  a: THREE.Vector3,
  b: THREE.Vector3,
  c: THREE.Vector3,
  d: THREE.Vector3,
): boolean {
  return getFrontIntersection(a, b, c, d) !== null;
}

function findFrontSelfIntersections(
  points: readonly THREE.Vector3[],
): Array<[number, number]> {
  const intersections: Array<[number, number]> = [];
  for (let left = 0; left < points.length; left += 1) {
    const leftNext = (left + 1) % points.length;
    for (let right = left + 2; right < points.length; right += 1) {
      const rightNext = (right + 1) % points.length;
      if (left === rightNext || leftNext === right) continue;
      if (
        segmentsIntersectFront(
          points[left],
          points[leftNext],
          points[right],
          points[rightNext],
        )
      ) {
        intersections.push([left, right]);
      }
    }
  }
  return intersections;
}

function hasSmallFrontLoop(
  points: readonly THREE.Vector3[],
  intersections: readonly [number, number][],
): boolean {
  return intersections.some(([start, end]) => {
    const arc = points.slice(start + 1, end + 1);
    if (arc.length < 3) return false;
    const bounds = new THREE.Box3().setFromPoints(arc);
    const size = bounds.getSize(new THREE.Vector3());
    return Math.max(size.x, size.y) < 0.3;
  });
}

function isVisibleWithOcclusion(
  x: number,
  y: number,
  z: number,
): boolean {
  const projectedRadius = Math.hypot(x, y);
  if (projectedRadius <= PANTHEON_FIVE_ORBIT_PARAMS.apertureRadius) {
    return true;
  }
  if (
    projectedRadius >=
    PANTHEON_FIVE_ORBIT_PARAMS.innerOcclusionRadius
  ) {
    return true;
  }
  const sphereFrontZ = Math.sqrt(
    PANTHEON_FIVE_ORBIT_PARAMS.innerOcclusionRadius ** 2 -
      projectedRadius ** 2,
  );
  return z > sphereFrontZ;
}

function collectFrontCrossingsBetween(
  left: readonly THREE.Vector3[],
  right: readonly THREE.Vector3[],
): {
  geometryCount: number;
  visiblePoints: THREE.Vector3[];
} {
  let geometryCount = 0;
  const visiblePoints: THREE.Vector3[] = [];
  for (let a = 0; a < left.length; a += 1) {
    for (let b = 0; b < right.length; b += 1) {
      const intersection = getFrontIntersection(
        left[a],
        left[(a + 1) % left.length],
        right[b],
        right[(b + 1) % right.length],
      );
      if (!intersection) continue;
      geometryCount += 1;
      const leftVisible = isVisibleWithOcclusion(
        intersection.x,
        intersection.y,
        intersection.leftZ,
      );
      const rightVisible = isVisibleWithOcclusion(
        intersection.x,
        intersection.y,
        intersection.rightZ,
      );
      if (leftVisible && rightVisible) {
        visiblePoints.push(
          new THREE.Vector3(
            intersection.x,
            intersection.y,
            Math.max(intersection.leftZ, intersection.rightZ) + 0.018,
          ),
        );
      }
    }
  }
  return { geometryCount, visiblePoints };
}

function calculateMetrics(
  configs: readonly OrbitConfig[],
  curves: ReadonlyMap<OrbitId, ArtDirectedOrbitCurve>,
): OrbitSphereMetrics {
  const count = PANTHEON_FIVE_ORBIT_PARAMS.metricSamples;
  const samples = new Map<OrbitId, THREE.Vector3[]>();
  const tracks = {} as Record<OrbitId, OrbitTrackStats>;
  const allPoints: THREE.Vector3[] = [];

  configs.forEach((config) => {
    const curve = curves.get(config.id);
    if (!curve) throw new Error(`Missing orbit curve: ${config.id}`);
    const points = sampleCurve(curve, count);
    samples.set(config.id, points);
    allPoints.push(...points);
    const radii = points.map((point) => point.length());
    const curvatures = calculateCurvatures(points);
    const maxCurvature = Math.max(...curvatures);
    const selfIntersections = findFrontSelfIntersections(points);
    const trackBounds = new THREE.Box3().setFromPoints(points);
    const trackSize = trackBounds.getSize(new THREE.Vector3());
    const planeOffsets = points.map((point) =>
      point.dot(curve.basis.n),
    );
    tracks[config.id] = {
      controlPointCount: curve.artControlPoints.length,
      minRadius: Math.min(...radii),
      maxRadius: Math.max(...radii),
      averageRadius:
        radii.reduce((sum, radius) => sum + radius, 0) / radii.length,
      maxCurvature,
      minBendRadius:
        maxCurvature > 0 ? 1 / maxCurvature : Number.POSITIVE_INFINITY,
      hasLocalLoop: hasSmallFrontLoop(points, selfIntersections),
      frontProjectedSelfIntersections: selfIntersections.length,
      nonPlanarOffset:
        Math.max(...planeOffsets) - Math.min(...planeOffsets),
      extentX: trackSize.x,
      extentY: trackSize.y,
      extentZ: trackSize.z,
      minY: trackBounds.min.y,
      maxY: trackBounds.max.y,
    };
  });

  const bounds = new THREE.Box3().setFromPoints(allPoints);
  const size = bounds.getSize(new THREE.Vector3());
  const radii = allPoints.map((point) => point.length());
  let nearestTrackDistance = Number.POSITIVE_INFINITY;
  let nearestTrackPair: [OrbitId, OrbitId] = [
    configs[0].id,
    configs[1].id,
  ];
  let frontProjectedCrossings = 0;
  let visibleFinalCrossings = 0;

  for (let left = 0; left < configs.length; left += 1) {
    for (let right = left + 1; right < configs.length; right += 1) {
      const leftPoints = samples.get(configs[left].id) ?? [];
      const rightPoints = samples.get(configs[right].id) ?? [];
      const crossingResult = collectFrontCrossingsBetween(
        leftPoints,
        rightPoints,
      );
      frontProjectedCrossings += crossingResult.geometryCount;
      visibleFinalCrossings += crossingResult.visiblePoints.length;
      leftPoints.forEach((leftPoint) => {
        rightPoints.forEach((rightPoint) => {
          const distance = leftPoint.distanceTo(rightPoint);
          if (distance < nearestTrackDistance) {
            nearestTrackDistance = distance;
            nearestTrackPair = [configs[left].id, configs[right].id];
          }
        });
      });
    }
  }

  const extents = [size.x, size.y, size.z];
  const withoutTrackExtentRatios = {} as Record<OrbitId, number>;
  const withoutTrackExtents = {} as OrbitSphereMetrics["withoutTrackExtents"];
  configs.forEach((excluded) => {
    const remainingPoints = configs.flatMap((config) =>
      config.id === excluded.id ? [] : samples.get(config.id) ?? [],
    );
    const remainingSize = new THREE.Box3()
      .setFromPoints(remainingPoints)
      .getSize(new THREE.Vector3());
    const remainingExtents = [
      remainingSize.x,
      remainingSize.y,
      remainingSize.z,
    ];
    withoutTrackExtentRatios[excluded.id] =
      Math.max(...remainingExtents) / Math.min(...remainingExtents);
    withoutTrackExtents[excluded.id] = {
      x: remainingSize.x,
      y: remainingSize.y,
      z: remainingSize.z,
      ratio: withoutTrackExtentRatios[excluded.id],
    };
  });
  return {
    trackCount: configs.length,
    sampleCountPerTrack: count,
    minRadius: Math.min(...radii),
    maxRadius: Math.max(...radii),
    averageRadius:
      radii.reduce((sum, radius) => sum + radius, 0) / radii.length,
    extentX: size.x,
    extentY: size.y,
    extentZ: size.z,
    extentRatio: Math.max(...extents) / Math.min(...extents),
    directionalCoverage: {
      front: bounds.max.z,
      back: -bounds.min.z,
      left: -bounds.min.x,
      right: bounds.max.x,
      top: bounds.max.y,
      bottom: -bounds.min.y,
    },
    nearestTrackDistance,
    nearestTrackPair,
    nearestCoreSurfaceDistance:
      Math.min(...radii) - PANTHEON_FIVE_ORBIT_PARAMS.coreRadius,
    frontProjectedCrossings,
    visibleFinalCrossings,
    coreVisibleRatioEstimate: Math.min(
      1,
      (PANTHEON_FIVE_ORBIT_PARAMS.apertureRadius /
        PANTHEON_FIVE_ORBIT_PARAMS.coreRadius) **
        2,
    ),
    withoutTrackExtentRatios,
    withoutTrackExtents,
    tracks,
  };
}

function assertConfigSet(configs: readonly OrbitConfig[]): void {
  const expectedIds = RECOMMENDED_ORBIT_CONFIGS.map(
    (config) => config.id,
  );
  if (
    configs.length !== expectedIds.length ||
    configs.some((config, index) => config.id !== expectedIds[index])
  ) {
    throw new Error("Orbit config must contain the five canonical tracks in order.");
  }
}

function collectVisibleFinalCrossingPoints(
  configs: readonly OrbitConfig[],
  curves: ReadonlyMap<OrbitId, ArtDirectedOrbitCurve>,
): THREE.Vector3[] {
  const samples = new Map<OrbitId, THREE.Vector3[]>();
  configs.forEach((config) => {
    const curve = curves.get(config.id);
    if (curve) samples.set(config.id, sampleCurve(curve, 192));
  });
  const points: THREE.Vector3[] = [];
  for (let left = 0; left < configs.length; left += 1) {
    for (let right = left + 1; right < configs.length; right += 1) {
      const result = collectFrontCrossingsBetween(
        samples.get(configs[left].id) ?? [],
        samples.get(configs[right].id) ?? [],
      );
      points.push(...result.visiblePoints);
    }
  }
  return points;
}

export function createPantheonFiveOrbitSphere(): THREE.Group {
  const root = new THREE.Group();
  root.name = "PantheonOrbitSphere";
  const resources = new Set<Disposable>();
  const nodes: Record<string, THREE.Object3D> = { PantheonOrbitSphere: root };
  const meshes: Record<string, THREE.Mesh> = {};
  const bandPivots: Record<string, THREE.Group> = {};
  const themeGroups: Record<string, THREE.Group> = {};
  const trackGroups = new Map<OrbitId, THREE.Group>();
  const debugTrackGroups = new Map<OrbitId, THREE.Group>();
  const curves = new Map<OrbitId, ArtDirectedOrbitCurve>();
  let configs = cloneConfigs(RECOMMENDED_ORBIT_CONFIGS);
  let metrics: OrbitSphereMetrics;
  let monochromeMode = false;
  let presentationMode: OrbitPresentationMode = "final-occluded";
  let occlusionSoloMode = false;
  let apertureDebugMode = false;
  let visibleCrossingsDebugMode = false;
  let debugVisualizationMode:
    | "off"
    | "all"
    | "control"
    | "curvature" = "off";

  const debugGroup = new THREE.Group();
  debugGroup.name = "PhaseADebugGuides";
  debugGroup.visible = false;
  root.add(debugGroup);
  nodes[debugGroup.name] = debugGroup;

  const visibleCrossingsDebug = new THREE.Group();
  visibleCrossingsDebug.name = "VisibleFinalCrossingsDebug";
  visibleCrossingsDebug.visible = false;
  root.add(visibleCrossingsDebug);
  nodes[visibleCrossingsDebug.name] = visibleCrossingsDebug;

  const sphereGeometry = new THREE.SphereGeometry(1, 32, 20);
  const sphereMaterial = new THREE.MeshBasicMaterial({
    color: 0x91a7bd,
    transparent: true,
    opacity: PANTHEON_FIVE_ORBIT_PARAMS.debugSphereOpacity,
    wireframe: true,
    depthWrite: false,
  });
  const referenceSphere = new THREE.Mesh(
    sphereGeometry,
    sphereMaterial,
  );
  referenceSphere.name = "DebugReferenceSphere";
  debugGroup.add(referenceSphere);
  resources.add(sphereGeometry);
  resources.add(sphereMaterial);

  const axes = new THREE.AxesHelper(1.28);
  axes.name = "WorldAxes";
  debugGroup.add(axes);
  resources.add(axes.geometry);
  (Array.isArray(axes.material) ? axes.material : [axes.material]).forEach(
    (material) => resources.add(material),
  );

  const innerOcclusionGeometry = new THREE.SphereGeometry(
    PANTHEON_FIVE_ORBIT_PARAMS.innerOcclusionRadius,
    64,
    48,
  );
  const innerOcclusionMaterial = new THREE.MeshStandardMaterial({
    color: 0x01060c,
    metalness: 0.1,
    roughness: 0.82,
    transparent: false,
    depthTest: true,
    depthWrite: true,
    alphaTest: 0.5,
    alphaToCoverage: true,
  });
  innerOcclusionMaterial.userData.apertureDebug = false;
  innerOcclusionMaterial.onBeforeCompile = (shader) => {
    shader.uniforms.uOcclusionCenterView = {
      value: new THREE.Vector2(),
    };
    shader.uniforms.uApertureRadius = {
      value: PANTHEON_FIVE_ORBIT_PARAMS.apertureRadius,
    };
    shader.uniforms.uApertureDebug = { value: 0 };
    shader.vertexShader = `
      uniform vec2 uOcclusionCenterView;
      varying vec3 vOcclusionViewPosition;
    ${shader.vertexShader}`.replace(
      "#include <project_vertex>",
      `#include <project_vertex>
      vOcclusionViewPosition = mvPosition.xyz;`,
    );
    shader.fragmentShader = `
      uniform vec2 uOcclusionCenterView;
      uniform float uApertureRadius;
      uniform float uApertureDebug;
      varying vec3 vOcclusionViewPosition;
    ${shader.fragmentShader}`.replace(
      "vec4 diffuseColor = vec4( diffuse, opacity );",
      `float apertureDistance = length(
        vOcclusionViewPosition.xy - uOcclusionCenterView
      );
      float apertureCoverage = smoothstep(
        uApertureRadius - 0.018,
        uApertureRadius + 0.018,
        apertureDistance
      );
      vec4 diffuseColor = vec4(diffuse, apertureCoverage);
      float apertureEdge = smoothstep(
        uApertureRadius,
        uApertureRadius + 0.09,
        apertureDistance
      );
      diffuseColor.rgb *= mix(0.42, 1.0, apertureEdge);
      float debugRing = 1.0 - smoothstep(
        0.012,
        0.028,
        abs(apertureDistance - uApertureRadius)
      );
      diffuseColor.rgb = mix(
        diffuseColor.rgb,
        vec3(0.95, 0.22, 0.62),
        debugRing * uApertureDebug
      );`,
    );
    innerOcclusionMaterial.userData.apertureShader = shader;
  };
  innerOcclusionMaterial.customProgramCacheKey = () =>
    "pantheon-phase-a6-opaque-aperture-v1";
  const innerOcclusionSphere = new THREE.Mesh(
    innerOcclusionGeometry,
    innerOcclusionMaterial,
  );
  innerOcclusionSphere.name = "InnerOcclusionSphere";
  innerOcclusionSphere.castShadow = true;
  innerOcclusionSphere.receiveShadow = true;
  const occlusionCenterWorld = new THREE.Vector3();
  innerOcclusionSphere.onBeforeRender = (
    _renderer,
    _scene,
    camera,
  ) => {
    const shader = innerOcclusionMaterial.userData.apertureShader;
    if (!shader) return;
    innerOcclusionSphere
      .getWorldPosition(occlusionCenterWorld)
      .applyMatrix4(camera.matrixWorldInverse);
    shader.uniforms.uOcclusionCenterView.value.set(
      occlusionCenterWorld.x,
      occlusionCenterWorld.y,
    );
    shader.uniforms.uApertureDebug.value =
      innerOcclusionMaterial.userData.apertureDebug ? 1 : 0;
  };
  // Phase B0 起正式候選不再渲染 A.6 內球；保留資源物件只供舊證據讀取。
  innerOcclusionSphere.visible = false;
  nodes[innerOcclusionSphere.name] = innerOcclusionSphere;
  meshes.innerOcclusionSphere = innerOcclusionSphere;
  resources.add(innerOcclusionGeometry);
  resources.add(innerOcclusionMaterial);

  configs.forEach((config) => {
    const group = new THREE.Group();
    group.name = `Orbit_${config.id}`;
    root.add(group);
    trackGroups.set(config.id, group);
    nodes[group.name] = group;
    themeGroups[config.id] = group;
    bandPivots[config.id] = group;

    const debugTrack = new THREE.Group();
    debugTrack.name = `Debug_${config.id}`;
    debugGroup.add(debugTrack);
    debugTrackGroups.set(config.id, debugTrack);
  });

  const coreGeometry = new THREE.SphereGeometry(
    PANTHEON_FIVE_ORBIT_PARAMS.coreRadius,
    48,
    32,
  );
  const coreMaterial = new THREE.MeshStandardMaterial({
    color: 0xc49b55,
    metalness: 0.52,
    roughness: 0.38,
  });
  const core = new THREE.Mesh(coreGeometry, coreMaterial);
  core.name = "CoreTimeSphere";
  core.castShadow = true;
  core.receiveShadow = true;
  root.add(core);
  nodes[core.name] = core;
  meshes.core = core;
  resources.add(coreGeometry);
  resources.add(coreMaterial);

  function clearGroup(group: THREE.Group): void {
    [...group.children].forEach((child) => {
      child.traverse((object) => {
        if (!(object instanceof THREE.Mesh || object instanceof THREE.LineSegments || object instanceof THREE.Points)) {
          return;
        }
        resources.delete(object.geometry);
        object.geometry.dispose();
        const materials = Array.isArray(object.material)
          ? object.material
          : [object.material];
        materials.forEach((material) => {
          resources.delete(material);
          material.dispose();
        });
      });
      group.remove(child);
    });
  }

  function rebuildTrack(config: OrbitConfig): void {
    const group = trackGroups.get(config.id);
    const debugTrack = debugTrackGroups.get(config.id);
    if (!group || !debugTrack) return;
    clearGroup(group);
    clearGroup(debugTrack);

    const curve = new ArtDirectedOrbitCurve(config);
    curves.set(config.id, curve);
    const geometry = new THREE.TubeGeometry(
      curve,
      PANTHEON_FIVE_ORBIT_PARAMS.tubularSegments,
      config.tubeRadius,
      PANTHEON_FIVE_ORBIT_PARAMS.radialSegments,
      true,
    );
    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(
        monochromeMode ? "#eef2f4" : config.color,
      ),
      metalness: 0.18,
      roughness: 0.5,
      transparent: false,
      depthTest: true,
      depthWrite: true,
    });
    const backBrightness = monochromeMode ? 0.44 : 0.5;
    material.onBeforeCompile = (shader) => {
      shader.vertexShader = `
        varying vec3 vOrbitWorldPosition;
      ${shader.vertexShader}`.replace(
        "#include <project_vertex>",
        `#include <project_vertex>
        vOrbitWorldPosition = (
          modelMatrix * vec4(transformed, 1.0)
        ).xyz;`,
      );
      shader.fragmentShader = `
        varying vec3 vOrbitWorldPosition;
      ${shader.fragmentShader}`.replace(
        "vec4 diffuseColor = vec4( diffuse, opacity );",
        `vec4 diffuseColor = vec4( diffuse, opacity );
        vec3 orbitSphereNormal = normalize(vOrbitWorldPosition);
        vec3 orbitViewDirection = normalize(
          cameraPosition - vOrbitWorldPosition
        );
        float orbitFacing = dot(
          orbitSphereNormal,
          orbitViewDirection
        );
        float orbitFrontFactor = smoothstep(-0.10, 0.55, orbitFacing);
        diffuseColor.rgb *= mix(
          ${backBrightness.toFixed(2)},
          1.0,
          orbitFrontFactor
        );`,
      );
    };
    material.customProgramCacheKey = () =>
      `pantheon-phase-a6-facing-${monochromeMode ? "mono" : "color"}`;
    const track = new THREE.Mesh(geometry, material);
    track.name = `${config.id}_OrbitTrack`;
    track.castShadow = true;
    track.receiveShadow = true;
    group.add(track);
    group.visible = config.visible;
    meshes[config.id] = track;
    nodes[`${group.name}/${track.name}`] = track;
    resources.add(geometry);
    resources.add(material);

    const controlPoints = curve.artControlPoints;
    const pointGeometry = new THREE.BufferGeometry().setFromPoints(
      controlPoints,
    );
    const pointMaterial = new THREE.PointsMaterial({
      color: config.color,
      size: 0.035,
      sizeAttenuation: true,
    });
    const points = new THREE.Points(pointGeometry, pointMaterial);
    points.name = `${config.id}_ControlPoints`;
    debugTrack.add(points);
    resources.add(pointGeometry);
    resources.add(pointMaterial);

    const tangentVertices: THREE.Vector3[] = [];
    controlPoints.forEach((point, index) => {
      tangentVertices.push(
        point,
        point
          .clone()
          .addScaledVector(
            curve.getTangent(index / controlPoints.length),
            0.1,
          ),
      );
    });
    const tangentGeometry = new THREE.BufferGeometry().setFromPoints(
      tangentVertices,
    );
    const tangentMaterial = new THREE.LineBasicMaterial({
      color: config.color,
    });
    const tangents = new THREE.LineSegments(
      tangentGeometry,
      tangentMaterial,
    );
    tangents.name = `${config.id}_Tangents`;
    debugTrack.add(tangents);
    resources.add(tangentGeometry);
    resources.add(tangentMaterial);

    const heatPoints = sampleCurve(curve, 192);
    const heatCurvatures = calculateCurvatures(heatPoints);
    const heatVertices: THREE.Vector3[] = [];
    const heatColors: number[] = [];
    heatPoints.forEach((point, index) => {
      const next = heatPoints[(index + 1) % heatPoints.length];
      const normalized = THREE.MathUtils.clamp(
        Math.max(
          heatCurvatures[index],
          heatCurvatures[(index + 1) % heatPoints.length],
        ) / 5.56,
        0,
        1,
      );
      const color = new THREE.Color().setHSL(
        THREE.MathUtils.lerp(0.62, 0, normalized),
        0.9,
        0.56,
      );
      heatVertices.push(point, next);
      heatColors.push(
        color.r,
        color.g,
        color.b,
        color.r,
        color.g,
        color.b,
      );
    });
    const heatGeometry = new THREE.BufferGeometry().setFromPoints(
      heatVertices,
    );
    heatGeometry.setAttribute(
      "color",
      new THREE.Float32BufferAttribute(heatColors, 3),
    );
    const heatMaterial = new THREE.LineBasicMaterial({
      vertexColors: true,
      depthTest: false,
      transparent: true,
      opacity: 0.95,
    });
    const curvatureHeat = new THREE.LineSegments(
      heatGeometry,
      heatMaterial,
    );
    curvatureHeat.name = `${config.id}_CurvatureHeat`;
    curvatureHeat.renderOrder = 20;
    debugTrack.add(curvatureHeat);
    resources.add(heatGeometry);
    resources.add(heatMaterial);
  }

  function rebuildAll(nextConfigs: readonly OrbitConfig[]): void {
    assertConfigSet(nextConfigs);
    configs = cloneConfigs(nextConfigs);
    configs.forEach(rebuildTrack);
    metrics = calculateMetrics(configs, curves);
    runtime.metrics = metrics;
    rebuildVisibleCrossingsDebug();
    applySceneVisibility();
  }

  function rebuildVisibleCrossingsDebug(): void {
    clearGroup(visibleCrossingsDebug);
    const crossingPoints = collectVisibleFinalCrossingPoints(
      configs,
      curves,
    );
    if (!crossingPoints.length) return;
    const geometry = new THREE.BufferGeometry().setFromPoints(
      crossingPoints,
    );
    const material = new THREE.PointsMaterial({
      color: 0xff4fa3,
      size: 0.045,
      sizeAttenuation: true,
      depthTest: false,
      depthWrite: false,
    });
    const points = new THREE.Points(geometry, material);
    points.name = "VisibleFinalCrossingMarkers";
    points.renderOrder = 30;
    visibleCrossingsDebug.add(points);
    resources.add(geometry);
    resources.add(material);
  }

  function applySceneVisibility(): void {
    const xrayMode =
      presentationMode === "xray" ||
      presentationMode === "monochrome-xray";
    innerOcclusionSphere.visible = false;
    core.visible = !occlusionSoloMode;
    configs.forEach((config) => {
      const trackGroup = trackGroups.get(config.id);
      if (!trackGroup) return;
      trackGroup.visible =
        !occlusionSoloMode &&
        debugVisualizationMode !== "curvature" &&
        config.visible;
    });
    visibleCrossingsDebug.visible =
      visibleCrossingsDebugMode && !occlusionSoloMode;
  }

  function applyDebugVisualization(
    mode: "off" | "all" | "control" | "curvature",
  ): void {
    debugVisualizationMode = mode;
    debugGroup.visible = mode !== "off";
    referenceSphere.visible = mode === "all";
    axes.visible = mode === "all" || mode === "control";
    debugTrackGroups.forEach((group) => {
      group.children.forEach((child) => {
        if (mode === "all") {
          child.visible = true;
        } else if (mode === "control") {
          child.visible =
            child.name.endsWith("_ControlPoints") ||
            child.name.endsWith("_Tangents");
        } else if (mode === "curvature") {
          child.visible = child.name.endsWith("_CurvatureHeat");
        } else {
          child.visible = false;
        }
      });
    });
    applySceneVisibility();
  }

  const runtime = {
    nodes,
    meshes,
    sockets: {},
    bandPivots,
    themeGroups,
    params: PANTHEON_FIVE_ORBIT_PARAMS,
    metrics: {} as OrbitSphereMetrics,
    monochromeMode,
    presentationMode: presentationMode as OrbitPresentationMode,
    getConfigs: () => cloneConfigs(configs),
    updateConfig(id: OrbitId, patch: Partial<OrbitConfig>) {
      const next = configs.map((config) =>
        config.id === id ? { ...config, ...patch, id } : config,
      );
      rebuildAll(next);
      return cloneConfigs(configs);
    },
    resetConfigs() {
      rebuildAll(RECOMMENDED_ORBIT_CONFIGS);
      return cloneConfigs(configs);
    },
    loadRecommendedPreset() {
      rebuildAll(RECOMMENDED_ORBIT_CONFIGS);
      return cloneConfigs(configs);
    },
    exportConfigJSON() {
      return JSON.stringify(configs, null, 2);
    },
    importConfigJSON(value: string) {
      const parsed = JSON.parse(value) as OrbitConfig[];
      rebuildAll(parsed);
      return cloneConfigs(configs);
    },
    setDebugMode(enabled: boolean) {
      applyDebugVisualization(enabled ? "all" : "off");
    },
    setDebugVisualization(
      mode: "off" | "all" | "control" | "curvature",
    ) {
      applyDebugVisualization(mode);
    },
    setMonochromeMode(enabled: boolean) {
      const xrayMode =
        presentationMode === "xray" ||
        presentationMode === "monochrome-xray";
      runtime.setPresentationMode(
        enabled
          ? xrayMode
            ? "monochrome-xray"
            : "monochrome-occluded"
          : xrayMode
            ? "xray"
            : "final-occluded",
      );
    },
    setPresentationMode(mode: OrbitPresentationMode) {
      presentationMode = mode;
      monochromeMode =
        mode === "monochrome-occluded" ||
        mode === "monochrome-xray";
      runtime.presentationMode = mode;
      runtime.monochromeMode = monochromeMode;
      rebuildAll(configs);
    },
    setApertureDebugMode(enabled: boolean) {
      apertureDebugMode = enabled;
      innerOcclusionMaterial.userData.apertureDebug = enabled;
      applySceneVisibility();
    },
    setOcclusionSoloMode(enabled: boolean) {
      occlusionSoloMode = enabled;
      applySceneVisibility();
    },
    setVisibleCrossingsDebugMode(enabled: boolean) {
      visibleCrossingsDebugMode = enabled;
      applySceneVisibility();
    },
    setThemeVisible(themeId: OrbitId, visible: boolean) {
      const next = configs.map((config) =>
        config.id === themeId ? { ...config, visible } : config,
      );
      rebuildAll(next);
    },
    tick(time: number) {
      root.rotation.y =
        (time / PANTHEON_FIVE_ORBIT_PARAMS.rotationSeconds) *
        Math.PI *
        2;
    },
    dispose() {
      resources.forEach((resource) => resource.dispose());
      resources.clear();
    },
  };

  rebuildAll(configs);
  root.userData.sculptRuntime = runtime;
  root.userData.lineToRibbonProgress = 0;
  return root;
}
