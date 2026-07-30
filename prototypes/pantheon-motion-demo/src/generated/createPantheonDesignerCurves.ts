import * as THREE from "three";
import designerData from "../data/pantheon-designer-curves.json";

export type DesignerDebugMode = "line" | "control-points" | "curvature";

export interface DesignerControlPoint2D {
  x: number;
  y: number;
}

export interface DesignerCurveConfig {
  id: string;
  label: string;
  color: string;
  controlPoints2D: DesignerControlPoint2D[];
  depthKeys: Array<{ t: number; z: number }>;
  scale: [number, number, number];
  position: [number, number, number];
  rotation: [number, number, number];
  shellTargetRadius: number;
  shellProfile: Array<{ t: number; weight: number }>;
  tubeRadius: number;
  closed: boolean;
  locked: boolean;
  seamIndex: number;
  primaryDirection: string;
}

export interface DesignerCurveMetrics {
  id: string;
  label: string;
  controlPointCount: number;
  closed: boolean;
  seamDistance: number;
  maxCurvature: number;
  minimumBendingRadius: number;
  minimumBendingRadiusRatio: number;
  selfIntersectionCount: number;
  hasSelfIntersection: boolean;
  hasSmallLoop: boolean;
  boundingBox: {
    min: [number, number];
    max: [number, number];
    width: number;
    height: number;
  };
}

const SAMPLE_COUNT = 360;
const HEAT_SAMPLE_COUNT = 90;
const WHITE = new THREE.Color("#f4f1e8");
const LOW_CURVATURE = new THREE.Color("#3d7cff");
const MID_CURVATURE = new THREE.Color("#f0cc55");
const HIGH_CURVATURE = new THREE.Color("#ff4a62");

function makeCurve(config: DesignerCurveConfig): THREE.CatmullRomCurve3 {
  const points = config.controlPoints2D.map(
    ({ x, y }) => new THREE.Vector3(x, y, 0),
  );
  return new THREE.CatmullRomCurve3(points, true, "centripetal", 0.5);
}

function sampleCurve(curve: THREE.Curve<THREE.Vector3>, count = SAMPLE_COUNT) {
  return Array.from({ length: count }, (_, index) =>
    curve.getPoint(index / count),
  );
}

function signedArea(a: THREE.Vector3, b: THREE.Vector3, c: THREE.Vector3) {
  return (
    (b.x - a.x) * (c.y - a.y) -
    (b.y - a.y) * (c.x - a.x)
  );
}

function segmentsIntersect(
  a: THREE.Vector3,
  b: THREE.Vector3,
  c: THREE.Vector3,
  d: THREE.Vector3,
) {
  const abC = signedArea(a, b, c);
  const abD = signedArea(a, b, d);
  const cdA = signedArea(c, d, a);
  const cdB = signedArea(c, d, b);
  const epsilon = 1e-7;
  return (
    abC * abD < -epsilon &&
    cdA * cdB < -epsilon
  );
}

function countSelfIntersections(points: THREE.Vector3[]) {
  let count = 0;
  const length = points.length;
  for (let first = 0; first < length; first += 1) {
    const firstNext = (first + 1) % length;
    for (let second = first + 2; second < length; second += 1) {
      const secondNext = (second + 1) % length;
      if (first === secondNext || firstNext === second) continue;
      if (
        segmentsIntersect(
          points[first],
          points[firstNext],
          points[second],
          points[secondNext],
        )
      ) {
        count += 1;
      }
    }
  }
  return count;
}

function curvatureAt(
  previous: THREE.Vector3,
  current: THREE.Vector3,
  next: THREE.Vector3,
) {
  const a = previous.distanceTo(current);
  const b = current.distanceTo(next);
  const c = next.distanceTo(previous);
  const denominator = a * b * c;
  if (denominator < 1e-9) return 0;
  const areaTwice = new THREE.Vector3()
    .subVectors(current, previous)
    .cross(new THREE.Vector3().subVectors(next, previous))
    .length();
  return (2 * areaTwice) / denominator;
}

function curveCurvatures(points: THREE.Vector3[]) {
  const sampleWindow = 5;
  return points.map((point, index) =>
    curvatureAt(
      points[
        (index - sampleWindow + points.length) % points.length
      ],
      point,
      points[(index + sampleWindow) % points.length],
    ),
  );
}

