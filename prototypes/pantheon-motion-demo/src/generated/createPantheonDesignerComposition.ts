import * as THREE from "three";
import source from "../data/pantheon-track-curves-3d.json";

export type CompositionDebugMode =
  | "none"
  | "reference-sphere"
  | "radius-heat"
  | "curvature"
  | "control-points"
  | "density-grid";

export interface TrackCurveConfig3D {
  id: string;
  label: string;
  controlPoints3D: Array<{ x: number; y: number; z: number }>;
  position: [number, number, number];
  rotation: [number, number, number];
  scale: [number, number, number];
  tubeRadius: number;
  color: string;
  closed: boolean;
  themeMaterialId: string | null;
  lineToRibbonProgress: number;
}

const TRACKS = source.tracks as TrackCurveConfig3D[];
const SAMPLE_COUNT = 360;
const DEBUG_SEGMENTS = 96;
const CORE_RADIUS = source.coreRadius;
const WHITE = new THREE.Color("#f3f0e9");

function makeTransform(config: TrackCurveConfig3D) {
  return new THREE.Matrix4().compose(
    new THREE.Vector3(...config.position),
    new THREE.Quaternion().setFromEuler(
      new THREE.Euler(
        THREE.MathUtils.degToRad(config.rotation[0]),
        THREE.MathUtils.degToRad(config.rotation[1]),
        THREE.MathUtils.degToRad(config.rotation[2]),
      ),
    ),
    new THREE.Vector3(...config.scale),
  );
}

function makeCurve(config: TrackCurveConfig3D) {
  const transform = makeTransform(config);
  return new THREE.CatmullRomCurve3(
    config.controlPoints3D.map(({ x, y, z }) =>
      new THREE.Vector3(x, y, z).applyMatrix4(transform),
    ),
    true,
    "centripetal",
    0.5,
  );
}

function sampleCurve(curve: THREE.Curve<THREE.Vector3>) {
  return Array.from({ length: SAMPLE_COUNT }, (_, index) =>
    curve.getPoint(index / SAMPLE_COUNT),
  );
}

function estimateCurvature(points: THREE.Vector3[], index: number) {
  const previous = points[(index - 1 + points.length) % points.length];
  const current = points[index];
  const next = points[(index + 1) % points.length];
  const a = current.distanceTo(previous);
  const b = next.distanceTo(current);
  const c = previous.distanceTo(next);
  const area2 = new THREE.Vector3()
    .crossVectors(
      current.clone().sub(previous),
      next.clone().sub(previous),
    )
    .length();
  return (2 * area2) / Math.max(a * b * c, 1e-8);
}

function hasApproximateSelfIntersection(points: THREE.Vector3[]) {
  const skip = 10;
  for (let a = 0; a < points.length; a += 1) {
    for (let b = a + skip; b < points.length; b += 1) {
      if (a < skip && b > points.length - skip) continue;
      if (points[a].distanceTo(points[b]) < 0.025) return true;
    }
  }
  return false;
}

function makeSegmentHeatmap(
  curve: THREE.Curve<THREE.Vector3>,
  tubeRadius: number,
  colorAt: (t: number) => THREE.Color,
) {
  const group = new THREE.Group();
  for (let index = 0; index < DEBUG_SEGMENTS; index += 1) {
    const start = index / DEBUG_SEGMENTS;
    const end = (index + 1) / DEBUG_SEGMENTS;
    group.add(
      new THREE.Mesh(
        new THREE.TubeGeometry(
          new THREE.LineCurve3(curve.getPoint(start), curve.getPoint(end)),
          1,
          tubeRadius * 1.28,
          6,
          false,
        ),
        new THREE.MeshBasicMaterial({ color: colorAt((start + end) / 2) }),
      ),
    );
  }
  return group;
}

