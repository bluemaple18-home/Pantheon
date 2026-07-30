import * as THREE from "three";

type Disposable = THREE.BufferGeometry | THREE.Material;

export const PANTHEON_THEME_PARAMS = {
  themeCount: 5,
  mainRibbonCount: 5,
  echoRibbonCount: 5,
  innerSphereRadius: 0.75,
  coreRadius: 0.21,
  astrolabeRadius: 1.28,
  longitudinalSegments: 320,
} as const;

export const PANTHEON_THEMES = [
  {
    id: "Constellation",
    label: "星座",
    color: 0x314d78,
    echoColor: 0x91a9bd,
    normal: [0.12, 0.96, 0.25],
    radius: 0.94,
    width: 0.245,
    phase: 0.1,
    roll: 0.12,
    depthWarp: 0.16,
    period: 8,
  },
  {
    id: "Tarot",
    label: "塔羅",
    color: 0xa95f68,
    echoColor: 0xd6a192,
    normal: [0.48, -0.38, 0.79],
    radius: 0.97,
    width: 0.27,
    phase: 1.25,
    roll: 0.65,
    depthWarp: 0.13,
    period: 9.5,
  },
  {
    id: "Personality",
    label: "人格",
    color: 0x3f8d84,
    echoColor: 0x91c5bc,
    normal: [-0.54, -0.26, 0.8],
    radius: 0.91,
    width: 0.235,
    phase: 2.4,
    roll: 1.05,
    depthWarp: 0.18,
    period: 7.2,
  },
  {
    id: "NatalChart",
    label: "命盤",
    color: 0xa8bac2,
    echoColor: 0xe3e6dc,
    normal: [0.93, 0.18, 0.32],
    radius: 0.95,
    width: 0.255,
    phase: 3.55,
    roll: 1.55,
    depthWarp: 0.14,
    period: 10.3,
  },
  {
    id: "Bazi",
    label: "八字",
    color: 0xb47748,
    echoColor: 0xd8ad61,
    normal: [-0.58, 0.67, 0.47],
    radius: 0.93,
    width: 0.25,
    phase: 4.7,
    roll: 2.05,
    depthWarp: 0.17,
    period: 8.8,
  },
] as const;

interface CurveBasis {
  normal: THREE.Vector3;
  u: THREE.Vector3;
  v: THREE.Vector3;
}

interface RibbonBuild {
  centerline: THREE.Vector3[];
  geometry: THREE.BufferGeometry;
  seam: {
    leftToStartRight: number;
    rightToStartLeft: number;
    leftToStartLeft: number;
  };
}

const Y_AXIS = new THREE.Vector3(0, 1, 0);
const X_AXIS = new THREE.Vector3(1, 0, 0);

function createBasis(normalValues: readonly number[]): CurveBasis {
  const normal = new THREE.Vector3(...normalValues).normalize();
  const helper = Math.abs(normal.y) < 0.88 ? Y_AXIS : X_AXIS;
  const u = new THREE.Vector3().crossVectors(helper, normal).normalize();
  const v = new THREE.Vector3().crossVectors(normal, u).normalize();
  return { normal, u, v };
}

function getCenterPoint(
  basis: CurveBasis,
  radius: number,
  phase: number,
  depthWarp: number,
  t: number,
  target = new THREE.Vector3(),
): THREE.Vector3 {
  const angle = t * Math.PI * 2 + phase;
  return target
    .copy(basis.u)
    .multiplyScalar(Math.cos(angle))
    .addScaledVector(basis.v, Math.sin(angle))
    .addScaledVector(
      basis.normal,
      depthWarp * Math.sin(angle * 2 + phase * 0.45),
    )
    .normalize()
    .multiplyScalar(radius);
}

function getRibbonEdgePair(
  basis: CurveBasis,
  radius: number,
  width: number,
  phase: number,
  roll: number,
  depthWarp: number,
  t: number,
): [THREE.Vector3, THREE.Vector3] {
  const center = getCenterPoint(basis, radius, phase, depthWarp, t);
  const step = 1 / PANTHEON_THEME_PARAMS.longitudinalSegments / 2;
  const previous = getCenterPoint(
    basis,
    radius,
    phase,
    depthWarp,
    t - step,
  );
  const next = getCenterPoint(
    basis,
    radius,
    phase,
    depthWarp,
    t + step,
  );
  const tangent = next.sub(previous).normalize();
  const radial = center.clone().normalize();
  const surfaceSide = new THREE.Vector3()
    .crossVectors(tangent, radial)
    .normalize();
  const twist = Math.PI * t + roll;
  const widthDirection = surfaceSide
    .multiplyScalar(Math.cos(twist))
    .addScaledVector(radial, Math.sin(twist))
    .normalize();
  return [
    center.clone().addScaledVector(widthDirection, width / 2),
    center.clone().addScaledVector(widthDirection, -width / 2),
  ];
}

