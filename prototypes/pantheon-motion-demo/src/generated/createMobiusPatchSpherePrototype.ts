import * as THREE from "three";

type Disposable = THREE.BufferGeometry | THREE.Material;

type BandDefinition = {
  color: number;
  normal: readonly [number, number, number];
  phase: number;
  radiusOffset: number;
  roll: number;
};

const COLORS = {
  gold: 0xc99b4f,
  teal: 0x3f746e,
  rose: 0x9e5960,
  navy: 0x263752,
  bronze: 0x85523d,
} as const;

const SHELL_RADIUS = 1.52;
const BAND_HALF_WIDTH = 0.135;
const BAND_HALF_THICKNESS = 0.022;
const PATH_WAVE = 0.12;
const WEAVE_DEPTH = 0.012;
const LONGITUDINAL_SEGMENTS = 192;
const CROSS_SECTION_SEGMENTS = 12;
const FIVEFOLD_TILT = THREE.MathUtils.degToRad(62);
const FIVEFOLD_STEP = (Math.PI * 2) / 5;

/*
 * 五條封閉大環採正五角對稱：法向量在同一圓錐上每 72° 等距分布。
 * 每色只保留一條主緞帶，並錯開球殼半徑，避免無規則穿模。
 */
const BAND_DEFINITIONS: readonly BandDefinition[] = [
  COLORS.gold,
  COLORS.teal,
  COLORS.rose,
  COLORS.navy,
  COLORS.bronze,
].map((color, index) => {
  const azimuth = index * FIVEFOLD_STEP - Math.PI / 2;
  return {
    color,
    normal: [
      Math.sin(FIVEFOLD_TILT) * Math.cos(azimuth),
      Math.cos(FIVEFOLD_TILT),
      Math.sin(FIVEFOLD_TILT) * Math.sin(azimuth),
    ] as const,
    phase: index * FIVEFOLD_STEP,
    radiusOffset: (index - 2) * 0.052,
    roll: index * FIVEFOLD_STEP * 0.5,
  };
});

function createTangentBasis(
  normal: THREE.Vector3,
  roll: number,
): [THREE.Vector3, THREE.Vector3] {
  const reference =
    Math.abs(normal.y) > 0.92
      ? new THREE.Vector3(1, 0, 0)
      : new THREE.Vector3(0, 1, 0);
  const tangentU = new THREE.Vector3()
    .crossVectors(reference, normal)
    .normalize();
  const tangentV = new THREE.Vector3()
    .crossVectors(normal, tangentU)
    .normalize();
  const cosine = Math.cos(roll);
  const sine = Math.sin(roll);
  return [
    tangentU
      .clone()
      .multiplyScalar(cosine)
      .addScaledVector(tangentV, sine),
    tangentU
      .clone()
      .multiplyScalar(-sine)
      .addScaledVector(tangentV, cosine),
  ];
}

function createBandCenters(
  definition: BandDefinition,
): THREE.Vector3[] {
  const normal = new THREE.Vector3(...definition.normal).normalize();
  const [tangentU, tangentV] = createTangentBasis(
    normal,
    definition.roll,
  );
  const centers: THREE.Vector3[] = [];

  for (let segment = 0; segment < LONGITUDINAL_SEGMENTS; segment += 1) {
    const angle = (segment / LONGITUDINAL_SEGMENTS) * Math.PI * 2;
    const direction = tangentU
      .clone()
      .multiplyScalar(Math.cos(angle))
      .addScaledVector(tangentV, Math.sin(angle))
      .addScaledVector(
        normal,
        Math.sin(angle * 2 + definition.phase) * PATH_WAVE,
      )
      .normalize();
    const radius =
      SHELL_RADIUS +
      definition.radiusOffset +
      Math.sin(angle * 4 + definition.phase) * WEAVE_DEPTH;
    centers.push(direction.multiplyScalar(radius));
  }

  return centers;
}

