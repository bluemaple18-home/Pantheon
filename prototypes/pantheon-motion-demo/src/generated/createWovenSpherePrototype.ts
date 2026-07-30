import * as THREE from "three";

type Disposable = THREE.BufferGeometry | THREE.Material;

export const WOVEN_SPHERE_PARAMS = {
  radius: 1,
  bandCount: 12,
  bandWidth: 0.15,
  bandThickness: 0.018,
  radialDelta: 0.028,
  weaveFrequency: 6,
  coreRadius: 0.21,
  longitudinalSegments: 256,
} as const;

export const WOVEN_BAND_COLORS = [
  0x4f827a,
  0xc99b4f,
  0x9e5960,
  0x263752,
  0x85523d,
  0x76558f,
  0xaebfc4,
] as const;

const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
const ORIGIN = new THREE.Vector3(0, 0, 0);
const Y_AXIS = new THREE.Vector3(0, 1, 0);
const X_AXIS = new THREE.Vector3(1, 0, 0);

interface PlaneBasis {
  normal: THREE.Vector3;
  u: THREE.Vector3;
  v: THREE.Vector3;
}

interface RibbonBuild {
  centerline: THREE.Vector3[];
  geometry: THREE.BufferGeometry;
  maxRadius: number;
  minRadius: number;
}

function createFibonacciNormal(index: number): THREE.Vector3 {
  const y = (index + 0.5) / WOVEN_SPHERE_PARAMS.bandCount;
  const theta = GOLDEN_ANGLE * index;
  const radial = Math.sqrt(1 - y * y);
  return new THREE.Vector3(
    radial * Math.cos(theta),
    y,
    radial * Math.sin(theta),
  ).normalize();
}

function createPlaneBasis(normal: THREE.Vector3): PlaneBasis {
  const helper = Math.abs(normal.y) < 0.9 ? Y_AXIS : X_AXIS;
  const u = new THREE.Vector3().crossVectors(helper, normal).normalize();
  const v = new THREE.Vector3().crossVectors(normal, u).normalize();
  return { normal, u, v };
}

function getCenterPoint(
  basis: PlaneBasis,
  phase: number,
  t: number,
  target = new THREE.Vector3(),
): THREE.Vector3 {
  const angle = t * Math.PI * 2;
  const radialOffset =
    WOVEN_SPHERE_PARAMS.radialDelta *
    Math.sin(WOVEN_SPHERE_PARAMS.weaveFrequency * angle + phase);
  const radius = WOVEN_SPHERE_PARAMS.radius + radialOffset;
  return target
    .copy(basis.u)
    .multiplyScalar(Math.cos(angle))
    .addScaledVector(basis.v, Math.sin(angle))
    .multiplyScalar(radius);
}

function createRibbonGeometry(
  basis: PlaneBasis,
  phase: number,
): RibbonBuild {
  const { longitudinalSegments, bandWidth, bandThickness } =
    WOVEN_SPHERE_PARAMS;
  const positions: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];
  const centerline: THREE.Vector3[] = [];
  const center = new THREE.Vector3();
  const previous = new THREE.Vector3();
  const next = new THREE.Vector3();
  const tangent = new THREE.Vector3();
  const sphericalNormal = new THREE.Vector3();
  const ribbonSide = new THREE.Vector3();
  const point = new THREE.Vector3();
  const derivativeStep = 1 / longitudinalSegments / 2;
  let minRadius = Number.POSITIVE_INFINITY;
  let maxRadius = 0;

  for (let segment = 0; segment < longitudinalSegments; segment += 1) {
    const t = segment / longitudinalSegments;
    getCenterPoint(basis, phase, t, center);
    getCenterPoint(basis, phase, t - derivativeStep, previous);
    getCenterPoint(basis, phase, t + derivativeStep, next);
    tangent.subVectors(next, previous).normalize();
    sphericalNormal.copy(center).normalize();
    ribbonSide
      .crossVectors(tangent, sphericalNormal)
      .normalize();

    const radius = center.length();
    minRadius = Math.min(minRadius, radius);
    maxRadius = Math.max(maxRadius, radius);
    centerline.push(center.clone());

    const crossSection = [
      [bandWidth / 2, bandThickness / 2],
      [-bandWidth / 2, bandThickness / 2],
      [-bandWidth / 2, -bandThickness / 2],
      [bandWidth / 2, -bandThickness / 2],
    ] as const;

    crossSection.forEach(([sideOffset, radialThickness], corner) => {
      point
        .copy(center)
        .addScaledVector(ribbonSide, sideOffset)
        .addScaledVector(sphericalNormal, radialThickness);
      positions.push(point.x, point.y, point.z);
      uvs.push(t, corner / 3);
    });
  }

  for (let segment = 0; segment < longitudinalSegments; segment += 1) {
    const nextSegment = (segment + 1) % longitudinalSegments;
    for (let edge = 0; edge < 4; edge += 1) {
      const nextEdge = (edge + 1) % 4;
      const a = segment * 4 + edge;
      const b = segment * 4 + nextEdge;
      const c = nextSegment * 4 + nextEdge;
      const d = nextSegment * 4 + edge;
      indices.push(a, b, c, a, c, d);
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(positions, 3),
  );
  geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return { centerline, geometry, minRadius, maxRadius };
}

