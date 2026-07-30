import * as THREE from "three";
import { createRoundedMobiusGeometry } from "./createSingleMobiusPrototype.ts";

type Disposable = THREE.BufferGeometry | THREE.Material;

type RibbonDefinition = {
  id: string;
  color: number;
  azimuth: number;
};

const COMMON_TILT = 0.08;

const RIBBONS: RibbonDefinition[] = [
  {
    id: "gold",
    color: 0xc99b4f,
    azimuth: 0,
  },
  {
    id: "teal",
    color: 0x497f77,
    azimuth: (Math.PI * 2) / 5,
  },
  {
    id: "rose",
    color: 0x9e5960,
    azimuth: (Math.PI * 4) / 5,
  },
  {
    id: "navy",
    color: 0x263752,
    azimuth: (Math.PI * 6) / 5,
  },
  {
    id: "bronze",
    color: 0x8b6249,
    azimuth: (Math.PI * 8) / 5,
  },
];

function createFadingRibbonMaterial(color: number): THREE.MeshPhysicalMaterial {
  const material = new THREE.MeshPhysicalMaterial({
    color,
    metalness: 0.84,
    roughness: 0.3,
    clearcoat: 0.4,
    clearcoatRoughness: 0.2,
    envMapIntensity: 1.3,
    side: THREE.DoubleSide,
    transparent: true,
    depthWrite: true,
  });

  material.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace(
        "void main() {",
        "varying vec3 vMobiusLocalPosition;\nvoid main() {",
      )
      .replace(
        "#include <begin_vertex>",
        [
          "#include <begin_vertex>",
          "vMobiusLocalPosition = position;",
        ].join("\n"),
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "void main() {",
        "varying vec3 vMobiusLocalPosition;\nvoid main() {",
      )
      .replace(
        "#include <output_fragment>",
        [
          "float coreDistance = length(vMobiusLocalPosition);",
          "diffuseColor.a *= smoothstep(0.38, 0.58, coreDistance);",
          "if (diffuseColor.a < 0.025) discard;",
          "#include <output_fragment>",
        ].join("\n"),
      );
  };
  material.customProgramCacheKey = () => "mobius-core-distance-fade-v1";
  return material;
}

export function createFiveMobiusSpherePrototype(): THREE.Group {
  const root = new THREE.Group();
  root.name = "five-crossing-mobius-sphere-root";

  const resources: Disposable[] = [];
  const geometry = createRoundedMobiusGeometry();
  resources.push(geometry);

  const nodes: Record<string, THREE.Object3D> = { root };
  const meshes: Record<string, THREE.Mesh> = {};
  const bandPivots: Record<string, THREE.Group> = {};

  RIBBONS.forEach((definition, index) => {
    const pivot = new THREE.Group();
    pivot.name = `${definition.id}-mobius-pivot`;
    const spinAroundCenter = new THREE.Quaternion().setFromEuler(
      new THREE.Euler(0, 0, definition.azimuth),
    );
    const sharedTilt = new THREE.Quaternion().setFromEuler(
      new THREE.Euler(COMMON_TILT, 0.12, 0),
    );
    pivot.quaternion.copy(spinAroundCenter.multiply(sharedTilt));

    const material = createFadingRibbonMaterial(definition.color);
    const ribbon = new THREE.Mesh(geometry, material);
    ribbon.name = `${definition.id}-mobius-ribbon`;
    ribbon.castShadow = true;
    ribbon.receiveShadow = true;
    ribbon.renderOrder = index;
    pivot.add(ribbon);
    root.add(pivot);

    nodes[pivot.name] = pivot;
    nodes[ribbon.name] = ribbon;
    meshes[ribbon.name] = ribbon;
    bandPivots[definition.id] = pivot;
    resources.push(material);
  });

  const coreGeometry = new THREE.SphereGeometry(0.38, 96, 64);
  const coreMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xd3a04b,
    emissive: 0x4f2b0c,
    emissiveIntensity: 0.16,
    metalness: 1,
    roughness: 0.18,
    clearcoat: 0.74,
    clearcoatRoughness: 0.1,
    envMapIntensity: 1.55,
    depthTest: false,
    transparent: true,
  });
  const core = new THREE.Mesh(coreGeometry, coreMaterial);
  core.name = "central-orb";
  core.castShadow = true;
  core.renderOrder = 100;
  root.add(core);
  nodes.core = core;
  meshes.core = core;
  resources.push(coreGeometry, coreMaterial);

  const glowGeometry = new THREE.SphereGeometry(0.5, 64, 40);
  const glowMaterial = new THREE.MeshBasicMaterial({
    color: 0xe2ad57,
    transparent: true,
    opacity: 0.065,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    toneMapped: false,
  });
  const glow = new THREE.Mesh(glowGeometry, glowMaterial);
  glow.name = "central-orb-glow";
  root.add(glow);
  nodes.glow = glow;
  meshes.glow = glow;
  resources.push(glowGeometry, glowMaterial);

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
