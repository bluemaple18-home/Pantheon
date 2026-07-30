import * as THREE from "three";

import { createRoundedMobiusGeometry } from "./createSingleMobiusPrototype.ts";

type Disposable = THREE.BufferGeometry | THREE.Material;

export const RING_COLORS = [
  0x4f827a,
  0xc99b4f,
  0x9e5960,
  0x263752,
  0x85523d,
  0x76558f,
  0xaebfc4,
] as const;

export const MOBIUS_COUNT = 12;
export const MOBIUS_COLORS = Array.from(
  { length: MOBIUS_COUNT },
  (_, index) => RING_COLORS[index % RING_COLORS.length],
);

const WORLD_UP = new THREE.Vector3(0, 1, 0);
const LAYER_SPECS = [
  { azimuth: 0, tilt: 0 },
  { azimuth: 45, tilt: 0 },
  { azimuth: 90, tilt: 0 },
  { azimuth: 135, tilt: 0 },
  { azimuth: 22.5, tilt: 54.7 },
  { azimuth: 67.5, tilt: 54.7 },
  { azimuth: 112.5, tilt: 54.7 },
  { azimuth: 157.5, tilt: 54.7 },
  { azimuth: 0, tilt: -54.7 },
  { azimuth: 45, tilt: -54.7 },
  { azimuth: 90, tilt: -54.7 },
  { azimuth: 135, tilt: -54.7 },
] as const;

function createPlaneQuaternion(
  azimuthDegrees: number,
  tiltDegrees: number,
): THREE.Quaternion {
  const azimuth = THREE.MathUtils.degToRad(azimuthDegrees);
  const tilt = THREE.MathUtils.degToRad(tiltDegrees);
  const normal = new THREE.Vector3(
    Math.sin(azimuth) * Math.cos(tilt),
    Math.sin(tilt),
    Math.cos(azimuth) * Math.cos(tilt),
  ).normalize();
  const vertical = WORLD_UP.clone()
    .addScaledVector(normal, -WORLD_UP.dot(normal))
    .normalize();
  const horizontal = new THREE.Vector3()
    .crossVectors(vertical, normal)
    .normalize();
  const frame = new THREE.Matrix4().makeBasis(
    horizontal,
    vertical,
    normal,
  );
  return new THREE.Quaternion().setFromRotationMatrix(frame).normalize();
}

export const LAYERED_QUATERNIONS = LAYER_SPECS.map(({ azimuth, tilt }) =>
  createPlaneQuaternion(azimuth, tilt),
);

export const SPHERICAL_ROTATIONS = LAYERED_QUATERNIONS.map((quaternion) => {
  const rotation = new THREE.Euler().setFromQuaternion(quaternion, "XYZ");
  return { x: rotation.x, y: rotation.y, z: rotation.z };
});

function createRibbonMaterial(color: number): THREE.MeshPhysicalMaterial {
  return new THREE.MeshPhysicalMaterial({
    color,
    metalness: 0.82,
    roughness: 0.3,
    clearcoat: 0.42,
    clearcoatRoughness: 0.2,
    envMapIntensity: 1.35,
    opacity: 0.72,
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
}

export function createControlledTwelveMobiusPrototype(): THREE.Group {
  const root = new THREE.Group();
  root.name = "controlled-twelve-layered-mobius-root";
  root.rotation.set(0, 0, 0);

  const resources: Disposable[] = [];
  const geometry = createRoundedMobiusGeometry();
  resources.push(geometry);

  const bandPivots: Record<string, THREE.Group> = {};
  const nodes: Record<string, THREE.Object3D> = { root };
  const meshes: Record<string, THREE.Mesh> = {};

  MOBIUS_COLORS.forEach((color, index) => {
    const id = `mobius-${String(index + 1).padStart(2, "0")}`;
    const material = createRibbonMaterial(color);
    const ribbon = new THREE.Mesh(geometry, material);
    ribbon.name = `${id}-ribbon`;
    ribbon.castShadow = false;
    ribbon.receiveShadow = false;

    const pivot = new THREE.Group();
    pivot.name = `${id}-pivot`;
    pivot.quaternion.copy(LAYERED_QUATERNIONS[index]);
    pivot.add(ribbon);
    root.add(pivot);

    nodes[pivot.name] = pivot;
    nodes[ribbon.name] = ribbon;
    meshes[ribbon.name] = ribbon;
    bandPivots[id] = pivot;
    resources.push(material);
  });

  const coreGeometry = new THREE.SphereGeometry(0.34, 96, 64);
  const coreMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xd3a04b,
    emissive: 0x4f2b0c,
    emissiveIntensity: 0.16,
    metalness: 1,
    roughness: 0.18,
    clearcoat: 0.72,
    clearcoatRoughness: 0.1,
    envMapIntensity: 1.55,
    depthTest: false,
  });
  const core = new THREE.Mesh(coreGeometry, coreMaterial);
  core.name = "central-orb";
  core.visible = false;
  core.renderOrder = 100;
  core.castShadow = true;
  root.add(core);
  nodes.core = core;
  meshes.core = core;
  resources.push(coreGeometry, coreMaterial);

  const coreGlowGeometry = new THREE.SphereGeometry(0.43, 64, 40);
  const coreGlowMaterial = new THREE.MeshBasicMaterial({
    color: 0xe2ad57,
    transparent: true,
    opacity: 0.07,
    blending: THREE.AdditiveBlending,
    depthTest: false,
    depthWrite: false,
    toneMapped: false,
  });
  const coreGlow = new THREE.Mesh(coreGlowGeometry, coreGlowMaterial);
  coreGlow.name = "central-orb-glow";
  coreGlow.visible = false;
  coreGlow.renderOrder = 99;
  root.add(coreGlow);
  nodes.coreGlow = coreGlow;
  meshes.coreGlow = coreGlow;
  resources.push(coreGlowGeometry, coreGlowMaterial);

  root.userData.sculptRuntime = {
    nodes,
    meshes,
    sockets: {},
    bandPivots,
    tick: () => undefined,
    dispose: () => resources.forEach((resource) => resource.dispose()),
  };
  root.userData.tick = () => undefined;
  return root;
}
