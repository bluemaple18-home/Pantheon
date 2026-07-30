import * as THREE from "three";
import geometryLockV1 from "../../geometry/pantheon-orbits-v1.json";
import geometryLockV1_1 from "../../geometry/pantheon-orbits-v1.1.json";
import ribbonFrameLock from "../../geometry/pantheon-ribbon-frame-v2.json";

export type StarOrbitId =
  | "Constellation"
  | "Tarot"
  | "MBTI"
  | "HumanDesign"
  | "ZiweiBazi";

export interface StarOrbitConfig {
  id: StarOrbitId;
  semiMajorAxis: number;
  semiMinorAxis: number;
  phase: number;
  scale: number;
  inclination: number;
  azimuth: number;
  roll: number;
}

export interface GeometryLockState {
  version: string;
  locked: boolean;
  newVersionRequired: boolean;
  signature: string;
  centerlineSignature: string;
  poseSignature: string;
  poseVersion: string;
  currentSignature: string;
  geometryVersionSignature: string;
  baseCenterlineSignature: string;
  orbitCount: number;
  positions: Record<string, number[]>;
  acceptanceReport: string;
}

export interface StarOrbitExportConfig extends StarOrbitConfig {
  normal: [number, number, number];
  quaternion: [number, number, number, number];
}

export interface StarOrbitMetric {
  id: StarOrbitId;
  minRadius: number;
  maxRadius: number;
  centerOffset: number;
  closureDistance: number;
  seamTangentDot: number;
  minimumForwardDot: number;
  selfIntersection: boolean;
}

export interface StarOrbitMetrics {
  orbitCount: number;
  commonCenter: [number, number, number];
  coreRadius: number;
  minRadius: number;
  maxRadius: number;
  extent: [number, number, number];
  extentRatio: number;
  orbits: StarOrbitMetric[];
}

export type StarOrbitPresentationMode =
  | "centerline"
  | "narrow-ribbon"
  | "mobius-frame";
export type RibbonFrameMode = "selected" | "fixed" | "legacy";

export interface RibbonFrameMetrics {
  id: StarOrbitId;
  phaseDegrees: number;
  naturalRoll: boolean;
  rollAmplitudeDegrees: number;
  rollPhaseDegrees: number;
  minimumAdjacentFrameDot: number;
  seamAlignment: number;
  seamNormalDot: number;
  seamTangentDot: number;
  seamSideDot: number;
  seamUvDelta: number;
  frameFlipCount: number;
  maxOrthonormalError: number;
  degenerateTriangleCount: number;
}

export interface RibbonPrototypeMetrics {
  width: number;
  thickness: number;
  bevelWidth: number;
  bevelSegments: number;
  profileFaceCount: number;
  minimumShellClearance: number;
  hasShellPenetration: boolean;
  regular: RibbonFrameMetrics[];
  mobius: RibbonFrameMetrics[];
}

const SAMPLE_COUNT = 512;
const TUBULAR_SEGMENTS = 320;
const RADIAL_SEGMENTS = 8;
const TUBE_RADIUS = 0.011;
const RIBBON_SEGMENTS = 320;
export type PantheonGeometryVersion = "v1.0" | "v1.1";
export const PANTHEON_CENTERLINE_SIGNATURE =
  geometryLockV1_1.centerlineSignature;
export const PANTHEON_ORBIT_POSE_VERSION =
  "Pantheon Orbit Pose v1 — LIMITED REFINEMENT";
export const PANTHEON_ORBIT_POSE_SIGNATURE =
  "sha256:9f0f15499211c8a9625524adb743fc2e017f873ebaa5f74b697ec4d35088b222";
export const PANTHEON_LIMITED_POSE_REFINEMENT = Object.freeze({
  ZiweiBazi: Object.freeze({
    inclination: 75.1,
    azimuth: 219.6,
    roll: 172.2,
  }),
});
export const SELF_CORE_RADIUS = geometryLockV1_1.selfCore.radius;
export const NARROW_RIBBON_DEFAULTS = {
  width: 0.22,
  thickness: 0.02,
} as const;
export const PANTHEON_BAND_DIMENSIONS = {
  desktopWidth: 0.22,
  mobileWidth: 0.2,
  thickness: 0.02,
  bevelWidth: 0.0024,
  bevelSegments: 2,
  locked: true,
} as const;
export const RIBBON_FRAME_CONFIG = Object.fromEntries(
  ribbonFrameLock.orbits.map((orbit) => [
    orbit.id,
    {
      phaseDegrees: orbit.phaseDegrees,
      naturalRoll: orbit.naturalRoll,
      rollAmplitudeDegrees: orbit.rollAmplitudeDegrees,
      rollPhaseDegrees: orbit.rollPhaseDegrees,
    },
  ]),
) as Record<
  StarOrbitId,
  {
    phaseDegrees: number;
    naturalRoll: boolean;
    rollAmplitudeDegrees: number;
    rollPhaseDegrees: number;
  }
>;
export const RIBBON_PHASE_DEGREES = Object.fromEntries(
  Object.entries(RIBBON_FRAME_CONFIG).map(([id, config]) => [
    id,
    config.phaseDegrees,
  ]),
) as Record<StarOrbitId, number>;
const LEGACY_RIBBON_PHASE_DEGREES: Record<StarOrbitId, number> = {
  Constellation: 0,
  Tarot: 36,
  MBTI: 72,
  HumanDesign: 108,
  ZiweiBazi: 144,
};