function makeControlPointDebug(
  config: TrackCurveConfig3D,
  curve: THREE.Curve<THREE.Vector3>,
) {
  const group = new THREE.Group();
  const transform = makeTransform(config);
  config.controlPoints3D.forEach(({ x, y, z }, index) => {
    const point = new THREE.Vector3(x, y, z).applyMatrix4(transform);
    const marker = new THREE.Mesh(
      new THREE.SphereGeometry(0.025, 12, 8),
      new THREE.MeshBasicMaterial({
        color: index === 0 ? 0xffd27d : 0xffffff,
      }),
    );
    marker.position.copy(point);
    marker.userData.controlPointIndex = index;
    group.add(marker);
    const tangent = curve.getTangent(index / config.controlPoints3D.length);
    group.add(
      new THREE.ArrowHelper(tangent, point, 0.12, 0x7dd8ff, 0.025, 0.015),
    );
  });
  return group;
}

function makeDensityDebug(density: number[]) {
  const group = new THREE.Group();
  const maximum = Math.max(...density);
  const cellSize = 2 / 3;
  density.forEach((value, index) => {
    const row = Math.floor(index / 3);
    const column = index % 3;
    const plane = new THREE.Mesh(
      new THREE.PlaneGeometry(cellSize - 0.016, cellSize - 0.016),
      new THREE.MeshBasicMaterial({
        color: new THREE.Color("#254c5e").lerp(
          new THREE.Color("#c99555"),
          value / maximum,
        ),
        transparent: true,
        opacity: 0.12 + (value / maximum) * 0.24,
        depthWrite: false,
        side: THREE.DoubleSide,
      }),
    );
    plane.position.set(
      -1 + cellSize * (column + 0.5),
      1 - cellSize * (row + 0.5),
      1.04,
    );
    group.add(plane);
  });
  const points: THREE.Vector3[] = [];
  [-1, -1 / 3, 1 / 3, 1].forEach((value) => {
    points.push(
      new THREE.Vector3(value, -1, 1.05),
      new THREE.Vector3(value, 1, 1.05),
      new THREE.Vector3(-1, value, 1.05),
      new THREE.Vector3(1, value, 1.05),
    );
  });
  group.add(
    new THREE.LineSegments(
      new THREE.BufferGeometry().setFromPoints(points),
      new THREE.LineBasicMaterial({ color: 0xe0c99d, depthTest: false }),
    ),
  );
  return group;
}