function createFinalMaterial(color: number): THREE.MeshPhysicalMaterial {
  return new THREE.MeshPhysicalMaterial({
    color,
    metalness: 0.78,
    roughness: 0.32,
    clearcoat: 0.5,
    clearcoatRoughness: 0.18,
    envMapIntensity: 1.25,
    side: THREE.DoubleSide,
  });
}

function createDebugMaterial(color: number): THREE.MeshBasicMaterial {
  return new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity: 0.3,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
}

export function createWovenSpherePrototype(): THREE.Group {
  const root = new THREE.Group();
  root.name = "woven-sphere-root";

  const resources: Disposable[] = [];
  const nodes: Record<string, THREE.Object3D> = { root };
  const meshes: Record<string, THREE.Mesh> = {};
  const bandPivots: Record<string, THREE.Group> = {};
  const bandMeshes: THREE.Mesh[] = [];
  const finalMaterials: THREE.Material[] = [];
  const debugMaterials: THREE.Material[] = [];
  const guideGroup = new THREE.Group();
  guideGroup.name = "woven-debug-guides";
  root.add(guideGroup);
  nodes[guideGroup.name] = guideGroup;

  const referenceGeometry = new THREE.SphereGeometry(
    WOVEN_SPHERE_PARAMS.radius,
    48,
    32,
  );
  const referenceMaterial = new THREE.MeshBasicMaterial({
    color: 0x6f918b,
    wireframe: true,
    transparent: true,
    opacity: 0.12,
    depthWrite: false,
  });
  const referenceSphere = new THREE.Mesh(
    referenceGeometry,
    referenceMaterial,
  );
  referenceSphere.name = "woven-reference-sphere";
  guideGroup.add(referenceSphere);
  nodes[referenceSphere.name] = referenceSphere;
  meshes.referenceSphere = referenceSphere;
  resources.push(referenceGeometry, referenceMaterial);

  const bandMetrics: Array<{
    maxRadius: number;
    minRadius: number;
    normal: [number, number, number];
    phase: number;
  }> = [];
  const shellBounds = new THREE.Box3();

  for (let index = 0; index < WOVEN_SPHERE_PARAMS.bandCount; index += 1) {
    const id = `band-${String(index + 1).padStart(2, "0")}`;
    const color =
      WOVEN_BAND_COLORS[index % WOVEN_BAND_COLORS.length];
    const phase =
      (Math.PI * 2 * index) / WOVEN_SPHERE_PARAMS.bandCount;
    const normal = createFibonacciNormal(index);
    const basis = createPlaneBasis(normal);
    const ribbonBuild = createRibbonGeometry(basis, phase);
    const finalMaterial = createFinalMaterial(color);
    const debugMaterial = createDebugMaterial(color);
    const ribbon = new THREE.Mesh(
      ribbonBuild.geometry,
      debugMaterial,
    );
    ribbon.name = `${id}-ribbon`;
    ribbon.castShadow = false;
    ribbon.receiveShadow = false;
    ribbon.renderOrder = index;
    const pivot = new THREE.Group();
    pivot.name = `${id}-pivot`;
    pivot.add(ribbon);
    root.add(pivot);

    const centerlineGeometry = new THREE.BufferGeometry().setFromPoints(
      ribbonBuild.centerline,
    );
    const centerlineMaterial = new THREE.LineBasicMaterial({
      color,
      transparent: true,
      opacity: 0.92,
      depthTest: false,
    });
    const centerline = new THREE.LineLoop(
      centerlineGeometry,
      centerlineMaterial,
    );
    centerline.name = `${id}-centerline`;
    centerline.renderOrder = 200 + index;
    guideGroup.add(centerline);

    const normalArrow = new THREE.ArrowHelper(
      normal,
      ORIGIN,
      1.24,
      color,
      0.07,
      0.035,
    );
    normalArrow.name = `${id}-normal`;
    guideGroup.add(normalArrow);

    bandPivots[id] = pivot;
    bandMeshes.push(ribbon);
    finalMaterials.push(finalMaterial);
    debugMaterials.push(debugMaterial);
    nodes[pivot.name] = pivot;
    nodes[ribbon.name] = ribbon;
    nodes[centerline.name] = centerline;
    meshes[ribbon.name] = ribbon;
    resources.push(
      ribbonBuild.geometry,
      finalMaterial,
      debugMaterial,
      centerlineGeometry,
      centerlineMaterial,
    );
    ribbonBuild.centerline.forEach((centerPoint) =>
      shellBounds.expandByPoint(centerPoint),
    );
    bandMetrics.push({
      maxRadius: ribbonBuild.maxRadius,
      minRadius: ribbonBuild.minRadius,
      normal: [normal.x, normal.y, normal.z],
      phase,
    });
  }

  const coreGeometry = new THREE.SphereGeometry(
    WOVEN_SPHERE_PARAMS.coreRadius,
    64,
    48,
  );
  const coreMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xd3a04b,
    emissive: 0x4f2b0c,
    emissiveIntensity: 0.12,
    metalness: 1,
    roughness: 0.18,
    clearcoat: 0.7,
    clearcoatRoughness: 0.1,
    envMapIntensity: 1.55,
  });
  const core = new THREE.Mesh(coreGeometry, coreMaterial);
  core.name = "woven-core";
  core.visible = false;
  root.add(core);
  nodes.core = core;
  meshes.core = core;
  resources.push(coreGeometry, coreMaterial);

  const setDebugMode = (enabled: boolean) => {
    guideGroup.visible = enabled;
    bandMeshes.forEach((mesh, index) => {
      mesh.material = enabled
        ? debugMaterials[index]
        : finalMaterials[index];
      mesh.castShadow = !enabled;
      mesh.receiveShadow = !enabled;
    });
  };

  root.userData.sculptRuntime = {
    nodes,
    meshes,
    sockets: {},
    bandPivots,
    metrics: {
      bandMetrics,
      shellBounds: {
        min: shellBounds.min.toArray(),
        max: shellBounds.max.toArray(),
      },
    },
    params: WOVEN_SPHERE_PARAMS,
    setDebugMode,
    tick: () => undefined,
    dispose: () => {
      guideGroup.traverse((object) => {
        if (object instanceof THREE.ArrowHelper) {
          object.line.geometry.dispose();
          if (Array.isArray(object.line.material)) {
            object.line.material.forEach((material) => material.dispose());
          } else {
            object.line.material.dispose();
          }
          object.cone.geometry.dispose();
          if (Array.isArray(object.cone.material)) {
            object.cone.material.forEach((material) => material.dispose());
          } else {
            object.cone.material.dispose();
          }
        }
      });
      resources.forEach((resource) => resource.dispose());
    },
  };
  root.userData.tick = () => undefined;
  setDebugMode(true);
  return root;
}
