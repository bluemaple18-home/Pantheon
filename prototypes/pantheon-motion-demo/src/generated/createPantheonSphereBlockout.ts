import * as THREE from "three";

type Disposable = THREE.BufferGeometry | THREE.Material;

export const PANTHEON_BLOCKOUT_PARAMS = {
  sphereRadius: 1,
  innerOcclusionRadius: 0.68,
  coreRadius: 0.205,
  ribbonThickness: 0.014,
  longitudinalSegments: 360,
} as const;

export const PANTHEON_BLOCKOUT_THEMES = [
  {
    id: "Constellation",
    gray: 0x666a6e,
    echoGray: 0x505458,
    width: 0.18,
    echoWidth: 0.068,
    radius: 0.93,
    latAmplitude: 0.34,
    latFrequency: 2,
    phase: 0.25,
    lonWarp: 0.12,
    rotation: [-0.2, 0.05, 0.3],
    twistPhase: 0.4,
  },
  {
    id: "Tarot",
    gray: 0x777b7f,
    echoGray: 0x585c60,
    width: 0.2,
    echoWidth: 0.078,
    radius: 0.975,
    latAmplitude: 0.52,
    latFrequency: 1,
    phase: 1.15,
    lonWarp: 0.18,
    rotation: [0.28, 0.42, -0.52],
    twistPhase: 1.1,
  },
  {
    id: "Personality",
    gray: 0x85898d,
    echoGray: 0x62666a,
    width: 0.19,
    echoWidth: 0.074,
    radius: 0.955,
    latAmplitude: 0.48,
    latFrequency: 1,
    phase: 2.2,
    lonWarp: 0.14,
    rotation: [-0.18, -0.32, 0.68],
    twistPhase: 2,
  },
  {
    id: "NatalChart",
    gray: 0x93979b,
    echoGray: 0x6c7074,
    width: 0.16,
    echoWidth: 0.06,
    radius: 0.94,
    latAmplitude: 0.4,
    latFrequency: 2,
    phase: 3.05,
    lonWarp: 0.1,
    rotation: [0.7, 0.08, 1.02],
    twistPhase: 2.8,
  },
  {
    id: "Bazi",
    gray: 0x6f7377,
    echoGray: 0x4f5357,
    width: 0.185,
    echoWidth: 0.07,
    radius: 0.92,
    latAmplitude: 0.44,
    latFrequency: 1,
    phase: 4.15,
    lonWarp: 0.16,
    rotation: [-0.52, 0.3, -0.82],
    twistPhase: 3.5,
  },
] as const;

type ThemeConfig = (typeof PANTHEON_BLOCKOUT_THEMES)[number];

interface PathVariant {
  echo: boolean;
  phaseOffset: number;
  radialOffset: number;
  latitudeOffset: number;
}

interface RibbonBuild {
  geometry: THREE.BufferGeometry;
  centerline: THREE.Vector3[];
  seamDistance: number;
  minRadius: number;
  maxRadius: number;
}

function createThemeQuaternion(
  rotation: readonly number[],
): THREE.Quaternion {
  return new THREE.Quaternion().setFromEuler(
    new THREE.Euler(rotation[0], rotation[1], rotation[2], "XYZ"),
  );
}

function getPathPoint(
  theme: ThemeConfig,
  variant: PathVariant,
  t: number,
  target = new THREE.Vector3(),
): THREE.Vector3 {
  const angle = t * Math.PI * 2;
  const phase = theme.phase + variant.phaseOffset;
  const latitude =
    theme.latAmplitude *
      Math.sin(theme.latFrequency * angle + phase) +
    0.075 * Math.sin(3 * angle - phase * 0.65) +
    variant.latitudeOffset * Math.sin(angle + phase);
  const longitude =
    angle +
    theme.lonWarp * Math.sin(2 * angle + phase * 0.45) +
    0.035 * Math.sin(5 * angle - phase);
  const cosLatitude = Math.cos(latitude);
  const radius =
    theme.radius +
    variant.radialOffset +
    0.032 * Math.sin(3 * angle + phase) +
    0.014 * Math.sin(5 * angle - phase * 0.7);

  return target
    .set(
      cosLatitude * Math.cos(longitude),
      Math.sin(latitude),
      cosLatitude * Math.sin(longitude),
    )
    .applyQuaternion(createThemeQuaternion(theme.rotation))
    .normalize()
    .multiplyScalar(radius);
}