function measure(curves: Map<string, THREE.CatmullRomCurve3>) {
  const allPoints: THREE.Vector3[] = [];
  const samples = new Map<string, THREE.Vector3[]>();
  const nineGridDensity = Array.from({ length: 9 }, () => 0);
  const curveMetrics = TRACKS.map((config) => {
    const curve = curves.get(config.id)!;
    const points = sampleCurve(curve);
    samples.set(config.id, points);
    allPoints.push(...points);
    const radii = points.map((point) => point.length());
    const curvatures = points.map((_, index) =>
      estimateCurvature(points, index),
    );
    points.forEach((point, index) => {
      const next = points[(index + 1) % points.length];
      const middle = point.clone().add(next).multiplyScalar(0.5);
      const column = THREE.MathUtils.clamp(
        Math.floor(((middle.x + 1) / 2) * 3),
        0,
        2,
      );
      const row = THREE.MathUtils.clamp(
        2 - Math.floor(((middle.y + 1) / 2) * 3),
        0,
        2,
      );
      nineGridDensity[row * 3 + column] += Math.hypot(
        next.x - point.x,
        next.y - point.y,
      );
    });
    const maxCurvature = Math.max(...curvatures);
    return {
      id: config.id,
      controlPointCount: config.controlPoints3D.length,
      minRadius: Math.min(...radii),
      maxRadius: Math.max(...radii),
      averageRadius:
        radii.reduce((sum, value) => sum + value, 0) / radii.length,
      shellCoverage:
        radii.filter((value) => value >= 0.88 && value <= 1.02).length /
        radii.length,
      maxCurvature,
      minBendingRadius: 1 / maxCurvature,
      coreDistance: Math.min(...radii),
      selfIntersection: hasApproximateSelfIntersection(points),
      seamDistance: curve.getPoint(0).distanceTo(curve.getPoint(1)),
      seamTangentDot: curve.getTangent(0).dot(curve.getTangent(0.99999)),
    };
  });
  const pairwiseMinimumDistance: Record<string, number> = {};
  TRACKS.forEach((first, firstIndex) => {
    TRACKS.slice(firstIndex + 1).forEach((second) => {
      let minimum = Infinity;
      samples.get(first.id)!.forEach((a) => {
        samples.get(second.id)!.forEach((b) => {
          minimum = Math.min(minimum, a.distanceTo(b));
        });
      });
      pairwiseMinimumDistance[`${first.id}:${second.id}`] = minimum;
    });
  });
  const centroid = allPoints
    .reduce((sum, point) => sum.add(point), new THREE.Vector3())
    .multiplyScalar(1 / allPoints.length);
  const size = new THREE.Box3()
    .setFromPoints(allPoints)
    .getSize(new THREE.Vector3());
  const extentValues = [size.x, size.y, size.z];
  const meanDensity =
    nineGridDensity.reduce((sum, value) => sum + value, 0) / 9;
  return {
    curveCount: TRACKS.length,
    curveMetrics,
    pairwiseMinimumDistance,
    centroid: [centroid.x, centroid.y, centroid.z] as [number, number, number],
    centroidLength: centroid.length(),
    extent: {
      x: size.x,
      y: size.y,
      z: size.z,
      ratio: Math.max(...extentValues) / Math.min(...extentValues),
    },
    nineGridDensity,
    nineGridMaxToMean: Math.max(...nineGridDensity) / meanDensity,
    nearestCoreDistance: Math.min(
      ...curveMetrics.map((metric) => metric.coreDistance),
    ),
    coreRadius: CORE_RADIUS,
  };
}