function createMobiusBandGeometry(
  definition: BandDefinition,
): THREE.BufferGeometry {
  const centers = createBandCenters(definition);
  const positions: number[] = [];
  const uvs: number[] = [];

  for (let segment = 0; segment < LONGITUDINAL_SEGMENTS; segment += 1) {
    const previous =
      centers[
        (segment - 1 + LONGITUDINAL_SEGMENTS) %
          LONGITUDINAL_SEGMENTS
      ];
    const center = centers[segment];
    const next = centers[(segment + 1) % LONGITUDINAL_SEGMENTS];
    const tangent = next.clone().sub(previous).normalize();
    const radial = center.clone().normalize();
    const surfaceWidth = new THREE.Vector3()
      .crossVectors(radial, tangent)
      .normalize();
    const angle = (segment / LONGITUDINAL_SEGMENTS) * Math.PI * 2;
    const twist =
      Math.sin(angle * 2 + definition.phase) * 0.1 +
      Math.sin(angle * 5 - definition.phase) * 0.025;
    const widthDirection = surfaceWidth
      .clone()
      .multiplyScalar(Math.cos(twist))
      .addScaledVector(radial, Math.sin(twist))
      .normalize();
    const depthDirection = new THREE.Vector3()
      .crossVectors(tangent, widthDirection)
      .normalize();

    for (
      let section = 0;
      section < CROSS_SECTION_SEGMENTS;
      section += 1
    ) {
      const sectionAngle =
        (section / CROSS_SECTION_SEGMENTS) * Math.PI * 2;
      const cosine = Math.cos(sectionAngle);
      const sine = Math.sin(sectionAngle);
      const roundedRectanglePower = 0.18;
      const across =
        Math.sign(cosine) *
        Math.pow(Math.abs(cosine), roundedRectanglePower) *
        BAND_HALF_WIDTH;
      const depth =
        Math.sign(sine) *
        Math.pow(Math.abs(sine), roundedRectanglePower) *
        BAND_HALF_THICKNESS;
      const point = center
        .clone()
        .addScaledVector(widthDirection, across)
        .addScaledVector(depthDirection, depth);
      positions.push(point.x, point.y, point.z);
      uvs.push(
        segment / LONGITUDINAL_SEGMENTS,
        section / CROSS_SECTION_SEGMENTS,
      );
    }
  }

  const indices: number[] = [];
  for (let segment = 0; segment < LONGITUDINAL_SEGMENTS; segment += 1) {
    const nextSegment = (segment + 1) % LONGITUDINAL_SEGMENTS;
    for (
      let section = 0;
      section < CROSS_SECTION_SEGMENTS;
      section += 1
    ) {
      const nextSection = (section + 1) % CROSS_SECTION_SEGMENTS;
      const a = segment * CROSS_SECTION_SEGMENTS + section;
      const b = nextSegment * CROSS_SECTION_SEGMENTS + section;
      const c = nextSegment * CROSS_SECTION_SEGMENTS + nextSection;
      const d = segment * CROSS_SECTION_SEGMENTS + nextSection;
      indices.push(a, b, d, b, c, d);
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
  return geometry;
}

function createBandMaterial(color: number): THREE.MeshPhysicalMaterial {
  return new THREE.MeshPhysicalMaterial({
    color,
    metalness: 0.82,
    roughness: 0.3,
    clearcoat: 0.42,
    clearcoatRoughness: 0.2,
    envMapIntensity: 1.35,
    side: THREE.DoubleSide,
  });
}

export function createMobiusPatchSpherePrototype(): THREE.Group {
  const root = new THREE.Group();
  root.name = "mobius-patch-sphere-root";
  root.rotation.set(-0.08, 0.15, -0.08);
  const outerGroup = new THREE.Group();
  outerGroup.name = "fivefold-ribbon-shell";
  root.add(outerGroup);

  const resources: Disposable[] = [];
  const nodes: Record<string, THREE.Object3D> = { root, outerGroup };
  const meshes: Record<string, THREE.Mesh> = {};
  const bandPivots: Record<string, THREE.Group> = {};

  BAND_DEFINITIONS.forEach((definition, index) => {
    const geometry = createMobiusBandGeometry(definition);
    const material = createBandMaterial(definition.color);
    const mesh = new THREE.Mesh(geometry, material);
    const id = `band-${String(index).padStart(2, "0")}`;
    mesh.name = `${id}-ribbon`;
    mesh.castShadow = true;
    mesh.receiveShadow = true;

    const pivot = new THREE.Group();
    pivot.name = `${id}-pivot`;
    pivot.add(mesh);
    outerGroup.add(pivot);

    nodes[pivot.name] = pivot;
    nodes[mesh.name] = mesh;
    meshes[mesh.name] = mesh;
    bandPivots[id] = pivot;
    resources.push(geometry, material);
  });

  const coreGeometry = new THREE.SphereGeometry(0.3, 72, 48);
  const coreMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xd3a04b,
    emissive: 0x4f2b0c,
    emissiveIntensity: 0.12,
    metalness: 1,
    roughness: 0.18,
    clearcoat: 0.78,
    clearcoatRoughness: 0.1,
    envMapIntensity: 1.6,
  });
  const core = new THREE.Mesh(coreGeometry, coreMaterial);
  core.name = "central-orb";
  core.castShadow = true;
  core.receiveShadow = true;
  root.add(core);
  nodes.core = core;
  meshes.core = core;
  resources.push(coreGeometry, coreMaterial);

  const baseOrientation = new THREE.Quaternion().setFromEuler(
    new THREE.Euler(-0.18, 0.32, 0.12),
  );
  const spinAxis = new THREE.Vector3(0.36, 1, 0.24).normalize();
  const precessionAxis = new THREE.Vector3(1, 0.16, 0.34).normalize();
  const spinRotation = new THREE.Quaternion();
  const precessionRotation = new THREE.Quaternion();
  const tick = (time: number) => {
    spinRotation.setFromAxisAngle(spinAxis, time * 0.24);
    precessionRotation.setFromAxisAngle(
      precessionAxis,
      Math.sin(time * 0.17) * 0.34,
    );
    outerGroup.quaternion
      .copy(precessionRotation)
      .multiply(spinRotation)
      .multiply(baseOrientation);
  };
  tick(0);

  root.userData.sculptRuntime = {
    nodes,
    meshes,
    sockets: {},
    bandPivots,
    tick,
    dispose: () => resources.forEach((resource) => resource.dispose()),
  };
  root.userData.tick = tick;
  return root;
}