function resolveRibbonFrameConfig(
  id: StarOrbitId,
  mode: RibbonFrameMode,
) {
  if (mode === "legacy") {
    return {
      phaseDegrees: LEGACY_RIBBON_PHASE_DEGREES[id],
      naturalRoll: false,
      rollAmplitudeDegrees: 0,
      rollPhaseDegrees: 0,
    };
  }
  if (mode === "fixed") {
    return {
      ...RIBBON_FRAME_CONFIG[id],
      naturalRoll: false,
      rollAmplitudeDegrees: 0,
    };
  }
  return RIBBON_FRAME_CONFIG[id];
}

function orbitConfigsFromLock(lock: typeof geometryLockV1) {
  return lock.orbits.map((orbit) => ({
    id: orbit.id as StarOrbitId,
    semiMajorAxis: orbit.semiMajorAxis,
    semiMinorAxis: orbit.semiMinorAxis,
    phase: orbit.phase,
    scale: orbit.scale,
    inclination: orbit.inclination,
    azimuth: orbit.azimuth,
    roll: orbit.roll,
  }));
}

export const STAR_ORBIT_CONFIGS_V1: readonly StarOrbitConfig[] =
  orbitConfigsFromLock(geometryLockV1);
export const STAR_ORBIT_CONFIGS: readonly StarOrbitConfig[] =
  orbitConfigsFromLock(geometryLockV1_1).map((config) => ({
    ...config,
    ...(PANTHEON_LIMITED_POSE_REFINEMENT[
      config.id as keyof typeof PANTHEON_LIMITED_POSE_REFINEMENT
    ] ?? {}),
  }));

class CenteredOrbitCurve extends THREE.Curve<THREE.Vector3> {
  readonly semiMajorAxis: number;
  readonly semiMinorAxis: number;
  readonly phase: number;

  constructor(config: StarOrbitConfig) {
    super();
    this.semiMajorAxis = config.semiMajorAxis;
    this.semiMinorAxis = config.semiMinorAxis;
    this.phase = config.phase;
  }

  getPoint(t: number, target = new THREE.Vector3()): THREE.Vector3 {
    const angle = t * Math.PI * 2 + this.phase;
    return target.set(
      this.semiMajorAxis * Math.cos(angle),
      this.semiMinorAxis * Math.sin(angle),
      0,
    );
  }

  getTangent(t: number, target = new THREE.Vector3()): THREE.Vector3 {
    const angle = t * Math.PI * 2 + this.phase;
    return target
      .set(
        -this.semiMajorAxis * Math.sin(angle),
        this.semiMinorAxis * Math.cos(angle),
        0,
      )
      .normalize();
  }
}

function orientationFromConfig(config: StarOrbitConfig): THREE.Quaternion {
  const zAxis = new THREE.Vector3(0, 0, 1);
  const xAxis = new THREE.Vector3(1, 0, 0);
  const azimuth = new THREE.Quaternion().setFromAxisAngle(
    zAxis,
    THREE.MathUtils.degToRad(config.azimuth),
  );
  const inclination = new THREE.Quaternion().setFromAxisAngle(
    xAxis,
    THREE.MathUtils.degToRad(config.inclination),
  );
  const roll = new THREE.Quaternion().setFromAxisAngle(
    zAxis,
    THREE.MathUtils.degToRad(config.roll),
  );
  return azimuth.multiply(inclination).multiply(roll).normalize();
}

function exportConfig(config: StarOrbitConfig): StarOrbitExportConfig {
  const quaternion = orientationFromConfig(config);
  const normal = new THREE.Vector3(0, 0, 1).applyQuaternion(quaternion);
  return {
    ...config,
    normal: [normal.x, normal.y, normal.z],
    quaternion: [
      quaternion.x,
      quaternion.y,
      quaternion.z,
      quaternion.w,
    ],
  };
}

function measureOrbit(
  config: StarOrbitConfig,
  curve: CenteredOrbitCurve,
  orientation: THREE.Quaternion,
): { metric: StarOrbitMetric; points: THREE.Vector3[] } {
  const points = Array.from({ length: SAMPLE_COUNT }, (_, index) =>
    curve
      .getPoint(index / SAMPLE_COUNT)
      .multiplyScalar(config.scale)
      .applyQuaternion(orientation),
  );
  const radii = points.map((point) => point.length());
  const center = points
    .reduce((sum, point) => sum.add(point), new THREE.Vector3())
    .multiplyScalar(1 / points.length);
  let minimumForwardDot = 1;
  for (let index = 0; index < points.length; index += 1) {
    const previous = points[(index - 1 + points.length) % points.length];
    const current = points[index];
    const next = points[(index + 1) % points.length];
    const incoming = current.clone().sub(previous).normalize();
    const outgoing = next.clone().sub(current).normalize();
    minimumForwardDot = Math.min(minimumForwardDot, incoming.dot(outgoing));
  }

  return {
    points,
    metric: {
      id: config.id,
      minRadius: Math.min(...radii),
      maxRadius: Math.max(...radii),
      centerOffset: center.length(),
      closureDistance: curve
        .getPoint(0)
        .multiplyScalar(config.scale)
        .applyQuaternion(orientation)
        .distanceTo(
          curve
            .getPoint(1)
            .multiplyScalar(config.scale)
            .applyQuaternion(orientation),
        ),
      seamTangentDot: curve
        .getTangent(0)
        .applyQuaternion(orientation)
        .dot(curve.getTangent(1).applyQuaternion(orientation)),
      minimumForwardDot,
      selfIntersection: false,
    },
  };
}