function createMobiusRibbonGeometry(
  basis: CurveBasis,
  radius: number,
  width: number,
  phase: number,
  roll: number,
  depthWarp: number,
): RibbonBuild {
  const segments = PANTHEON_THEME_PARAMS.longitudinalSegments;
  const positions: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];
  const centerline: THREE.Vector3[] = [];

  for (let segment = 0; segment < segments; segment += 1) {
    const t = segment / segments;
    const center = getCenterPoint(
      basis,
      radius,
      phase,
      depthWarp,
      t,
    );
    const [left, right] = getRibbonEdgePair(
      basis,
      radius,
      width,
      phase,
      roll,
      depthWarp,
      t,
    );
    centerline.push(center);
    positions.push(left.x, left.y, left.z, right.x, right.y, right.z);
    uvs.push(t, 0, t, 1);
  }

  for (let segment = 0; segment < segments - 1; segment += 1) {
    const left = segment * 2;
    const right = left + 1;
    const nextLeft = left + 2;
    const nextRight = left + 3;
    indices.push(left, right, nextRight, left, nextRight, nextLeft);
  }

  const lastLeft = (segments - 1) * 2;
  const lastRight = lastLeft + 1;
  indices.push(lastLeft, lastRight, 0, lastLeft, 0, 1);

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

  const [endLeft, endRight] = getRibbonEdgePair(
    basis,
    radius,
    width,
    phase,
    roll,
    depthWarp,
    1,
  );
  const [startLeft, startRight] = getRibbonEdgePair(
    basis,
    radius,
    width,
    phase,
    roll,
    depthWarp,
    0,
  );

  return {
    centerline,
    geometry,
    seam: {
      leftToStartRight: endLeft.distanceTo(startRight),
      rightToStartLeft: endRight.distanceTo(startLeft),
      leftToStartLeft: endLeft.distanceTo(startLeft),
    },
  };
}

function createRibbonMaterial(
  color: number,
  echo: boolean,
): THREE.MeshPhysicalMaterial {
  return new THREE.MeshPhysicalMaterial({
    color,
    metalness: echo ? 0.72 : 0.83,
    roughness: echo ? 0.31 : 0.24,
    clearcoat: 0.72,
    clearcoatRoughness: 0.14,
    envMapIntensity: echo ? 1.1 : 1.35,
    side: THREE.DoubleSide,
  });
}

