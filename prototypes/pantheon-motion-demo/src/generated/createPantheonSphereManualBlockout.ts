import * as THREE from "three";

type Disposable = THREE.BufferGeometry | THREE.Material;
type Anchor = readonly [x: number, y: number, z: number, radius: number];

interface ThemeSculpt {
  id: "Constellation" | "Tarot" | "Personality" | "NatalChart" | "Bazi";
  gray: number;
  echoGray: number;
  width: number;
  echoWidth: number;
  echoBlend: number;
  echoRadiusOffset: number;
  echoAxis: readonly [number, number, number];
  echoAngleDegrees: number;
  anchors: readonly Anchor[];
}

export const PANTHEON_MANUAL_BLOCKOUT_PARAMS = {
  sphereRadius: 1,
  innerOcclusionRadius: 0.36,
  coreRadius: 0.205,
  ribbonThickness: 0.014,
  longitudinalSegments: 320,
} as const;

/**
 * 每個座標都是人工安排的球殼控制點。
 * 半徑欄位負責逐段 over-under，不由平面角度或球面分布公式生成。
 */
export const PANTHEON_MANUAL_BLOCKOUT_THEMES: readonly ThemeSculpt[] = [
  {
    id: "Constellation",
    gray: 0x777b7f,
    echoGray: 0x555a5f,
    width: 0.19,
    echoWidth: 0.064,
    echoBlend: 0.11,
    echoRadiusOffset: -0.026,
    echoAxis: [1, 0, 0],
    echoAngleDegrees: 11,
    anchors: [
      [0.94, 0.2, 0.24, 0.97],
      [0.68, 0.36, -0.64, 0.91],
      [0.12, 0.29, -0.95, 0.89],
      [-0.57, 0.08, -0.8, 0.94],
      [-0.96, -0.16, -0.12, 0.98],
      [-0.72, -0.34, 0.56, 0.91],
      [-0.12, -0.25, 0.96, 0.95],
      [0.52, -0.02, 0.84, 0.99],
    ],
  },
  {
    id: "Tarot",
    gray: 0x8b8f93,
    echoGray: 0x62676b,
    width: 0.2,
    echoWidth: 0.07,
    echoBlend: 0.085,
    echoRadiusOffset: 0.018,
    echoAxis: [0, 1, 0],
    echoAngleDegrees: 12,
    anchors: [
      [-0.82, -0.5, 0.22, 0.98],
      [-0.39, -0.78, -0.45, 0.91],
      [0.24, -0.75, -0.61, 0.89],
      [0.77, -0.28, -0.52, 0.96],
      [0.83, 0.32, 0.34, 0.99],
      [0.38, 0.78, 0.49, 0.92],
      [-0.24, 0.83, 0.48, 0.9],
      [-0.72, 0.4, 0.52, 0.96],
      [-0.9, -0.12, 0.36, 0.99],
    ],
  },
  {
    id: "Personality",
    gray: 0x9a9ea2,
    echoGray: 0x707579,
    width: 0.19,
    echoWidth: 0.066,
    echoBlend: 0.1,
    echoRadiusOffset: -0.018,
    echoAxis: [0, 1, 0],
    echoAngleDegrees: -12,
    anchors: [
      [0.82, -0.5, 0.24, 0.99],
      [0.4, -0.77, -0.46, 0.92],
      [-0.22, -0.74, -0.63, 0.89],
      [-0.75, -0.25, -0.57, 0.95],
      [-0.84, 0.36, 0.32, 0.98],
      [-0.38, 0.79, 0.47, 0.91],
      [0.26, 0.82, 0.49, 0.9],
      [0.73, 0.37, 0.53, 0.96],
      [0.91, -0.13, 0.35, 0.98],
    ],
  },
  {
    id: "NatalChart",
    gray: 0xabadb0,
    echoGray: 0x7c8185,
    width: 0.165,
    echoWidth: 0.055,
    echoBlend: 0.12,
    echoRadiusOffset: 0.014,
    echoAxis: [0, 0, 1],
    echoAngleDegrees: 13,
    anchors: [
      [-0.12, -0.96, 0.25, 0.98],
      [0.15, -0.65, 0.75, 0.94],
      [0.2, -0.05, 0.97, 0.99],
      [0.1, 0.62, 0.78, 0.95],
      [0.03, 0.97, 0.22, 0.98],
      [-0.3, 0.72, -0.62, 0.91],
      [-0.45, 0.05, -0.87, 0.89],
      [-0.32, -0.65, -0.65, 0.92],
    ],
  },
  {
    id: "Bazi",
    gray: 0x818589,
    echoGray: 0x5b6064,
    width: 0.185,
    echoWidth: 0.062,
    echoBlend: 0.095,
    echoRadiusOffset: -0.012,
    echoAxis: [1, 0, 1],
    echoAngleDegrees: -11,
    anchors: [
      [-0.72, -0.65, 0.28, 0.97],
      [-0.28, -0.56, 0.8, 0.94],
      [0.15, -0.15, 0.98, 0.99],
      [0.55, 0.25, 0.78, 0.95],
      [0.72, 0.65, 0.25, 0.98],
      [0.38, 0.7, -0.58, 0.91],
      [-0.12, 0.35, -0.92, 0.89],
      [-0.55, -0.15, -0.82, 0.92],
      [-0.75, -0.55, -0.35, 0.95],
    ],
  },
] as const;