function measureCurve(config: DesignerCurveConfig): DesignerCurveMetrics {
  const curve = makeCurve(config);
  const points = sampleCurve(curve);
  const curvatures = curveCurvatures(points);
  const box = new THREE.Box3().setFromPoints(points);
  const width = box.max.x - box.min.x;
  const height = box.max.y - box.min.y;
  const baselineRadius = Math.max(width, height) * 0.5;
  const maxCurvature = Math.max(...curvatures);
  const minimumBendingRadius =
    maxCurvature > 1e-8 ? 1 / maxCurvature : Number.POSITIVE_INFINITY;
  const selfIntersectionCount = countSelfIntersections(points);
  return {
    id: config.id,
    label: config.label,
    controlPointCount: config.controlPoints2D.length,
    closed: config.closed,
    seamDistance: curve.getPoint(0).distanceTo(curve.getPoint(1)),
    maxCurvature,
    minimumBendingRadius,
    minimumBendingRadiusRatio: minimumBendingRadius / baselineRadius,
    selfIntersectionCount,
    hasSelfIntersection: selfIntersectionCount > 0,
    hasSmallLoop: selfIntersectionCount > 0,
    boundingBox: {
      min: [box.min.x, box.min.y],
      max: [box.max.x, box.max.y],
      width,
      height,
    },
  };
}

function makeCurvatureHeatmap(
  curve: THREE.Curve<THREE.Vector3>,
  maxCurvature: number,
) {
  const group = new THREE.Group();
  for (let index = 0; index < HEAT_SAMPLE_COUNT; index += 1) {
    const startT = index / HEAT_SAMPLE_COUNT;
    const endT = (index + 1) / HEAT_SAMPLE_COUNT;
    const previous = curve.getPoint(
      ((index - 3 + HEAT_SAMPLE_COUNT) % HEAT_SAMPLE_COUNT) /
        HEAT_SAMPLE_COUNT,
    );
    const start = curve.getPoint(startT);
    const end = curve.getPoint(
      ((index + 3) % HEAT_SAMPLE_COUNT) / HEAT_SAMPLE_COUNT,
    );
    const normalized = THREE.MathUtils.clamp(
      curvatureAt(previous, start, end) / Math.max(maxCurvature, 1e-8),
      0,
      1,
    );
    const color =
      normalized < 0.5
        ? LOW_CURVATURE.clone().lerp(MID_CURVATURE, normalized * 2)
        : MID_CURVATURE.clone().lerp(HIGH_CURVATURE, (normalized - 0.5) * 2);
    start.z = 0.008;
    end.z = 0.008;
    const segment = new THREE.Mesh(
      new THREE.TubeGeometry(
        new THREE.LineCurve3(start, end),
        1,
        0.007,
        6,
        false,
      ),
      new THREE.MeshBasicMaterial({ color }),
    );
    group.add(segment);
  }
  return group;
}

function makeIndexLabel(index: number) {
  const canvas = document.createElement("canvas");
  canvas.width = 64;
  canvas.height = 64;
  const context = canvas.getContext("2d");
  if (context) {
    context.fillStyle = "#07090c";
    context.beginPath();
    context.arc(32, 32, 24, 0, Math.PI * 2);
    context.fill();
    context.strokeStyle = "#ffcb64";
    context.lineWidth = 3;
    context.stroke();
    context.fillStyle = "#ffdf91";
    context.font = "600 24px monospace";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(String(index), 32, 33);
  }
  const texture = new THREE.CanvasTexture(canvas);
  const sprite = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: false,
    }),
  );
  sprite.scale.setScalar(0.12);
  sprite.userData.ownedTexture = texture;
  return sprite;
}

function makeControlPointDebug(config: DesignerCurveConfig) {
  const group = new THREE.Group();
  const points = config.controlPoints2D.map(
    ({ x, y }) => new THREE.Vector3(x, y, 0.018),
  );
  points.forEach((point, index) => {
    const marker = new THREE.Mesh(
      new THREE.CircleGeometry(0.025, 16),
      new THREE.MeshBasicMaterial({
        color: 0xffcb64,
        depthTest: false,
      }),
    );
    marker.position.copy(point);
    marker.position.z = 0.035;
    group.add(marker);
    const label = makeIndexLabel(index);
    label.position.copy(point);
    label.position.y += 0.065;
    label.position.z = 0.04;
    group.add(label);
  });

  const polygonPoints = [...points, points[0]];
  const polygon = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(polygonPoints),
    new THREE.LineDashedMaterial({
      color: 0x7891a3,
      dashSize: 0.035,
      gapSize: 0.025,
      transparent: true,
      opacity: 0.58,
    }),
  );
  polygon.computeLineDistances();
  group.add(polygon);

  const seam = new THREE.Mesh(
    new THREE.RingGeometry(0.06, 0.075, 24),
    new THREE.MeshBasicMaterial({
      color: 0xff4f78,
      side: THREE.DoubleSide,
    }),
  );
  seam.position.copy(points[config.seamIndex]);
  seam.position.z = 0.025;
  group.add(seam);
  return group;
}

