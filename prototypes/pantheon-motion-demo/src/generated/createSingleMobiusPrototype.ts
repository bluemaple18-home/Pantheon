import * as THREE from "three";

type Disposable = THREE.BufferGeometry | THREE.Material;

class CrossingLoopCurve extends THREE.Curve<THREE.Vector3> {
  constructor() {
    super();
  }

  override getPoint(t: number, target = new THREE.Vector3()): THREE.Vector3 {
    const angle = t * Math.PI * 2;
    return target.set(
      Math.sin(angle) * 1.47,
      Math.sin(angle * 2) * 1.05,
      0,
    );
  }
}

export function createRoundedMobiusGeometry(): THREE.BufferGeometry {
  const curve = new CrossingLoopCurve();
  const longitudinalSegments = 192;
  const crossSectionSegments = 16;
  const halfWidth = 0.055;
  const halfThickness = 0.015;
  const frames = curve.computeFrenetFrames(longitudinalSegments, true);
  const positions: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];

  for (let segment = 0; segment < longitudinalSegments; segment += 1) {
    const t = segment / longitudinalSegments;
    const center = curve.getPointAt(t);
    const twist = t * Math.PI + Math.PI / 4;
    const normal = frames.normals[segment];
    const binormal = frames.binormals[segment];
    const widthDirection = normal
      .clone()
      .multiplyScalar(Math.cos(twist))
      .addScaledVector(binormal, Math.sin(twist))
      .normalize();
    const thicknessDirection = normal
      .clone()
      .multiplyScalar(-Math.sin(twist))
      .addScaledVector(binormal, Math.cos(twist))
      .normalize();

    for (
      let section = 0;
      section < crossSectionSegments;
      section += 1
    ) {
      const sectionAngle =
        (section / crossSectionSegments) * Math.PI * 2;
      const cosine = Math.cos(sectionAngle);
      const sine = Math.sin(sectionAngle);
      const roundedRectanglePower = 0.16;
      const across =
        Math.sign(cosine) *
        Math.pow(Math.abs(cosine), roundedRectanglePower) *
        halfWidth;
      const depth =
        Math.sign(sine) *
        Math.pow(Math.abs(sine), roundedRectanglePower) *
        halfThickness;
      const point = center
        .clone()
        .addScaledVector(widthDirection, across)
        .addScaledVector(thicknessDirection, depth);

      positions.push(point.x, point.y, point.z);
      uvs.push(t, section / crossSectionSegments);
    }
  }

  for (let segment = 0; segment < longitudinalSegments; segment += 1) {
    const nextSegment = (segment + 1) % longitudinalSegments;
    const seamOffset =
      nextSegment === 0 ? crossSectionSegments / 2 : 0;

    for (
      let section = 0;
      section < crossSectionSegments;
      section += 1
    ) {
      const nextSection = (section + 1) % crossSectionSegments;
      const a = segment * crossSectionSegments + section;
      const b =
        nextSegment * crossSectionSegments +
        ((section + seamOffset) % crossSectionSegments);
      const c =
        nextSegment * crossSectionSegments +
        ((nextSection + seamOffset) % crossSectionSegments);
      const d = segment * crossSectionSegments + nextSection;
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

export function createSingleMobiusPrototype(): THREE.Group {
  const root = new THREE.Group();
  root.name = "single-crossing-mobius-root";
  root.rotation.set(-0.08, 0.12, -0.08);

  const resources: Disposable[] = [];
  const ribbonGeometry = createRoundedMobiusGeometry();
  const ribbonMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x4f827a,
    metalness: 0.82,
    roughness: 0.3,
    clearcoat: 0.42,
    clearcoatRoughness: 0.2,
    envMapIntensity: 1.35,
    side: THREE.DoubleSide,
  });
  const ribbon = new THREE.Mesh(ribbonGeometry, ribbonMaterial);
  ribbon.name = "crossing-mobius-ribbon";
  ribbon.castShadow = true;
  ribbon.receiveShadow = true;
  root.add(ribbon);
  resources.push(ribbonGeometry, ribbonMaterial);

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
  resources.push(coreGlowGeometry, coreGlowMaterial);

  root.userData.sculptRuntime = {
    nodes: { root, ribbon, core, coreGlow },
    meshes: { ribbon, core, coreGlow },
    sockets: {},
    bandPivots: { mobius: root },
    tick: () => undefined,
    dispose: () => resources.forEach((resource) => resource.dispose()),
  };
  root.userData.tick = () => undefined;

  return root;
}