function createRibbonGeometry(
  theme: ThemeConfig,
  width: number,
  variant: PathVariant,
): RibbonBuild {
  const segments = PANTHEON_BLOCKOUT_PARAMS.longitudinalSegments;
  const thickness = PANTHEON_BLOCKOUT_PARAMS.ribbonThickness;
  const positions: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];
  const centerline: THREE.Vector3[] = [];
  const controlPoints = Array.from({ length: 96 }, (_, index) =>
    getPathPoint(theme, variant, index / 96),
  );
  const curve = new THREE.CatmullRomCurve3(
    controlPoints,
    true,
    "centripetal",
    0.5,
  );
  const frames = curve.computeFrenetFrames(segments, true);
  const center = new THREE.Vector3();
  const widthDirection = new THREE.Vector3();
  const surfaceNormal = new THREE.Vector3();
  const point = new THREE.Vector3();
  let minRadius = Number.POSITIVE_INFINITY;
  let maxRadius = 0;

  for (let segment = 0; segment < segments; segment += 1) {
    const t = segment / segments;
    const angle = t * Math.PI * 2;
    curve.getPointAt(t, center);
    const tangent = frames.tangents[segment];
    const normal = frames.normals[segment];
    const binormal = frames.binormals[segment];

    const twist =
      Math.sin(angle + theme.twistPhase + variant.phaseOffset) *
      Math.PI *
      0.12;
    widthDirection
      .copy(binormal)
      .multiplyScalar(Math.cos(twist))
      .addScaledVector(normal, Math.sin(twist))
      .normalize();
    surfaceNormal
      .crossVectors(tangent, widthDirection)
      .normalize();

    const radius = center.length();
    minRadius = Math.min(minRadius, radius);
    maxRadius = Math.max(maxRadius, radius);
    centerline.push(center.clone());

    const crossSection = [
      [width / 2, thickness / 2],
      [-width / 2, thickness / 2],
      [-width / 2, -thickness / 2],
      [width / 2, -thickness / 2],
    ] as const;

    crossSection.forEach(([sideOffset, normalOffset], corner) => {
      point
        .copy(center)
        .addScaledVector(widthDirection, sideOffset)
        .addScaledVector(surfaceNormal, normalOffset);
      positions.push(point.x, point.y, point.z);
      uvs.push(t, corner / 3);
    });
  }

  for (let segment = 0; segment < segments; segment += 1) {
    const nextSegment = (segment + 1) % segments;
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

  const start = getPathPoint(theme, variant, 0);
  const end = getPathPoint(theme, variant, 1);
  return {
    geometry,
    centerline,
    seamDistance: start.distanceTo(end),
    minRadius,
    maxRadius,
  };
}

function createBlockoutMaterial(color: number): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color,
    metalness: 0,
    roughness: 0.78,
    side: THREE.DoubleSide,
  });
}