interface RibbonBuild {
  geometry: THREE.BufferGeometry;
  seamDistance: number;
  minRadius: number;
  maxRadius: number;
}

function anchorToPoint(anchor: Anchor): THREE.Vector3 {
  return new THREE.Vector3(anchor[0], anchor[1], anchor[2])
    .normalize()
    .multiplyScalar(anchor[3]);
}

function createCurve(
  theme: ThemeSculpt,
  echo: boolean,
): THREE.CatmullRomCurve3 {
  const echoQuaternion = new THREE.Quaternion().setFromAxisAngle(
    new THREE.Vector3(...theme.echoAxis).normalize(),
    THREE.MathUtils.degToRad(theme.echoAngleDegrees),
  );
  const points = theme.anchors.map((anchor, index) => {
    const point = anchorToPoint(anchor);
    if (!echo) return point;

    const next = anchorToPoint(
      theme.anchors[(index + 1) % theme.anchors.length],
    );
    return point
      .lerp(next, theme.echoBlend)
      .applyQuaternion(echoQuaternion)
      .normalize()
      .multiplyScalar(anchor[3] + theme.echoRadiusOffset);
  });

  return new THREE.CatmullRomCurve3(points, true, "centripetal", 0.5);
}

function createRibbonGeometry(
  theme: ThemeSculpt,
  width: number,
  echo: boolean,
): RibbonBuild {
  const segments = PANTHEON_MANUAL_BLOCKOUT_PARAMS.longitudinalSegments;
  const thickness = PANTHEON_MANUAL_BLOCKOUT_PARAMS.ribbonThickness;
  const curve = createCurve(theme, echo);
  const positions: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];
  const centers: THREE.Vector3[] = [];
  const tangents: THREE.Vector3[] = [];
  const widths: THREE.Vector3[] = [];
  const normals: THREE.Vector3[] = [];
  let minRadius = Number.POSITIVE_INFINITY;
  let maxRadius = 0;

  for (let segment = 0; segment < segments; segment += 1) {
    const t = segment / segments;
    const center = curve.getPointAt(t);
    const tangent = curve.getTangentAt(t).normalize();
    const radial = center.clone().normalize();
    const widthDirection = new THREE.Vector3()
      .crossVectors(radial, tangent)
      .normalize();

    if (
      segment > 0 &&
      widthDirection.dot(widths[segment - 1]) < 0
    ) {
      widthDirection.negate();
    }

    const surfaceNormal = new THREE.Vector3()
      .crossVectors(tangent, widthDirection)
      .normalize();
    const radius = center.length();
    minRadius = Math.min(minRadius, radius);
    maxRadius = Math.max(maxRadius, radius);
    centers.push(center);
    tangents.push(tangent);
    widths.push(widthDirection);
    normals.push(surfaceNormal);
  }

  const seamRoll = Math.atan2(
    widths[segments - 1]
      .clone()
      .cross(widths[0])
      .dot(tangents[0]),
    widths[segments - 1].dot(widths[0]),
  );
  const axis = new THREE.Vector3();
  const correctedWidth = new THREE.Vector3();
  const correctedNormal = new THREE.Vector3();
  const point = new THREE.Vector3();

  for (let segment = 0; segment < segments; segment += 1) {
    const t = segment / segments;
    axis.copy(tangents[segment]);
    correctedWidth
      .copy(widths[segment])
      .applyAxisAngle(axis, seamRoll * t);
    correctedNormal
      .crossVectors(tangents[segment], correctedWidth)
      .normalize();

    const crossSection = [
      [width / 2, thickness / 2],
      [-width / 2, thickness / 2],
      [-width / 2, -thickness / 2],
      [width / 2, -thickness / 2],
    ] as const;

    crossSection.forEach(([sideOffset, normalOffset], corner) => {
      point
        .copy(centers[segment])
        .addScaledVector(correctedWidth, sideOffset)
        .addScaledVector(correctedNormal, normalOffset);
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

  return {
    geometry,
    seamDistance: curve.getPointAt(0).distanceTo(curve.getPointAt(1)),
    minRadius,
    maxRadius,
  };
}

function createBlockoutMaterial(color: number): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color,
    metalness: 0,
    roughness: 0.8,
    side: THREE.DoubleSide,
  });
}

