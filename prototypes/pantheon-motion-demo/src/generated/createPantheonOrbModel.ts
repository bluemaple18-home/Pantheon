import * as THREE from "three";

export const PANTHEON_LOOP_SECONDS = 24;

export type PantheonOrbRuntime = {
  nodes: Record<string, THREE.Object3D>;
  meshes: Record<string, THREE.Mesh>;
  sockets: Record<string, THREE.Object3D>;
  bandPivots: Record<string, THREE.Group>;
  tick: (elapsedSeconds: number) => void;
  dispose: () => void;
};

type BandDefinition = {
  id: string;
  color: number;
  radius: number;
  normal: [number, number, number];
  phase: number;
};

const BAND_HALF_WIDTH = 0.135;
const BAND_HALF_THICKNESS = 0.022;

const BAND_DEFINITIONS: BandDefinition[] = [
  { id: "gold", color: 0xc99b4f, radius: 1.58, normal: [0.76, 0.28, 0.32], phase: 0 },
  { id: "teal", color: 0x497f77, radius: 1.56, normal: [-0.70, 0.20, 0.50], phase: 0.2 },
  { id: "rose", color: 0x9e5960, radius: 1.54, normal: [0.72, 0.40, 0.42], phase: 0.4 },
  { id: "navy", color: 0x263752, radius: 1.52, normal: [-0.30, -0.76, 0.30], phase: 0.6 },
  { id: "bronze", color: 0x8b6249, radius: 1.50, normal: [0.87, 0.03, 0.36], phase: 0.8 },
];