export function createPantheonDesignerComposition(): THREE.Group {
  const root = new THREE.Group();
  root.name = "PantheonTrackSphereC3";
  const trackGroup = new THREE.Group();
  trackGroup.name = "PantheonSphere";
  root.add(trackGroup);
  const debugGroups = new Map<CompositionDebugMode, THREE.Group>();
  const curves = new Map<string, THREE.CatmullRomCurve3>();
  const trackMeshes = new Map<string, THREE.Mesh>();
  const materials = new Map<string, THREE.MeshStandardMaterial>();

  TRACKS.forEach((config) => {
    const curve = makeCurve(config);
    curves.set(config.id, curve);
    const material = new THREE.MeshStandardMaterial({
      color: config.color,
      emissive: new THREE.Color(config.color).multiplyScalar(0.08),
      metalness: 0.14,
      roughness: 0.5,
    });
    materials.set(config.id, material);
    const mesh = new THREE.Mesh(
      new THREE.TubeGeometry(curve, 256, config.tubeRadius, 8, true),
      material,
    );
    mesh.name = `Track_${config.id}`;
    mesh.userData.trackId = config.id;
    trackGroup.add(mesh);
    trackMeshes.set(config.id, mesh);
  });

  const metrics = measure(curves);
  const reference = new THREE.Group();
  reference.add(
    new THREE.Mesh(
      new THREE.SphereGeometry(1, 24, 16),
      new THREE.MeshBasicMaterial({
        color: 0x8297a4,
        wireframe: true,
        transparent: true,
        opacity: 0.16,
        depthWrite: false,
      }),
    ),
  );
  debugGroups.set("reference-sphere", reference);

  const radiusHeat = new THREE.Group();
  const curvatureHeat = new THREE.Group();
  const controls = new THREE.Group();
  TRACKS.forEach((config) => {
    const curve = curves.get(config.id)!;
    radiusHeat.add(
      makeSegmentHeatmap(curve, config.tubeRadius, (t) => {
        const radius = curve.getPoint(t).length();
        return radius < 0.88
          ? new THREE.Color("#f16f68").lerp(
              new THREE.Color("#e8c263"),
              THREE.MathUtils.clamp((radius - 0.5) / 0.38, 0, 1),
            )
          : new THREE.Color("#68cbd1");
      }),
    );
    const points = sampleCurve(curve);
    const maximum = Math.max(
      ...points.map((_, index) => estimateCurvature(points, index)),
    );
    curvatureHeat.add(
      makeSegmentHeatmap(curve, config.tubeRadius, (t) =>
        new THREE.Color("#5cc7d0").lerp(
          new THREE.Color("#ff646d"),
          estimateCurvature(
            points,
            Math.floor(t * SAMPLE_COUNT) % SAMPLE_COUNT,
          ) / maximum,
        ),
      ),
    );
    controls.add(makeControlPointDebug(config, curve));
  });
  debugGroups.set("radius-heat", radiusHeat);
  debugGroups.set("curvature", curvatureHeat);
  debugGroups.set("control-points", controls);
  debugGroups.set("density-grid", makeDensityDebug(metrics.nineGridDensity));
  debugGroups.forEach((group, mode) => {
    group.name = `Debug_${mode}`;
    group.visible = false;
    root.add(group);
  });

  const core = new THREE.Mesh(
    new THREE.SphereGeometry(CORE_RADIUS, 40, 24),
    new THREE.MeshStandardMaterial({
      color: 0xc79b50,
      emissive: 0x281805,
      metalness: 0.72,
      roughness: 0.32,
    }),
  );
  core.name = "CoreTimeSphere";
  root.add(core);

  let debugMode: CompositionDebugMode = "none";
  let soloTrack: string | null = null;
  const applyVisibility = () => {
    trackGroup.visible =
      debugMode === "none" ||
      debugMode === "reference-sphere" ||
      debugMode === "density-grid" ||
      debugMode === "control-points";
    debugGroups.forEach((group, mode) => {
      group.visible = debugMode === mode;
    });
    trackMeshes.forEach((mesh, id) => {
      mesh.visible = soloTrack === null || soloTrack === id;
    });
    core.visible = soloTrack === null;
  };
  const runtime = {
    metrics,
    trackGroup,
    core,
    tracks: TRACKS,
    tick: (_time: number) => undefined,
    setMonochrome(enabled: boolean) {
      TRACKS.forEach((config) => {
        const material = materials.get(config.id)!;
        const color = enabled ? WHITE : new THREE.Color(config.color);
        material.color.copy(color);
        material.emissive.copy(color).multiplyScalar(0.08);
      });
    },
    setDebugMode(mode: CompositionDebugMode) {
      debugMode = mode;
      applyVisibility();
    },
    setSoloTrack(id: string | null) {
      if (id !== null && !trackMeshes.has(id)) return false;
      soloTrack = id;
      applyVisibility();
      return true;
    },
    getMonochrome: () =>
      materials.get(TRACKS[0].id)!.color.getHex() === WHITE.getHex(),
    getDebugMode: () => debugMode,
    getSoloTrack: () => soloTrack,
    getConfigs: () => JSON.parse(JSON.stringify(TRACKS)) as TrackCurveConfig3D[],
    exportJSON: () => JSON.stringify(source, null, 2),
    dispose() {
      root.traverse((object) => {
        if (
          object instanceof THREE.Mesh ||
          object instanceof THREE.Line ||
          object instanceof THREE.LineSegments
        ) {
          object.geometry.dispose();
          const material = object.material;
          if (Array.isArray(material)) {
            material.forEach((entry) => entry.dispose());
          } else {
            material.dispose();
          }
        }
      });
    },
  };
  root.userData.compositionRuntime = runtime;
  applyVisibility();
  return root;
}

export function getPantheonDesignerCompositionRuntime(root: THREE.Group) {
  return root.userData.compositionRuntime as ReturnType<
    typeof createPantheonDesignerComposition
  >["userData"]["compositionRuntime"];
}

export { TRACKS as PANTHEON_TRACK_CURVES_3D };