export const PANTHEON_DESIGNER_CURVES =
  designerData.curves as DesignerCurveConfig[];

export function createPantheonDesignerCurves(): THREE.Group {
  const root = new THREE.Group();
  root.name = "PantheonDesignerCurvesB0";
  const curveGroups = new Map<string, THREE.Group>();
  const metrics = PANTHEON_DESIGNER_CURVES.map(measureCurve);

  PANTHEON_DESIGNER_CURVES.forEach((config, configIndex) => {
    const curve = makeCurve(config);
    const metric = metrics[configIndex];
    const group = new THREE.Group();
    group.name = `DesignerCurve_${config.id}`;

    const line = new THREE.Mesh(
      new THREE.TubeGeometry(curve, 240, config.tubeRadius, 8, true),
      new THREE.MeshBasicMaterial({ color: WHITE }),
    );
    line.name = `WhiteLine_${config.id}`;
    line.userData.designerLayer = "line";
    group.add(line);

    const controlDebug = makeControlPointDebug(config);
    controlDebug.name = `ControlPoints_${config.id}`;
    controlDebug.userData.designerLayer = "control-points";
    controlDebug.visible = false;
    group.add(controlDebug);

    const heatmap = makeCurvatureHeatmap(curve, metric.maxCurvature);
    heatmap.name = `CurvatureHeatmap_${config.id}`;
    heatmap.userData.designerLayer = "curvature";
    heatmap.visible = false;
    group.add(heatmap);

    group.visible = configIndex === 0;
    root.add(group);
    curveGroups.set(config.id, group);
  });

  let activeCurveId = PANTHEON_DESIGNER_CURVES[0].id;
  let debugMode: DesignerDebugMode = "line";

  const applyVisibility = () => {
    curveGroups.forEach((group, id) => {
      group.visible = id === activeCurveId;
      group.traverse((object) => {
        const layer = object.userData.designerLayer;
        if (!layer) return;
        object.visible =
          layer === "line"
            ? debugMode !== "curvature"
            : layer === debugMode;
      });
    });
  };

  const runtime = {
    tick: (_time: number) => undefined,
    metrics,
    getConfigs: () =>
      PANTHEON_DESIGNER_CURVES.map((config) =>
        JSON.parse(JSON.stringify(config)),
      ) as DesignerCurveConfig[],
    getActiveCurveId: () => activeCurveId,
    getDebugMode: () => debugMode,
    setSoloCurve: (id: string) => {
      if (!curveGroups.has(id)) return false;
      activeCurveId = id;
      applyVisibility();
      return true;
    },
    setDebugMode: (mode: DesignerDebugMode) => {
      debugMode = mode;
      applyVisibility();
    },
    exportJSON: () => JSON.stringify(designerData, null, 2),
    dispose: () => {
      root.traverse((object) => {
        if (
          object instanceof THREE.Mesh ||
          object instanceof THREE.Line ||
          object instanceof THREE.LineSegments ||
          object instanceof THREE.Points
        ) {
          object.geometry.dispose();
          const material = object.material;
          if (Array.isArray(material)) {
            material.forEach((entry) => entry.dispose());
          } else {
            material.dispose();
          }
        }
        if (object instanceof THREE.Sprite) object.material.dispose();
        const ownedTexture = object.userData.ownedTexture;
        if (ownedTexture instanceof THREE.Texture) ownedTexture.dispose();
      });
    },
  };
  root.userData.designerRuntime = runtime;
  applyVisibility();
  return root;
}

export function getPantheonDesignerRuntime(root: THREE.Group) {
  return root.userData.designerRuntime as ReturnType<
    typeof createPantheonDesignerCurves
  >["userData"]["designerRuntime"];
}