function createMetrics(
  measurements: Array<{
    metric: StarOrbitMetric;
    points: THREE.Vector3[];
  }>,
  coreRadius: number,
): StarOrbitMetrics {
  const points = measurements.flatMap(({ points: orbitPoints }) => orbitPoints);
  const extent = new THREE.Box3()
    .setFromPoints(points)
    .getSize(new THREE.Vector3());
  const radii = points.map((point) => point.length());
  return {
    orbitCount: measurements.length,
    commonCenter: [0, 0, 0],
    coreRadius,
    minRadius: Math.min(...radii),
    maxRadius: Math.max(...radii),
    extent: [extent.x, extent.y, extent.z],
    extentRatio:
      Math.max(extent.x, extent.y, extent.z) /
      Math.min(extent.x, extent.y, extent.z),
    orbits: measurements.map(({ metric }) => metric),
  };
}

function signedAngleAroundAxis(
  from: THREE.Vector3,
  to: THREE.Vector3,
  axis: THREE.Vector3,
) {
  return Math.atan2(
    axis.dot(new THREE.Vector3().crossVectors(from, to)),
    THREE.MathUtils.clamp(from.dot(to), -1, 1),
  );
}

function createRibbonGeometry(
  id: StarOrbitId,
  curve: CenteredOrbitCurve,
  width: number,
  thickness: number,
  halfTwist: boolean,
  frameConfig = RIBBON_FRAME_CONFIG[id],
): { geometry: THREE.BufferGeometry; metrics: RibbonFrameMetrics } {
  const ringCount = RIBBON_SEGMENTS + 1;
  const points = Array.from({ length: ringCount }, (_, index) =>
    curve.getPoint(index / RIBBON_SEGMENTS),
  );
  const tangents = Array.from(
    { length: ringCount },
    (_, index) => curve.getTangent(index / RIBBON_SEGMENTS),
  );
  const widthFrames: THREE.Vector3[] = [];
  const initialWidth = points[0]
    .clone()
    .addScaledVector(tangents[0], -points[0].dot(tangents[0]))
    .normalize();
  widthFrames.push(initialWidth);

  for (let index = 1; index < ringCount; index += 1) {
    const transport = new THREE.Quaternion().setFromUnitVectors(
      tangents[index - 1],
      tangents[index],
    );
    const widthFrame = widthFrames[index - 1]
      .clone()
      .applyQuaternion(transport)
      .addScaledVector(
        tangents[index],
        -widthFrames[index - 1]
          .clone()
          .applyQuaternion(transport)
          .dot(tangents[index]),
      )
      .normalize();
    widthFrames.push(widthFrame);
  }

  const transportedSeamWidth = widthFrames[RIBBON_SEGMENTS].clone();
  const seamCorrection = signedAngleAroundAxis(
    transportedSeamWidth,
    initialWidth,
    tangents[0],
  );

  widthFrames.forEach((frame, index) => {
    frame.applyAxisAngle(
      tangents[index],
      seamCorrection * (index / RIBBON_SEGMENTS),
    );
    const naturalRoll =
      frameConfig.naturalRoll && !halfTwist
        ? THREE.MathUtils.degToRad(
            frameConfig.rollAmplitudeDegrees,
          ) *
          Math.sin(
            (index / RIBBON_SEGMENTS) * Math.PI * 2 +
              THREE.MathUtils.degToRad(
                frameConfig.rollPhaseDegrees,
              ),
          )
        : 0;
    frame.applyAxisAngle(
      tangents[index],
      THREE.MathUtils.degToRad(frameConfig.phaseDegrees) +
        naturalRoll,
    );
    if (halfTwist) {
      frame.applyAxisAngle(
        tangents[index],
        Math.PI * (index / RIBBON_SEGMENTS),
      );
    }
    frame.normalize();
  });

  const vertices: number[] = [];
  const centerlines: number[] = [];
  const widthOffsets: number[] = [];
  const thicknessOffsets: number[] = [];
  const tangentsAttribute: number[] = [];
  const progressAttribute: number[] = [];
  const normals: number[] = [];
  const uvs: number[] = [];
  const faceTypes: number[] = [];
  const indices: number[] = [];
  const geometryGroups: Array<{
    start: number;
    count: number;
    materialIndex: number;
  }> = [];
  const halfWidth = width * 0.5;
  const halfThickness = thickness * 0.5;
  const bevelWidth = Math.min(
    PANTHEON_BAND_DIMENSIONS.bevelWidth,
    halfThickness * 0.92,
  );
  const bevelSegments = PANTHEON_BAND_DIMENSIONS.bevelSegments;
  const faces: Array<{
    corners: Array<[number, number]>;
    materialIndex: number;
    faceType: number;
    normalCoefficients: [number, number];
  }> = [];
  const addFace = (
    a: [number, number],
    b: [number, number],
    normalCoefficients: [number, number],
    materialIndex: number,
    faceType: number,
  ) => {
    faces.push({
      corners: [a, b],
      materialIndex,
      faceType,
      normalCoefficients,
    });
  };
  const topLeft: [number, number] = [
    -halfWidth + bevelWidth,
    halfThickness,
  ];
  const topRight: [number, number] = [
    halfWidth - bevelWidth,
    halfThickness,
  ];
  addFace(topRight, topLeft, [0, 1], 0, 0);
  const addBevel = (
    centerX: number,
    centerY: number,
    startAngle: number,
    endAngle: number,
  ) => {
    for (let segment = 0; segment < bevelSegments; segment += 1) {
      const start =
        startAngle +
        ((endAngle - startAngle) * segment) / bevelSegments;
      const end =
        startAngle +
        ((endAngle - startAngle) * (segment + 1)) / bevelSegments;
      const midpoint = (start + end) * 0.5;
      addFace(
        [
          centerX + Math.cos(start) * bevelWidth,
          centerY + Math.sin(start) * bevelWidth,
        ],
        [
          centerX + Math.cos(end) * bevelWidth,
          centerY + Math.sin(end) * bevelWidth,
        ],
        [Math.cos(midpoint), Math.sin(midpoint)],
        1,
        1,
      );
    }
  };
  addBevel(
    halfWidth - bevelWidth,
    halfThickness - bevelWidth,
    Math.PI / 2,
    0,
  );
  addFace(
    [halfWidth, halfThickness - bevelWidth],
    [halfWidth, -halfThickness + bevelWidth],
    [1, 0],
    2,
    2,
  );
  addBevel(
    halfWidth - bevelWidth,
    -halfThickness + bevelWidth,
    0,
    -Math.PI / 2,
  );
  addFace(
    [halfWidth - bevelWidth, -halfThickness],
    [-halfWidth + bevelWidth, -halfThickness],
    [0, -1],
    0,
    0,
  );
  addBevel(
    -halfWidth + bevelWidth,
    -halfThickness + bevelWidth,
    -Math.PI / 2,
    -Math.PI,
  );
  addFace(
    [-halfWidth, -halfThickness + bevelWidth],
    [-halfWidth, halfThickness - bevelWidth],
    [-1, 0],
    2,
    2,
  );
  addBevel(
    -halfWidth + bevelWidth,
    halfThickness - bevelWidth,
    Math.PI,
    Math.PI / 2,
  );
  let maxOrthonormalError = 0;
  widthFrames.forEach((widthFrame, index) => {
    const thicknessFrame = new THREE.Vector3()
      .crossVectors(tangents[index], widthFrame)
      .normalize();
    maxOrthonormalError = Math.max(
      maxOrthonormalError,
      Math.abs(tangents[index].dot(widthFrame)),
      Math.abs(tangents[index].dot(thicknessFrame)),
      Math.abs(widthFrame.dot(thicknessFrame)),
      Math.abs(1 - widthFrame.length()),
      Math.abs(1 - thicknessFrame.length()),
    );
    faces.forEach((face) => {
      const faceNormal = widthFrame
        .clone()
        .multiplyScalar(face.normalCoefficients[0])
        .addScaledVector(
          thicknessFrame,
          face.normalCoefficients[1],
        )
        .normalize();
      face.corners.forEach(([widthOffset, thicknessOffset], cornerIndex) => {
        const widthCoefficient = widthOffset / halfWidth;
        const thicknessCoefficient = thicknessOffset / halfThickness;
        const vertex = points[index]
          .clone()
          .addScaledVector(widthFrame, widthOffset)
          .addScaledVector(thicknessFrame, thicknessOffset);
        vertices.push(vertex.x, vertex.y, vertex.z);
        centerlines.push(
          points[index].x,
          points[index].y,
          points[index].z,
        );
        widthOffsets.push(
          widthFrame.x * widthCoefficient,
          widthFrame.y * widthCoefficient,
          widthFrame.z * widthCoefficient,
        );
        thicknessOffsets.push(
          thicknessFrame.x * thicknessCoefficient,
          thicknessFrame.y * thicknessCoefficient,
          thicknessFrame.z * thicknessCoefficient,
        );
        tangentsAttribute.push(
          tangents[index].x,
          tangents[index].y,
          tangents[index].z,
        );
        progressAttribute.push(index / RIBBON_SEGMENTS);
        normals.push(faceNormal.x, faceNormal.y, faceNormal.z);
        uvs.push(index / RIBBON_SEGMENTS, cornerIndex);
        faceTypes.push(face.faceType);
      });
    });
  });

  faces.forEach((face, faceIndex) => {
    const groupStart = indices.length;
    for (let index = 0; index < RIBBON_SEGMENTS; index += 1) {
      const current = index * faces.length * 2 + faceIndex * 2;
      const next =
        (index + 1) * faces.length * 2 + faceIndex * 2;
      indices.push(
        current,
        current + 1,
        next,
        current + 1,
        next + 1,
        next,
      );
    }
    const groupCount = indices.length - groupStart;
    // group 0 = top/bottom；group 1 = bevel；group 2 = thickness edge。
    geometryGroups.push({
      start: groupStart,
      count: groupCount,
      materialIndex: face.materialIndex,
    });
  });

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(vertices, 3),
  );
  geometry.setAttribute(
    "aCenterline",
    new THREE.Float32BufferAttribute(centerlines, 3),
  );
  geometry.setAttribute(
    "aWidthOffset",
    new THREE.Float32BufferAttribute(widthOffsets, 3),
  );
  geometry.setAttribute(
    "aThicknessOffset",
    new THREE.Float32BufferAttribute(thicknessOffsets, 3),
  );
  geometry.setAttribute(
    "aTangent",
    new THREE.Float32BufferAttribute(tangentsAttribute, 3),
  );
  geometry.setAttribute(
    "aOrbitProgress",
    new THREE.Float32BufferAttribute(progressAttribute, 1),
  );
  geometry.setAttribute(
    "normal",
    new THREE.Float32BufferAttribute(normals, 3),
  );
  geometry.setAttribute(
    "uv",
    new THREE.Float32BufferAttribute(uvs, 2),
  );
  geometry.setAttribute(
    "aFaceType",
    new THREE.Float32BufferAttribute(faceTypes, 1),
  );
  geometry.setIndex(indices);
  geometryGroups.forEach((group) =>
    geometry.addGroup(
      group.start,
      group.count,
      group.materialIndex,
    ),
  );

  let degenerateTriangleCount = 0;
  const position = geometry.getAttribute("position");
  const index = geometry.getIndex()!;
  for (let offset = 0; offset < index.count; offset += 3) {
    const a = new THREE.Vector3().fromBufferAttribute(
      position,
      index.getX(offset),
    );
    const b = new THREE.Vector3().fromBufferAttribute(
      position,
      index.getX(offset + 1),
    );
    const c = new THREE.Vector3().fromBufferAttribute(
      position,
      index.getX(offset + 2),
    );
    if (
      new THREE.Vector3()
        .crossVectors(b.clone().sub(a), c.clone().sub(a))
        .lengthSq() < 1e-14
    ) {
      degenerateTriangleCount += 1;
    }
  }

  let minimumAdjacentFrameDot = 1;
  let frameFlipCount = 0;
  for (let index = 1; index < widthFrames.length; index += 1) {
    const dot = widthFrames[index - 1].dot(widthFrames[index]);
    minimumAdjacentFrameDot = Math.min(minimumAdjacentFrameDot, dot);
    if (dot < 0) frameFlipCount += 1;
  }
  const finalSeamWidth = widthFrames[RIBBON_SEGMENTS].clone();
  const seamTarget = initialWidth
    .clone()
    .multiplyScalar(halfTwist ? -1 : 1);
  const startNormal = new THREE.Vector3()
    .crossVectors(tangents[0], widthFrames[0])
    .normalize();
  const endNormal = new THREE.Vector3()
    .crossVectors(
      tangents[RIBBON_SEGMENTS],
      widthFrames[RIBBON_SEGMENTS],
    )
    .normalize();
  const normalTarget = startNormal
    .clone()
    .multiplyScalar(halfTwist ? -1 : 1);

  return {
    geometry,
    metrics: {
      id,
      phaseDegrees: frameConfig.phaseDegrees,
      naturalRoll: frameConfig.naturalRoll && !halfTwist,
      rollAmplitudeDegrees:
        frameConfig.naturalRoll && !halfTwist
          ? frameConfig.rollAmplitudeDegrees
          : 0,
      rollPhaseDegrees: frameConfig.rollPhaseDegrees,
      minimumAdjacentFrameDot,
      seamAlignment: finalSeamWidth.dot(seamTarget),
      seamNormalDot: endNormal.dot(normalTarget),
      seamTangentDot: tangents[RIBBON_SEGMENTS].dot(tangents[0]),
      seamSideDot: finalSeamWidth.dot(seamTarget),
      seamUvDelta: Math.abs(
        RIBBON_SEGMENTS / RIBBON_SEGMENTS - 1,
      ),
      frameFlipCount,
      maxOrthonormalError,
      degenerateTriangleCount,
    },
  };
}