export function createPantheonSphereBlockout(): THREE.Group {
  const root = new THREE.Group();
  root.name = "PantheonSphere";

  const resources: Disposable[] = [];
  const nodes: Record<string, THREE.Object3D> = { PantheonSphere: root };
  const meshes: Record<string, THREE.Mesh> = {};
  const bandPivots: Record<string, THREE.Group> = {};
  const themeGroups: Record<string, THREE.Group> = {};
  const seamMetrics: Record<string, number> = {};
  const radiusMetrics: Record<
    string,
    { minRadius: number; maxRadius: number }
  > = {};

  const occlusionGeometry = new THREE.SphereGeometry(
    PANTHEON_BLOCKOUT_PARAMS.innerOcclusionRadius,
    64,
    40,
  );
  const occlusionMaterial = new THREE.MeshStandardMaterial({
    color: 0x20252a,
    metalness: 0.08,
    roughness: 0.68,
    side: THREE.BackSide,
  });
  const innerOcclusion = new THREE.Mesh(
    occlusionGeometry,
    occlusionMaterial,
  );
  innerOcclusion.name = "InnerOcclusionSphere";
  innerOcclusion.receiveShadow = true;
  root.add(innerOcclusion);
  nodes[innerOcclusion.name] = innerOcclusion;
  meshes.innerOcclusion = innerOcclusion;
  resources.push(occlusionGeometry, occlusionMaterial);

  PANTHEON_BLOCKOUT_THEMES.forEach((theme, index) => {
    const themeGroup = new THREE.Group();
    themeGroup.name = `Theme_${theme.id}`;
    root.add(themeGroup);
    nodes[themeGroup.name] = themeGroup;
    themeGroups[theme.id] = themeGroup;
    bandPivots[theme.id] = themeGroup;

    const mainVariant: PathVariant = {
      echo: false,
      phaseOffset: 0,
      radialOffset: 0,
      latitudeOffset: 0,
    };
    const mainBuild = createRibbonGeometry(
      theme,
      theme.width,
      mainVariant,
    );
    const mainMaterial = createBlockoutMaterial(theme.gray);
    const mainRibbon = new THREE.Mesh(
      mainBuild.geometry,
      mainMaterial,
    );
    mainRibbon.name = "MainRibbon";
    mainRibbon.castShadow = true;
    mainRibbon.receiveShadow = true;
    mainRibbon.renderOrder = index * 2;
    themeGroup.add(mainRibbon);
    nodes[`${themeGroup.name}/MainRibbon`] = mainRibbon;
    meshes[`${theme.id}MainRibbon`] = mainRibbon;

    const echoVariant: PathVariant = {
      echo: true,
      phaseOffset: 0.22 + index * 0.025,
      radialOffset: index % 2 === 0 ? -0.025 : 0.022,
      latitudeOffset: index % 2 === 0 ? 0.12 : -0.1,
    };
    const echoBuild = createRibbonGeometry(
      theme,
      theme.echoWidth,
      echoVariant,
    );
    const echoMaterial = createBlockoutMaterial(theme.echoGray);
    const echoRibbon = new THREE.Mesh(
      echoBuild.geometry,
      echoMaterial,
    );
    echoRibbon.name = "EchoRibbon";
    echoRibbon.castShadow = true;
    echoRibbon.receiveShadow = true;
    echoRibbon.renderOrder = index * 2 + 1;
    themeGroup.add(echoRibbon);
    nodes[`${themeGroup.name}/EchoRibbon`] = echoRibbon;
    meshes[`${theme.id}EchoRibbon`] = echoRibbon;

    seamMetrics[`${theme.id}MainRibbon`] = mainBuild.seamDistance;
    seamMetrics[`${theme.id}EchoRibbon`] = echoBuild.seamDistance;
    radiusMetrics[`${theme.id}MainRibbon`] = {
      minRadius: mainBuild.minRadius,
      maxRadius: mainBuild.maxRadius,
    };
    radiusMetrics[`${theme.id}EchoRibbon`] = {
      minRadius: echoBuild.minRadius,
      maxRadius: echoBuild.maxRadius,
    };
    resources.push(
      mainBuild.geometry,
      mainMaterial,
      echoBuild.geometry,
      echoMaterial,
    );
  });

  const coreGeometry = new THREE.SphereGeometry(
    PANTHEON_BLOCKOUT_PARAMS.coreRadius,
    64,
    40,
  );
  const coreMaterial = new THREE.MeshStandardMaterial({
    color: 0xb9b9b7,
    metalness: 0,
    roughness: 0.48,
  });
  const core = new THREE.Mesh(coreGeometry, coreMaterial);
  core.name = "CoreTimeSphere";
  core.castShadow = true;
  core.receiveShadow = true;
  root.add(core);
  nodes[core.name] = core;
  meshes.core = core;
  resources.push(coreGeometry, coreMaterial);

  const setThemeVisible = (themeId: string, visible: boolean) => {
    if (themeGroups[themeId]) themeGroups[themeId].visible = visible;
  };

  root.userData.sculptRuntime = {
    nodes,
    meshes,
    sockets: {},
    bandPivots,
    themeGroups,
    params: PANTHEON_BLOCKOUT_PARAMS,
    metrics: {
      themeCount: PANTHEON_BLOCKOUT_THEMES.length,
      ribbonCount: PANTHEON_BLOCKOUT_THEMES.length * 2,
      seamMetrics,
      radiusMetrics,
    },
    setThemeVisible,
    tick: () => undefined,
    dispose: () => {
      resources.forEach((resource) => resource.dispose());
    },
  };
  root.userData.tick = () => undefined;
  return root;
}
