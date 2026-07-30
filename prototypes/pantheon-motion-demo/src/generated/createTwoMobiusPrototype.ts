import * as THREE from "three";

import { createRoundedMobiusGeometry } from "./createSingleMobiusPrototype.ts";

type Disposable = THREE.BufferGeometry | THREE.Material;

const SECOND_LOOP_ANGLE = THREE.MathUtils.degToRad(30);

function createRibbonMaterial(color: number): THREE.MeshPhysicalMaterial {
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

export function createTwoMobiusPrototype(): THREE.Group {
  const root = new THREE.Group();
  root.name = "two-crossing-mobius-root";
  root.rotation.set(-0.08, 0.12, -0.08);

  const resources: Disposable[] = [];
  const geometry = createRoundedMobiusGeometry();
  resources.push(geometry);

  const bandPivots: Record<string, THREE.Group> = {};
  const nodes: Record<string, THREE.Object3D> = { root };
  const meshes: Record<string, THREE.Mesh> = {};
  const loopDefinitions = [
    { color: 0x4f827a, rotation: new THREE.Euler(0, 0, 0) },
    {
      color: 0xc99b4f,
      rotation: new THREE.Euler(
        SECOND_LOOP_ANGLE,
        SECOND_LOOP_ANGLE,
        SECOND_LOOP_ANGLE,
      ),
    },
  ];

  loopDefinitions.forEach((definition, index) => {
    const id = `mobius-${String(index + 1).padStart(2, "0")}`;
    const material = createRibbonMaterial(definition.color);
    const ribbon = new THREE.Mesh(geometry, material);
    ribbon.name = `${id}-ribbon`;
    ribbon.castShadow = true;
    ribbon.receiveShadow = true;

    const pivot = new THREE.Group();
    pivot.name = `${id}-pivot`;
    pivot.rotation.copy(definition.rotation);
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
  });
  const core = new THREE.Mesh(coreGeometry, coreMaterial);
  core.name = "central-orb";
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
    depthWrite: false,
    toneMapped: false,
  });
  const coreGlow = new THREE.Mesh(coreGlowGeometry, coreGlowMaterial);
  coreGlow.name = "central-orb-glow";
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