export function createPantheonSphereManualBlockout(): THREE.Group {
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
    PANTHEON_MANUAL_BLOCKOUT_PARAMS.innerOcclusionRadius,
    64,
    40,
  );
  const occlusionMaterial = new THREE.MeshStandardMaterial({
    color: 0x1e2429,
    metalness: 0,
    roughness: 0.78,
    side: THREE.BackSide,
  });
  const innerOcclusion = new THREE.Mesh(
    occlusionGeometry,
    occlusionMaterial,
  );
  innerOcclusion.name = "InnerOcclusionSphere";
  root.add(innerOcclusion);
  nodes[innerOcclusion.name] = innerOcclusion;
  meshes.innerOcclusion = innerOcclusion;
  resources.push(occlusionGeometry, occlusionMaterial);

  PANTHEON_MANUAL_BLOCKOUT_THEMES.forEach((theme, index) => {
    const themeGroup = new THREE.Group();
    themeGroup.name = `Theme_${theme.id}`;
    root.add(themeGroup);
    nodes[themeGroup.name] = themeGroup;
    themeGroups[theme.id] = themeGroup;
    bandPivots[theme.id] = themeGroup;

    const mainBuild = createRibbonGeometry(theme, theme.width, false);
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

    const echoBuild = createRibbonGeometry(
      theme,
      theme.echoWidth,
      true,
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
    PANTHEON_MANUAL_BLOCKOUT_PARAMS.coreRadius,
    64,
    40,
  );
  const coreMaterial = new THREE.MeshStandardMaterial({
    color: 0xb8bab9,
    metalness: 0,
    roughness: 0.5,
  });
  const core = new THREE.Mesh(coreGeometry, coreMaterial);
  core.name = "CoreTimeSphere";
  core.castShadow = true;
  core.receiveShadow = true;
  root.add(core);
  nodes[core.name] = core;
  meshes.core = core;
  resources.push(coreGeometry, coreMaterial);

  root.userData.sculptRuntime = {
    nodes,
    meshes,
    sockets: {},
    bandPivots,
    themeGroups,
    params: PANTHEON_MANUAL_BLOCKOUT_PARAMS,
    metrics: {
      themeCount: PANTHEON_MANUAL_BLOCKOUT_THEMES.length,
      ribbonCount: PANTHEON_MANUAL_BLOCKOUT_THEMES.length * 2,
      seamMetrics,
      radiusMetrics,
    },
    setThemeVisible(themeId: string, visible: boolean) {
      if (themeGroups[themeId]) themeGroups[themeId].visible = visible;
    },
    tick: () => undefined,
    dispose() {
      resources.forEach((resource) => resource.dispose());
    },
  };
  root.userData.tick = () => undefined;
  return root;
}