function matchesLockedGeometry(
  configs: readonly StarOrbitConfig[],
  lockedConfigs: readonly StarOrbitConfig[],
) {
  return configs.every((config, index) => {
    const locked = lockedConfigs[index];
    return (
      locked &&
      (
        [
          "id",
          "semiMajorAxis",
          "semiMinorAxis",
          "phase",
          "scale",
          "inclination",
          "azimuth",
          "roll",
        ] as const
      ).every((field) => config[field] === locked[field])
    );
  });
}

export function createPantheonStarOrbits(
  options: {
    ribbonFrameMode?: RibbonFrameMode;
    geometryVersion?: PantheonGeometryVersion;
  } = {},
): THREE.Group {
  const ribbonFrameMode = options.ribbonFrameMode ?? "selected";
  const geometryVersion = options.geometryVersion ?? "v1.1";
  const activeGeometryLock =
    geometryVersion === "v1.0" ? geometryLockV1 : geometryLockV1_1;
  const lockedConfigs =
    geometryVersion === "v1.0"
      ? STAR_ORBIT_CONFIGS_V1
      : STAR_ORBIT_CONFIGS;
  const root = new THREE.Group();
  root.name = "PantheonStarOrbits";
  const orbitGroup = new THREE.Group();
  orbitGroup.name = "StarOrbitTracks";
  root.add(orbitGroup);
  const ribbonGroup = new THREE.Group();
  ribbonGroup.name = "NarrowRibbonPrototype";
  ribbonGroup.userData.publicName = "PantheonBandSystem";
  ribbonGroup.visible = false;
  root.add(ribbonGroup);
  const mobiusGroup = new THREE.Group();
  mobiusGroup.name = "MobiusFramePrototype";
  mobiusGroup.visible = false;
  root.add(mobiusGroup);
  const hitAreaGroup = new THREE.Group();
  hitAreaGroup.name = "OrbitHitAreas";
  root.add(hitAreaGroup);

  const orbitMaterial = new THREE.MeshBasicMaterial({
    color: 0xf5f5f2,
    toneMapped: false,
  });
  const ribbonMaterial = new THREE.MeshStandardMaterial({
    color: 0xf5f5f2,
    metalness: 0,
    roughness: 0.72,
    side: THREE.DoubleSide,
  });
  const coreMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xc9a24f,
    emissive: 0x2a1b06,
    emissiveIntensity: 0.09,
    metalness: 0.92,
    roughness: 0.24,
    clearcoat: 0.12,
    clearcoatRoughness: 0.18,
    envMapIntensity: 0.74,
  });
  const core = new THREE.Mesh(
    new THREE.SphereGeometry(SELF_CORE_RADIUS, 48, 32),
    coreMaterial,
  );
  core.name = "SelfCore";
  core.position.set(0, 0, 0);
  core.userData = {
    geometryRole: "self-core",
    radius: SELF_CORE_RADIUS,
  };
  root.add(core);

  const configs = lockedConfigs.map((config) => ({ ...config }));
  const curves = new Map<StarOrbitId, CenteredOrbitCurve>();
  const meshes = new Map<StarOrbitId, THREE.Mesh>();
  const ribbonMeshes = new Map<StarOrbitId, THREE.Mesh>();
  const mobiusMeshes = new Map<StarOrbitId, THREE.Mesh>();
  const hitAreaMeshes = new Map<StarOrbitId, THREE.Mesh>();
  let geometryLocked = true;
  let newVersionRequired = false;
  let coreRadius = SELF_CORE_RADIUS;
  let presentationMode: StarOrbitPresentationMode = "centerline";
  let ribbonMetrics = {} as RibbonPrototypeMetrics;

  configs.forEach((config) => {
    const curve = new CenteredOrbitCurve(config);
    curves.set(config.id, curve);
    const orbit = new THREE.Mesh(
      new THREE.TubeGeometry(
        curve,
        TUBULAR_SEGMENTS,
        TUBE_RADIUS,
        RADIAL_SEGMENTS,
        true,
      ),
      orbitMaterial,
    );
    orbit.name = `StarOrbit.${config.id}`;
    orbit.quaternion.copy(orientationFromConfig(config));
    orbit.scale.setScalar(config.scale);
    orbit.userData = {
      id: config.id,
      center: [0, 0, 0],
      closed: true,
      geometryRole: "orbit",
    };
    meshes.set(config.id, orbit);
    orbitGroup.add(orbit);

    const hitArea = new THREE.Mesh(
      new THREE.TubeGeometry(
        curve,
        TUBULAR_SEGMENTS,
        TUBE_RADIUS * 2.75,
        5,
        true,
      ),
      new THREE.MeshBasicMaterial({
        transparent: true,
        opacity: 0,
        depthWrite: false,
        colorWrite: false,
      }),
    );
    hitArea.name = `OrbitHitArea.${config.id}`;
    hitArea.quaternion.copy(orientationFromConfig(config));
    hitArea.scale.setScalar(config.scale);
    hitArea.userData = {
      id: config.id,
      geometryRole: "orbit-hit-area",
    };
    hitAreaMeshes.set(config.id, hitArea);
    hitAreaGroup.add(hitArea);
  });

  const applyPose = (config: StarOrbitConfig) => {
    const quaternion = orientationFromConfig(config);
    [meshes, ribbonMeshes, mobiusMeshes, hitAreaMeshes].forEach((collection) => {
      const mesh = collection.get(config.id);
      if (!mesh) return;
      mesh.quaternion.copy(quaternion);
      mesh.scale.setScalar(config.scale);
      mesh.position.set(0, 0, 0);
    });
  };

  const clearPrototypeGroup = (
    group: THREE.Group,
    collection: Map<StarOrbitId, THREE.Mesh>,
  ) => {
    group.children.forEach((child) => {
      if (child instanceof THREE.Mesh) child.geometry.dispose();
    });
    group.clear();
    collection.clear();
  };

  const rebuildRibbonPrototypes = (width: number, thickness: number) => {
    clearPrototypeGroup(ribbonGroup, ribbonMeshes);
    clearPrototypeGroup(mobiusGroup, mobiusMeshes);
    const regular: RibbonFrameMetrics[] = [];
    const mobius: RibbonFrameMetrics[] = [];
    configs.forEach((config) => {
      const curve = curves.get(config.id)!;
      const regularPrototype = createRibbonGeometry(
        config.id,
        curve,
        width,
        thickness,
        false,
        resolveRibbonFrameConfig(config.id, ribbonFrameMode),
      );
      const regularMesh = new THREE.Mesh(
        regularPrototype.geometry,
        ribbonMaterial,
      );
      regularMesh.name = `NarrowRibbon.${config.id}`;
      regularMesh.userData = {
        geometryRole: "narrow-ribbon",
        publicRole: "pantheon-band",
        publicName: `PantheonBand.${config.id}`,
      };
      ribbonMeshes.set(config.id, regularMesh);
      ribbonGroup.add(regularMesh);
      regular.push(regularPrototype.metrics);

      const mobiusPrototype = createRibbonGeometry(
        config.id,
        curve,
        width,
        thickness,
        true,
        resolveRibbonFrameConfig(config.id, ribbonFrameMode),
      );
      const mobiusMesh = new THREE.Mesh(
        mobiusPrototype.geometry,
        ribbonMaterial,
      );
      mobiusMesh.name = `MobiusFrame.${config.id}`;
      mobiusMesh.userData.geometryRole = "mobius-frame-test";
      mobiusMeshes.set(config.id, mobiusMesh);
      mobiusGroup.add(mobiusMesh);
      mobius.push(mobiusPrototype.metrics);
      applyPose(config);
    });

    const ordered = [...configs].sort(
      (a, b) =>
        b.semiMajorAxis * b.scale - a.semiMajorAxis * a.scale,
    );
    const minimumShellClearance = Math.min(
      ...ordered.slice(0, -1).map((outer, index) => {
        const inner = ordered[index + 1];
        const shellGap =
          outer.semiMinorAxis * outer.scale -
          inner.semiMajorAxis * inner.scale;
        const prototypeReach =
          width * Math.max(outer.scale, inner.scale) +
          thickness * Math.max(outer.scale, inner.scale);
        return shellGap - prototypeReach;
      }),
    );
    ribbonMetrics = {
      width,
      thickness,
      bevelWidth: PANTHEON_BAND_DIMENSIONS.bevelWidth,
      bevelSegments: PANTHEON_BAND_DIMENSIONS.bevelSegments,
      profileFaceCount: regularPrototypeFaceCount(),
      minimumShellClearance,
      hasShellPenetration: minimumShellClearance <= 0,
      regular,
      mobius,
    };
    return ribbonMetrics;
  };
  function regularPrototypeFaceCount() {
    return 4 + PANTHEON_BAND_DIMENSIONS.bevelSegments * 4;
  }

  const runtime = {
    configs,
    metrics: {} as StarOrbitMetrics,
    get ribbonMetrics() {
      return ribbonMetrics;
    },
    get bandMetrics() {
      return ribbonMetrics;
    },
    get presentationMode() {
      return presentationMode;
    },
    get ribbonFrameMode() {
      return ribbonFrameMode;
    },
    getExportConfigs() {
      return configs.map(exportConfig);
    },
    assertGeometryWritable() {
      if (geometryLocked) {
        throw new Error(
          "Geometry v1.0 is LOCKED. Unlocking requires a new geometry version.",
        );
      }
    },
    unlockGeometry(confirmation: string) {
      if (confirmation !== "CREATE_GEOMETRY_V1_1") {
        throw new Error(
          "Unlock rejected. Confirm CREATE_GEOMETRY_V1_1 to create a new version.",
        );
      }
      geometryLocked = false;
      newVersionRequired = true;
      return this.getGeometryLock();
    },
    updateAngles(
      id: StarOrbitId,
      patch: Partial<Pick<StarOrbitConfig, "inclination" | "azimuth" | "roll">>,
    ) {
      this.assertGeometryWritable();
      const config = configs.find((candidate) => candidate.id === id);
      if (!config) return this.getExportConfigs();
      Object.assign(config, patch);
      applyPose(config);
      this.recalculateMetrics();
      return this.getExportConfigs();
    },
    setOrbitScale(id: StarOrbitId, scale: number) {
      this.assertGeometryWritable();
      const config = configs.find((candidate) => candidate.id === id);
      if (!config) return this.getExportConfigs();
      config.scale = scale;
      applyPose(config);
      rebuildRibbonPrototypes(
        ribbonMetrics.width,
        ribbonMetrics.thickness,
      );
      this.recalculateMetrics();
      return this.getExportConfigs();
    },
    resetAngles() {
      this.assertGeometryWritable();
      configs.splice(
        0,
        configs.length,
        ...lockedConfigs.map((config) => ({ ...config })),
      );
      configs.forEach(applyPose);
      rebuildRibbonPrototypes(
        ribbonMetrics.width,
        ribbonMetrics.thickness,
      );
      this.recalculateMetrics();
      return this.getExportConfigs();
    },
    exportConfigJSON() {
      return JSON.stringify(this.getExportConfigs(), null, 2);
    },
    setMonochrome(enabled: boolean) {
      coreMaterial.color.set(enabled ? 0xf5f5f2 : 0xc9a24f);
      coreMaterial.emissive.set(enabled ? 0x000000 : 0x2a1b06);
    },
    setCoreRadius(radius: number) {
      this.assertGeometryWritable();
      coreRadius = radius;
      core.scale.setScalar(radius / SELF_CORE_RADIUS);
      core.userData.radius = radius;
      this.recalculateMetrics();
      return coreRadius;
    },
    setPresentationMode(mode: StarOrbitPresentationMode) {
      presentationMode = mode;
      orbitGroup.visible = mode === "centerline";
      ribbonGroup.visible = mode === "narrow-ribbon";
      mobiusGroup.visible = mode === "mobius-frame";
      return presentationMode;
    },
    setMaterialInteractionMode() {
      presentationMode = "centerline";
      orbitGroup.visible = false;
      ribbonGroup.visible = true;
      mobiusGroup.visible = false;
      return presentationMode;
    },
    updateRibbonPrototype(width: number, thickness: number) {
      return rebuildRibbonPrototypes(width, thickness);
    },
    updateBandPrototype(width: number, thickness: number) {
      return rebuildRibbonPrototypes(width, thickness);
    },
    getGeometryLock() {
      return {
        version: activeGeometryLock.version,
        locked: geometryLocked,
        newVersionRequired,
        signature: activeGeometryLock.centerlineSignature,
        centerlineSignature: activeGeometryLock.centerlineSignature,
        poseSignature:
          geometryVersion === "v1.1"
            ? PANTHEON_ORBIT_POSE_SIGNATURE
            : activeGeometryLock.centerlineSignature,
        poseVersion:
          geometryVersion === "v1.1"
            ? PANTHEON_ORBIT_POSE_VERSION
            : "Geometry v1.0 pose",
        currentSignature: matchesLockedGeometry(configs, lockedConfigs)
          ? activeGeometryLock.centerlineSignature
          : "modified:new-version-required",
        geometryVersionSignature:
          "geometryVersionSignature" in activeGeometryLock
            ? activeGeometryLock.geometryVersionSignature
            : activeGeometryLock.centerlineSignature,
        baseCenterlineSignature:
          "baseCenterlineSignature" in activeGeometryLock
            ? activeGeometryLock.baseCenterlineSignature
            : activeGeometryLock.centerlineSignature,
        orbitCount: configs.length,
        positions: Object.fromEntries(
          configs.map((config) => [config.id, [0, 0, 0]]),
        ),
        acceptanceReport: activeGeometryLock.acceptanceReport,
      };
    },
    getThemeNodes() {
      return {
        orbitGroup,
        ribbonGroup,
        bandGroup: ribbonGroup,
        mobiusGroup,
        hitAreaGroup,
        core,
        meshes,
        ribbonMeshes,
        hitAreaMeshes,
      };
    },
    getCenterlineSamples(sampleCount = 360) {
      return Object.fromEntries(
        configs.map((config) => {
          const curve = curves.get(config.id)!;
          const quaternion = orientationFromConfig(config);
          return [
            config.id,
            Array.from({ length: sampleCount }, (_, index) =>
              curve
                .getPoint(index / sampleCount)
                .multiplyScalar(config.scale)
                .applyQuaternion(quaternion)
                .toArray(),
            ),
          ];
        }),
      ) as Record<StarOrbitId, [number, number, number][]>;
    },
    recalculateMetrics() {
      const measurements = configs.map((config) =>
        measureOrbit(
          config,
          curves.get(config.id)!,
          orientationFromConfig(config),
        ),
      );
      this.metrics = createMetrics(measurements, coreRadius);
      return this.metrics;
    },
    dispose() {
      orbitGroup.traverse((child) => {
        if (child instanceof THREE.Mesh) child.geometry.dispose();
      });
      hitAreaGroup.traverse((child) => {
        if (!(child instanceof THREE.Mesh)) return;
        child.geometry.dispose();
        if (child.material instanceof THREE.Material) child.material.dispose();
      });
      clearPrototypeGroup(ribbonGroup, ribbonMeshes);
      clearPrototypeGroup(mobiusGroup, mobiusMeshes);
      core.geometry.dispose();
      orbitMaterial.dispose();
      ribbonMaterial.dispose();
      coreMaterial.dispose();
    },
  };
  rebuildRibbonPrototypes(
    NARROW_RIBBON_DEFAULTS.width,
    NARROW_RIBBON_DEFAULTS.thickness,
  );
  runtime.recalculateMetrics();
  root.userData.starOrbitRuntime = runtime;
  return root;
}