function createSphericalBandGeometry(radius: number): THREE.BufferGeometry {
  const segmentsU = 192;
  const segmentsV = 12;
  const positions: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];

  for (const surfaceRadius of [
    radius + BAND_HALF_THICKNESS,
    radius - BAND_HALF_THICKNESS,
  ]) {
    for (let uIndex = 0; uIndex <= segmentsU; uIndex += 1) {
      const u = (uIndex / segmentsU) * Math.PI * 2;
      for (let vIndex = 0; vIndex <= segmentsV; vIndex += 1) {
        const v =
          -BAND_HALF_WIDTH +
          (vIndex / segmentsV) * BAND_HALF_WIDTH * 2;
        positions.push(
          surfaceRadius * Math.cos(v) * Math.cos(u),
          surfaceRadius * Math.cos(v) * Math.sin(u),
          surfaceRadius * Math.sin(v),
        );
        uvs.push(uIndex / segmentsU, vIndex / segmentsV);
      }
    }
  }

  const row = segmentsV + 1;
  const surfaceSize = (segmentsU + 1) * row;
  for (let surface = 0; surface < 2; surface += 1) {
    const offset = surface * surfaceSize;
    for (let uIndex = 0; uIndex < segmentsU; uIndex += 1) {
      for (let vIndex = 0; vIndex < segmentsV; vIndex += 1) {
        const a = offset + uIndex * row + vIndex;
        const b = a + row;
        const c = b + 1;
        const d = a + 1;
        if (surface === 0) indices.push(a, b, d, b, c, d);
        else indices.push(a, d, b, b, d, c);
      }
    }
  }

  for (const edgeIndex of [0, segmentsV]) {
    for (let uIndex = 0; uIndex < segmentsU; uIndex += 1) {
      const outerA = uIndex * row + edgeIndex;
      const outerB = outerA + row;
      const innerA = surfaceSize + outerA;
      const innerB = surfaceSize + outerB;
      if (edgeIndex === 0) {
        indices.push(outerA, innerA, outerB, outerB, innerA, innerB);
      } else {
        indices.push(outerA, outerB, innerA, outerB, innerB, innerA);
      }
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function createBand(definition: BandDefinition): {
  pivot: THREE.Group;
  mesh: THREE.Mesh;
  resources: Array<THREE.BufferGeometry | THREE.Material>;
} {
  const pivot = new THREE.Group();
  pivot.name = `${definition.id}-pivot`;
  pivot.quaternion.setFromUnitVectors(
    new THREE.Vector3(0, 0, 1),
    new THREE.Vector3(...definition.normal).normalize(),
  );

  const geometry = createSphericalBandGeometry(definition.radius);
  const material = new THREE.MeshPhysicalMaterial({
    color: definition.color,
    metalness: 0.35,
    roughness: 0.48,
    clearcoat: 0.18,
    clearcoatRoughness: 0.35,
    envMapIntensity: 0.9,
    side: THREE.DoubleSide,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = `${definition.id}-shell`;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  pivot.add(mesh);

  const socket = new THREE.Object3D();
  socket.name = `${definition.id}-center`;
  pivot.add(socket);

  return {
    pivot,
    mesh,
    resources: [geometry, material],
  };
}

export function createPantheonOrbModel(): THREE.Group {
  const root = new THREE.Group();
  root.name = "pantheon-orb-root";

  const nodes: Record<string, THREE.Object3D> = { root };
  const meshes: Record<string, THREE.Mesh> = {};
  const sockets: Record<string, THREE.Object3D> = {};
  const bandPivots: Record<string, THREE.Group> = {};
  const resources: Array<THREE.BufferGeometry | THREE.Material> = [];
  const baseRotations = new Map<string, THREE.Euler>();

  const coreGeometry = new THREE.SphereGeometry(0.32, 96, 64);
  const coreMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xd9a54c,
    emissive: 0x5b310c,
    emissiveIntensity: 0.22,
    metalness: 1,
    roughness: 0.18,
    clearcoat: 0.72,
    clearcoatRoughness: 0.12,
    envMapIntensity: 1.6,
  });
  const core = new THREE.Mesh(coreGeometry, coreMaterial);
  core.name = "core";
  core.castShadow = true;
  root.add(core);
  nodes.core = core;
  meshes.core = core;
  resources.push(coreGeometry, coreMaterial);

  const glowGeometry = new THREE.SphereGeometry(0.4, 64, 40);
  const glowMaterial = new THREE.MeshBasicMaterial({
    color: 0xe1aa55,
    transparent: true,
    opacity: 0.075,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    toneMapped: false,
  });
  const glow = new THREE.Mesh(glowGeometry, glowMaterial);
  glow.name = "core-glow";
  root.add(glow);
  nodes["core-glow"] = glow;
  meshes["core-glow"] = glow;
  resources.push(glowGeometry, glowMaterial);

  for (const definition of BAND_DEFINITIONS) {
    const band = createBand(definition);
    root.add(band.pivot);
    nodes[band.pivot.name] = band.pivot;
    nodes[band.mesh.name] = band.mesh;
    meshes[band.mesh.name] = band.mesh;
    bandPivots[definition.id] = band.pivot;
    const socket = band.pivot.getObjectByName(`${definition.id}-center`);
    if (socket) sockets[socket.name] = socket;
    baseRotations.set(definition.id, band.pivot.rotation.clone());
    resources.push(...band.resources);
  }

  const tick = (elapsedSeconds: number) => {
    root.rotation.set(-0.055, 0, 0);

    BAND_DEFINITIONS.forEach((definition) => {
      const pivot = bandPivots[definition.id];
      const base = baseRotations.get(definition.id);
      if (!pivot || !base) return;
      pivot.rotation.copy(base);
    });

    core.scale.setScalar(1);
    glow.scale.setScalar(1);
    glowMaterial.opacity = 0.055;
  };

  const dispose = () => {
    resources.forEach((resource) => resource.dispose());
  };

  const runtime: PantheonOrbRuntime = {
    nodes,
    meshes,
    sockets,
    bandPivots,
    tick,
    dispose,
  };
  root.userData.sculptRuntime = runtime;
  root.userData.tick = tick;
  tick(0);
  return root;
}

export function getPantheonOrbRuntime(root: THREE.Group): PantheonOrbRuntime {
  return root.userData.sculptRuntime as PantheonOrbRuntime;
}