export function createPantheonThemeSpherePrototype(): THREE.Group {
  const root = new THREE.Group();
  root.name = "PantheonSphere";

  const resources: Disposable[] = [];
  const nodes: Record<string, THREE.Object3D> = { PantheonSphere: root };
  const meshes: Record<string, THREE.Mesh> = {};
  const bandPivots: Record<string, THREE.Group> = {};
  const themeGroups: Record<string, THREE.Group> = {};
  const echoMeshes: THREE.Mesh[] = [];
  const guideGroup = new THREE.Group();
  guideGroup.name = "ThemeSphereDebugGuides";
  guideGroup.visible = false;
  root.add(guideGroup);
  nodes[guideGroup.name] = guideGroup;

  const innerGeometry = new THREE.SphereGeometry(
    PANTHEON_THEME_PARAMS.innerSphereRadius,
    72,
    48,
  );
  const innerMaterial = new THREE.MeshBasicMaterial({
    color: 0x010305,
    side: THREE.BackSide,
  });
  const innerSphere = new THREE.Mesh(innerGeometry, innerMaterial);
  innerSphere.name = "InnerDarkSphere";
  innerSphere.receiveShadow = true;
  root.add(innerSphere);
  nodes[innerSphere.name] = innerSphere;
  meshes.innerSphere = innerSphere;
  resources.push(innerGeometry, innerMaterial);

  const seamMetrics: Record<string, RibbonBuild["seam"]> = {};

  PANTHEON_THEMES.forEach((theme, index) => {
    const themeGroup = new THREE.Group();
    themeGroup.name = `ThemeGroup_${theme.id}`;
    themeGroup.userData.baseRotation = new THREE.Euler(0, 0, 0);
    root.add(themeGroup);
    nodes[themeGroup.name] = themeGroup;
    themeGroups[theme.id] = themeGroup;

    const basis = createBasis(theme.normal);
    const mainBuild = createMobiusRibbonGeometry(
      basis,
      theme.radius,
      theme.width,
      theme.phase,
      theme.roll,
      theme.depthWarp,
    );
    const mainMaterial = createRibbonMaterial(theme.color, false);
    const mainRibbon = new THREE.Mesh(mainBuild.geometry, mainMaterial);
    mainRibbon.name = `${theme.id}_MainMobiusRibbon`;
    mainRibbon.castShadow = true;
    mainRibbon.receiveShadow = true;
    mainRibbon.renderOrder = index * 2;
    themeGroup.add(mainRibbon);

    const echoNormal = basis.normal
      .clone()
      .applyAxisAngle(
        basis.u,
        THREE.MathUtils.degToRad(index % 2 === 0 ? 12 : -12),
      );
    const echoBasis = createBasis(echoNormal.toArray());
    const echoBuild = createMobiusRibbonGeometry(
      echoBasis,
      theme.radius + 0.035,
      theme.width * 0.42,
      theme.phase + 0.095,
      theme.roll + 0.22,
      theme.depthWarp * 0.88,
    );
    const echoMaterial = createRibbonMaterial(theme.echoColor, true);
    const echoRibbon = new THREE.Mesh(echoBuild.geometry, echoMaterial);
    echoRibbon.name = `${theme.id}_EchoRibbon`;
    echoRibbon.castShadow = true;
    echoRibbon.receiveShadow = true;
    echoRibbon.renderOrder = index * 2 + 1;
    themeGroup.add(echoRibbon);
    echoMeshes.push(echoRibbon);

    const lineGeometry = new THREE.BufferGeometry().setFromPoints(
      mainBuild.centerline,
    );
    const lineMaterial = new THREE.LineBasicMaterial({
      color: theme.echoColor,
      transparent: true,
      opacity: 0.75,
      depthTest: false,
    });
    const centerline = new THREE.LineLoop(lineGeometry, lineMaterial);
    centerline.name = `${theme.id}_Centerline`;
    centerline.renderOrder = 100 + index;
    guideGroup.add(centerline);

    nodes[mainRibbon.name] = mainRibbon;
    nodes[echoRibbon.name] = echoRibbon;
    nodes[centerline.name] = centerline;
    meshes[mainRibbon.name] = mainRibbon;
    meshes[echoRibbon.name] = echoRibbon;
    bandPivots[`${theme.id}-main`] = themeGroup;
    bandPivots[`${theme.id}-echo`] = themeGroup;
    seamMetrics[`${theme.id}-main`] = mainBuild.seam;
    seamMetrics[`${theme.id}-echo`] = echoBuild.seam;
    resources.push(
      mainBuild.geometry,
      mainMaterial,
      echoBuild.geometry,
      echoMaterial,
      lineGeometry,
      lineMaterial,
    );
  });

  const coreGeometry = new THREE.SphereGeometry(
    PANTHEON_THEME_PARAMS.coreRadius,
    72,
    48,
  );
  const coreMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xd9a84f,
    emissive: 0x70420d,
    emissiveIntensity: 0.18,
    metalness: 1,
    roughness: 0.13,
    clearcoat: 0.85,
    clearcoatRoughness: 0.08,
    envMapIntensity: 1.65,
    depthTest: false,
  });
  const core = new THREE.Mesh(coreGeometry, coreMaterial);
  core.name = "CoreSphere";
  core.renderOrder = 50;
  core.castShadow = true;
  root.add(core);
  nodes[core.name] = core;
  meshes.core = core;
  resources.push(coreGeometry, coreMaterial);

  const astrolabe = new THREE.Group();
  astrolabe.name = "OuterAstrolabe";
  astrolabe.rotation.set(0.16, -0.08, 0);
  root.add(astrolabe);
  nodes[astrolabe.name] = astrolabe;
  [1.19, 1.27, PANTHEON_THEME_PARAMS.astrolabeRadius].forEach(
    (radius, index) => {
      const geometry = new THREE.TorusGeometry(
        radius,
        index === 1 ? 0.006 : 0.0035,
        8,
        180,
      );
      const material = new THREE.MeshBasicMaterial({
        color: index === 1 ? 0xb88b43 : 0xd2b479,
        transparent: true,
        opacity: index === 1 ? 0.34 : 0.2,
        depthWrite: false,
      });
      const ring = new THREE.Mesh(geometry, material);
      ring.name = `AstrolabeRing_${index + 1}`;
      astrolabe.add(ring);
      nodes[ring.name] = ring;
      resources.push(geometry, material);
    },
  );

  const tickGeometry = new THREE.BoxGeometry(0.004, 0.045, 0.004);
  const tickMaterial = new THREE.MeshBasicMaterial({
    color: 0xd5b778,
    transparent: true,
    opacity: 0.38,
    depthWrite: false,
  });
  for (let index = 0; index < 36; index += 1) {
    const angle = (index / 36) * Math.PI * 2;
    const tick = new THREE.Mesh(tickGeometry, tickMaterial);
    tick.name = `AstrolabeTick_${String(index + 1).padStart(2, "0")}`;
    tick.position.set(
      Math.cos(angle) * 1.33,
      Math.sin(angle) * 1.33,
      0,
    );
    tick.rotation.z = angle;
    tick.scale.y = index % 3 === 0 ? 1.45 : 0.72;
    astrolabe.add(tick);
  }
  resources.push(tickGeometry, tickMaterial);

  const referenceGeometry = new THREE.SphereGeometry(1, 32, 20);
  const referenceMaterial = new THREE.MeshBasicMaterial({
    color: 0x84aaa4,
    wireframe: true,
    transparent: true,
    opacity: 0.12,
    depthWrite: false,
  });
  const referenceSphere = new THREE.Mesh(
    referenceGeometry,
    referenceMaterial,
  );
  referenceSphere.name = "ThemeReferenceSphere";
  guideGroup.add(referenceSphere);
  nodes[referenceSphere.name] = referenceSphere;
  resources.push(referenceGeometry, referenceMaterial);

  const setDebugMode = (enabled: boolean) => {
    guideGroup.visible = enabled;
  };
  const setEchoVisible = (visible: boolean) => {
    echoMeshes.forEach((mesh) => {
      mesh.visible = visible;
    });
  };
  const setThemeVisibleCount = (count: number) => {
    PANTHEON_THEMES.forEach((theme, index) => {
      themeGroups[theme.id].visible = index < count;
    });
  };

  root.userData.sculptRuntime = {
    nodes,
    meshes,
    sockets: {},
    bandPivots,
    themeGroups,
    params: PANTHEON_THEME_PARAMS,
    metrics: {
      themeCount: PANTHEON_THEMES.length,
      ribbonCount: PANTHEON_THEMES.length * 2,
      seamMetrics,
    },
    setDebugMode,
    setEchoVisible,
    setThemeVisibleCount,
    tick: (time: number) => {
      root.rotation.x =
        THREE.MathUtils.degToRad(-9.5) +
        Math.sin(time * 0.11) * THREE.MathUtils.degToRad(0.7);
      root.rotation.y = (time / 42) * Math.PI * 2;
      root.rotation.z =
        Math.sin(time * 0.17) * THREE.MathUtils.degToRad(1);
      PANTHEON_THEMES.forEach((theme, index) => {
        const group = themeGroups[theme.id];
        const pulse =
          Math.sin((time / theme.period) * Math.PI * 2 + index * 0.9);
        group.scale.setScalar(1 + pulse * 0.008);
        group.rotation.z = pulse * THREE.MathUtils.degToRad(0.8);
      });
      const corePulse = Math.sin(time * 0.8);
      core.scale.setScalar(1 + corePulse * 0.02);
      coreMaterial.emissiveIntensity = 0.18 + corePulse * 0.08;
      astrolabe.rotation.z = -(time / 78) * Math.PI * 2;
    },
    dispose: () => {
      resources.forEach((resource) => resource.dispose());
    },
  };
  root.userData.tick = (time: number) =>
    root.userData.sculptRuntime.tick(time);
  setDebugMode(false);
  setEchoVisible(true);
  return root;
}