export function getPantheonStarOrbitRuntime(root: THREE.Group) {
  return root.userData.starOrbitRuntime as {
    configs: StarOrbitConfig[];
    metrics: StarOrbitMetrics;
    readonly ribbonMetrics: RibbonPrototypeMetrics;
    readonly bandMetrics: RibbonPrototypeMetrics;
    readonly presentationMode: StarOrbitPresentationMode;
    readonly ribbonFrameMode: RibbonFrameMode;
    getExportConfigs: () => StarOrbitExportConfig[];
    assertGeometryWritable: () => void;
    unlockGeometry: (confirmation: string) => GeometryLockState;
    updateAngles: (
      id: StarOrbitId,
      patch: Partial<
        Pick<StarOrbitConfig, "inclination" | "azimuth" | "roll">
      >,
    ) => StarOrbitExportConfig[];
    setOrbitScale: (
      id: StarOrbitId,
      scale: number,
    ) => StarOrbitExportConfig[];
    resetAngles: () => StarOrbitExportConfig[];
    exportConfigJSON: () => string;
    setMonochrome: (enabled: boolean) => void;
    setCoreRadius: (radius: number) => number;
    setPresentationMode: (
      mode: StarOrbitPresentationMode,
    ) => StarOrbitPresentationMode;
    setMaterialInteractionMode: () => StarOrbitPresentationMode;
    updateRibbonPrototype: (
      width: number,
      thickness: number,
    ) => RibbonPrototypeMetrics;
    updateBandPrototype: (
      width: number,
      thickness: number,
    ) => RibbonPrototypeMetrics;
    getGeometryLock: () => GeometryLockState;
    getThemeNodes: () => {
      orbitGroup: THREE.Group;
      ribbonGroup: THREE.Group;
      bandGroup: THREE.Group;
      mobiusGroup: THREE.Group;
      hitAreaGroup: THREE.Group;
      core: THREE.Mesh;
      meshes: Map<StarOrbitId, THREE.Mesh>;
      ribbonMeshes: Map<StarOrbitId, THREE.Mesh>;
      hitAreaMeshes: Map<StarOrbitId, THREE.Mesh>;
    };
    getCenterlineSamples: (
      sampleCount?: number,
    ) => Record<StarOrbitId, [number, number, number][]>;
    recalculateMetrics: () => StarOrbitMetrics;
    dispose: () => void;
  };
}
