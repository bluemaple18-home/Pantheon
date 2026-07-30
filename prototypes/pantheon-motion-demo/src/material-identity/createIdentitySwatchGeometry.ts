import * as THREE from "three";

const SWATCH_COUNT = 5;
const LENGTH_SEGMENTS = 144;
const WIDTH_SEGMENTS = 8;

const THEME_PREVIEW_COLORS = [
  ["#132c4a", "#6280a8"],
  ["#762c42", "#b65d74"],
  ["#1c5f5a", "#509389"],
  ["#95a3a7", "#bdcbcd"],
  ["#7d472d", "#bc7b47"],
] as const;

type VertexBuffers = {
  positions: number[];
  normals: number[];
  uvs: number[];
  identities: number[];
  bandV: number[];
  themeColors: number[];
  indices: number[];
};

function pushVertex(
  buffers: VertexBuffers,
  identity: number,
  position: THREE.Vector3,
  normal: THREE.Vector3,
  localU: number,
  localV: number,
) {
  const colorStart = new THREE.Color(THEME_PREVIEW_COLORS[identity][0]);
  const colorEnd = new THREE.Color(THEME_PREVIEW_COLORS[identity][1]);
  const color = colorStart.lerp(colorEnd, localV);
  buffers.positions.push(position.x, position.y, position.z);
  buffers.normals.push(normal.x, normal.y, normal.z);
  buffers.uvs.push((identity + localU) / SWATCH_COUNT, localV);
  buffers.identities.push(identity);
  buffers.bandV.push(localV);
  buffers.themeColors.push(color.r, color.g, color.b);
  return buffers.positions.length / 3 - 1;
}

function addFaceGrid(
  buffers: VertexBuffers,
  identity: number,
  yOffset: number,
  surfaceSign: 1 | -1,
) {
  const rowStart = buffers.positions.length / 3;
  const halfWidth = 0.205;
  const halfThickness = 0.022;
  for (let uIndex = 0; uIndex <= LENGTH_SEGMENTS; uIndex += 1) {
    const u = uIndex / LENGTH_SEGMENTS;
    const x = (u - 0.5) * 3.45;
    const phase = (u - 0.5) * Math.PI;
    const z = 0.34 * Math.cos(phase) - 0.12;
    const dzdu = -0.34 * Math.PI * Math.sin(phase);
    const tangent = new THREE.Vector3(3.45, 0, dzdu).normalize();
    const normal = new THREE.Vector3(-tangent.z, 0, tangent.x)
      .normalize()
      .multiplyScalar(surfaceSign);
    for (let vIndex = 0; vIndex <= WIDTH_SEGMENTS; vIndex += 1) {
      const localV = vIndex / WIDTH_SEGMENTS;
      const across = (localV - 0.5) * halfWidth * 2;
      const position = new THREE.Vector3(
        x,
        yOffset + across,
        z,
      ).addScaledVector(normal, halfThickness);
      pushVertex(buffers, identity, position, normal, u, localV);
    }
  }

  const stride = WIDTH_SEGMENTS + 1;
  for (let uIndex = 0; uIndex < LENGTH_SEGMENTS; uIndex += 1) {
    for (let vIndex = 0; vIndex < WIDTH_SEGMENTS; vIndex += 1) {
      const a = rowStart + uIndex * stride + vIndex;
      const b = a + stride;
      const c = b + 1;
      const d = a + 1;
      if (surfaceSign > 0) {
        buffers.indices.push(a, b, d, b, c, d);
      } else {
        buffers.indices.push(a, d, b, b, d, c);
      }
    }
  }
}

function addEdge(
  buffers: VertexBuffers,
  identity: number,
  yOffset: number,
  localV: 0 | 1,
) {
  const start = buffers.positions.length / 3;
  const halfWidth = 0.205;
  const halfThickness = 0.022;
  for (let uIndex = 0; uIndex <= LENGTH_SEGMENTS; uIndex += 1) {
    const u = uIndex / LENGTH_SEGMENTS;
    const x = (u - 0.5) * 3.45;
    const phase = (u - 0.5) * Math.PI;
    const z = 0.34 * Math.cos(phase) - 0.12;
    const dzdu = -0.34 * Math.PI * Math.sin(phase);
    const tangent = new THREE.Vector3(3.45, 0, dzdu).normalize();
    const faceNormal = new THREE.Vector3(-tangent.z, 0, tangent.x).normalize();
    const edgeNormal = new THREE.Vector3(0, localV === 0 ? -1 : 1, 0);
    for (const surfaceSign of [-1, 1]) {
      const position = new THREE.Vector3(
        x,
        yOffset + (localV - 0.5) * halfWidth * 2,
        z,
      ).addScaledVector(faceNormal, halfThickness * surfaceSign);
      pushVertex(
        buffers,
        identity,
        position,
        edgeNormal,
        u,
        surfaceSign < 0 ? 0 : 1,
      );
    }
  }
  for (let uIndex = 0; uIndex < LENGTH_SEGMENTS; uIndex += 1) {
    const a = start + uIndex * 2;
    const b = a + 2;
    const c = b + 1;
    const d = a + 1;
    const flip = localV === 0;
    buffers.indices.push(
      ...(flip ? [a, d, b, b, d, c] : [a, b, d, b, c, d]),
    );
  }
}

export function createIdentitySwatchGeometry() {
  const buffers: VertexBuffers = {
    positions: [],
    normals: [],
    uvs: [],
    identities: [],
    bandV: [],
    themeColors: [],
    indices: [],
  };
  const spacing = 0.63;
  for (let identity = 0; identity < SWATCH_COUNT; identity += 1) {
    const yOffset = (2 - identity) * spacing;
    addFaceGrid(buffers, identity, yOffset, 1);
    addFaceGrid(buffers, identity, yOffset, -1);
    addEdge(buffers, identity, yOffset, 0);
    addEdge(buffers, identity, yOffset, 1);
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(buffers.positions, 3),
  );
  geometry.setAttribute(
    "normal",
    new THREE.Float32BufferAttribute(buffers.normals, 3),
  );
  geometry.setAttribute(
    "uv",
    new THREE.Float32BufferAttribute(buffers.uvs, 2),
  );
  geometry.setAttribute(
    "aIdentity",
    new THREE.Float32BufferAttribute(buffers.identities, 1),
  );
  geometry.setAttribute(
    "aBandV",
    new THREE.Float32BufferAttribute(buffers.bandV, 1),
  );
  geometry.setAttribute(
    "aThemeColor",
    new THREE.Float32BufferAttribute(buffers.themeColors, 3),
  );
  geometry.setIndex(buffers.indices);
  geometry.computeBoundingSphere();
  geometry.userData.identitySwatchCount = SWATCH_COUNT;
  geometry.userData.geometryContract =
    "Independent lab swatches — formal Geometry v1.1 untouched";
  return geometry;
}
