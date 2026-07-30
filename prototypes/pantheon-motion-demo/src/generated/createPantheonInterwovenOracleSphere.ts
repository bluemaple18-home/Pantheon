import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { BokehPass } from 'three/examples/jsm/postprocessing/BokehPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

export type ProceduralModelOptions = {
  wireframe?: boolean;
  castShadow?: boolean;
  receiveShadow?: boolean;
  textureSize?: number;
  textureAnisotropy?: number;
  qualityPriority?: 'reference-fidelity' | 'balanced';
};

export type ProceduralModelRuntime = {
  nodes: Record<string, THREE.Object3D>;
  meshes: Record<string, THREE.Mesh>;
  sockets: Record<string, THREE.Object3D>;
  colliders: Record<string, unknown>;
  destructionGroups: Record<string, THREE.Object3D[]>;
};

type SculptMaterialSpec = Record<string, any>;

function hashString(value: string): number {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function readLayerNumber(value: unknown, keys: string[], fallback: number): number {
  if (typeof value === 'number') return value;
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    for (const key of keys) {
      if (typeof record[key] === 'number') return record[key] as number;
    }
  }
  return fallback;
}

function hexToRgb(hex: string): [number, number, number] {
  const normalized = /^#[0-9a-f]{3}$/i.test(hex)
    ? '#' + hex.slice(1).split('').map((part) => part + part).join('')
    : hex;
  const value = /^#[0-9a-f]{6}$/i.test(normalized) ? Number.parseInt(normalized.slice(1), 16) : 0x8a7a5f;
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

function materialPalette(spec: SculptMaterialSpec): string[] {
  const palette = spec.colorVariation?.palette;
  if (Array.isArray(palette) && palette.length > 0) return palette.filter((value) => typeof value === 'string');
  const secondary = spec.albedo?.secondary;
  const colors = [spec.baseColor ?? spec.color ?? spec.albedo?.dominant, ...(Array.isArray(secondary) ? secondary : [])];
  return colors.filter((value): value is string => typeof value === 'string' && value.startsWith('#'));
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

function smoothCurve(value: number): number {
  return value * value * (3 - 2 * value);
}

function periodicHash(x: number, y: number, seed: number, periodX: number, periodY: number): number {
  const wrappedX = ((x % periodX) + periodX) % periodX;
  const wrappedY = ((y % periodY) + periodY) % periodY;
  let value = Math.imul(wrappedX + seed * 17, 374761393) ^ Math.imul(wrappedY + seed * 31, 668265263);
  value = Math.imul(value ^ (value >>> 13), 1274126177);
  return ((value ^ (value >>> 16)) >>> 0) / 4294967295;
}

function periodicValueNoise(u: number, v: number, seed: number, periodX: number, periodY: number): number {
  const x = u * periodX;
  const y = v * periodY;
  const x0 = Math.floor(x);
  const y0 = Math.floor(y);
  const tx = smoothCurve(x - x0);
  const ty = smoothCurve(y - y0);
  const a = periodicHash(x0, y0, seed, periodX, periodY);
  const b = periodicHash(x0 + 1, y0, seed, periodX, periodY);
  const c = periodicHash(x0, y0 + 1, seed, periodX, periodY);
  const d = periodicHash(x0 + 1, y0 + 1, seed, periodX, periodY);
  return THREE.MathUtils.lerp(THREE.MathUtils.lerp(a, b, tx), THREE.MathUtils.lerp(c, d, tx), ty);
}

type SurfaceBand = {
  frequency: number;
  amplitude: number;
  stretchX: number;
  stretchY: number;
  ridge: boolean;
};

function surfaceBands(spec: SculptMaterialSpec): SurfaceBand[] {
  const source = Array.isArray(spec.surfaceFrequencyBands) ? spec.surfaceFrequencyBands : [];
  const parsed = source.flatMap((item: unknown) => {
    if (!item || typeof item !== 'object') return [];
    const band = item as Record<string, unknown>;
    const frequency = typeof band.frequency === 'number' ? band.frequency : 0;
    const amplitude = typeof band.amplitude === 'number' ? band.amplitude : 0;
    if (frequency <= 0 || amplitude <= 0) return [];
    const stretch = Array.isArray(band.stretch) ? band.stretch : [1, 1];
    const description = `${String(band.pattern ?? '')} ${String(band.role ?? '')}`.toLowerCase();
    return [{
      frequency,
      amplitude,
      stretchX: typeof stretch[0] === 'number' ? Math.max(0.1, stretch[0]) : 1,
      stretchY: typeof stretch[1] === 'number' ? Math.max(0.1, stretch[1]) : 1,
      ridge: /(ridge|groove|grain|fiber|striated|crack)/.test(description),
    }];
  });
  return parsed.length > 0 ? parsed : [
    { frequency: 2, amplitude: 0.42, stretchX: 1, stretchY: 1, ridge: false },
    { frequency: 12, amplitude: 0.22, stretchX: 1, stretchY: 1, ridge: false },
    { frequency: 56, amplitude: 0.08, stretchX: 1, stretchY: 1, ridge: false },
  ];
}

function sampleSurface(u: number, v: number, bands: SurfaceBand[], seed: number): number {
  let value = 0;
  let weight = 0;
  for (let index = 0; index < bands.length; index += 1) {
    const band = bands[index];
    const periodX = Math.max(1, Math.round(band.frequency * band.stretchX));
    const periodY = Math.max(1, Math.round(band.frequency * band.stretchY));
    let sample = periodicValueNoise(u, v, seed + index * 1013, periodX, periodY);
    if (band.ridge) sample = 1 - Math.abs(sample * 2 - 1);
    value += sample * band.amplitude;
    weight += band.amplitude;
  }
  return weight > 0 ? clamp01(value / weight) : 0.5;
}

function mixPalette(colors: [number, number, number][], value: number): [number, number, number] {
  if (colors.length === 1) return colors[0];
  const scaled = clamp01(value) * (colors.length - 1);
  const index = Math.min(colors.length - 2, Math.floor(scaled));
  const mix = scaled - index;
  const a = colors[index];
  const b = colors[index + 1];
  return [
    Math.round(THREE.MathUtils.lerp(a[0], b[0], mix)),
    Math.round(THREE.MathUtils.lerp(a[1], b[1], mix)),
    Math.round(THREE.MathUtils.lerp(a[2], b[2], mix)),
  ];
}

type ColorGradientStop = { offset: number; color: string };
type ColorGradientSpec = {
  type: 'linear' | 'radial';
  axis: [number, number];
  stops: ColorGradientStop[];
};

function parseRgba(value: string): [number, number, number] {
  const match = /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/.exec(value);
  if (!match) return [138, 122, 95];
  return [Number(match[1]), Number(match[2]), Number(match[3])];
}

// Analytical per-pixel gradient sample. The extraction schema's colorGradient carries
// exact rgba(...) stop colors (see extract_part_color_recipe.py), so this samples the
// same trend directly in JS math rather than round-tripping through a Canvas 2D
// createLinearGradient/createRadialGradient object — same visual result, and it composes
// directly with the existing noise/height-correlated colorVariation blend below.
function sampleColorGradient(gradient: ColorGradientSpec, u: number, v: number): [number, number, number] {
  const stops = gradient.stops.length >= 2 ? gradient.stops : [{ offset: 0, color: 'rgba(138,122,95,1)' }, { offset: 1, color: 'rgba(138,122,95,1)' }];
  let t: number;
  if (gradient.type === 'radial') {
    const [cx, cy] = gradient.axis;
    const dx = u - cx;
    const dy = v - cy;
    const maxRadius = Math.max(0.001, Math.hypot(Math.max(cx, 1 - cx), Math.max(cy, 1 - cy)));
    t = clamp01(Math.hypot(dx, dy) / maxRadius);
  } else {
    const [ax, ay] = gradient.axis;
    const projection = (u - 0.5) * ax + (v - 0.5) * ay;
    const maxProjection = 0.5 * (Math.abs(ax) + Math.abs(ay)) || 0.5;
    t = clamp01(projection / maxProjection + 0.5);
  }
  const scaled = t * (stops.length - 1);
  const index = Math.min(stops.length - 2, Math.max(0, Math.floor(scaled)));
  const mix = scaled - index;
  const a = parseRgba(stops[index].color);
  const b = parseRgba(stops[index + 1].color);
  return [
    THREE.MathUtils.lerp(a[0], b[0], mix),
    THREE.MathUtils.lerp(a[1], b[1], mix),
    THREE.MathUtils.lerp(a[2], b[2], mix),
  ];
}

function writePixel(data: Uint8ClampedArray, offset: number, red: number, green: number, blue: number): void {
  data[offset] = Math.max(0, Math.min(255, Math.round(red)));
  data[offset + 1] = Math.max(0, Math.min(255, Math.round(green)));
  data[offset + 2] = Math.max(0, Math.min(255, Math.round(blue)));
  data[offset + 3] = 255;
}

function makeCanvas(size: number): HTMLCanvasElement {
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  return canvas;
}

function createMapTexture(
  canvas: HTMLCanvasElement,
  colorSpace: THREE.ColorSpace,
  spec: SculptMaterialSpec,
  options: ProceduralModelOptions,
): THREE.CanvasTexture {
  const texture = new THREE.CanvasTexture(canvas);
  const projection = spec.textureProjection && typeof spec.textureProjection === 'object' ? spec.textureProjection : {};
  const repeat = Array.isArray(projection.repeat) ? projection.repeat : [2, 2];
  texture.colorSpace = colorSpace;
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(
    typeof repeat[0] === 'number' ? repeat[0] : 2,
    typeof repeat[1] === 'number' ? repeat[1] : 2,
  );
  texture.anisotropy = Math.max(1, Math.round(options.textureAnisotropy ?? projection.anisotropy ?? 8));
  texture.needsUpdate = true;
  return texture;
}

type ProceduralTextureSet = {
  albedo: THREE.Texture;
  roughness: THREE.Texture;
  height: THREE.Texture;
  normal: THREE.Texture;
  ao: THREE.Texture;
  source: 'reference-pixel-extraction' | 'procedural';
};

function referenceMapUrl(spec: SculptMaterialSpec, channel: string): string | null {
  const reference = spec.referencePbr;
  if (!reference || typeof reference !== 'object') return null;
  if (reference.usable === false) return null;
  const confidence = typeof reference.confidence === 'number'
    ? reference.confidence
    : (typeof reference.estimatedFidelity === 'number' ? reference.estimatedFidelity : 0);
  const threshold = typeof reference.targetThreshold === 'number' ? reference.targetThreshold : 0.7;
  if (confidence < threshold) return null;
  const maps = reference.maps;
  if (!maps || typeof maps !== 'object') return null;
  const map = (maps as Record<string, unknown>)[channel];
  if (!map || typeof map !== 'object') return null;
  const record = map as Record<string, unknown>;
  const url = typeof record.url === 'string' && record.url.trim() ? record.url : record.path;
  return typeof url === 'string' && url.trim() ? url : null;
}

function createLoadedMapTexture(
  url: string,
  colorSpace: THREE.ColorSpace,
  spec: SculptMaterialSpec,
  options: ProceduralModelOptions,
): THREE.Texture {
  const texture = new THREE.TextureLoader().load(url);
  const projection = spec.textureProjection && typeof spec.textureProjection === 'object' ? spec.textureProjection : {};
  const repeat = Array.isArray(projection.repeat) ? projection.repeat : [1, 1];
  texture.colorSpace = colorSpace;
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(
    typeof repeat[0] === 'number' ? repeat[0] : 1,
    typeof repeat[1] === 'number' ? repeat[1] : 1,
  );
  texture.anisotropy = Math.max(1, Math.round(options.textureAnisotropy ?? projection.anisotropy ?? 8));
  texture.needsUpdate = true;
  return texture;
}

function makeReferenceTextureSet(spec: SculptMaterialSpec, options: ProceduralModelOptions): ProceduralTextureSet | null {
  const albedo = referenceMapUrl(spec, 'albedo');
  const roughness = referenceMapUrl(spec, 'roughness');
  const height = referenceMapUrl(spec, 'height');
  const normal = referenceMapUrl(spec, 'normal');
  const ao = referenceMapUrl(spec, 'ao');
  if (!albedo || !roughness || !height || !normal || !ao) return null;
  return {
    albedo: createLoadedMapTexture(albedo, THREE.SRGBColorSpace, spec, options),
    roughness: createLoadedMapTexture(roughness, THREE.NoColorSpace, spec, options),
    height: createLoadedMapTexture(height, THREE.NoColorSpace, spec, options),
    normal: createLoadedMapTexture(normal, THREE.NoColorSpace, spec, options),
    ao: createLoadedMapTexture(ao, THREE.NoColorSpace, spec, options),
    source: 'reference-pixel-extraction',
  };
}

function makeProceduralTextureSet(
  id: string,
  spec: SculptMaterialSpec,
  options: ProceduralModelOptions,
): ProceduralTextureSet | null {
  if (typeof document === 'undefined') return null;
  const qualityFirst = (options.qualityPriority ?? 'reference-fidelity') === 'reference-fidelity';
  const requested = options.textureSize ?? spec.textureResolution;
  const requestedSize = typeof requested === 'number' && Number.isFinite(requested)
    ? requested
    : (qualityFirst ? 1024 : 512);
  const size = Math.max(256, Math.min(2048, 2 ** Math.round(Math.log2(requestedSize))));
  const canvases = {
    albedo: makeCanvas(size),
    roughness: makeCanvas(size),
    height: makeCanvas(size),
    normal: makeCanvas(size),
    ao: makeCanvas(size),
  };
  const contexts = {
    albedo: canvases.albedo.getContext('2d'),
    roughness: canvases.roughness.getContext('2d'),
    height: canvases.height.getContext('2d'),
    normal: canvases.normal.getContext('2d'),
    ao: canvases.ao.getContext('2d'),
  };
  if (!contexts.albedo || !contexts.roughness || !contexts.height || !contexts.normal || !contexts.ao) return null;
  const images = {
    albedo: contexts.albedo.createImageData(size, size),
    roughness: contexts.roughness.createImageData(size, size),
    height: contexts.height.createImageData(size, size),
    normal: contexts.normal.createImageData(size, size),
    ao: contexts.ao.createImageData(size, size),
  };
  const seed = hashString(id);
  const bands = surfaceBands(spec);
  const heightField = new Float32Array(size * size);
  const roughnessField = new Float32Array(size * size);
  const palette = materialPalette(spec);
  const fallback = typeof spec.baseColor === 'string' ? spec.baseColor : '#8A7A5F';
  const colors = (palette.length >= 2 ? palette : [fallback, '#6E614B', '#A08F70']).map(hexToRgb);
  const baseRoughness = clamp01(readLayerNumber(spec.roughness, ['base'], 0.76));
  const roughnessVariation = clamp01(readLayerNumber(spec.roughness, ['variation'], 0.18));
  const colorAmplitude = clamp01(readLayerNumber(spec.colorVariation, ['amplitude', 'variation'], 0.18));
  const heightCorrelation = clamp01(readLayerNumber(spec.colorVariation, ['heightCorrelation'], 0.3));
  const colorGradient: ColorGradientSpec | undefined = spec.colorGradient;
  for (let y = 0; y < size; y += 1) {
    const v = y / size;
    for (let x = 0; x < size; x += 1) {
      const u = x / size;
      const index = y * size + x;
      const height = sampleSurface(u, v, bands, seed + 101);
      const roughNoise = sampleSurface(u, v, bands, seed + 7001);
      const colorNoise = sampleSurface(u, v, bands, seed + 15013);
      heightField[index] = height;
      roughnessField[index] = clamp01(baseRoughness + (roughNoise - 0.5) * roughnessVariation * 2);
      let color: [number, number, number];
      if (colorGradient) {
        // Evidence-derived spatial gradient (Plan 1.3 Workstream C) takes priority
        // over the noise-based palette blend below — it is a measured trend, not a guess.
        color = sampleColorGradient(colorGradient, u, v);
      } else {
        const paletteValue = clamp01(
          0.5 + (colorNoise - 0.5) * colorAmplitude * 2 + (height - 0.5) * heightCorrelation
        );
        color = mixPalette(colors, paletteValue);
      }
      writePixel(images.albedo.data, index * 4, color[0], color[1], color[2]);
    }
  }
  const normalStrength = Math.max(0.05, readLayerNumber(spec.normal, ['strength', 'amplitude'], 0.35));
  const aoStrength = clamp01(readLayerNumber(spec.ambientOcclusion, ['cavityStrength', 'strength'], 0.35));
  for (let y = 0; y < size; y += 1) {
    const up = ((y - 1 + size) % size) * size;
    const down = ((y + 1) % size) * size;
    for (let x = 0; x < size; x += 1) {
      const left = (x - 1 + size) % size;
      const right = (x + 1) % size;
      const index = y * size + x;
      const center = heightField[index];
      const dx = (heightField[y * size + right] - heightField[y * size + left]) * normalStrength * 6;
      const dy = (heightField[down + x] - heightField[up + x]) * normalStrength * 6;
      const inverseLength = 1 / Math.sqrt(dx * dx + dy * dy + 1);
      const normalX = -dx * inverseLength;
      const normalY = -dy * inverseLength;
      const normalZ = inverseLength;
      const neighborAverage = (
        heightField[y * size + left] + heightField[y * size + right]
        + heightField[up + x] + heightField[down + x]
      ) * 0.25;
      const cavity = Math.max(0, neighborAverage - center);
      const ao = clamp01(1 - aoStrength * (cavity * 12 + (1 - center) * 0.16));
      const offset = index * 4;
      const heightByte = center * 255;
      const roughnessByte = roughnessField[index] * 255;
      writePixel(images.height.data, offset, heightByte, heightByte, heightByte);
      writePixel(images.roughness.data, offset, roughnessByte, roughnessByte, roughnessByte);
      writePixel(
        images.normal.data, offset,
        (normalX * 0.5 + 0.5) * 255,
        (normalY * 0.5 + 0.5) * 255,
        (normalZ * 0.5 + 0.5) * 255,
      );
      writePixel(images.ao.data, offset, ao * 255, ao * 255, ao * 255);
    }
  }
  contexts.albedo.putImageData(images.albedo, 0, 0);
  contexts.roughness.putImageData(images.roughness, 0, 0);
  contexts.height.putImageData(images.height, 0, 0);
  contexts.normal.putImageData(images.normal, 0, 0);
  contexts.ao.putImageData(images.ao, 0, 0);
  return {
    albedo: createMapTexture(canvases.albedo, THREE.SRGBColorSpace, spec, options),
    roughness: createMapTexture(canvases.roughness, THREE.NoColorSpace, spec, options),
    height: createMapTexture(canvases.height, THREE.NoColorSpace, spec, options),
    normal: createMapTexture(canvases.normal, THREE.NoColorSpace, spec, options),
    ao: createMapTexture(canvases.ao, THREE.NoColorSpace, spec, options),
    source: 'procedural',
  };
}

function createSculptMaterial(id: string, spec: SculptMaterialSpec, options: ProceduralModelOptions): THREE.MeshPhysicalMaterial {
  const textures = makeReferenceTextureSet(spec, options) ?? makeProceduralTextureSet(id, spec, options);
  const material = new THREE.MeshPhysicalMaterial({
    color: textures ? 0xffffff : new THREE.Color(typeof spec.baseColor === 'string' ? spec.baseColor : '#8A7A5F'),
    roughness: textures ? 1 : clamp01(readLayerNumber(spec.roughness, ['base'], 0.76)),
    metalness: clamp01(readLayerNumber(spec.metalness, ['base'], 0.0)),
    clearcoat: clamp01(readLayerNumber(spec.clearcoat, ['base', 'amount'], 0)),
    clearcoatRoughness: clamp01(readLayerNumber(spec.clearcoatRoughness, ['base'], 0.25)),
    transmission: clamp01(readLayerNumber(spec.transmission, ['base', 'amount'], 0)),
    ior: Math.max(1, readLayerNumber(spec.ior, ['base', 'value'], 1.5)),
    thickness: Math.max(0, readLayerNumber(spec.thickness, ['base', 'amount'], 0)),
    attenuationDistance: Math.max(0.001, readLayerNumber(spec.attenuationDistance, ['base', 'value'], Infinity)),
    attenuationColor: new THREE.Color(typeof spec.attenuationColor === 'string' ? spec.attenuationColor : '#ffffff'),
    sheen: clamp01(readLayerNumber(spec.sheen, ['base', 'amount'], 0)),
    sheenColor: new THREE.Color(typeof spec.sheenColor === 'string' ? spec.sheenColor : '#ffffff'),
    sheenRoughness: clamp01(readLayerNumber(spec.sheenRoughness, ['base'], 1.0)),
    iridescence: clamp01(readLayerNumber(spec.iridescence, ['base', 'amount'], 0)),
    iridescenceIOR: Math.max(1, readLayerNumber(spec.iridescenceIOR, ['base', 'value'], 1.3)),
    anisotropy: clamp01(readLayerNumber(spec.anisotropy, ['base', 'amount'], 0)),
    anisotropyRotation: readLayerNumber(spec.anisotropy, ['rotation'], 0),
    specularIntensity: clamp01(readLayerNumber(spec.specularIntensity, ['base'], 1.0)),
    specularColor: new THREE.Color(typeof spec.specularColor === 'string' ? spec.specularColor : '#ffffff'),
    emissive: new THREE.Color(typeof spec.emissive === 'string' ? spec.emissive : '#000000'),
    emissiveIntensity: Math.max(0, readLayerNumber(spec.emissiveIntensity, ['base'], 1.0)),
    opacity: clamp01(readLayerNumber(spec.opacity, ['base'], 1)),
    transparent: readLayerNumber(spec.transmission, ['base', 'amount'], 0) > 0 || readLayerNumber(spec.opacity, ['base'], 1) < 1,
    alphaTest: Math.max(0, readLayerNumber(spec.alpha, ['cutoff', 'alphaTest'], 0)),
    wireframe: options.wireframe ?? false,
    side: spec.doubleSided === true ? THREE.DoubleSide : THREE.FrontSide,
  });
  if (textures) {
    material.map = textures.albedo;
    material.roughnessMap = textures.roughness;
    material.normalMap = textures.normal;
    material.normalScale.setScalar(Math.max(0.05, readLayerNumber(spec.normal, ['strength', 'amplitude'], 0.35)));
    material.aoMap = textures.ao;
    material.aoMap.channel = 0;
    material.aoMapIntensity = readLayerNumber(spec.ambientOcclusion, ['cavityStrength', 'strength'], 0.35);
    const bumpScale = Math.max(0, readLayerNumber(spec.bump, ['amplitude', 'strength'], 0));
    if (bumpScale > 0) {
      material.bumpMap = textures.height;
      material.bumpScale = bumpScale;
    }
    const displacementScale = Math.max(0, readLayerNumber(spec.displacement, ['amplitude', 'strength'], 0));
    if (displacementScale > 0) {
      material.displacementMap = textures.height;
      material.displacementScale = displacementScale;
      material.displacementBias = -displacementScale * 0.5;
    }
  }
  material.envMapIntensity = readLayerNumber(spec, ['envMapIntensity'], 0.8);
  material.userData.sculptMaterial = spec;
  material.userData.proceduralMapsIndependent = true;
  material.userData.pbrTextureSource = textures?.source ?? 'flat-fallback';
  material.userData.referencePbr = spec.referencePbr ?? null;
  material.needsUpdate = true;
  return material;
}

type AttachmentEndpoint = {
  start: THREE.Vector3;
  midpoint: THREE.Vector3;
  quaternion: THREE.Quaternion;
  length: number;
  baseRadius: number;
  endRadius: number;
};

function readVector3(value: unknown, fallback: [number, number, number]): THREE.Vector3 {
  if (Array.isArray(value) && value.length === 3 && value.every((item) => typeof item === 'number')) {
    return new THREE.Vector3(value[0], value[1], value[2]);
  }
  return new THREE.Vector3(fallback[0], fallback[1], fallback[2]);
}

function readNumber(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function makeAttachmentEndpoint(attachment: unknown): AttachmentEndpoint | null {
  if (!attachment || typeof attachment !== 'object') return null;
  const record = attachment as Record<string, unknown>;
  const start = readVector3(record.localStart, [0, 0, 0]);
  const end = readVector3(record.localEnd, [0, 1, 0]);
  const delta = end.clone().sub(start);
  const length = delta.length();
  if (length <= 0.0001) return null;
  const direction = delta.clone().normalize();
  const quaternion = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
  const baseRadius = Math.max(0.005, readNumber(record.baseRadius, 0.06));
  const endRadius = Math.max(0.003, readNumber(record.endRadius, baseRadius * 0.55));
  return {
    start,
    midpoint: delta.multiplyScalar(0.5),
    quaternion,
    length,
    baseRadius,
    endRadius,
  };
}

// Generated from ObjectSculptSpec target: Pantheon interwoven oracle sphere
// Sculpt build pass: optimization-pass
// This factory is intentionally pass-gated. Finish browser screenshot review before unlocking deeper passes.
export function createPantheonInterwovenOracleSphereModel(options: ProceduralModelOptions = {}): THREE.Group {
  const root = new THREE.Group();
  root.name = "Pantheon interwoven oracle sphere";
  root.userData.reconstructionEvidence = {"itemFamily": null, "subtype": null, "componentAdapter": null, "route": null, "exactnessTier": null, "referenceCamera": {"solved": false, "fovDegrees": 32, "aspect": 1, "orientation": {"yaw": 0, "pitch": 0, "roll": 0}, "positionHint": [0, 0, 7], "note": "Heuristic camera matched by browser comparison; source image does not provide calibration."}, "approximationNotes": []};

  const materialMap: Record<string, THREE.Material> = {};
  materialMap["gold-band"] = createSculptMaterial(
    "gold-band",
    {"id": "gold-band", "name": "Warm brushed gold", "type": "physical", "shaderModel": "MeshStandardMaterial / PBR approximation", "baseColor": "#C99B4F", "color": "#C99B4F", "albedo": {"dominant": "#C99B4F", "secondary": ["#F0D18B", "#2D2626"], "samplingNotes": "Palette is matched by host vision to visible reference zones."}, "colorVariation": {"palette": ["#C99B4F", "#F0D18B"], "pattern": "directional brushed gradient", "amplitude": 0.12, "heightCorrelation": 0.2}, "textureResolution": 1024, "textureProjection": {"mode": "uv", "repeat": [2, 2], "anisotropy": 8, "texelDensityIntent": "Preserve stable world/object-scale detail; do not stretch micro detail with component scale."}, "surfaceFrequencyBands": [{"id": "macro", "frequency": 2, "amplitude": 0.52, "role": "reference-derived broad albedo and height breakup"}, {"id": "meso", "frequency": 14, "amplitude": 0.35, "role": "reference-derived cracks, ridges, pores, grain, or leaf clusters"}, {"id": "micro", "frequency": 72, "amplitude": 0.14, "role": "reference-derived micro highlight breakup under grazing light"}], "roughness": {"base": 0.32, "variation": 0.1, "map": "reference-independent-roughness", "localResponse": "lower on bevels and raised glyphs"}, "metalness": {"base": 0.96, "variation": 0.04}, "normal": {"pattern": "directional-brush", "strength": 0.16, "scale": 72, "space": "tangent"}, "bump": {"pattern": "rune-relief", "amplitude": 0.018, "scale": 1}, "displacement": {"pattern": "none", "amplitude": 0, "scale": 1, "silhouetteAffects": false}, "ambientOcclusion": {"cavityStrength": 0.38, "contactShadowBias": 0.42, "notes": "Preserve depth at crossings and inner faces."}, "wear": {"edgeWear": 0.12, "scratches": ["subtle longitudinal hairlines"], "chips": []}, "dirt": {"amount": 0.02, "cavityBias": 0.35, "color": "#2D2626"}, "localOverrides": [{"id": "gold-band-bevel-gloss", "mask": "bevel", "roughness": 0.16, "evidenceRefs": ["full-object"]}, {"id": "gold-band-rune-relief", "mask": "rune-glyphs", "roughness": 0.18, "metalness": 1, "evidenceRefs": ["full-object"]}], "shaderNotes": ["Prefer MeshPhysicalMaterial when clearcoat, sheen, transmission, or thin-surface response is observed; otherwise use MeshStandardMaterial-compatible PBR channels.", "Generate albedo, roughness, height/normal, and AO independently; never alias albedo into roughness.", "Use normal/bump/displacement only when they map to observed surface relief.", "Use displacement geometry when the observed relief changes the close-up silhouette; texture-only relief is insufficient there.", "Reference-derived maps are estimates from image pixels; verify with neutral, grazing, and reference-matched renders.", "Do not treat baked image shadows as final albedo; rerun extraction with a tighter material crop if highlights/shadows pollute the maps."], "notes": "Reference-derived full-image PBR is treated as evidence, while final per-band color is host-observed and procedurally authored.", "referencePbr": {"version": "1.0", "sourceImage": "/Users/mattkuo/Documents/Pantheon/app/web/static/pantheon-oracle-sphere-transparent.png", "extractor": "stage1_intake/extract_pbr_evidence.py", "method": "single-image pixel evidence with de-lighting estimate; not photogrammetry", "usable": true, "verdict": "pass", "confidence": 0.86, "estimatedFidelity": 0.86, "targetThreshold": 0.7, "hardLimit": "A single image cannot uniquely recover true albedo/roughness/normal/AO; maps are reference-derived estimates.", "maps": {"albedo": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_albedo.png", "url": "base_albedo.png", "channel": "albedo", "source": "reference-pixel-extraction"}, "roughness": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_roughness.png", "url": "base_roughness.png", "channel": "roughness", "source": "reference-pixel-extraction"}, "height": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_height.png", "url": "base_height.png", "channel": "height", "source": "reference-pixel-extraction"}, "normal": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_normal.png", "url": "base_normal.png", "channel": "normal", "source": "reference-pixel-extraction"}, "ao": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_ao.png", "url": "base_ao.png", "channel": "ao", "source": "reference-pixel-extraction"}}, "diagnostics": {"sourceWidth": 1254, "sourceHeight": 1254, "mapSize": 512, "cropBBoxPixels": {"x": 47, "y": 34, "width": 1120, "height": 1193}, "mask": {"backgroundColor": "#FFFFFF", "backgroundNoise": 0, "transparentPixelFraction": 0.6836, "foregroundCoverage": 0.3472}, "mapStats": {"valueRange": 0.7192, "heightP90Gradient": 0.09639, "roughnessBase": 0.716, "roughnessVariation": 0.191, "normalStrength": 0.269, "blurRadius": 10}, "palette": ["#A38C70", "#524A44", "#7E644E", "#E5D6C2", "#C9AF95", "#2D2626"]}, "warnings": ["single-image inverse rendering cannot prove true physical PBR; confidence is capped"]}, "clearcoat": {"base": 0.24, "roughness": 0.28}},
    options
  );
  materialMap["teal-band"] = createSculptMaterial(
    "teal-band",
    {"id": "teal-band", "name": "Muted jade metal", "type": "physical", "shaderModel": "MeshStandardMaterial / PBR approximation", "baseColor": "#497F77", "color": "#497F77", "albedo": {"dominant": "#497F77", "secondary": ["#91B7A5", "#2D2626"], "samplingNotes": "Palette is matched by host vision to visible reference zones."}, "colorVariation": {"palette": ["#497F77", "#91B7A5"], "pattern": "directional brushed gradient", "amplitude": 0.12, "heightCorrelation": 0.2}, "textureResolution": 1024, "textureProjection": {"mode": "uv", "repeat": [2, 2], "anisotropy": 8, "texelDensityIntent": "Preserve stable world/object-scale detail; do not stretch micro detail with component scale."}, "surfaceFrequencyBands": [{"id": "macro", "frequency": 2, "amplitude": 0.52, "role": "reference-derived broad albedo and height breakup"}, {"id": "meso", "frequency": 14, "amplitude": 0.35, "role": "reference-derived cracks, ridges, pores, grain, or leaf clusters"}, {"id": "micro", "frequency": 72, "amplitude": 0.14, "role": "reference-derived micro highlight breakup under grazing light"}], "roughness": {"base": 0.38, "variation": 0.1, "map": "reference-independent-roughness", "localResponse": "lower on bevels and raised glyphs"}, "metalness": {"base": 0.9, "variation": 0.04}, "normal": {"pattern": "directional-brush", "strength": 0.16, "scale": 72, "space": "tangent"}, "bump": {"pattern": "rune-relief", "amplitude": 0.018, "scale": 1}, "displacement": {"pattern": "none", "amplitude": 0, "scale": 1, "silhouetteAffects": false}, "ambientOcclusion": {"cavityStrength": 0.38, "contactShadowBias": 0.42, "notes": "Preserve depth at crossings and inner faces."}, "wear": {"edgeWear": 0.12, "scratches": ["subtle longitudinal hairlines"], "chips": []}, "dirt": {"amount": 0.02, "cavityBias": 0.35, "color": "#2D2626"}, "localOverrides": [{"id": "teal-band-bevel-gloss", "mask": "bevel", "roughness": 0.22, "evidenceRefs": ["full-object"]}, {"id": "teal-band-rune-relief", "mask": "rune-glyphs", "roughness": 0.18, "metalness": 1, "evidenceRefs": ["full-object"]}], "shaderNotes": ["Prefer MeshPhysicalMaterial when clearcoat, sheen, transmission, or thin-surface response is observed; otherwise use MeshStandardMaterial-compatible PBR channels.", "Generate albedo, roughness, height/normal, and AO independently; never alias albedo into roughness.", "Use normal/bump/displacement only when they map to observed surface relief.", "Use displacement geometry when the observed relief changes the close-up silhouette; texture-only relief is insufficient there.", "Reference-derived maps are estimates from image pixels; verify with neutral, grazing, and reference-matched renders.", "Do not treat baked image shadows as final albedo; rerun extraction with a tighter material crop if highlights/shadows pollute the maps."], "notes": "Reference-derived full-image PBR is treated as evidence, while final per-band color is host-observed and procedurally authored.", "referencePbr": {"version": "1.0", "sourceImage": "/Users/mattkuo/Documents/Pantheon/app/web/static/pantheon-oracle-sphere-transparent.png", "extractor": "stage1_intake/extract_pbr_evidence.py", "method": "single-image pixel evidence with de-lighting estimate; not photogrammetry", "usable": true, "verdict": "pass", "confidence": 0.86, "estimatedFidelity": 0.86, "targetThreshold": 0.7, "hardLimit": "A single image cannot uniquely recover true albedo/roughness/normal/AO; maps are reference-derived estimates.", "maps": {"albedo": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_albedo.png", "url": "base_albedo.png", "channel": "albedo", "source": "reference-pixel-extraction"}, "roughness": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_roughness.png", "url": "base_roughness.png", "channel": "roughness", "source": "reference-pixel-extraction"}, "height": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_height.png", "url": "base_height.png", "channel": "height", "source": "reference-pixel-extraction"}, "normal": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_normal.png", "url": "base_normal.png", "channel": "normal", "source": "reference-pixel-extraction"}, "ao": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_ao.png", "url": "base_ao.png", "channel": "ao", "source": "reference-pixel-extraction"}}, "diagnostics": {"sourceWidth": 1254, "sourceHeight": 1254, "mapSize": 512, "cropBBoxPixels": {"x": 47, "y": 34, "width": 1120, "height": 1193}, "mask": {"backgroundColor": "#FFFFFF", "backgroundNoise": 0, "transparentPixelFraction": 0.6836, "foregroundCoverage": 0.3472}, "mapStats": {"valueRange": 0.7192, "heightP90Gradient": 0.09639, "roughnessBase": 0.716, "roughnessVariation": 0.191, "normalStrength": 0.269, "blurRadius": 10}, "palette": ["#A38C70", "#524A44", "#7E644E", "#E5D6C2", "#C9AF95", "#2D2626"]}, "warnings": ["single-image inverse rendering cannot prove true physical PBR; confidence is capped"]}, "clearcoat": {"base": 0.24, "roughness": 0.28}},
    options
  );
  materialMap["rose-band"] = createSculptMaterial(
    "rose-band",
    {"id": "rose-band", "name": "Rose copper metal", "type": "physical", "shaderModel": "MeshStandardMaterial / PBR approximation", "baseColor": "#9E5960", "color": "#9E5960", "albedo": {"dominant": "#9E5960", "secondary": ["#D69A91", "#2D2626"], "samplingNotes": "Palette is matched by host vision to visible reference zones."}, "colorVariation": {"palette": ["#9E5960", "#D69A91"], "pattern": "directional brushed gradient", "amplitude": 0.12, "heightCorrelation": 0.2}, "textureResolution": 1024, "textureProjection": {"mode": "uv", "repeat": [2, 2], "anisotropy": 8, "texelDensityIntent": "Preserve stable world/object-scale detail; do not stretch micro detail with component scale."}, "surfaceFrequencyBands": [{"id": "macro", "frequency": 2, "amplitude": 0.52, "role": "reference-derived broad albedo and height breakup"}, {"id": "meso", "frequency": 14, "amplitude": 0.35, "role": "reference-derived cracks, ridges, pores, grain, or leaf clusters"}, {"id": "micro", "frequency": 72, "amplitude": 0.14, "role": "reference-derived micro highlight breakup under grazing light"}], "roughness": {"base": 0.36, "variation": 0.1, "map": "reference-independent-roughness", "localResponse": "lower on bevels and raised glyphs"}, "metalness": {"base": 0.9, "variation": 0.04}, "normal": {"pattern": "directional-brush", "strength": 0.16, "scale": 72, "space": "tangent"}, "bump": {"pattern": "rune-relief", "amplitude": 0.018, "scale": 1}, "displacement": {"pattern": "none", "amplitude": 0, "scale": 1, "silhouetteAffects": false}, "ambientOcclusion": {"cavityStrength": 0.38, "contactShadowBias": 0.42, "notes": "Preserve depth at crossings and inner faces."}, "wear": {"edgeWear": 0.12, "scratches": ["subtle longitudinal hairlines"], "chips": []}, "dirt": {"amount": 0.02, "cavityBias": 0.35, "color": "#2D2626"}, "localOverrides": [{"id": "rose-band-bevel-gloss", "mask": "bevel", "roughness": 0.19999999999999998, "evidenceRefs": ["full-object"]}, {"id": "rose-band-rune-relief", "mask": "rune-glyphs", "roughness": 0.18, "metalness": 1, "evidenceRefs": ["full-object"]}], "shaderNotes": ["Prefer MeshPhysicalMaterial when clearcoat, sheen, transmission, or thin-surface response is observed; otherwise use MeshStandardMaterial-compatible PBR channels.", "Generate albedo, roughness, height/normal, and AO independently; never alias albedo into roughness.", "Use normal/bump/displacement only when they map to observed surface relief.", "Use displacement geometry when the observed relief changes the close-up silhouette; texture-only relief is insufficient there.", "Reference-derived maps are estimates from image pixels; verify with neutral, grazing, and reference-matched renders.", "Do not treat baked image shadows as final albedo; rerun extraction with a tighter material crop if highlights/shadows pollute the maps."], "notes": "Reference-derived full-image PBR is treated as evidence, while final per-band color is host-observed and procedurally authored.", "referencePbr": {"version": "1.0", "sourceImage": "/Users/mattkuo/Documents/Pantheon/app/web/static/pantheon-oracle-sphere-transparent.png", "extractor": "stage1_intake/extract_pbr_evidence.py", "method": "single-image pixel evidence with de-lighting estimate; not photogrammetry", "usable": true, "verdict": "pass", "confidence": 0.86, "estimatedFidelity": 0.86, "targetThreshold": 0.7, "hardLimit": "A single image cannot uniquely recover true albedo/roughness/normal/AO; maps are reference-derived estimates.", "maps": {"albedo": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_albedo.png", "url": "base_albedo.png", "channel": "albedo", "source": "reference-pixel-extraction"}, "roughness": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_roughness.png", "url": "base_roughness.png", "channel": "roughness", "source": "reference-pixel-extraction"}, "height": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_height.png", "url": "base_height.png", "channel": "height", "source": "reference-pixel-extraction"}, "normal": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_normal.png", "url": "base_normal.png", "channel": "normal", "source": "reference-pixel-extraction"}, "ao": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_ao.png", "url": "base_ao.png", "channel": "ao", "source": "reference-pixel-extraction"}}, "diagnostics": {"sourceWidth": 1254, "sourceHeight": 1254, "mapSize": 512, "cropBBoxPixels": {"x": 47, "y": 34, "width": 1120, "height": 1193}, "mask": {"backgroundColor": "#FFFFFF", "backgroundNoise": 0, "transparentPixelFraction": 0.6836, "foregroundCoverage": 0.3472}, "mapStats": {"valueRange": 0.7192, "heightP90Gradient": 0.09639, "roughnessBase": 0.716, "roughnessVariation": 0.191, "normalStrength": 0.269, "blurRadius": 10}, "palette": ["#A38C70", "#524A44", "#7E644E", "#E5D6C2", "#C9AF95", "#2D2626"]}, "warnings": ["single-image inverse rendering cannot prove true physical PBR; confidence is capped"]}, "clearcoat": {"base": 0.24, "roughness": 0.28}},
    options
  );
  materialMap["navy-band"] = createSculptMaterial(
    "navy-band",
    {"id": "navy-band", "name": "Deep navy metal", "type": "physical", "shaderModel": "MeshStandardMaterial / PBR approximation", "baseColor": "#263752", "color": "#263752", "albedo": {"dominant": "#263752", "secondary": ["#60779B", "#2D2626"], "samplingNotes": "Palette is matched by host vision to visible reference zones."}, "colorVariation": {"palette": ["#263752", "#60779B"], "pattern": "directional brushed gradient", "amplitude": 0.12, "heightCorrelation": 0.2}, "textureResolution": 1024, "textureProjection": {"mode": "uv", "repeat": [2, 2], "anisotropy": 8, "texelDensityIntent": "Preserve stable world/object-scale detail; do not stretch micro detail with component scale."}, "surfaceFrequencyBands": [{"id": "macro", "frequency": 2, "amplitude": 0.52, "role": "reference-derived broad albedo and height breakup"}, {"id": "meso", "frequency": 14, "amplitude": 0.35, "role": "reference-derived cracks, ridges, pores, grain, or leaf clusters"}, {"id": "micro", "frequency": 72, "amplitude": 0.14, "role": "reference-derived micro highlight breakup under grazing light"}], "roughness": {"base": 0.3, "variation": 0.1, "map": "reference-independent-roughness", "localResponse": "lower on bevels and raised glyphs"}, "metalness": {"base": 0.84, "variation": 0.04}, "normal": {"pattern": "directional-brush", "strength": 0.16, "scale": 72, "space": "tangent"}, "bump": {"pattern": "rune-relief", "amplitude": 0.018, "scale": 1}, "displacement": {"pattern": "none", "amplitude": 0, "scale": 1, "silhouetteAffects": false}, "ambientOcclusion": {"cavityStrength": 0.38, "contactShadowBias": 0.42, "notes": "Preserve depth at crossings and inner faces."}, "wear": {"edgeWear": 0.12, "scratches": ["subtle longitudinal hairlines"], "chips": []}, "dirt": {"amount": 0.02, "cavityBias": 0.35, "color": "#2D2626"}, "localOverrides": [{"id": "navy-band-bevel-gloss", "mask": "bevel", "roughness": 0.13999999999999999, "evidenceRefs": ["full-object"]}, {"id": "navy-band-rune-relief", "mask": "rune-glyphs", "roughness": 0.18, "metalness": 1, "evidenceRefs": ["full-object"]}], "shaderNotes": ["Prefer MeshPhysicalMaterial when clearcoat, sheen, transmission, or thin-surface response is observed; otherwise use MeshStandardMaterial-compatible PBR channels.", "Generate albedo, roughness, height/normal, and AO independently; never alias albedo into roughness.", "Use normal/bump/displacement only when they map to observed surface relief.", "Use displacement geometry when the observed relief changes the close-up silhouette; texture-only relief is insufficient there.", "Reference-derived maps are estimates from image pixels; verify with neutral, grazing, and reference-matched renders.", "Do not treat baked image shadows as final albedo; rerun extraction with a tighter material crop if highlights/shadows pollute the maps."], "notes": "Reference-derived full-image PBR is treated as evidence, while final per-band color is host-observed and procedurally authored.", "referencePbr": {"version": "1.0", "sourceImage": "/Users/mattkuo/Documents/Pantheon/app/web/static/pantheon-oracle-sphere-transparent.png", "extractor": "stage1_intake/extract_pbr_evidence.py", "method": "single-image pixel evidence with de-lighting estimate; not photogrammetry", "usable": true, "verdict": "pass", "confidence": 0.86, "estimatedFidelity": 0.86, "targetThreshold": 0.7, "hardLimit": "A single image cannot uniquely recover true albedo/roughness/normal/AO; maps are reference-derived estimates.", "maps": {"albedo": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_albedo.png", "url": "base_albedo.png", "channel": "albedo", "source": "reference-pixel-extraction"}, "roughness": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_roughness.png", "url": "base_roughness.png", "channel": "roughness", "source": "reference-pixel-extraction"}, "height": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_height.png", "url": "base_height.png", "channel": "height", "source": "reference-pixel-extraction"}, "normal": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_normal.png", "url": "base_normal.png", "channel": "normal", "source": "reference-pixel-extraction"}, "ao": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_ao.png", "url": "base_ao.png", "channel": "ao", "source": "reference-pixel-extraction"}}, "diagnostics": {"sourceWidth": 1254, "sourceHeight": 1254, "mapSize": 512, "cropBBoxPixels": {"x": 47, "y": 34, "width": 1120, "height": 1193}, "mask": {"backgroundColor": "#FFFFFF", "backgroundNoise": 0, "transparentPixelFraction": 0.6836, "foregroundCoverage": 0.3472}, "mapStats": {"valueRange": 0.7192, "heightP90Gradient": 0.09639, "roughnessBase": 0.716, "roughnessVariation": 0.191, "normalStrength": 0.269, "blurRadius": 10}, "palette": ["#A38C70", "#524A44", "#7E644E", "#E5D6C2", "#C9AF95", "#2D2626"]}, "warnings": ["single-image inverse rendering cannot prove true physical PBR; confidence is capped"]}, "clearcoat": {"base": 0.24, "roughness": 0.28}},
    options
  );
  materialMap["bronze-band"] = createSculptMaterial(
    "bronze-band",
    {"id": "bronze-band", "name": "Champagne bronze metal", "type": "physical", "shaderModel": "MeshStandardMaterial / PBR approximation", "baseColor": "#8B6249", "color": "#8B6249", "albedo": {"dominant": "#8B6249", "secondary": ["#C59A72", "#2D2626"], "samplingNotes": "Palette is matched by host vision to visible reference zones."}, "colorVariation": {"palette": ["#8B6249", "#C59A72"], "pattern": "directional brushed gradient", "amplitude": 0.12, "heightCorrelation": 0.2}, "textureResolution": 1024, "textureProjection": {"mode": "uv", "repeat": [2, 2], "anisotropy": 8, "texelDensityIntent": "Preserve stable world/object-scale detail; do not stretch micro detail with component scale."}, "surfaceFrequencyBands": [{"id": "macro", "frequency": 2, "amplitude": 0.52, "role": "reference-derived broad albedo and height breakup"}, {"id": "meso", "frequency": 14, "amplitude": 0.35, "role": "reference-derived cracks, ridges, pores, grain, or leaf clusters"}, {"id": "micro", "frequency": 72, "amplitude": 0.14, "role": "reference-derived micro highlight breakup under grazing light"}], "roughness": {"base": 0.35, "variation": 0.1, "map": "reference-independent-roughness", "localResponse": "lower on bevels and raised glyphs"}, "metalness": {"base": 0.92, "variation": 0.04}, "normal": {"pattern": "directional-brush", "strength": 0.16, "scale": 72, "space": "tangent"}, "bump": {"pattern": "rune-relief", "amplitude": 0.018, "scale": 1}, "displacement": {"pattern": "none", "amplitude": 0, "scale": 1, "silhouetteAffects": false}, "ambientOcclusion": {"cavityStrength": 0.38, "contactShadowBias": 0.42, "notes": "Preserve depth at crossings and inner faces."}, "wear": {"edgeWear": 0.12, "scratches": ["subtle longitudinal hairlines"], "chips": []}, "dirt": {"amount": 0.02, "cavityBias": 0.35, "color": "#2D2626"}, "localOverrides": [{"id": "bronze-band-bevel-gloss", "mask": "bevel", "roughness": 0.18999999999999997, "evidenceRefs": ["full-object"]}, {"id": "bronze-band-rune-relief", "mask": "rune-glyphs", "roughness": 0.18, "metalness": 1, "evidenceRefs": ["full-object"]}], "shaderNotes": ["Prefer MeshPhysicalMaterial when clearcoat, sheen, transmission, or thin-surface response is observed; otherwise use MeshStandardMaterial-compatible PBR channels.", "Generate albedo, roughness, height/normal, and AO independently; never alias albedo into roughness.", "Use normal/bump/displacement only when they map to observed surface relief.", "Use displacement geometry when the observed relief changes the close-up silhouette; texture-only relief is insufficient there.", "Reference-derived maps are estimates from image pixels; verify with neutral, grazing, and reference-matched renders.", "Do not treat baked image shadows as final albedo; rerun extraction with a tighter material crop if highlights/shadows pollute the maps."], "notes": "Reference-derived full-image PBR is treated as evidence, while final per-band color is host-observed and procedurally authored.", "referencePbr": {"version": "1.0", "sourceImage": "/Users/mattkuo/Documents/Pantheon/app/web/static/pantheon-oracle-sphere-transparent.png", "extractor": "stage1_intake/extract_pbr_evidence.py", "method": "single-image pixel evidence with de-lighting estimate; not photogrammetry", "usable": true, "verdict": "pass", "confidence": 0.86, "estimatedFidelity": 0.86, "targetThreshold": 0.7, "hardLimit": "A single image cannot uniquely recover true albedo/roughness/normal/AO; maps are reference-derived estimates.", "maps": {"albedo": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_albedo.png", "url": "base_albedo.png", "channel": "albedo", "source": "reference-pixel-extraction"}, "roughness": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_roughness.png", "url": "base_roughness.png", "channel": "roughness", "source": "reference-pixel-extraction"}, "height": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_height.png", "url": "base_height.png", "channel": "height", "source": "reference-pixel-extraction"}, "normal": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_normal.png", "url": "base_normal.png", "channel": "normal", "source": "reference-pixel-extraction"}, "ao": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_ao.png", "url": "base_ao.png", "channel": "ao", "source": "reference-pixel-extraction"}}, "diagnostics": {"sourceWidth": 1254, "sourceHeight": 1254, "mapSize": 512, "cropBBoxPixels": {"x": 47, "y": 34, "width": 1120, "height": 1193}, "mask": {"backgroundColor": "#FFFFFF", "backgroundNoise": 0, "transparentPixelFraction": 0.6836, "foregroundCoverage": 0.3472}, "mapStats": {"valueRange": 0.7192, "heightP90Gradient": 0.09639, "roughnessBase": 0.716, "roughnessVariation": 0.191, "normalStrength": 0.269, "blurRadius": 10}, "palette": ["#A38C70", "#524A44", "#7E644E", "#E5D6C2", "#C9AF95", "#2D2626"]}, "warnings": ["single-image inverse rendering cannot prove true physical PBR; confidence is capped"]}, "clearcoat": {"base": 0.24, "roughness": 0.28}},
    options
  );
  materialMap["core-gold"] = createSculptMaterial(
    "core-gold",
    {"id": "core-gold", "name": "Oracle core gold", "type": "physical", "shaderModel": "MeshStandardMaterial / PBR approximation", "baseColor": "#D8A84E", "color": "#D8A84E", "albedo": {"dominant": "#D8A84E", "secondary": ["#FFE7A6", "#2D2626"], "samplingNotes": "Palette is matched by host vision to visible reference zones."}, "colorVariation": {"palette": ["#D8A84E", "#FFE7A6"], "pattern": "directional brushed gradient", "amplitude": 0.12, "heightCorrelation": 0.2}, "textureResolution": 1024, "textureProjection": {"mode": "uv", "repeat": [2, 2], "anisotropy": 8, "texelDensityIntent": "Preserve stable world/object-scale detail; do not stretch micro detail with component scale."}, "surfaceFrequencyBands": [{"id": "macro", "frequency": 2, "amplitude": 0.52, "role": "reference-derived broad albedo and height breakup"}, {"id": "meso", "frequency": 14, "amplitude": 0.35, "role": "reference-derived cracks, ridges, pores, grain, or leaf clusters"}, {"id": "micro", "frequency": 72, "amplitude": 0.14, "role": "reference-derived micro highlight breakup under grazing light"}], "roughness": {"base": 0.2, "variation": 0.1, "map": "reference-independent-roughness", "localResponse": "lower on bevels and raised glyphs"}, "metalness": {"base": 1, "variation": 0.04}, "normal": {"pattern": "directional-brush", "strength": 0.16, "scale": 72, "space": "tangent"}, "bump": {"pattern": "rune-relief", "amplitude": 0.018, "scale": 1}, "displacement": {"pattern": "none", "amplitude": 0, "scale": 1, "silhouetteAffects": false}, "ambientOcclusion": {"cavityStrength": 0.38, "contactShadowBias": 0.42, "notes": "Preserve depth at crossings and inner faces."}, "wear": {"edgeWear": 0.12, "scratches": ["subtle longitudinal hairlines"], "chips": []}, "dirt": {"amount": 0.02, "cavityBias": 0.35, "color": "#2D2626"}, "localOverrides": [{"id": "core-gold-bevel-gloss", "mask": "bevel", "roughness": 0.12, "evidenceRefs": ["full-object"]}, {"id": "core-gold-rune-relief", "mask": "rune-glyphs", "roughness": 0.18, "metalness": 1, "evidenceRefs": ["full-object"]}], "shaderNotes": ["Prefer MeshPhysicalMaterial when clearcoat, sheen, transmission, or thin-surface response is observed; otherwise use MeshStandardMaterial-compatible PBR channels.", "Generate albedo, roughness, height/normal, and AO independently; never alias albedo into roughness.", "Use normal/bump/displacement only when they map to observed surface relief.", "Use displacement geometry when the observed relief changes the close-up silhouette; texture-only relief is insufficient there.", "Reference-derived maps are estimates from image pixels; verify with neutral, grazing, and reference-matched renders.", "Do not treat baked image shadows as final albedo; rerun extraction with a tighter material crop if highlights/shadows pollute the maps."], "notes": "Reference-derived full-image PBR is treated as evidence, while final per-band color is host-observed and procedurally authored.", "referencePbr": {"version": "1.0", "sourceImage": "/Users/mattkuo/Documents/Pantheon/app/web/static/pantheon-oracle-sphere-transparent.png", "extractor": "stage1_intake/extract_pbr_evidence.py", "method": "single-image pixel evidence with de-lighting estimate; not photogrammetry", "usable": true, "verdict": "pass", "confidence": 0.86, "estimatedFidelity": 0.86, "targetThreshold": 0.7, "hardLimit": "A single image cannot uniquely recover true albedo/roughness/normal/AO; maps are reference-derived estimates.", "maps": {"albedo": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_albedo.png", "url": "base_albedo.png", "channel": "albedo", "source": "reference-pixel-extraction"}, "roughness": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_roughness.png", "url": "base_roughness.png", "channel": "roughness", "source": "reference-pixel-extraction"}, "height": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_height.png", "url": "base_height.png", "channel": "height", "source": "reference-pixel-extraction"}, "normal": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_normal.png", "url": "base_normal.png", "channel": "normal", "source": "reference-pixel-extraction"}, "ao": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_ao.png", "url": "base_ao.png", "channel": "ao", "source": "reference-pixel-extraction"}}, "diagnostics": {"sourceWidth": 1254, "sourceHeight": 1254, "mapSize": 512, "cropBBoxPixels": {"x": 47, "y": 34, "width": 1120, "height": 1193}, "mask": {"backgroundColor": "#FFFFFF", "backgroundNoise": 0, "transparentPixelFraction": 0.6836, "foregroundCoverage": 0.3472}, "mapStats": {"valueRange": 0.7192, "heightP90Gradient": 0.09639, "roughnessBase": 0.716, "roughnessVariation": 0.191, "normalStrength": 0.269, "blurRadius": 10}, "palette": ["#A38C70", "#524A44", "#7E644E", "#E5D6C2", "#C9AF95", "#2D2626"]}, "warnings": ["single-image inverse rendering cannot prove true physical PBR; confidence is capped"]}, "emissive": {"color": "#A86F22", "intensity": 0.16}, "clearcoat": {"base": 0.62, "roughness": 0.15}},
    options
  );
  materialMap["core-glow"] = createSculptMaterial(
    "core-glow",
    {"id": "core-glow", "name": "Core translucent glow", "type": "physical", "shaderModel": "MeshStandardMaterial / PBR approximation", "baseColor": "#D8A84E", "color": "#D8A84E", "albedo": {"dominant": "#D8A84E", "secondary": ["#FFE7A6", "#2D2626"], "samplingNotes": "Palette is matched by host vision to visible reference zones."}, "colorVariation": {"palette": ["#D8A84E", "#FFE7A6"], "pattern": "directional brushed gradient", "amplitude": 0.12, "heightCorrelation": 0.2}, "textureResolution": 1024, "textureProjection": {"mode": "uv", "repeat": [2, 2], "anisotropy": 8, "texelDensityIntent": "Preserve stable world/object-scale detail; do not stretch micro detail with component scale."}, "surfaceFrequencyBands": [{"id": "macro", "frequency": 2, "amplitude": 0.52, "role": "reference-derived broad albedo and height breakup"}, {"id": "meso", "frequency": 14, "amplitude": 0.35, "role": "reference-derived cracks, ridges, pores, grain, or leaf clusters"}, {"id": "micro", "frequency": 72, "amplitude": 0.14, "role": "reference-derived micro highlight breakup under grazing light"}], "roughness": {"base": 0.18, "variation": 0.1, "map": "reference-independent-roughness", "localResponse": "lower on bevels and raised glyphs"}, "metalness": {"base": 0.5, "variation": 0.04}, "normal": {"pattern": "directional-brush", "strength": 0.16, "scale": 72, "space": "tangent"}, "bump": {"pattern": "rune-relief", "amplitude": 0.018, "scale": 1}, "displacement": {"pattern": "none", "amplitude": 0, "scale": 1, "silhouetteAffects": false}, "ambientOcclusion": {"cavityStrength": 0.38, "contactShadowBias": 0.42, "notes": "Preserve depth at crossings and inner faces."}, "wear": {"edgeWear": 0.12, "scratches": ["subtle longitudinal hairlines"], "chips": []}, "dirt": {"amount": 0.02, "cavityBias": 0.35, "color": "#2D2626"}, "localOverrides": [{"id": "core-glow-bevel-gloss", "mask": "bevel", "roughness": 0.12, "evidenceRefs": ["full-object"]}, {"id": "core-glow-rune-relief", "mask": "rune-glyphs", "roughness": 0.18, "metalness": 1, "evidenceRefs": ["full-object"]}], "shaderNotes": ["Prefer MeshPhysicalMaterial when clearcoat, sheen, transmission, or thin-surface response is observed; otherwise use MeshStandardMaterial-compatible PBR channels.", "Generate albedo, roughness, height/normal, and AO independently; never alias albedo into roughness.", "Use normal/bump/displacement only when they map to observed surface relief.", "Use displacement geometry when the observed relief changes the close-up silhouette; texture-only relief is insufficient there.", "Reference-derived maps are estimates from image pixels; verify with neutral, grazing, and reference-matched renders.", "Do not treat baked image shadows as final albedo; rerun extraction with a tighter material crop if highlights/shadows pollute the maps."], "notes": "Reference-derived full-image PBR is treated as evidence, while final per-band color is host-observed and procedurally authored.", "referencePbr": {"version": "1.0", "sourceImage": "/Users/mattkuo/Documents/Pantheon/app/web/static/pantheon-oracle-sphere-transparent.png", "extractor": "stage1_intake/extract_pbr_evidence.py", "method": "single-image pixel evidence with de-lighting estimate; not photogrammetry", "usable": true, "verdict": "pass", "confidence": 0.86, "estimatedFidelity": 0.86, "targetThreshold": 0.7, "hardLimit": "A single image cannot uniquely recover true albedo/roughness/normal/AO; maps are reference-derived estimates.", "maps": {"albedo": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_albedo.png", "url": "base_albedo.png", "channel": "albedo", "source": "reference-pixel-extraction"}, "roughness": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_roughness.png", "url": "base_roughness.png", "channel": "roughness", "source": "reference-pixel-extraction"}, "height": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_height.png", "url": "base_height.png", "channel": "height", "source": "reference-pixel-extraction"}, "normal": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_normal.png", "url": "base_normal.png", "channel": "normal", "source": "reference-pixel-extraction"}, "ao": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_ao.png", "url": "base_ao.png", "channel": "ao", "source": "reference-pixel-extraction"}}, "diagnostics": {"sourceWidth": 1254, "sourceHeight": 1254, "mapSize": 512, "cropBBoxPixels": {"x": 47, "y": 34, "width": 1120, "height": 1193}, "mask": {"backgroundColor": "#FFFFFF", "backgroundNoise": 0, "transparentPixelFraction": 0.6836, "foregroundCoverage": 0.3472}, "mapStats": {"valueRange": 0.7192, "heightP90Gradient": 0.09639, "roughnessBase": 0.716, "roughnessVariation": 0.191, "normalStrength": 0.269, "blurRadius": 10}, "palette": ["#A38C70", "#524A44", "#7E644E", "#E5D6C2", "#C9AF95", "#2D2626"]}, "warnings": ["single-image inverse rendering cannot prove true physical PBR; confidence is capped"]}, "emissive": {"color": "#A86F22", "intensity": 0.16}, "clearcoat": {"base": 0.62, "roughness": 0.15}},
    options
  );
  materialMap["rune-gold"] = createSculptMaterial(
    "rune-gold",
    {"id": "rune-gold", "name": "Raised rune gold", "type": "physical", "shaderModel": "MeshStandardMaterial / PBR approximation", "baseColor": "#E8C675", "color": "#E8C675", "albedo": {"dominant": "#E8C675", "secondary": ["#FFF0B8", "#2D2626"], "samplingNotes": "Palette is matched by host vision to visible reference zones."}, "colorVariation": {"palette": ["#E8C675", "#FFF0B8"], "pattern": "directional brushed gradient", "amplitude": 0.12, "heightCorrelation": 0.2}, "textureResolution": 1024, "textureProjection": {"mode": "uv", "repeat": [2, 2], "anisotropy": 8, "texelDensityIntent": "Preserve stable world/object-scale detail; do not stretch micro detail with component scale."}, "surfaceFrequencyBands": [{"id": "macro", "frequency": 2, "amplitude": 0.52, "role": "reference-derived broad albedo and height breakup"}, {"id": "meso", "frequency": 14, "amplitude": 0.35, "role": "reference-derived cracks, ridges, pores, grain, or leaf clusters"}, {"id": "micro", "frequency": 72, "amplitude": 0.14, "role": "reference-derived micro highlight breakup under grazing light"}], "roughness": {"base": 0.18, "variation": 0.1, "map": "reference-independent-roughness", "localResponse": "lower on bevels and raised glyphs"}, "metalness": {"base": 1, "variation": 0.04}, "normal": {"pattern": "directional-brush", "strength": 0.16, "scale": 72, "space": "tangent"}, "bump": {"pattern": "rune-relief", "amplitude": 0.018, "scale": 1}, "displacement": {"pattern": "none", "amplitude": 0, "scale": 1, "silhouetteAffects": false}, "ambientOcclusion": {"cavityStrength": 0.38, "contactShadowBias": 0.42, "notes": "Preserve depth at crossings and inner faces."}, "wear": {"edgeWear": 0.12, "scratches": ["subtle longitudinal hairlines"], "chips": []}, "dirt": {"amount": 0.02, "cavityBias": 0.35, "color": "#2D2626"}, "localOverrides": [{"id": "rune-gold-bevel-gloss", "mask": "bevel", "roughness": 0.12, "evidenceRefs": ["full-object"]}, {"id": "rune-gold-rune-relief", "mask": "rune-glyphs", "roughness": 0.18, "metalness": 1, "evidenceRefs": ["full-object"]}], "shaderNotes": ["Prefer MeshPhysicalMaterial when clearcoat, sheen, transmission, or thin-surface response is observed; otherwise use MeshStandardMaterial-compatible PBR channels.", "Generate albedo, roughness, height/normal, and AO independently; never alias albedo into roughness.", "Use normal/bump/displacement only when they map to observed surface relief.", "Use displacement geometry when the observed relief changes the close-up silhouette; texture-only relief is insufficient there.", "Reference-derived maps are estimates from image pixels; verify with neutral, grazing, and reference-matched renders.", "Do not treat baked image shadows as final albedo; rerun extraction with a tighter material crop if highlights/shadows pollute the maps."], "notes": "Reference-derived full-image PBR is treated as evidence, while final per-band color is host-observed and procedurally authored.", "referencePbr": {"version": "1.0", "sourceImage": "/Users/mattkuo/Documents/Pantheon/app/web/static/pantheon-oracle-sphere-transparent.png", "extractor": "stage1_intake/extract_pbr_evidence.py", "method": "single-image pixel evidence with de-lighting estimate; not photogrammetry", "usable": true, "verdict": "pass", "confidence": 0.86, "estimatedFidelity": 0.86, "targetThreshold": 0.7, "hardLimit": "A single image cannot uniquely recover true albedo/roughness/normal/AO; maps are reference-derived estimates.", "maps": {"albedo": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_albedo.png", "url": "base_albedo.png", "channel": "albedo", "source": "reference-pixel-extraction"}, "roughness": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_roughness.png", "url": "base_roughness.png", "channel": "roughness", "source": "reference-pixel-extraction"}, "height": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_height.png", "url": "base_height.png", "channel": "height", "source": "reference-pixel-extraction"}, "normal": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_normal.png", "url": "base_normal.png", "channel": "normal", "source": "reference-pixel-extraction"}, "ao": {"path": "/Users/mattkuo/Documents/Pantheon/artifacts/pantheon_motion_img2threejs/evidence/pbr/base_ao.png", "url": "base_ao.png", "channel": "ao", "source": "reference-pixel-extraction"}}, "diagnostics": {"sourceWidth": 1254, "sourceHeight": 1254, "mapSize": 512, "cropBBoxPixels": {"x": 47, "y": 34, "width": 1120, "height": 1193}, "mask": {"backgroundColor": "#FFFFFF", "backgroundNoise": 0, "transparentPixelFraction": 0.6836, "foregroundCoverage": 0.3472}, "mapStats": {"valueRange": 0.7192, "heightP90Gradient": 0.09639, "roughnessBase": 0.716, "roughnessVariation": 0.191, "normalStrength": 0.269, "blurRadius": 10}, "palette": ["#A38C70", "#524A44", "#7E644E", "#E5D6C2", "#C9AF95", "#2D2626"]}, "warnings": ["single-image inverse rendering cannot prove true physical PBR; confidence is capped"]}, "clearcoat": {"base": 0.24, "roughness": 0.28}},
    options
  );

  const nodes: Record<string, THREE.Object3D> = { root };
  const meshes: Record<string, THREE.Mesh> = {};
  const sockets: Record<string, THREE.Object3D> = {};
  const colliders: Record<string, unknown> = {};
  const destructionGroups: Record<string, THREE.Object3D[]> = {};

  const attachment_root_0 = null;
  const endpoint_root_0 = makeAttachmentEndpoint(attachment_root_0);
  const node_root_0 = new THREE.Group();
  node_root_0.name = "Pantheon oracle sphere root__pivot";
  if (endpoint_root_0) {
    node_root_0.position.copy(endpoint_root_0.start);
    node_root_0.rotation.set(0, 0, 0);
    node_root_0.scale.set(1, 1, 1);
  } else {
    node_root_0.position.set(0.0, 0.0, 0.0);
    node_root_0.rotation.set(0.0, 0.0, 0.0);
    node_root_0.scale.set(0.01, 0.01, 0.01);
  }
  node_root_0.userData.sculptComponent = {"id": "root", "name": "Pantheon oracle sphere root", "level": "macro", "role": "root", "importance": 1, "confidence": 0.9, "primitive": "sphere", "topologyClass": "assembled-solid", "topologyRationale": "A watertight primitive is sufficient for this centered component.", "geometryDescriptor": {"topologyIntent": "watertight procedural solid", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": null, "attachment": null, "dimensions": {"width": 0.01, "height": 0.01, "depth": 0.01, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [0.01, 0.01, 0.01]}, "actionProfile": {"animationRole": "root", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "root-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "sphere", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "core-gold", "materialLayers": ["core-gold"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "blockout", "colorMaterialRecipe": {"dominantAlbedo": "rgba(216, 168, 78, 1.0)", "secondaryAlbedo": "rgba(255, 231, 166, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(140, 92, 35, 1.0)"}, {"offset": 1, "color": "rgba(255, 231, 166, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_root_0.userData.actionProfile = {"animationRole": "root", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "root-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "sphere", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["root"] ?? root).add(node_root_0);
  nodes["root"] = node_root_0;
  const mesh_root_0Geometry = endpoint_root_0
    ? new THREE.CylinderGeometry(endpoint_root_0.endRadius, endpoint_root_0.baseRadius, endpoint_root_0.length, 32, 12)
    : new THREE.SphereGeometry(0.5, 64, 40);
  const mesh_root_0 = new THREE.Mesh(
    mesh_root_0Geometry,
    materialMap["core-gold"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_root_0.name = "Pantheon oracle sphere root";
  if (endpoint_root_0) {
    mesh_root_0.position.copy(endpoint_root_0.midpoint);
    mesh_root_0.quaternion.copy(endpoint_root_0.quaternion);
  }
  mesh_root_0.castShadow = options.castShadow ?? true;
  mesh_root_0.receiveShadow = options.receiveShadow ?? true;
  mesh_root_0.userData.sculptComponent = {"id": "root", "name": "Pantheon oracle sphere root", "level": "macro", "role": "root", "importance": 1, "confidence": 0.9, "primitive": "sphere", "topologyClass": "assembled-solid", "topologyRationale": "A watertight primitive is sufficient for this centered component.", "geometryDescriptor": {"topologyIntent": "watertight procedural solid", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": null, "attachment": null, "dimensions": {"width": 0.01, "height": 0.01, "depth": 0.01, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [0.01, 0.01, 0.01]}, "actionProfile": {"animationRole": "root", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "root-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "sphere", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "core-gold", "materialLayers": ["core-gold"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "blockout", "colorMaterialRecipe": {"dominantAlbedo": "rgba(216, 168, 78, 1.0)", "secondaryAlbedo": "rgba(255, 231, 166, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(140, 92, 35, 1.0)"}, {"offset": 1, "color": "rgba(255, 231, 166, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_root_0.add(mesh_root_0);
  meshes["root"] = mesh_root_0;
  colliders["root"] = {"type": "sphere", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_root_0);
  const socket_root_root_center_0 = new THREE.Object3D();
  socket_root_root_center_0.name = "root-center";
  socket_root_root_center_0.position.set(0.0, 0.0, 0.0);
  socket_root_root_center_0.rotation.set(0, 0, 0);
  socket_root_root_center_0.userData.socket = {"id": "root-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_root_0.add(socket_root_root_center_0);
  sockets["root:root-center"] = socket_root_root_center_0;

  const attachment_core_1 = {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_core_1 = makeAttachmentEndpoint(attachment_core_1);
  const node_core_1 = new THREE.Group();
  node_core_1.name = "Warm gold oracle core__pivot";
  if (endpoint_core_1) {
    node_core_1.position.copy(endpoint_core_1.start);
    node_core_1.rotation.set(0, 0, 0);
    node_core_1.scale.set(1, 1, 1);
  } else {
    node_core_1.position.set(0.0, 0.0, 0.0);
    node_core_1.rotation.set(0.0, 0.0, 0.0);
    node_core_1.scale.set(0.58, 0.58, 0.58);
  }
  node_core_1.userData.sculptComponent = {"id": "core", "name": "Warm gold oracle core", "level": "macro", "role": "core", "importance": 1, "confidence": 0.82, "primitive": "sphere", "topologyClass": "assembled-solid", "topologyRationale": "A watertight primitive is sufficient for this centered component.", "geometryDescriptor": {"topologyIntent": "watertight procedural solid", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "root", "attachment": {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 0.58, "height": 0.58, "depth": 0.58, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [0.58, 0.58, 0.58]}, "actionProfile": {"animationRole": "pulse", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "core-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "sphere", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "core-gold", "materialLayers": ["core-gold"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "core-gloss", "kind": "gloss", "description": "Bright warm highlight and soft reflected fill."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "blockout", "colorMaterialRecipe": {"dominantAlbedo": "rgba(216, 168, 78, 1.0)", "secondaryAlbedo": "rgba(255, 231, 166, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(140, 92, 35, 1.0)"}, {"offset": 1, "color": "rgba(255, 231, 166, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_core_1.userData.actionProfile = {"animationRole": "pulse", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "core-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "sphere", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["root"] ?? root).add(node_core_1);
  nodes["core"] = node_core_1;
  const mesh_core_1Geometry = endpoint_core_1
    ? new THREE.CylinderGeometry(endpoint_core_1.endRadius, endpoint_core_1.baseRadius, endpoint_core_1.length, 32, 12)
    : new THREE.SphereGeometry(0.5, 64, 40);
  const mesh_core_1 = new THREE.Mesh(
    mesh_core_1Geometry,
    materialMap["core-gold"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_core_1.name = "Warm gold oracle core";
  if (endpoint_core_1) {
    mesh_core_1.position.copy(endpoint_core_1.midpoint);
    mesh_core_1.quaternion.copy(endpoint_core_1.quaternion);
  }
  mesh_core_1.castShadow = options.castShadow ?? true;
  mesh_core_1.receiveShadow = options.receiveShadow ?? true;
  mesh_core_1.userData.sculptComponent = {"id": "core", "name": "Warm gold oracle core", "level": "macro", "role": "core", "importance": 1, "confidence": 0.82, "primitive": "sphere", "topologyClass": "assembled-solid", "topologyRationale": "A watertight primitive is sufficient for this centered component.", "geometryDescriptor": {"topologyIntent": "watertight procedural solid", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "root", "attachment": {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 0.58, "height": 0.58, "depth": 0.58, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [0.58, 0.58, 0.58]}, "actionProfile": {"animationRole": "pulse", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "core-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "sphere", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "core-gold", "materialLayers": ["core-gold"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "core-gloss", "kind": "gloss", "description": "Bright warm highlight and soft reflected fill."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "blockout", "colorMaterialRecipe": {"dominantAlbedo": "rgba(216, 168, 78, 1.0)", "secondaryAlbedo": "rgba(255, 231, 166, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(140, 92, 35, 1.0)"}, {"offset": 1, "color": "rgba(255, 231, 166, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_core_1.add(mesh_core_1);
  meshes["core"] = mesh_core_1;
  colliders["core"] = {"type": "sphere", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_core_1);
  const socket_core_core_center_0 = new THREE.Object3D();
  socket_core_core_center_0.name = "core-center";
  socket_core_core_center_0.position.set(0.0, 0.0, 0.0);
  socket_core_core_center_0.rotation.set(0, 0, 0);
  socket_core_core_center_0.userData.socket = {"id": "core-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_core_1.add(socket_core_core_center_0);
  sockets["core:core-center"] = socket_core_core_center_0;

  const attachment_core_glow_2 = {"parentId": "core", "parentSocket": "core-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_core_glow_2 = makeAttachmentEndpoint(attachment_core_glow_2);
  const node_core_glow_2 = new THREE.Group();
  node_core_glow_2.name = "Core glow shell__pivot";
  if (endpoint_core_glow_2) {
    node_core_glow_2.position.copy(endpoint_core_glow_2.start);
    node_core_glow_2.rotation.set(0, 0, 0);
    node_core_glow_2.scale.set(1, 1, 1);
  } else {
    node_core_glow_2.position.set(0.0, 0.0, 0.0);
    node_core_glow_2.rotation.set(0.0, 0.0, 0.0);
    node_core_glow_2.scale.set(0.69, 0.69, 0.69);
  }
  node_core_glow_2.userData.sculptComponent = {"id": "core-glow", "name": "Core glow shell", "level": "meso", "role": "effect-shell", "importance": 1, "confidence": 0.82, "primitive": "sphere", "topologyClass": "assembled-solid", "topologyRationale": "A watertight primitive is sufficient for this centered component.", "geometryDescriptor": {"topologyIntent": "watertight procedural solid", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "core", "attachment": {"parentId": "core", "parentSocket": "core-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 0.69, "height": 0.69, "depth": 0.69, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [0.69, 0.69, 0.69]}, "actionProfile": {"animationRole": "pulse", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "core-glow-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "sphere", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "core-glow", "materialLayers": ["core-glow"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(176, 138, 90, 1.0)", "secondaryAlbedo": "rgba(224, 192, 144, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(138, 106, 68, 1.0)"}, {"offset": 1, "color": "rgba(224, 192, 144, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_core_glow_2.userData.actionProfile = {"animationRole": "pulse", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "core-glow-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "sphere", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["core"] ?? root).add(node_core_glow_2);
  nodes["core-glow"] = node_core_glow_2;
  const mesh_core_glow_2Geometry = endpoint_core_glow_2
    ? new THREE.CylinderGeometry(endpoint_core_glow_2.endRadius, endpoint_core_glow_2.baseRadius, endpoint_core_glow_2.length, 32, 12)
    : new THREE.SphereGeometry(0.5, 64, 40);
  const mesh_core_glow_2 = new THREE.Mesh(
    mesh_core_glow_2Geometry,
    materialMap["core-glow"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_core_glow_2.name = "Core glow shell";
  if (endpoint_core_glow_2) {
    mesh_core_glow_2.position.copy(endpoint_core_glow_2.midpoint);
    mesh_core_glow_2.quaternion.copy(endpoint_core_glow_2.quaternion);
  }
  mesh_core_glow_2.castShadow = options.castShadow ?? true;
  mesh_core_glow_2.receiveShadow = options.receiveShadow ?? true;
  mesh_core_glow_2.userData.sculptComponent = {"id": "core-glow", "name": "Core glow shell", "level": "meso", "role": "effect-shell", "importance": 1, "confidence": 0.82, "primitive": "sphere", "topologyClass": "assembled-solid", "topologyRationale": "A watertight primitive is sufficient for this centered component.", "geometryDescriptor": {"topologyIntent": "watertight procedural solid", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "core", "attachment": {"parentId": "core", "parentSocket": "core-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 0.69, "height": 0.69, "depth": 0.69, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [0.69, 0.69, 0.69]}, "actionProfile": {"animationRole": "pulse", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "core-glow-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "sphere", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "core-glow", "materialLayers": ["core-glow"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(176, 138, 90, 1.0)", "secondaryAlbedo": "rgba(224, 192, 144, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(138, 106, 68, 1.0)"}, {"offset": 1, "color": "rgba(224, 192, 144, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_core_glow_2.add(mesh_core_glow_2);
  meshes["core-glow"] = mesh_core_glow_2;
  colliders["core-glow"] = {"type": "sphere", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_core_glow_2);
  const socket_core_glow_core_glow_center_0 = new THREE.Object3D();
  socket_core_glow_core_glow_center_0.name = "core-glow-center";
  socket_core_glow_core_glow_center_0.position.set(0.0, 0.0, 0.0);
  socket_core_glow_core_glow_center_0.rotation.set(0, 0, 0);
  socket_core_glow_core_glow_center_0.userData.socket = {"id": "core-glow-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_core_glow_2.add(socket_core_glow_core_glow_center_0);
  sockets["core-glow:core-glow-center"] = socket_core_glow_core_glow_center_0;

  const attachment_gold_pivot_3 = {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_gold_pivot_3 = makeAttachmentEndpoint(attachment_gold_pivot_3);
  const node_gold_pivot_3 = new THREE.Group();
  node_gold_pivot_3.name = "Gold meridian pivot__pivot";
  if (endpoint_gold_pivot_3) {
    node_gold_pivot_3.position.copy(endpoint_gold_pivot_3.start);
    node_gold_pivot_3.rotation.set(0, 0, 0);
    node_gold_pivot_3.scale.set(1, 1, 1);
  } else {
    node_gold_pivot_3.position.set(0.0, 0.0, 0.0);
    node_gold_pivot_3.rotation.set(0.18, 0.04, -0.55);
    node_gold_pivot_3.scale.set(3.0, 3.0, 0.42);
  }
  node_gold_pivot_3.userData.sculptComponent = {"id": "gold-pivot", "name": "Gold meridian pivot", "level": "macro", "role": "band-pivot", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "root", "attachment": {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 3, "height": 3, "depth": 0.42, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0.18, 0.04, -0.55], "scale": [3, 3, 0.42]}, "actionProfile": {"animationRole": "independent-orbit", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "gold-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "gold-band", "materialLayers": ["gold-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "gold-closed-loop", "kind": "contour", "description": "Continuous closed loop with a readable side silhouette."}, {"id": "gold-beveled-edge", "kind": "bevel", "description": "Rounded polished edges catch narrow highlights."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "blockout", "colorMaterialRecipe": {"dominantAlbedo": "rgba(201, 155, 79, 1.0)", "secondaryAlbedo": "rgba(240, 209, 139, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(201, 155, 79, 1.0)"}, {"offset": 1, "color": "rgba(240, 209, 139, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_gold_pivot_3.userData.actionProfile = {"animationRole": "independent-orbit", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "gold-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["root"] ?? root).add(node_gold_pivot_3);
  nodes["gold-pivot"] = node_gold_pivot_3;
  const mesh_gold_pivot_3Geometry = endpoint_gold_pivot_3
    ? new THREE.CylinderGeometry(endpoint_gold_pivot_3.endRadius, endpoint_gold_pivot_3.baseRadius, endpoint_gold_pivot_3.length, 32, 12)
    : new THREE.TorusGeometry(0.45, 0.081, 24, 96);
  const mesh_gold_pivot_3 = new THREE.Mesh(
    mesh_gold_pivot_3Geometry,
    materialMap["gold-band"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_gold_pivot_3.name = "Gold meridian pivot";
  if (endpoint_gold_pivot_3) {
    mesh_gold_pivot_3.position.copy(endpoint_gold_pivot_3.midpoint);
    mesh_gold_pivot_3.quaternion.copy(endpoint_gold_pivot_3.quaternion);
  }
  mesh_gold_pivot_3.castShadow = options.castShadow ?? true;
  mesh_gold_pivot_3.receiveShadow = options.receiveShadow ?? true;
  mesh_gold_pivot_3.userData.sculptComponent = {"id": "gold-pivot", "name": "Gold meridian pivot", "level": "macro", "role": "band-pivot", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "root", "attachment": {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 3, "height": 3, "depth": 0.42, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0.18, 0.04, -0.55], "scale": [3, 3, 0.42]}, "actionProfile": {"animationRole": "independent-orbit", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "gold-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "gold-band", "materialLayers": ["gold-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "gold-closed-loop", "kind": "contour", "description": "Continuous closed loop with a readable side silhouette."}, {"id": "gold-beveled-edge", "kind": "bevel", "description": "Rounded polished edges catch narrow highlights."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "blockout", "colorMaterialRecipe": {"dominantAlbedo": "rgba(201, 155, 79, 1.0)", "secondaryAlbedo": "rgba(240, 209, 139, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(201, 155, 79, 1.0)"}, {"offset": 1, "color": "rgba(240, 209, 139, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_gold_pivot_3.add(mesh_gold_pivot_3);
  meshes["gold-pivot"] = mesh_gold_pivot_3;
  colliders["gold-pivot"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_gold_pivot_3);
  const socket_gold_pivot_gold_pivot_center_0 = new THREE.Object3D();
  socket_gold_pivot_gold_pivot_center_0.name = "gold-pivot-center";
  socket_gold_pivot_gold_pivot_center_0.position.set(0.0, 0.0, 0.0);
  socket_gold_pivot_gold_pivot_center_0.rotation.set(0, 0, 0);
  socket_gold_pivot_gold_pivot_center_0.userData.socket = {"id": "gold-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_gold_pivot_3.add(socket_gold_pivot_gold_pivot_center_0);
  sockets["gold-pivot:gold-pivot-center"] = socket_gold_pivot_gold_pivot_center_0;

  const attachment_gold_shell_4 = {"parentId": "gold-pivot", "parentSocket": "gold-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_gold_shell_4 = makeAttachmentEndpoint(attachment_gold_shell_4);
  const node_gold_shell_4 = new THREE.Group();
  node_gold_shell_4.name = "Gold meridian visible shell__pivot";
  if (endpoint_gold_shell_4) {
    node_gold_shell_4.position.copy(endpoint_gold_shell_4.start);
    node_gold_shell_4.rotation.set(0, 0, 0);
    node_gold_shell_4.scale.set(1, 1, 1);
  } else {
    node_gold_shell_4.position.set(0.0, 0.0, 0.0);
    node_gold_shell_4.rotation.set(0.0, 0.0, 0.0);
    node_gold_shell_4.scale.set(1.0, 1.0, 1.0);
  }
  node_gold_shell_4.userData.sculptComponent = {"id": "gold-shell", "name": "Gold meridian visible shell", "level": "meso", "role": "band-shell", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.17}, "parent": "gold-pivot", "attachment": {"parentId": "gold-pivot", "parentSocket": "gold-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "gold-shell-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "gold-band", "materialLayers": ["gold-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(201, 155, 79, 1.0)", "secondaryAlbedo": "rgba(240, 209, 139, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(201, 155, 79, 1.0)"}, {"offset": 1, "color": "rgba(240, 209, 139, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_gold_shell_4.userData.actionProfile = {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "gold-shell-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["gold-pivot"] ?? root).add(node_gold_shell_4);
  nodes["gold-shell"] = node_gold_shell_4;
  const mesh_gold_shell_4Geometry = endpoint_gold_shell_4
    ? new THREE.CylinderGeometry(endpoint_gold_shell_4.endRadius, endpoint_gold_shell_4.baseRadius, endpoint_gold_shell_4.length, 32, 12)
    : new THREE.TorusGeometry(0.45, 0.0765, 24, 96);
  const mesh_gold_shell_4 = new THREE.Mesh(
    mesh_gold_shell_4Geometry,
    materialMap["gold-band"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_gold_shell_4.name = "Gold meridian visible shell";
  if (endpoint_gold_shell_4) {
    mesh_gold_shell_4.position.copy(endpoint_gold_shell_4.midpoint);
    mesh_gold_shell_4.quaternion.copy(endpoint_gold_shell_4.quaternion);
  }
  mesh_gold_shell_4.castShadow = options.castShadow ?? true;
  mesh_gold_shell_4.receiveShadow = options.receiveShadow ?? true;
  mesh_gold_shell_4.userData.sculptComponent = {"id": "gold-shell", "name": "Gold meridian visible shell", "level": "meso", "role": "band-shell", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.17}, "parent": "gold-pivot", "attachment": {"parentId": "gold-pivot", "parentSocket": "gold-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "gold-shell-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "gold-band", "materialLayers": ["gold-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(201, 155, 79, 1.0)", "secondaryAlbedo": "rgba(240, 209, 139, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(201, 155, 79, 1.0)"}, {"offset": 1, "color": "rgba(240, 209, 139, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_gold_shell_4.add(mesh_gold_shell_4);
  meshes["gold-shell"] = mesh_gold_shell_4;
  colliders["gold-shell"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_gold_shell_4);
  const socket_gold_shell_gold_shell_center_0 = new THREE.Object3D();
  socket_gold_shell_gold_shell_center_0.name = "gold-shell-center";
  socket_gold_shell_gold_shell_center_0.position.set(0.0, 0.0, 0.0);
  socket_gold_shell_gold_shell_center_0.rotation.set(0, 0, 0);
  socket_gold_shell_gold_shell_center_0.userData.socket = {"id": "gold-shell-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_gold_shell_4.add(socket_gold_shell_gold_shell_center_0);
  sockets["gold-shell:gold-shell-center"] = socket_gold_shell_gold_shell_center_0;

  const attachment_gold_inner_5 = {"parentId": "gold-pivot", "parentSocket": "gold-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_gold_inner_5 = makeAttachmentEndpoint(attachment_gold_inner_5);
  const node_gold_inner_5 = new THREE.Group();
  node_gold_inner_5.name = "Gold meridian inner face__pivot";
  if (endpoint_gold_inner_5) {
    node_gold_inner_5.position.copy(endpoint_gold_inner_5.start);
    node_gold_inner_5.rotation.set(0, 0, 0);
    node_gold_inner_5.scale.set(1, 1, 1);
  } else {
    node_gold_inner_5.position.set(0.0, 0.0, 0.0);
    node_gold_inner_5.rotation.set(0.0, 0.0, 0.0);
    node_gold_inner_5.scale.set(0.985, 0.985, 0.94);
  }
  node_gold_inner_5.userData.sculptComponent = {"id": "gold-inner", "name": "Gold meridian inner face", "level": "meso", "role": "inner-face", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.16}, "parent": "gold-pivot", "attachment": {"parentId": "gold-pivot", "parentSocket": "gold-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 0.985, "height": 0.985, "depth": 0.94, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [0.985, 0.985, 0.94]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "gold-inner-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "gold-band", "materialLayers": ["gold-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(201, 155, 79, 1.0)", "secondaryAlbedo": "rgba(240, 209, 139, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(201, 155, 79, 1.0)"}, {"offset": 1, "color": "rgba(240, 209, 139, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_gold_inner_5.userData.actionProfile = {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "gold-inner-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["gold-pivot"] ?? root).add(node_gold_inner_5);
  nodes["gold-inner"] = node_gold_inner_5;
  const mesh_gold_inner_5Geometry = endpoint_gold_inner_5
    ? new THREE.CylinderGeometry(endpoint_gold_inner_5.endRadius, endpoint_gold_inner_5.baseRadius, endpoint_gold_inner_5.length, 32, 12)
    : new THREE.TorusGeometry(0.45, 0.072, 24, 96);
  const mesh_gold_inner_5 = new THREE.Mesh(
    mesh_gold_inner_5Geometry,
    materialMap["gold-band"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_gold_inner_5.name = "Gold meridian inner face";
  if (endpoint_gold_inner_5) {
    mesh_gold_inner_5.position.copy(endpoint_gold_inner_5.midpoint);
    mesh_gold_inner_5.quaternion.copy(endpoint_gold_inner_5.quaternion);
  }
  mesh_gold_inner_5.castShadow = options.castShadow ?? true;
  mesh_gold_inner_5.receiveShadow = options.receiveShadow ?? true;
  mesh_gold_inner_5.userData.sculptComponent = {"id": "gold-inner", "name": "Gold meridian inner face", "level": "meso", "role": "inner-face", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.16}, "parent": "gold-pivot", "attachment": {"parentId": "gold-pivot", "parentSocket": "gold-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 0.985, "height": 0.985, "depth": 0.94, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [0.985, 0.985, 0.94]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "gold-inner-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "gold-band", "materialLayers": ["gold-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(201, 155, 79, 1.0)", "secondaryAlbedo": "rgba(240, 209, 139, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(201, 155, 79, 1.0)"}, {"offset": 1, "color": "rgba(240, 209, 139, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_gold_inner_5.add(mesh_gold_inner_5);
  meshes["gold-inner"] = mesh_gold_inner_5;
  colliders["gold-inner"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_gold_inner_5);
  const socket_gold_inner_gold_inner_center_0 = new THREE.Object3D();
  socket_gold_inner_gold_inner_center_0.name = "gold-inner-center";
  socket_gold_inner_gold_inner_center_0.position.set(0.0, 0.0, 0.0);
  socket_gold_inner_gold_inner_center_0.rotation.set(0, 0, 0);
  socket_gold_inner_gold_inner_center_0.userData.socket = {"id": "gold-inner-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_gold_inner_5.add(socket_gold_inner_gold_inner_center_0);
  sockets["gold-inner:gold-inner-center"] = socket_gold_inner_gold_inner_center_0;

  const attachment_gold_runes_6 = {"parentId": "gold-pivot", "parentSocket": "gold-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_gold_runes_6 = makeAttachmentEndpoint(attachment_gold_runes_6);
  const node_gold_runes_6 = new THREE.Group();
  node_gold_runes_6.name = "Gold meridian rune relief__pivot";
  if (endpoint_gold_runes_6) {
    node_gold_runes_6.position.copy(endpoint_gold_runes_6.start);
    node_gold_runes_6.rotation.set(0, 0, 0);
    node_gold_runes_6.scale.set(1, 1, 1);
  } else {
    node_gold_runes_6.position.set(0.0, 0.0, 0.0);
    node_gold_runes_6.rotation.set(0.0, 0.0, 0.0);
    node_gold_runes_6.scale.set(1.0, 1.0, 1.0);
  }
  node_gold_runes_6.userData.sculptComponent = {"id": "gold-runes", "name": "Gold meridian rune relief", "level": "meso", "role": "surface-relief", "importance": 1, "confidence": 0.82, "primitive": "instanced-cluster", "topologyClass": "surface-relief", "topologyRationale": "A watertight primitive is sufficient for this centered component.", "geometryDescriptor": {"topologyIntent": "watertight procedural solid", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "gold-pivot", "attachment": {"parentId": "gold-pivot", "parentSocket": "gold-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "gold-runes-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "rune-gold", "materialLayers": ["rune-gold"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "gold-rune-path", "kind": "linework", "description": "Procedural diamonds, forks, nodes and connecting strokes."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(176, 138, 90, 1.0)", "secondaryAlbedo": "rgba(224, 192, 144, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(138, 106, 68, 1.0)"}, {"offset": 1, "color": "rgba(224, 192, 144, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_gold_runes_6.userData.actionProfile = {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "gold-runes-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["gold-pivot"] ?? root).add(node_gold_runes_6);
  nodes["gold-runes"] = node_gold_runes_6;
  const mesh_gold_runes_6Geometry = endpoint_gold_runes_6
    ? new THREE.CylinderGeometry(endpoint_gold_runes_6.endRadius, endpoint_gold_runes_6.baseRadius, endpoint_gold_runes_6.length, 32, 12)
    : new THREE.BoxGeometry(1, 1, 1, 12, 12, 12);
  const mesh_gold_runes_6 = new THREE.Mesh(
    mesh_gold_runes_6Geometry,
    materialMap["rune-gold"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_gold_runes_6.name = "Gold meridian rune relief";
  if (endpoint_gold_runes_6) {
    mesh_gold_runes_6.position.copy(endpoint_gold_runes_6.midpoint);
    mesh_gold_runes_6.quaternion.copy(endpoint_gold_runes_6.quaternion);
  }
  mesh_gold_runes_6.castShadow = options.castShadow ?? true;
  mesh_gold_runes_6.receiveShadow = options.receiveShadow ?? true;
  mesh_gold_runes_6.userData.sculptComponent = {"id": "gold-runes", "name": "Gold meridian rune relief", "level": "meso", "role": "surface-relief", "importance": 1, "confidence": 0.82, "primitive": "instanced-cluster", "topologyClass": "surface-relief", "topologyRationale": "A watertight primitive is sufficient for this centered component.", "geometryDescriptor": {"topologyIntent": "watertight procedural solid", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "gold-pivot", "attachment": {"parentId": "gold-pivot", "parentSocket": "gold-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "gold-runes-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "rune-gold", "materialLayers": ["rune-gold"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "gold-rune-path", "kind": "linework", "description": "Procedural diamonds, forks, nodes and connecting strokes."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(176, 138, 90, 1.0)", "secondaryAlbedo": "rgba(224, 192, 144, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(138, 106, 68, 1.0)"}, {"offset": 1, "color": "rgba(224, 192, 144, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_gold_runes_6.add(mesh_gold_runes_6);
  meshes["gold-runes"] = mesh_gold_runes_6;
  colliders["gold-runes"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_gold_runes_6);
  const socket_gold_runes_gold_runes_center_0 = new THREE.Object3D();
  socket_gold_runes_gold_runes_center_0.name = "gold-runes-center";
  socket_gold_runes_gold_runes_center_0.position.set(0.0, 0.0, 0.0);
  socket_gold_runes_gold_runes_center_0.rotation.set(0, 0, 0);
  socket_gold_runes_gold_runes_center_0.userData.socket = {"id": "gold-runes-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_gold_runes_6.add(socket_gold_runes_gold_runes_center_0);
  sockets["gold-runes:gold-runes-center"] = socket_gold_runes_gold_runes_center_0;

  const attachment_teal_pivot_7 = {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_teal_pivot_7 = makeAttachmentEndpoint(attachment_teal_pivot_7);
  const node_teal_pivot_7 = new THREE.Group();
  node_teal_pivot_7.name = "Jade diagonal pivot__pivot";
  if (endpoint_teal_pivot_7) {
    node_teal_pivot_7.position.copy(endpoint_teal_pivot_7.start);
    node_teal_pivot_7.rotation.set(0, 0, 0);
    node_teal_pivot_7.scale.set(1, 1, 1);
  } else {
    node_teal_pivot_7.position.set(0.0, 0.0, 0.0);
    node_teal_pivot_7.rotation.set(1.08, 0.22, 0.42);
    node_teal_pivot_7.scale.set(3.0, 3.0, 0.42);
  }
  node_teal_pivot_7.userData.sculptComponent = {"id": "teal-pivot", "name": "Jade diagonal pivot", "level": "macro", "role": "band-pivot", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "root", "attachment": {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 3, "height": 3, "depth": 0.42, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [1.08, 0.22, 0.42], "scale": [3, 3, 0.42]}, "actionProfile": {"animationRole": "independent-orbit", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "teal-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "teal-band", "materialLayers": ["teal-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "teal-closed-loop", "kind": "contour", "description": "Continuous closed loop with a readable side silhouette."}, {"id": "teal-beveled-edge", "kind": "bevel", "description": "Rounded polished edges catch narrow highlights."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "blockout", "colorMaterialRecipe": {"dominantAlbedo": "rgba(73, 127, 119, 1.0)", "secondaryAlbedo": "rgba(145, 183, 165, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(73, 127, 119, 1.0)"}, {"offset": 1, "color": "rgba(145, 183, 165, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_teal_pivot_7.userData.actionProfile = {"animationRole": "independent-orbit", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "teal-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["root"] ?? root).add(node_teal_pivot_7);
  nodes["teal-pivot"] = node_teal_pivot_7;
  const mesh_teal_pivot_7Geometry = endpoint_teal_pivot_7
    ? new THREE.CylinderGeometry(endpoint_teal_pivot_7.endRadius, endpoint_teal_pivot_7.baseRadius, endpoint_teal_pivot_7.length, 32, 12)
    : new THREE.TorusGeometry(0.45, 0.081, 24, 96);
  const mesh_teal_pivot_7 = new THREE.Mesh(
    mesh_teal_pivot_7Geometry,
    materialMap["teal-band"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_teal_pivot_7.name = "Jade diagonal pivot";
  if (endpoint_teal_pivot_7) {
    mesh_teal_pivot_7.position.copy(endpoint_teal_pivot_7.midpoint);
    mesh_teal_pivot_7.quaternion.copy(endpoint_teal_pivot_7.quaternion);
  }
  mesh_teal_pivot_7.castShadow = options.castShadow ?? true;
  mesh_teal_pivot_7.receiveShadow = options.receiveShadow ?? true;
  mesh_teal_pivot_7.userData.sculptComponent = {"id": "teal-pivot", "name": "Jade diagonal pivot", "level": "macro", "role": "band-pivot", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "root", "attachment": {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 3, "height": 3, "depth": 0.42, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [1.08, 0.22, 0.42], "scale": [3, 3, 0.42]}, "actionProfile": {"animationRole": "independent-orbit", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "teal-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "teal-band", "materialLayers": ["teal-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "teal-closed-loop", "kind": "contour", "description": "Continuous closed loop with a readable side silhouette."}, {"id": "teal-beveled-edge", "kind": "bevel", "description": "Rounded polished edges catch narrow highlights."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "blockout", "colorMaterialRecipe": {"dominantAlbedo": "rgba(73, 127, 119, 1.0)", "secondaryAlbedo": "rgba(145, 183, 165, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(73, 127, 119, 1.0)"}, {"offset": 1, "color": "rgba(145, 183, 165, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_teal_pivot_7.add(mesh_teal_pivot_7);
  meshes["teal-pivot"] = mesh_teal_pivot_7;
  colliders["teal-pivot"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_teal_pivot_7);
  const socket_teal_pivot_teal_pivot_center_0 = new THREE.Object3D();
  socket_teal_pivot_teal_pivot_center_0.name = "teal-pivot-center";
  socket_teal_pivot_teal_pivot_center_0.position.set(0.0, 0.0, 0.0);
  socket_teal_pivot_teal_pivot_center_0.rotation.set(0, 0, 0);
  socket_teal_pivot_teal_pivot_center_0.userData.socket = {"id": "teal-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_teal_pivot_7.add(socket_teal_pivot_teal_pivot_center_0);
  sockets["teal-pivot:teal-pivot-center"] = socket_teal_pivot_teal_pivot_center_0;

  const attachment_teal_shell_8 = {"parentId": "teal-pivot", "parentSocket": "teal-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_teal_shell_8 = makeAttachmentEndpoint(attachment_teal_shell_8);
  const node_teal_shell_8 = new THREE.Group();
  node_teal_shell_8.name = "Jade diagonal visible shell__pivot";
  if (endpoint_teal_shell_8) {
    node_teal_shell_8.position.copy(endpoint_teal_shell_8.start);
    node_teal_shell_8.rotation.set(0, 0, 0);
    node_teal_shell_8.scale.set(1, 1, 1);
  } else {
    node_teal_shell_8.position.set(0.0, 0.0, 0.0);
    node_teal_shell_8.rotation.set(0.0, 0.0, 0.0);
    node_teal_shell_8.scale.set(1.0, 1.0, 1.0);
  }
  node_teal_shell_8.userData.sculptComponent = {"id": "teal-shell", "name": "Jade diagonal visible shell", "level": "meso", "role": "band-shell", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.17}, "parent": "teal-pivot", "attachment": {"parentId": "teal-pivot", "parentSocket": "teal-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "teal-shell-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "teal-band", "materialLayers": ["teal-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(73, 127, 119, 1.0)", "secondaryAlbedo": "rgba(145, 183, 165, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(73, 127, 119, 1.0)"}, {"offset": 1, "color": "rgba(145, 183, 165, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_teal_shell_8.userData.actionProfile = {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "teal-shell-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["teal-pivot"] ?? root).add(node_teal_shell_8);
  nodes["teal-shell"] = node_teal_shell_8;
  const mesh_teal_shell_8Geometry = endpoint_teal_shell_8
    ? new THREE.CylinderGeometry(endpoint_teal_shell_8.endRadius, endpoint_teal_shell_8.baseRadius, endpoint_teal_shell_8.length, 32, 12)
    : new THREE.TorusGeometry(0.45, 0.0765, 24, 96);
  const mesh_teal_shell_8 = new THREE.Mesh(
    mesh_teal_shell_8Geometry,
    materialMap["teal-band"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_teal_shell_8.name = "Jade diagonal visible shell";
  if (endpoint_teal_shell_8) {
    mesh_teal_shell_8.position.copy(endpoint_teal_shell_8.midpoint);
    mesh_teal_shell_8.quaternion.copy(endpoint_teal_shell_8.quaternion);
  }
  mesh_teal_shell_8.castShadow = options.castShadow ?? true;
  mesh_teal_shell_8.receiveShadow = options.receiveShadow ?? true;
  mesh_teal_shell_8.userData.sculptComponent = {"id": "teal-shell", "name": "Jade diagonal visible shell", "level": "meso", "role": "band-shell", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.17}, "parent": "teal-pivot", "attachment": {"parentId": "teal-pivot", "parentSocket": "teal-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "teal-shell-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "teal-band", "materialLayers": ["teal-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(73, 127, 119, 1.0)", "secondaryAlbedo": "rgba(145, 183, 165, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(73, 127, 119, 1.0)"}, {"offset": 1, "color": "rgba(145, 183, 165, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_teal_shell_8.add(mesh_teal_shell_8);
  meshes["teal-shell"] = mesh_teal_shell_8;
  colliders["teal-shell"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_teal_shell_8);
  const socket_teal_shell_teal_shell_center_0 = new THREE.Object3D();
  socket_teal_shell_teal_shell_center_0.name = "teal-shell-center";
  socket_teal_shell_teal_shell_center_0.position.set(0.0, 0.0, 0.0);
  socket_teal_shell_teal_shell_center_0.rotation.set(0, 0, 0);
  socket_teal_shell_teal_shell_center_0.userData.socket = {"id": "teal-shell-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_teal_shell_8.add(socket_teal_shell_teal_shell_center_0);
  sockets["teal-shell:teal-shell-center"] = socket_teal_shell_teal_shell_center_0;

  const attachment_teal_inner_9 = {"parentId": "teal-pivot", "parentSocket": "teal-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_teal_inner_9 = makeAttachmentEndpoint(attachment_teal_inner_9);
  const node_teal_inner_9 = new THREE.Group();
  node_teal_inner_9.name = "Jade diagonal inner face__pivot";
  if (endpoint_teal_inner_9) {
    node_teal_inner_9.position.copy(endpoint_teal_inner_9.start);
    node_teal_inner_9.rotation.set(0, 0, 0);
    node_teal_inner_9.scale.set(1, 1, 1);
  } else {
    node_teal_inner_9.position.set(0.0, 0.0, 0.0);
    node_teal_inner_9.rotation.set(0.0, 0.0, 0.0);
    node_teal_inner_9.scale.set(0.985, 0.985, 0.94);
  }
  node_teal_inner_9.userData.sculptComponent = {"id": "teal-inner", "name": "Jade diagonal inner face", "level": "meso", "role": "inner-face", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.16}, "parent": "teal-pivot", "attachment": {"parentId": "teal-pivot", "parentSocket": "teal-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 0.985, "height": 0.985, "depth": 0.94, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [0.985, 0.985, 0.94]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "teal-inner-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "teal-band", "materialLayers": ["teal-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(73, 127, 119, 1.0)", "secondaryAlbedo": "rgba(145, 183, 165, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(73, 127, 119, 1.0)"}, {"offset": 1, "color": "rgba(145, 183, 165, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_teal_inner_9.userData.actionProfile = {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "teal-inner-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["teal-pivot"] ?? root).add(node_teal_inner_9);
  nodes["teal-inner"] = node_teal_inner_9;
  const mesh_teal_inner_9Geometry = endpoint_teal_inner_9
    ? new THREE.CylinderGeometry(endpoint_teal_inner_9.endRadius, endpoint_teal_inner_9.baseRadius, endpoint_teal_inner_9.length, 32, 12)
    : new THREE.TorusGeometry(0.45, 0.072, 24, 96);
  const mesh_teal_inner_9 = new THREE.Mesh(
    mesh_teal_inner_9Geometry,
    materialMap["teal-band"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_teal_inner_9.name = "Jade diagonal inner face";
  if (endpoint_teal_inner_9) {
    mesh_teal_inner_9.position.copy(endpoint_teal_inner_9.midpoint);
    mesh_teal_inner_9.quaternion.copy(endpoint_teal_inner_9.quaternion);
  }
  mesh_teal_inner_9.castShadow = options.castShadow ?? true;
  mesh_teal_inner_9.receiveShadow = options.receiveShadow ?? true;
  mesh_teal_inner_9.userData.sculptComponent = {"id": "teal-inner", "name": "Jade diagonal inner face", "level": "meso", "role": "inner-face", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.16}, "parent": "teal-pivot", "attachment": {"parentId": "teal-pivot", "parentSocket": "teal-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 0.985, "height": 0.985, "depth": 0.94, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [0.985, 0.985, 0.94]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "teal-inner-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "teal-band", "materialLayers": ["teal-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(73, 127, 119, 1.0)", "secondaryAlbedo": "rgba(145, 183, 165, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(73, 127, 119, 1.0)"}, {"offset": 1, "color": "rgba(145, 183, 165, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_teal_inner_9.add(mesh_teal_inner_9);
  meshes["teal-inner"] = mesh_teal_inner_9;
  colliders["teal-inner"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_teal_inner_9);
  const socket_teal_inner_teal_inner_center_0 = new THREE.Object3D();
  socket_teal_inner_teal_inner_center_0.name = "teal-inner-center";
  socket_teal_inner_teal_inner_center_0.position.set(0.0, 0.0, 0.0);
  socket_teal_inner_teal_inner_center_0.rotation.set(0, 0, 0);
  socket_teal_inner_teal_inner_center_0.userData.socket = {"id": "teal-inner-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_teal_inner_9.add(socket_teal_inner_teal_inner_center_0);
  sockets["teal-inner:teal-inner-center"] = socket_teal_inner_teal_inner_center_0;

  const attachment_teal_runes_10 = {"parentId": "teal-pivot", "parentSocket": "teal-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_teal_runes_10 = makeAttachmentEndpoint(attachment_teal_runes_10);
  const node_teal_runes_10 = new THREE.Group();
  node_teal_runes_10.name = "Jade diagonal rune relief__pivot";
  if (endpoint_teal_runes_10) {
    node_teal_runes_10.position.copy(endpoint_teal_runes_10.start);
    node_teal_runes_10.rotation.set(0, 0, 0);
    node_teal_runes_10.scale.set(1, 1, 1);
  } else {
    node_teal_runes_10.position.set(0.0, 0.0, 0.0);
    node_teal_runes_10.rotation.set(0.0, 0.0, 0.0);
    node_teal_runes_10.scale.set(1.0, 1.0, 1.0);
  }
  node_teal_runes_10.userData.sculptComponent = {"id": "teal-runes", "name": "Jade diagonal rune relief", "level": "meso", "role": "surface-relief", "importance": 1, "confidence": 0.82, "primitive": "instanced-cluster", "topologyClass": "surface-relief", "topologyRationale": "A watertight primitive is sufficient for this centered component.", "geometryDescriptor": {"topologyIntent": "watertight procedural solid", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "teal-pivot", "attachment": {"parentId": "teal-pivot", "parentSocket": "teal-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "teal-runes-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "rune-gold", "materialLayers": ["rune-gold"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "teal-rune-path", "kind": "linework", "description": "Procedural diamonds, forks, nodes and connecting strokes."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(176, 138, 90, 1.0)", "secondaryAlbedo": "rgba(224, 192, 144, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(138, 106, 68, 1.0)"}, {"offset": 1, "color": "rgba(224, 192, 144, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_teal_runes_10.userData.actionProfile = {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "teal-runes-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["teal-pivot"] ?? root).add(node_teal_runes_10);
  nodes["teal-runes"] = node_teal_runes_10;
  const mesh_teal_runes_10Geometry = endpoint_teal_runes_10
    ? new THREE.CylinderGeometry(endpoint_teal_runes_10.endRadius, endpoint_teal_runes_10.baseRadius, endpoint_teal_runes_10.length, 32, 12)
    : new THREE.BoxGeometry(1, 1, 1, 12, 12, 12);
  const mesh_teal_runes_10 = new THREE.Mesh(
    mesh_teal_runes_10Geometry,
    materialMap["rune-gold"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_teal_runes_10.name = "Jade diagonal rune relief";
  if (endpoint_teal_runes_10) {
    mesh_teal_runes_10.position.copy(endpoint_teal_runes_10.midpoint);
    mesh_teal_runes_10.quaternion.copy(endpoint_teal_runes_10.quaternion);
  }
  mesh_teal_runes_10.castShadow = options.castShadow ?? true;
  mesh_teal_runes_10.receiveShadow = options.receiveShadow ?? true;
  mesh_teal_runes_10.userData.sculptComponent = {"id": "teal-runes", "name": "Jade diagonal rune relief", "level": "meso", "role": "surface-relief", "importance": 1, "confidence": 0.82, "primitive": "instanced-cluster", "topologyClass": "surface-relief", "topologyRationale": "A watertight primitive is sufficient for this centered component.", "geometryDescriptor": {"topologyIntent": "watertight procedural solid", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "teal-pivot", "attachment": {"parentId": "teal-pivot", "parentSocket": "teal-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "teal-runes-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "rune-gold", "materialLayers": ["rune-gold"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "teal-rune-path", "kind": "linework", "description": "Procedural diamonds, forks, nodes and connecting strokes."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(176, 138, 90, 1.0)", "secondaryAlbedo": "rgba(224, 192, 144, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(138, 106, 68, 1.0)"}, {"offset": 1, "color": "rgba(224, 192, 144, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_teal_runes_10.add(mesh_teal_runes_10);
  meshes["teal-runes"] = mesh_teal_runes_10;
  colliders["teal-runes"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_teal_runes_10);
  const socket_teal_runes_teal_runes_center_0 = new THREE.Object3D();
  socket_teal_runes_teal_runes_center_0.name = "teal-runes-center";
  socket_teal_runes_teal_runes_center_0.position.set(0.0, 0.0, 0.0);
  socket_teal_runes_teal_runes_center_0.rotation.set(0, 0, 0);
  socket_teal_runes_teal_runes_center_0.userData.socket = {"id": "teal-runes-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_teal_runes_10.add(socket_teal_runes_teal_runes_center_0);
  sockets["teal-runes:teal-runes-center"] = socket_teal_runes_teal_runes_center_0;

  const attachment_rose_pivot_11 = {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_rose_pivot_11 = makeAttachmentEndpoint(attachment_rose_pivot_11);
  const node_rose_pivot_11 = new THREE.Group();
  node_rose_pivot_11.name = "Rose equator pivot__pivot";
  if (endpoint_rose_pivot_11) {
    node_rose_pivot_11.position.copy(endpoint_rose_pivot_11.start);
    node_rose_pivot_11.rotation.set(0, 0, 0);
    node_rose_pivot_11.scale.set(1, 1, 1);
  } else {
    node_rose_pivot_11.position.set(0.0, 0.0, 0.0);
    node_rose_pivot_11.rotation.set(0.55, 1.12, -0.08);
    node_rose_pivot_11.scale.set(3.0, 3.0, 0.42);
  }
  node_rose_pivot_11.userData.sculptComponent = {"id": "rose-pivot", "name": "Rose equator pivot", "level": "macro", "role": "band-pivot", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "root", "attachment": {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 3, "height": 3, "depth": 0.42, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0.55, 1.12, -0.08], "scale": [3, 3, 0.42]}, "actionProfile": {"animationRole": "independent-orbit", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "rose-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "rose-band", "materialLayers": ["rose-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "rose-closed-loop", "kind": "contour", "description": "Continuous closed loop with a readable side silhouette."}, {"id": "rose-beveled-edge", "kind": "bevel", "description": "Rounded polished edges catch narrow highlights."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "blockout", "colorMaterialRecipe": {"dominantAlbedo": "rgba(158, 89, 96, 1.0)", "secondaryAlbedo": "rgba(214, 154, 145, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(158, 89, 96, 1.0)"}, {"offset": 1, "color": "rgba(214, 154, 145, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_rose_pivot_11.userData.actionProfile = {"animationRole": "independent-orbit", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "rose-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["root"] ?? root).add(node_rose_pivot_11);
  nodes["rose-pivot"] = node_rose_pivot_11;
  const mesh_rose_pivot_11Geometry = endpoint_rose_pivot_11
    ? new THREE.CylinderGeometry(endpoint_rose_pivot_11.endRadius, endpoint_rose_pivot_11.baseRadius, endpoint_rose_pivot_11.length, 32, 12)
    : new THREE.TorusGeometry(0.45, 0.081, 24, 96);
  const mesh_rose_pivot_11 = new THREE.Mesh(
    mesh_rose_pivot_11Geometry,
    materialMap["rose-band"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_rose_pivot_11.name = "Rose equator pivot";
  if (endpoint_rose_pivot_11) {
    mesh_rose_pivot_11.position.copy(endpoint_rose_pivot_11.midpoint);
    mesh_rose_pivot_11.quaternion.copy(endpoint_rose_pivot_11.quaternion);
  }
  mesh_rose_pivot_11.castShadow = options.castShadow ?? true;
  mesh_rose_pivot_11.receiveShadow = options.receiveShadow ?? true;
  mesh_rose_pivot_11.userData.sculptComponent = {"id": "rose-pivot", "name": "Rose equator pivot", "level": "macro", "role": "band-pivot", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "root", "attachment": {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 3, "height": 3, "depth": 0.42, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0.55, 1.12, -0.08], "scale": [3, 3, 0.42]}, "actionProfile": {"animationRole": "independent-orbit", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "rose-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "rose-band", "materialLayers": ["rose-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "rose-closed-loop", "kind": "contour", "description": "Continuous closed loop with a readable side silhouette."}, {"id": "rose-beveled-edge", "kind": "bevel", "description": "Rounded polished edges catch narrow highlights."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "blockout", "colorMaterialRecipe": {"dominantAlbedo": "rgba(158, 89, 96, 1.0)", "secondaryAlbedo": "rgba(214, 154, 145, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(158, 89, 96, 1.0)"}, {"offset": 1, "color": "rgba(214, 154, 145, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_rose_pivot_11.add(mesh_rose_pivot_11);
  meshes["rose-pivot"] = mesh_rose_pivot_11;
  colliders["rose-pivot"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_rose_pivot_11);
  const socket_rose_pivot_rose_pivot_center_0 = new THREE.Object3D();
  socket_rose_pivot_rose_pivot_center_0.name = "rose-pivot-center";
  socket_rose_pivot_rose_pivot_center_0.position.set(0.0, 0.0, 0.0);
  socket_rose_pivot_rose_pivot_center_0.rotation.set(0, 0, 0);
  socket_rose_pivot_rose_pivot_center_0.userData.socket = {"id": "rose-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_rose_pivot_11.add(socket_rose_pivot_rose_pivot_center_0);
  sockets["rose-pivot:rose-pivot-center"] = socket_rose_pivot_rose_pivot_center_0;

  const attachment_rose_shell_12 = {"parentId": "rose-pivot", "parentSocket": "rose-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_rose_shell_12 = makeAttachmentEndpoint(attachment_rose_shell_12);
  const node_rose_shell_12 = new THREE.Group();
  node_rose_shell_12.name = "Rose equator visible shell__pivot";
  if (endpoint_rose_shell_12) {
    node_rose_shell_12.position.copy(endpoint_rose_shell_12.start);
    node_rose_shell_12.rotation.set(0, 0, 0);
    node_rose_shell_12.scale.set(1, 1, 1);
  } else {
    node_rose_shell_12.position.set(0.0, 0.0, 0.0);
    node_rose_shell_12.rotation.set(0.0, 0.0, 0.0);
    node_rose_shell_12.scale.set(1.0, 1.0, 1.0);
  }
  node_rose_shell_12.userData.sculptComponent = {"id": "rose-shell", "name": "Rose equator visible shell", "level": "meso", "role": "band-shell", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.17}, "parent": "rose-pivot", "attachment": {"parentId": "rose-pivot", "parentSocket": "rose-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "rose-shell-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "rose-band", "materialLayers": ["rose-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(158, 89, 96, 1.0)", "secondaryAlbedo": "rgba(214, 154, 145, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(158, 89, 96, 1.0)"}, {"offset": 1, "color": "rgba(214, 154, 145, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_rose_shell_12.userData.actionProfile = {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "rose-shell-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["rose-pivot"] ?? root).add(node_rose_shell_12);
  nodes["rose-shell"] = node_rose_shell_12;
  const mesh_rose_shell_12Geometry = endpoint_rose_shell_12
    ? new THREE.CylinderGeometry(endpoint_rose_shell_12.endRadius, endpoint_rose_shell_12.baseRadius, endpoint_rose_shell_12.length, 32, 12)
    : new THREE.TorusGeometry(0.45, 0.0765, 24, 96);
  const mesh_rose_shell_12 = new THREE.Mesh(
    mesh_rose_shell_12Geometry,
    materialMap["rose-band"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_rose_shell_12.name = "Rose equator visible shell";
  if (endpoint_rose_shell_12) {
    mesh_rose_shell_12.position.copy(endpoint_rose_shell_12.midpoint);
    mesh_rose_shell_12.quaternion.copy(endpoint_rose_shell_12.quaternion);
  }
  mesh_rose_shell_12.castShadow = options.castShadow ?? true;
  mesh_rose_shell_12.receiveShadow = options.receiveShadow ?? true;
  mesh_rose_shell_12.userData.sculptComponent = {"id": "rose-shell", "name": "Rose equator visible shell", "level": "meso", "role": "band-shell", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.17}, "parent": "rose-pivot", "attachment": {"parentId": "rose-pivot", "parentSocket": "rose-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "rose-shell-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "rose-band", "materialLayers": ["rose-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(158, 89, 96, 1.0)", "secondaryAlbedo": "rgba(214, 154, 145, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(158, 89, 96, 1.0)"}, {"offset": 1, "color": "rgba(214, 154, 145, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_rose_shell_12.add(mesh_rose_shell_12);
  meshes["rose-shell"] = mesh_rose_shell_12;
  colliders["rose-shell"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_rose_shell_12);
  const socket_rose_shell_rose_shell_center_0 = new THREE.Object3D();
  socket_rose_shell_rose_shell_center_0.name = "rose-shell-center";
  socket_rose_shell_rose_shell_center_0.position.set(0.0, 0.0, 0.0);
  socket_rose_shell_rose_shell_center_0.rotation.set(0, 0, 0);
  socket_rose_shell_rose_shell_center_0.userData.socket = {"id": "rose-shell-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_rose_shell_12.add(socket_rose_shell_rose_shell_center_0);
  sockets["rose-shell:rose-shell-center"] = socket_rose_shell_rose_shell_center_0;

  const attachment_rose_inner_13 = {"parentId": "rose-pivot", "parentSocket": "rose-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_rose_inner_13 = makeAttachmentEndpoint(attachment_rose_inner_13);
  const node_rose_inner_13 = new THREE.Group();
  node_rose_inner_13.name = "Rose equator inner face__pivot";
  if (endpoint_rose_inner_13) {
    node_rose_inner_13.position.copy(endpoint_rose_inner_13.start);
    node_rose_inner_13.rotation.set(0, 0, 0);
    node_rose_inner_13.scale.set(1, 1, 1);
  } else {
    node_rose_inner_13.position.set(0.0, 0.0, 0.0);
    node_rose_inner_13.rotation.set(0.0, 0.0, 0.0);
    node_rose_inner_13.scale.set(0.985, 0.985, 0.94);
  }
  node_rose_inner_13.userData.sculptComponent = {"id": "rose-inner", "name": "Rose equator inner face", "level": "meso", "role": "inner-face", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.16}, "parent": "rose-pivot", "attachment": {"parentId": "rose-pivot", "parentSocket": "rose-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 0.985, "height": 0.985, "depth": 0.94, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [0.985, 0.985, 0.94]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "rose-inner-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "rose-band", "materialLayers": ["rose-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(158, 89, 96, 1.0)", "secondaryAlbedo": "rgba(214, 154, 145, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(158, 89, 96, 1.0)"}, {"offset": 1, "color": "rgba(214, 154, 145, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_rose_inner_13.userData.actionProfile = {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "rose-inner-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["rose-pivot"] ?? root).add(node_rose_inner_13);
  nodes["rose-inner"] = node_rose_inner_13;
  const mesh_rose_inner_13Geometry = endpoint_rose_inner_13
    ? new THREE.CylinderGeometry(endpoint_rose_inner_13.endRadius, endpoint_rose_inner_13.baseRadius, endpoint_rose_inner_13.length, 32, 12)
    : new THREE.TorusGeometry(0.45, 0.072, 24, 96);
  const mesh_rose_inner_13 = new THREE.Mesh(
    mesh_rose_inner_13Geometry,
    materialMap["rose-band"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_rose_inner_13.name = "Rose equator inner face";
  if (endpoint_rose_inner_13) {
    mesh_rose_inner_13.position.copy(endpoint_rose_inner_13.midpoint);
    mesh_rose_inner_13.quaternion.copy(endpoint_rose_inner_13.quaternion);
  }
  mesh_rose_inner_13.castShadow = options.castShadow ?? true;
  mesh_rose_inner_13.receiveShadow = options.receiveShadow ?? true;
  mesh_rose_inner_13.userData.sculptComponent = {"id": "rose-inner", "name": "Rose equator inner face", "level": "meso", "role": "inner-face", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.16}, "parent": "rose-pivot", "attachment": {"parentId": "rose-pivot", "parentSocket": "rose-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 0.985, "height": 0.985, "depth": 0.94, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [0.985, 0.985, 0.94]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "rose-inner-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "rose-band", "materialLayers": ["rose-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(158, 89, 96, 1.0)", "secondaryAlbedo": "rgba(214, 154, 145, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(158, 89, 96, 1.0)"}, {"offset": 1, "color": "rgba(214, 154, 145, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_rose_inner_13.add(mesh_rose_inner_13);
  meshes["rose-inner"] = mesh_rose_inner_13;
  colliders["rose-inner"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_rose_inner_13);
  const socket_rose_inner_rose_inner_center_0 = new THREE.Object3D();
  socket_rose_inner_rose_inner_center_0.name = "rose-inner-center";
  socket_rose_inner_rose_inner_center_0.position.set(0.0, 0.0, 0.0);
  socket_rose_inner_rose_inner_center_0.rotation.set(0, 0, 0);
  socket_rose_inner_rose_inner_center_0.userData.socket = {"id": "rose-inner-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_rose_inner_13.add(socket_rose_inner_rose_inner_center_0);
  sockets["rose-inner:rose-inner-center"] = socket_rose_inner_rose_inner_center_0;

  const attachment_rose_runes_14 = {"parentId": "rose-pivot", "parentSocket": "rose-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_rose_runes_14 = makeAttachmentEndpoint(attachment_rose_runes_14);
  const node_rose_runes_14 = new THREE.Group();
  node_rose_runes_14.name = "Rose equator rune relief__pivot";
  if (endpoint_rose_runes_14) {
    node_rose_runes_14.position.copy(endpoint_rose_runes_14.start);
    node_rose_runes_14.rotation.set(0, 0, 0);
    node_rose_runes_14.scale.set(1, 1, 1);
  } else {
    node_rose_runes_14.position.set(0.0, 0.0, 0.0);
    node_rose_runes_14.rotation.set(0.0, 0.0, 0.0);
    node_rose_runes_14.scale.set(1.0, 1.0, 1.0);
  }
  node_rose_runes_14.userData.sculptComponent = {"id": "rose-runes", "name": "Rose equator rune relief", "level": "meso", "role": "surface-relief", "importance": 1, "confidence": 0.82, "primitive": "instanced-cluster", "topologyClass": "surface-relief", "topologyRationale": "A watertight primitive is sufficient for this centered component.", "geometryDescriptor": {"topologyIntent": "watertight procedural solid", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "rose-pivot", "attachment": {"parentId": "rose-pivot", "parentSocket": "rose-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "rose-runes-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "rune-gold", "materialLayers": ["rune-gold"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "rose-rune-path", "kind": "linework", "description": "Procedural diamonds, forks, nodes and connecting strokes."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(176, 138, 90, 1.0)", "secondaryAlbedo": "rgba(224, 192, 144, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(138, 106, 68, 1.0)"}, {"offset": 1, "color": "rgba(224, 192, 144, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_rose_runes_14.userData.actionProfile = {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "rose-runes-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["rose-pivot"] ?? root).add(node_rose_runes_14);
  nodes["rose-runes"] = node_rose_runes_14;
  const mesh_rose_runes_14Geometry = endpoint_rose_runes_14
    ? new THREE.CylinderGeometry(endpoint_rose_runes_14.endRadius, endpoint_rose_runes_14.baseRadius, endpoint_rose_runes_14.length, 32, 12)
    : new THREE.BoxGeometry(1, 1, 1, 12, 12, 12);
  const mesh_rose_runes_14 = new THREE.Mesh(
    mesh_rose_runes_14Geometry,
    materialMap["rune-gold"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_rose_runes_14.name = "Rose equator rune relief";
  if (endpoint_rose_runes_14) {
    mesh_rose_runes_14.position.copy(endpoint_rose_runes_14.midpoint);
    mesh_rose_runes_14.quaternion.copy(endpoint_rose_runes_14.quaternion);
  }
  mesh_rose_runes_14.castShadow = options.castShadow ?? true;
  mesh_rose_runes_14.receiveShadow = options.receiveShadow ?? true;
  mesh_rose_runes_14.userData.sculptComponent = {"id": "rose-runes", "name": "Rose equator rune relief", "level": "meso", "role": "surface-relief", "importance": 1, "confidence": 0.82, "primitive": "instanced-cluster", "topologyClass": "surface-relief", "topologyRationale": "A watertight primitive is sufficient for this centered component.", "geometryDescriptor": {"topologyIntent": "watertight procedural solid", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "rose-pivot", "attachment": {"parentId": "rose-pivot", "parentSocket": "rose-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "rose-runes-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "rune-gold", "materialLayers": ["rune-gold"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "rose-rune-path", "kind": "linework", "description": "Procedural diamonds, forks, nodes and connecting strokes."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(176, 138, 90, 1.0)", "secondaryAlbedo": "rgba(224, 192, 144, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(138, 106, 68, 1.0)"}, {"offset": 1, "color": "rgba(224, 192, 144, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_rose_runes_14.add(mesh_rose_runes_14);
  meshes["rose-runes"] = mesh_rose_runes_14;
  colliders["rose-runes"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_rose_runes_14);
  const socket_rose_runes_rose_runes_center_0 = new THREE.Object3D();
  socket_rose_runes_rose_runes_center_0.name = "rose-runes-center";
  socket_rose_runes_rose_runes_center_0.position.set(0.0, 0.0, 0.0);
  socket_rose_runes_rose_runes_center_0.rotation.set(0, 0, 0);
  socket_rose_runes_rose_runes_center_0.userData.socket = {"id": "rose-runes-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_rose_runes_14.add(socket_rose_runes_rose_runes_center_0);
  sockets["rose-runes:rose-runes-center"] = socket_rose_runes_rose_runes_center_0;

  const attachment_navy_pivot_15 = {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_navy_pivot_15 = makeAttachmentEndpoint(attachment_navy_pivot_15);
  const node_navy_pivot_15 = new THREE.Group();
  node_navy_pivot_15.name = "Navy ascending pivot__pivot";
  if (endpoint_navy_pivot_15) {
    node_navy_pivot_15.position.copy(endpoint_navy_pivot_15.start);
    node_navy_pivot_15.rotation.set(0, 0, 0);
    node_navy_pivot_15.scale.set(1, 1, 1);
  } else {
    node_navy_pivot_15.position.set(0.0, 0.0, 0.0);
    node_navy_pivot_15.rotation.set(1.16, -0.64, -0.42);
    node_navy_pivot_15.scale.set(3.0, 3.0, 0.42);
  }
  node_navy_pivot_15.userData.sculptComponent = {"id": "navy-pivot", "name": "Navy ascending pivot", "level": "macro", "role": "band-pivot", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "root", "attachment": {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 3, "height": 3, "depth": 0.42, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [1.16, -0.64, -0.42], "scale": [3, 3, 0.42]}, "actionProfile": {"animationRole": "independent-orbit", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "navy-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "navy-band", "materialLayers": ["navy-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "navy-closed-loop", "kind": "contour", "description": "Continuous closed loop with a readable side silhouette."}, {"id": "navy-beveled-edge", "kind": "bevel", "description": "Rounded polished edges catch narrow highlights."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "blockout", "colorMaterialRecipe": {"dominantAlbedo": "rgba(38, 55, 82, 1.0)", "secondaryAlbedo": "rgba(96, 119, 155, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(38, 55, 82, 1.0)"}, {"offset": 1, "color": "rgba(96, 119, 155, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_navy_pivot_15.userData.actionProfile = {"animationRole": "independent-orbit", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "navy-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["root"] ?? root).add(node_navy_pivot_15);
  nodes["navy-pivot"] = node_navy_pivot_15;
  const mesh_navy_pivot_15Geometry = endpoint_navy_pivot_15
    ? new THREE.CylinderGeometry(endpoint_navy_pivot_15.endRadius, endpoint_navy_pivot_15.baseRadius, endpoint_navy_pivot_15.length, 32, 12)
    : new THREE.TorusGeometry(0.45, 0.081, 24, 96);
  const mesh_navy_pivot_15 = new THREE.Mesh(
    mesh_navy_pivot_15Geometry,
    materialMap["navy-band"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_navy_pivot_15.name = "Navy ascending pivot";
  if (endpoint_navy_pivot_15) {
    mesh_navy_pivot_15.position.copy(endpoint_navy_pivot_15.midpoint);
    mesh_navy_pivot_15.quaternion.copy(endpoint_navy_pivot_15.quaternion);
  }
  mesh_navy_pivot_15.castShadow = options.castShadow ?? true;
  mesh_navy_pivot_15.receiveShadow = options.receiveShadow ?? true;
  mesh_navy_pivot_15.userData.sculptComponent = {"id": "navy-pivot", "name": "Navy ascending pivot", "level": "macro", "role": "band-pivot", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "root", "attachment": {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 3, "height": 3, "depth": 0.42, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [1.16, -0.64, -0.42], "scale": [3, 3, 0.42]}, "actionProfile": {"animationRole": "independent-orbit", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "navy-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "navy-band", "materialLayers": ["navy-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "navy-closed-loop", "kind": "contour", "description": "Continuous closed loop with a readable side silhouette."}, {"id": "navy-beveled-edge", "kind": "bevel", "description": "Rounded polished edges catch narrow highlights."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "blockout", "colorMaterialRecipe": {"dominantAlbedo": "rgba(38, 55, 82, 1.0)", "secondaryAlbedo": "rgba(96, 119, 155, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(38, 55, 82, 1.0)"}, {"offset": 1, "color": "rgba(96, 119, 155, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_navy_pivot_15.add(mesh_navy_pivot_15);
  meshes["navy-pivot"] = mesh_navy_pivot_15;
  colliders["navy-pivot"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_navy_pivot_15);
  const socket_navy_pivot_navy_pivot_center_0 = new THREE.Object3D();
  socket_navy_pivot_navy_pivot_center_0.name = "navy-pivot-center";
  socket_navy_pivot_navy_pivot_center_0.position.set(0.0, 0.0, 0.0);
  socket_navy_pivot_navy_pivot_center_0.rotation.set(0, 0, 0);
  socket_navy_pivot_navy_pivot_center_0.userData.socket = {"id": "navy-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_navy_pivot_15.add(socket_navy_pivot_navy_pivot_center_0);
  sockets["navy-pivot:navy-pivot-center"] = socket_navy_pivot_navy_pivot_center_0;

  const attachment_navy_shell_16 = {"parentId": "navy-pivot", "parentSocket": "navy-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_navy_shell_16 = makeAttachmentEndpoint(attachment_navy_shell_16);
  const node_navy_shell_16 = new THREE.Group();
  node_navy_shell_16.name = "Navy ascending visible shell__pivot";
  if (endpoint_navy_shell_16) {
    node_navy_shell_16.position.copy(endpoint_navy_shell_16.start);
    node_navy_shell_16.rotation.set(0, 0, 0);
    node_navy_shell_16.scale.set(1, 1, 1);
  } else {
    node_navy_shell_16.position.set(0.0, 0.0, 0.0);
    node_navy_shell_16.rotation.set(0.0, 0.0, 0.0);
    node_navy_shell_16.scale.set(1.0, 1.0, 1.0);
  }
  node_navy_shell_16.userData.sculptComponent = {"id": "navy-shell", "name": "Navy ascending visible shell", "level": "meso", "role": "band-shell", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.17}, "parent": "navy-pivot", "attachment": {"parentId": "navy-pivot", "parentSocket": "navy-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "navy-shell-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "navy-band", "materialLayers": ["navy-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(38, 55, 82, 1.0)", "secondaryAlbedo": "rgba(96, 119, 155, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(38, 55, 82, 1.0)"}, {"offset": 1, "color": "rgba(96, 119, 155, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_navy_shell_16.userData.actionProfile = {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "navy-shell-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["navy-pivot"] ?? root).add(node_navy_shell_16);
  nodes["navy-shell"] = node_navy_shell_16;
  const mesh_navy_shell_16Geometry = endpoint_navy_shell_16
    ? new THREE.CylinderGeometry(endpoint_navy_shell_16.endRadius, endpoint_navy_shell_16.baseRadius, endpoint_navy_shell_16.length, 32, 12)
    : new THREE.TorusGeometry(0.45, 0.0765, 24, 96);
  const mesh_navy_shell_16 = new THREE.Mesh(
    mesh_navy_shell_16Geometry,
    materialMap["navy-band"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_navy_shell_16.name = "Navy ascending visible shell";
  if (endpoint_navy_shell_16) {
    mesh_navy_shell_16.position.copy(endpoint_navy_shell_16.midpoint);
    mesh_navy_shell_16.quaternion.copy(endpoint_navy_shell_16.quaternion);
  }
  mesh_navy_shell_16.castShadow = options.castShadow ?? true;
  mesh_navy_shell_16.receiveShadow = options.receiveShadow ?? true;
  mesh_navy_shell_16.userData.sculptComponent = {"id": "navy-shell", "name": "Navy ascending visible shell", "level": "meso", "role": "band-shell", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.17}, "parent": "navy-pivot", "attachment": {"parentId": "navy-pivot", "parentSocket": "navy-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "navy-shell-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "navy-band", "materialLayers": ["navy-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(38, 55, 82, 1.0)", "secondaryAlbedo": "rgba(96, 119, 155, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(38, 55, 82, 1.0)"}, {"offset": 1, "color": "rgba(96, 119, 155, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_navy_shell_16.add(mesh_navy_shell_16);
  meshes["navy-shell"] = mesh_navy_shell_16;
  colliders["navy-shell"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_navy_shell_16);
  const socket_navy_shell_navy_shell_center_0 = new THREE.Object3D();
  socket_navy_shell_navy_shell_center_0.name = "navy-shell-center";
  socket_navy_shell_navy_shell_center_0.position.set(0.0, 0.0, 0.0);
  socket_navy_shell_navy_shell_center_0.rotation.set(0, 0, 0);
  socket_navy_shell_navy_shell_center_0.userData.socket = {"id": "navy-shell-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_navy_shell_16.add(socket_navy_shell_navy_shell_center_0);
  sockets["navy-shell:navy-shell-center"] = socket_navy_shell_navy_shell_center_0;

  const attachment_navy_inner_17 = {"parentId": "navy-pivot", "parentSocket": "navy-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_navy_inner_17 = makeAttachmentEndpoint(attachment_navy_inner_17);
  const node_navy_inner_17 = new THREE.Group();
  node_navy_inner_17.name = "Navy ascending inner face__pivot";
  if (endpoint_navy_inner_17) {
    node_navy_inner_17.position.copy(endpoint_navy_inner_17.start);
    node_navy_inner_17.rotation.set(0, 0, 0);
    node_navy_inner_17.scale.set(1, 1, 1);
  } else {
    node_navy_inner_17.position.set(0.0, 0.0, 0.0);
    node_navy_inner_17.rotation.set(0.0, 0.0, 0.0);
    node_navy_inner_17.scale.set(0.985, 0.985, 0.94);
  }
  node_navy_inner_17.userData.sculptComponent = {"id": "navy-inner", "name": "Navy ascending inner face", "level": "meso", "role": "inner-face", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.16}, "parent": "navy-pivot", "attachment": {"parentId": "navy-pivot", "parentSocket": "navy-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 0.985, "height": 0.985, "depth": 0.94, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [0.985, 0.985, 0.94]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "navy-inner-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "navy-band", "materialLayers": ["navy-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(38, 55, 82, 1.0)", "secondaryAlbedo": "rgba(96, 119, 155, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(38, 55, 82, 1.0)"}, {"offset": 1, "color": "rgba(96, 119, 155, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_navy_inner_17.userData.actionProfile = {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "navy-inner-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["navy-pivot"] ?? root).add(node_navy_inner_17);
  nodes["navy-inner"] = node_navy_inner_17;
  const mesh_navy_inner_17Geometry = endpoint_navy_inner_17
    ? new THREE.CylinderGeometry(endpoint_navy_inner_17.endRadius, endpoint_navy_inner_17.baseRadius, endpoint_navy_inner_17.length, 32, 12)
    : new THREE.TorusGeometry(0.45, 0.072, 24, 96);
  const mesh_navy_inner_17 = new THREE.Mesh(
    mesh_navy_inner_17Geometry,
    materialMap["navy-band"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_navy_inner_17.name = "Navy ascending inner face";
  if (endpoint_navy_inner_17) {
    mesh_navy_inner_17.position.copy(endpoint_navy_inner_17.midpoint);
    mesh_navy_inner_17.quaternion.copy(endpoint_navy_inner_17.quaternion);
  }
  mesh_navy_inner_17.castShadow = options.castShadow ?? true;
  mesh_navy_inner_17.receiveShadow = options.receiveShadow ?? true;
  mesh_navy_inner_17.userData.sculptComponent = {"id": "navy-inner", "name": "Navy ascending inner face", "level": "meso", "role": "inner-face", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.16}, "parent": "navy-pivot", "attachment": {"parentId": "navy-pivot", "parentSocket": "navy-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 0.985, "height": 0.985, "depth": 0.94, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [0.985, 0.985, 0.94]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "navy-inner-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "navy-band", "materialLayers": ["navy-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(38, 55, 82, 1.0)", "secondaryAlbedo": "rgba(96, 119, 155, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(38, 55, 82, 1.0)"}, {"offset": 1, "color": "rgba(96, 119, 155, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_navy_inner_17.add(mesh_navy_inner_17);
  meshes["navy-inner"] = mesh_navy_inner_17;
  colliders["navy-inner"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_navy_inner_17);
  const socket_navy_inner_navy_inner_center_0 = new THREE.Object3D();
  socket_navy_inner_navy_inner_center_0.name = "navy-inner-center";
  socket_navy_inner_navy_inner_center_0.position.set(0.0, 0.0, 0.0);
  socket_navy_inner_navy_inner_center_0.rotation.set(0, 0, 0);
  socket_navy_inner_navy_inner_center_0.userData.socket = {"id": "navy-inner-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_navy_inner_17.add(socket_navy_inner_navy_inner_center_0);
  sockets["navy-inner:navy-inner-center"] = socket_navy_inner_navy_inner_center_0;

  const attachment_navy_runes_18 = {"parentId": "navy-pivot", "parentSocket": "navy-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_navy_runes_18 = makeAttachmentEndpoint(attachment_navy_runes_18);
  const node_navy_runes_18 = new THREE.Group();
  node_navy_runes_18.name = "Navy ascending rune relief__pivot";
  if (endpoint_navy_runes_18) {
    node_navy_runes_18.position.copy(endpoint_navy_runes_18.start);
    node_navy_runes_18.rotation.set(0, 0, 0);
    node_navy_runes_18.scale.set(1, 1, 1);
  } else {
    node_navy_runes_18.position.set(0.0, 0.0, 0.0);
    node_navy_runes_18.rotation.set(0.0, 0.0, 0.0);
    node_navy_runes_18.scale.set(1.0, 1.0, 1.0);
  }
  node_navy_runes_18.userData.sculptComponent = {"id": "navy-runes", "name": "Navy ascending rune relief", "level": "meso", "role": "surface-relief", "importance": 1, "confidence": 0.82, "primitive": "instanced-cluster", "topologyClass": "surface-relief", "topologyRationale": "A watertight primitive is sufficient for this centered component.", "geometryDescriptor": {"topologyIntent": "watertight procedural solid", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "navy-pivot", "attachment": {"parentId": "navy-pivot", "parentSocket": "navy-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "navy-runes-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "rune-gold", "materialLayers": ["rune-gold"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "navy-rune-path", "kind": "linework", "description": "Procedural diamonds, forks, nodes and connecting strokes."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(176, 138, 90, 1.0)", "secondaryAlbedo": "rgba(224, 192, 144, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(138, 106, 68, 1.0)"}, {"offset": 1, "color": "rgba(224, 192, 144, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_navy_runes_18.userData.actionProfile = {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "navy-runes-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["navy-pivot"] ?? root).add(node_navy_runes_18);
  nodes["navy-runes"] = node_navy_runes_18;
  const mesh_navy_runes_18Geometry = endpoint_navy_runes_18
    ? new THREE.CylinderGeometry(endpoint_navy_runes_18.endRadius, endpoint_navy_runes_18.baseRadius, endpoint_navy_runes_18.length, 32, 12)
    : new THREE.BoxGeometry(1, 1, 1, 12, 12, 12);
  const mesh_navy_runes_18 = new THREE.Mesh(
    mesh_navy_runes_18Geometry,
    materialMap["rune-gold"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_navy_runes_18.name = "Navy ascending rune relief";
  if (endpoint_navy_runes_18) {
    mesh_navy_runes_18.position.copy(endpoint_navy_runes_18.midpoint);
    mesh_navy_runes_18.quaternion.copy(endpoint_navy_runes_18.quaternion);
  }
  mesh_navy_runes_18.castShadow = options.castShadow ?? true;
  mesh_navy_runes_18.receiveShadow = options.receiveShadow ?? true;
  mesh_navy_runes_18.userData.sculptComponent = {"id": "navy-runes", "name": "Navy ascending rune relief", "level": "meso", "role": "surface-relief", "importance": 1, "confidence": 0.82, "primitive": "instanced-cluster", "topologyClass": "surface-relief", "topologyRationale": "A watertight primitive is sufficient for this centered component.", "geometryDescriptor": {"topologyIntent": "watertight procedural solid", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "navy-pivot", "attachment": {"parentId": "navy-pivot", "parentSocket": "navy-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "navy-runes-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "rune-gold", "materialLayers": ["rune-gold"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "navy-rune-path", "kind": "linework", "description": "Procedural diamonds, forks, nodes and connecting strokes."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(176, 138, 90, 1.0)", "secondaryAlbedo": "rgba(224, 192, 144, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(138, 106, 68, 1.0)"}, {"offset": 1, "color": "rgba(224, 192, 144, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_navy_runes_18.add(mesh_navy_runes_18);
  meshes["navy-runes"] = mesh_navy_runes_18;
  colliders["navy-runes"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_navy_runes_18);
  const socket_navy_runes_navy_runes_center_0 = new THREE.Object3D();
  socket_navy_runes_navy_runes_center_0.name = "navy-runes-center";
  socket_navy_runes_navy_runes_center_0.position.set(0.0, 0.0, 0.0);
  socket_navy_runes_navy_runes_center_0.rotation.set(0, 0, 0);
  socket_navy_runes_navy_runes_center_0.userData.socket = {"id": "navy-runes-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_navy_runes_18.add(socket_navy_runes_navy_runes_center_0);
  sockets["navy-runes:navy-runes-center"] = socket_navy_runes_navy_runes_center_0;

  const attachment_bronze_pivot_19 = {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_bronze_pivot_19 = makeAttachmentEndpoint(attachment_bronze_pivot_19);
  const node_bronze_pivot_19 = new THREE.Group();
  node_bronze_pivot_19.name = "Bronze descending pivot__pivot";
  if (endpoint_bronze_pivot_19) {
    node_bronze_pivot_19.position.copy(endpoint_bronze_pivot_19.start);
    node_bronze_pivot_19.rotation.set(0, 0, 0);
    node_bronze_pivot_19.scale.set(1, 1, 1);
  } else {
    node_bronze_pivot_19.position.set(0.0, 0.0, 0.0);
    node_bronze_pivot_19.rotation.set(0.76, 0.82, 0.72);
    node_bronze_pivot_19.scale.set(3.0, 3.0, 0.42);
  }
  node_bronze_pivot_19.userData.sculptComponent = {"id": "bronze-pivot", "name": "Bronze descending pivot", "level": "macro", "role": "band-pivot", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "root", "attachment": {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 3, "height": 3, "depth": 0.42, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0.76, 0.82, 0.72], "scale": [3, 3, 0.42]}, "actionProfile": {"animationRole": "independent-orbit", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "bronze-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "bronze-band", "materialLayers": ["bronze-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "bronze-closed-loop", "kind": "contour", "description": "Continuous closed loop with a readable side silhouette."}, {"id": "bronze-beveled-edge", "kind": "bevel", "description": "Rounded polished edges catch narrow highlights."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "blockout", "colorMaterialRecipe": {"dominantAlbedo": "rgba(139, 98, 73, 1.0)", "secondaryAlbedo": "rgba(197, 154, 114, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(139, 98, 73, 1.0)"}, {"offset": 1, "color": "rgba(197, 154, 114, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_bronze_pivot_19.userData.actionProfile = {"animationRole": "independent-orbit", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "bronze-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["root"] ?? root).add(node_bronze_pivot_19);
  nodes["bronze-pivot"] = node_bronze_pivot_19;
  const mesh_bronze_pivot_19Geometry = endpoint_bronze_pivot_19
    ? new THREE.CylinderGeometry(endpoint_bronze_pivot_19.endRadius, endpoint_bronze_pivot_19.baseRadius, endpoint_bronze_pivot_19.length, 32, 12)
    : new THREE.TorusGeometry(0.45, 0.081, 24, 96);
  const mesh_bronze_pivot_19 = new THREE.Mesh(
    mesh_bronze_pivot_19Geometry,
    materialMap["bronze-band"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_bronze_pivot_19.name = "Bronze descending pivot";
  if (endpoint_bronze_pivot_19) {
    mesh_bronze_pivot_19.position.copy(endpoint_bronze_pivot_19.midpoint);
    mesh_bronze_pivot_19.quaternion.copy(endpoint_bronze_pivot_19.quaternion);
  }
  mesh_bronze_pivot_19.castShadow = options.castShadow ?? true;
  mesh_bronze_pivot_19.receiveShadow = options.receiveShadow ?? true;
  mesh_bronze_pivot_19.userData.sculptComponent = {"id": "bronze-pivot", "name": "Bronze descending pivot", "level": "macro", "role": "band-pivot", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "root", "attachment": {"parentId": "root", "parentSocket": "root-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 3, "height": 3, "depth": 0.42, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0.76, 0.82, 0.72], "scale": [3, 3, 0.42]}, "actionProfile": {"animationRole": "independent-orbit", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "bronze-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "bronze-band", "materialLayers": ["bronze-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "bronze-closed-loop", "kind": "contour", "description": "Continuous closed loop with a readable side silhouette."}, {"id": "bronze-beveled-edge", "kind": "bevel", "description": "Rounded polished edges catch narrow highlights."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "blockout", "colorMaterialRecipe": {"dominantAlbedo": "rgba(139, 98, 73, 1.0)", "secondaryAlbedo": "rgba(197, 154, 114, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(139, 98, 73, 1.0)"}, {"offset": 1, "color": "rgba(197, 154, 114, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_bronze_pivot_19.add(mesh_bronze_pivot_19);
  meshes["bronze-pivot"] = mesh_bronze_pivot_19;
  colliders["bronze-pivot"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_bronze_pivot_19);
  const socket_bronze_pivot_bronze_pivot_center_0 = new THREE.Object3D();
  socket_bronze_pivot_bronze_pivot_center_0.name = "bronze-pivot-center";
  socket_bronze_pivot_bronze_pivot_center_0.position.set(0.0, 0.0, 0.0);
  socket_bronze_pivot_bronze_pivot_center_0.rotation.set(0, 0, 0);
  socket_bronze_pivot_bronze_pivot_center_0.userData.socket = {"id": "bronze-pivot-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_bronze_pivot_19.add(socket_bronze_pivot_bronze_pivot_center_0);
  sockets["bronze-pivot:bronze-pivot-center"] = socket_bronze_pivot_bronze_pivot_center_0;

  const attachment_bronze_shell_20 = {"parentId": "bronze-pivot", "parentSocket": "bronze-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_bronze_shell_20 = makeAttachmentEndpoint(attachment_bronze_shell_20);
  const node_bronze_shell_20 = new THREE.Group();
  node_bronze_shell_20.name = "Bronze descending visible shell__pivot";
  if (endpoint_bronze_shell_20) {
    node_bronze_shell_20.position.copy(endpoint_bronze_shell_20.start);
    node_bronze_shell_20.rotation.set(0, 0, 0);
    node_bronze_shell_20.scale.set(1, 1, 1);
  } else {
    node_bronze_shell_20.position.set(0.0, 0.0, 0.0);
    node_bronze_shell_20.rotation.set(0.0, 0.0, 0.0);
    node_bronze_shell_20.scale.set(1.0, 1.0, 1.0);
  }
  node_bronze_shell_20.userData.sculptComponent = {"id": "bronze-shell", "name": "Bronze descending visible shell", "level": "meso", "role": "band-shell", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.17}, "parent": "bronze-pivot", "attachment": {"parentId": "bronze-pivot", "parentSocket": "bronze-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "bronze-shell-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "bronze-band", "materialLayers": ["bronze-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(139, 98, 73, 1.0)", "secondaryAlbedo": "rgba(197, 154, 114, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(139, 98, 73, 1.0)"}, {"offset": 1, "color": "rgba(197, 154, 114, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_bronze_shell_20.userData.actionProfile = {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "bronze-shell-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["bronze-pivot"] ?? root).add(node_bronze_shell_20);
  nodes["bronze-shell"] = node_bronze_shell_20;
  const mesh_bronze_shell_20Geometry = endpoint_bronze_shell_20
    ? new THREE.CylinderGeometry(endpoint_bronze_shell_20.endRadius, endpoint_bronze_shell_20.baseRadius, endpoint_bronze_shell_20.length, 32, 12)
    : new THREE.TorusGeometry(0.45, 0.0765, 24, 96);
  const mesh_bronze_shell_20 = new THREE.Mesh(
    mesh_bronze_shell_20Geometry,
    materialMap["bronze-band"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_bronze_shell_20.name = "Bronze descending visible shell";
  if (endpoint_bronze_shell_20) {
    mesh_bronze_shell_20.position.copy(endpoint_bronze_shell_20.midpoint);
    mesh_bronze_shell_20.quaternion.copy(endpoint_bronze_shell_20.quaternion);
  }
  mesh_bronze_shell_20.castShadow = options.castShadow ?? true;
  mesh_bronze_shell_20.receiveShadow = options.receiveShadow ?? true;
  mesh_bronze_shell_20.userData.sculptComponent = {"id": "bronze-shell", "name": "Bronze descending visible shell", "level": "meso", "role": "band-shell", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.17}, "parent": "bronze-pivot", "attachment": {"parentId": "bronze-pivot", "parentSocket": "bronze-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "bronze-shell-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "bronze-band", "materialLayers": ["bronze-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(139, 98, 73, 1.0)", "secondaryAlbedo": "rgba(197, 154, 114, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(139, 98, 73, 1.0)"}, {"offset": 1, "color": "rgba(197, 154, 114, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_bronze_shell_20.add(mesh_bronze_shell_20);
  meshes["bronze-shell"] = mesh_bronze_shell_20;
  colliders["bronze-shell"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_bronze_shell_20);
  const socket_bronze_shell_bronze_shell_center_0 = new THREE.Object3D();
  socket_bronze_shell_bronze_shell_center_0.name = "bronze-shell-center";
  socket_bronze_shell_bronze_shell_center_0.position.set(0.0, 0.0, 0.0);
  socket_bronze_shell_bronze_shell_center_0.rotation.set(0, 0, 0);
  socket_bronze_shell_bronze_shell_center_0.userData.socket = {"id": "bronze-shell-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_bronze_shell_20.add(socket_bronze_shell_bronze_shell_center_0);
  sockets["bronze-shell:bronze-shell-center"] = socket_bronze_shell_bronze_shell_center_0;

  const attachment_bronze_inner_21 = {"parentId": "bronze-pivot", "parentSocket": "bronze-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_bronze_inner_21 = makeAttachmentEndpoint(attachment_bronze_inner_21);
  const node_bronze_inner_21 = new THREE.Group();
  node_bronze_inner_21.name = "Bronze descending inner face__pivot";
  if (endpoint_bronze_inner_21) {
    node_bronze_inner_21.position.copy(endpoint_bronze_inner_21.start);
    node_bronze_inner_21.rotation.set(0, 0, 0);
    node_bronze_inner_21.scale.set(1, 1, 1);
  } else {
    node_bronze_inner_21.position.set(0.0, 0.0, 0.0);
    node_bronze_inner_21.rotation.set(0.0, 0.0, 0.0);
    node_bronze_inner_21.scale.set(0.985, 0.985, 0.94);
  }
  node_bronze_inner_21.userData.sculptComponent = {"id": "bronze-inner", "name": "Bronze descending inner face", "level": "meso", "role": "inner-face", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.16}, "parent": "bronze-pivot", "attachment": {"parentId": "bronze-pivot", "parentSocket": "bronze-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 0.985, "height": 0.985, "depth": 0.94, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [0.985, 0.985, 0.94]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "bronze-inner-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "bronze-band", "materialLayers": ["bronze-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(139, 98, 73, 1.0)", "secondaryAlbedo": "rgba(197, 154, 114, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(139, 98, 73, 1.0)"}, {"offset": 1, "color": "rgba(197, 154, 114, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_bronze_inner_21.userData.actionProfile = {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "bronze-inner-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["bronze-pivot"] ?? root).add(node_bronze_inner_21);
  nodes["bronze-inner"] = node_bronze_inner_21;
  const mesh_bronze_inner_21Geometry = endpoint_bronze_inner_21
    ? new THREE.CylinderGeometry(endpoint_bronze_inner_21.endRadius, endpoint_bronze_inner_21.baseRadius, endpoint_bronze_inner_21.length, 32, 12)
    : new THREE.TorusGeometry(0.45, 0.072, 24, 96);
  const mesh_bronze_inner_21 = new THREE.Mesh(
    mesh_bronze_inner_21Geometry,
    materialMap["bronze-band"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_bronze_inner_21.name = "Bronze descending inner face";
  if (endpoint_bronze_inner_21) {
    mesh_bronze_inner_21.position.copy(endpoint_bronze_inner_21.midpoint);
    mesh_bronze_inner_21.quaternion.copy(endpoint_bronze_inner_21.quaternion);
  }
  mesh_bronze_inner_21.castShadow = options.castShadow ?? true;
  mesh_bronze_inner_21.receiveShadow = options.receiveShadow ?? true;
  mesh_bronze_inner_21.userData.sculptComponent = {"id": "bronze-inner", "name": "Bronze descending inner face", "level": "meso", "role": "inner-face", "importance": 1, "confidence": 0.82, "primitive": "torus", "topologyClass": "assembled-solid", "topologyRationale": "A closed toroidal solid proves continuity from non-reference viewpoints.", "geometryDescriptor": {"topologyIntent": "closed beveled orbital band", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.16}, "parent": "bronze-pivot", "attachment": {"parentId": "bronze-pivot", "parentSocket": "bronze-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 0.985, "height": 0.985, "depth": 0.94, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [0.985, 0.985, 0.94]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "bronze-inner-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "bronze-band", "materialLayers": ["bronze-band"], "deformations": [], "joints": [], "seams": [], "localFeatures": [], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(139, 98, 73, 1.0)", "secondaryAlbedo": "rgba(197, 154, 114, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(139, 98, 73, 1.0)"}, {"offset": 1, "color": "rgba(197, 154, 114, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_bronze_inner_21.add(mesh_bronze_inner_21);
  meshes["bronze-inner"] = mesh_bronze_inner_21;
  colliders["bronze-inner"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_bronze_inner_21);
  const socket_bronze_inner_bronze_inner_center_0 = new THREE.Object3D();
  socket_bronze_inner_bronze_inner_center_0.name = "bronze-inner-center";
  socket_bronze_inner_bronze_inner_center_0.position.set(0.0, 0.0, 0.0);
  socket_bronze_inner_bronze_inner_center_0.rotation.set(0, 0, 0);
  socket_bronze_inner_bronze_inner_center_0.userData.socket = {"id": "bronze-inner-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_bronze_inner_21.add(socket_bronze_inner_bronze_inner_center_0);
  sockets["bronze-inner:bronze-inner-center"] = socket_bronze_inner_bronze_inner_center_0;

  const attachment_bronze_runes_22 = {"parentId": "bronze-pivot", "parentSocket": "bronze-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]};
  const endpoint_bronze_runes_22 = makeAttachmentEndpoint(attachment_bronze_runes_22);
  const node_bronze_runes_22 = new THREE.Group();
  node_bronze_runes_22.name = "Bronze descending rune relief__pivot";
  if (endpoint_bronze_runes_22) {
    node_bronze_runes_22.position.copy(endpoint_bronze_runes_22.start);
    node_bronze_runes_22.rotation.set(0, 0, 0);
    node_bronze_runes_22.scale.set(1, 1, 1);
  } else {
    node_bronze_runes_22.position.set(0.0, 0.0, 0.0);
    node_bronze_runes_22.rotation.set(0.0, 0.0, 0.0);
    node_bronze_runes_22.scale.set(1.0, 1.0, 1.0);
  }
  node_bronze_runes_22.userData.sculptComponent = {"id": "bronze-runes", "name": "Bronze descending rune relief", "level": "meso", "role": "surface-relief", "importance": 1, "confidence": 0.82, "primitive": "instanced-cluster", "topologyClass": "surface-relief", "topologyRationale": "A watertight primitive is sufficient for this centered component.", "geometryDescriptor": {"topologyIntent": "watertight procedural solid", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "bronze-pivot", "attachment": {"parentId": "bronze-pivot", "parentSocket": "bronze-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "bronze-runes-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "rune-gold", "materialLayers": ["rune-gold"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "bronze-rune-path", "kind": "linework", "description": "Procedural diamonds, forks, nodes and connecting strokes."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(176, 138, 90, 1.0)", "secondaryAlbedo": "rgba(224, 192, 144, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(138, 106, 68, 1.0)"}, {"offset": 1, "color": "rgba(224, 192, 144, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_bronze_runes_22.userData.actionProfile = {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "bronze-runes-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}};
  (nodes["bronze-pivot"] ?? root).add(node_bronze_runes_22);
  nodes["bronze-runes"] = node_bronze_runes_22;
  const mesh_bronze_runes_22Geometry = endpoint_bronze_runes_22
    ? new THREE.CylinderGeometry(endpoint_bronze_runes_22.endRadius, endpoint_bronze_runes_22.baseRadius, endpoint_bronze_runes_22.length, 32, 12)
    : new THREE.BoxGeometry(1, 1, 1, 12, 12, 12);
  const mesh_bronze_runes_22 = new THREE.Mesh(
    mesh_bronze_runes_22Geometry,
    materialMap["rune-gold"] ?? new THREE.MeshStandardMaterial({ color: 0x888888 })
  );
  mesh_bronze_runes_22.name = "Bronze descending rune relief";
  if (endpoint_bronze_runes_22) {
    mesh_bronze_runes_22.position.copy(endpoint_bronze_runes_22.midpoint);
    mesh_bronze_runes_22.quaternion.copy(endpoint_bronze_runes_22.quaternion);
  }
  mesh_bronze_runes_22.castShadow = options.castShadow ?? true;
  mesh_bronze_runes_22.receiveShadow = options.receiveShadow ?? true;
  mesh_bronze_runes_22.userData.sculptComponent = {"id": "bronze-runes", "name": "Bronze descending rune relief", "level": "meso", "role": "surface-relief", "importance": 1, "confidence": 0.82, "primitive": "instanced-cluster", "topologyClass": "surface-relief", "topologyRationale": "A watertight primitive is sufficient for this centered component.", "geometryDescriptor": {"topologyIntent": "watertight procedural solid", "edgeTreatment": {"type": "bevel", "bevelRadius": 0.035, "segments": 4}, "deformationStack": [], "uvStrategy": "generated procedural coordinates", "normalStrategy": "smooth vertex normals", "torusTubeRatio": 0.18}, "parent": "bronze-pivot", "attachment": {"parentId": "bronze-pivot", "parentSocket": "bronze-pivot-center", "contactType": "nested-transform", "localStart": [0, 0, 0], "localEnd": [0, 0, 0], "contactNormal": [0, 1, 0], "overlap": 0.02, "gapTolerance": 0.01, "evidenceRefs": ["full-object"]}, "dimensions": {"width": 1, "height": 1, "depth": 1, "units": "relative", "confidence": 0.82}, "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]}, "actionProfile": {"animationRole": "static", "pivot": {"mode": "center", "localPosition": [0, 0, 0], "axis": [0, 1, 0], "confidence": 0.95}, "transformChannels": {"translate": true, "rotate": true, "scale": true, "bend": false, "twist": false, "detach": false, "visibility": true, "materialState": true}, "sockets": [{"id": "bronze-runes-center", "type": "pivot", "localPosition": [0, 0, 0]}], "collider": {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."}, "constraints": [], "destruction": {"breakable": false, "fractureGroup": "root", "seamRefs": [], "detachableFragments": [], "breakImpulse": 0, "debrisMaterial": "base"}}, "material": "rune-gold", "materialLayers": ["rune-gold"], "deformations": [], "joints": [], "seams": [], "localFeatures": [{"id": "bronze-rune-path", "kind": "linework", "description": "Procedural diamonds, forks, nodes and connecting strokes."}], "surfaceDetail": {"macroRoughness": 0.08, "microRoughness": 0.04, "bumpAmplitude": 0.012, "normalPattern": "fine directional brushing", "displacementPattern": "raised rune relief", "occlusionPattern": "crossing and inner-face cavity darkening", "edgeWearPattern": "polished bevel highlights", "notes": "Satin metal face with glossier bevel and glyph relief."}, "evidenceRefs": ["full-object"], "details": [], "fidelityTier": "structural-pass", "colorMaterialRecipe": {"dominantAlbedo": "rgba(176, 138, 90, 1.0)", "secondaryAlbedo": "rgba(224, 192, 144, 1.0)", "materialClass": "metal", "materialClassConfidence": 0.92, "colorGradient": {"type": "linear", "stops": [{"offset": 0, "color": "rgba(138, 106, 68, 1.0)"}, {"offset": 1, "color": "rgba(224, 192, 144, 1.0)"}]}, "evidenceRefs": ["full-object"]}};
  node_bronze_runes_22.add(mesh_bronze_runes_22);
  meshes["bronze-runes"] = mesh_bronze_runes_22;
  colliders["bronze-runes"] = {"type": "compound-torus", "offset": [0, 0, 0], "scale": [1, 1, 1], "isTrigger": false, "notes": "Authoring metadata only; the deployed video has no physics runtime."};
  destructionGroups["root"] ??= [];
  destructionGroups["root"].push(node_bronze_runes_22);
  const socket_bronze_runes_bronze_runes_center_0 = new THREE.Object3D();
  socket_bronze_runes_bronze_runes_center_0.name = "bronze-runes-center";
  socket_bronze_runes_bronze_runes_center_0.position.set(0.0, 0.0, 0.0);
  socket_bronze_runes_bronze_runes_center_0.rotation.set(0, 0, 0);
  socket_bronze_runes_bronze_runes_center_0.userData.socket = {"id": "bronze-runes-center", "type": "pivot", "localPosition": [0, 0, 0]};
  node_bronze_runes_22.add(socket_bronze_runes_bronze_runes_center_0);
  sockets["bronze-runes:bronze-runes-center"] = socket_bronze_runes_bronze_runes_center_0;

  root.userData.sculptRuntime = { nodes, meshes, sockets, colliders, destructionGroups } satisfies ProceduralModelRuntime;
  root.userData.lookDevTargets = {"qualityPriority": "reference-fidelity", "materialPass": {"albedoPaletteRequired": true, "roughnessVariationRequired": true, "normalOrBumpRequired": true, "localOverridesRequired": true, "minimumTextureResolution": 1024, "preferredTextureResolution": 2048, "independentMapChannels": ["albedo", "roughness", "height", "normal", "ambient-occlusion"], "requiredSurfaceFrequencyBands": ["macro", "meso", "micro"], "geometryReliefRequiredWhenSilhouetteAffected": true, "referencePbrExtraction": {"requiredWhenSourceImagePresent": true, "targetThreshold": 0.7, "stopOnLowConfidence": true, "script": "forge/stage1_intake/extract_pbr_evidence.py", "acceptedLimitation": "single-image extraction is reference-derived inference, not exact photogrammetry"}, "mustAvoid": ["single flat albedo per material", "uniform roughness", "albedo texture reused as roughness/height/normal/AO", "single-frequency random noise", "plastic-looking smooth bark, stone, cloth, foliage, or aged material", "local color/detail described only in prose without material masks", "claiming exact PBR recovery when confidence is below the target threshold"]}, "lightingPass": {"requiredTerms": ["key light", "fill light", "rim or environment light", "exposure", "tone mapping", "background", "contact shadow"], "mustAvoid": ["ambient-only lighting", "flat value range", "missing contact shadow", "reference lighting copied without separating material readability"]}, "screenshotReview": ["Compare albedo palette and local color zones.", "Compare roughness/normal/bump response under light.", "Compare cavity dirt, edge wear, stains, moss, scratches, or other local masks.", "Compare key/fill/rim structure, exposure, tone mapping, background, and contact shadows.", "Capture a neutral-light render to verify material readability without reference lighting.", "Capture a grazing-light close-up to expose flat normals, uniform roughness, tiling, and plastic highlights.", "Capture a reference-matched render from the same camera framing as the source."]};
  root.userData.actionReadiness = {
    note: 'Use root.userData.sculptRuntime.nodes for transforms, sockets for attachments, colliders for physics proxies, and destructionGroups for breakable sets.',
  };
  return root;
}

export function createPantheonInterwovenOracleSphereLookDevLights(
  mode: 'neutral' | 'grazing' | 'reference' = 'neutral',
): THREE.Group {
  const lights = new THREE.Group();
  lights.name = "Pantheon interwoven oracle sphere look-dev lights";
  const hemi = new THREE.HemisphereLight(
    mode === 'reference' ? 0xfff0d6 : 0xf2f4ff,
    0x363b42,
    mode === 'grazing' ? 0.28 : mode === 'reference' ? 0.72 : 0.85,
  );
  lights.add(hemi);
  const key = new THREE.DirectionalLight(
    mode === 'reference' ? 0xffcf8a : 0xfff4e8,
    mode === 'grazing' ? 4.2 : mode === 'reference' ? 2.6 : 2.15,
  );
  if (mode === 'grazing') key.position.set(7.5, 1.1, 4.0);
  else if (mode === 'reference') key.position.set(-4.5, 7.5, 5.0);
  else key.position.set(-4.0, 6.0, 5.5);
  key.castShadow = true;
  key.shadow.mapSize.set(4096, 4096);
  key.shadow.bias = -0.00025;
  key.shadow.normalBias = 0.018;
  key.shadow.radius = 7;
  key.shadow.blurSamples = 24;
  key.shadow.camera.near = 0.5;
  key.shadow.camera.far = 30;
  key.shadow.camera.left = -2.6;
  key.shadow.camera.right = 2.6;
  key.shadow.camera.top = 2.6;
  key.shadow.camera.bottom = -2.6;
  key.shadow.camera.updateProjectionMatrix();
  lights.add(key);
  const fill = new THREE.DirectionalLight(0xa8c4ff, mode === 'grazing' ? 0.12 : 0.42);
  fill.position.set(4.0, 3.0, 3.5);
  lights.add(fill);
  const rim = new THREE.DirectionalLight(0xfff1c4, mode === 'grazing' ? 0.28 : 0.85);
  rim.position.set(0.5, 4.5, -6.0);
  lights.add(rim);
  lights.userData.reviewMode = mode;
  lights.userData.lightingFromPhoto = ["Key light: warm area light from upper-left/front, color #FFE0A3, intensity 3.2.", "Fill light: cool soft area light from lower-right/front, color #B7D8D2, intensity 1.1.", "Rim light: warm-neutral back light, color #FFF1D0, intensity 2.0.", "Environment light: low-intensity warm studio environment for metal readability.", "Exposure 1.05 with ACES filmic tone mapping; preserve band hue separation.", "Transparent background with soft ambient occlusion/contact shadow at band crossings; no ground plane in exported media."];
  lights.userData.lookDevTargets = {"qualityPriority": "reference-fidelity", "materialPass": {"albedoPaletteRequired": true, "roughnessVariationRequired": true, "normalOrBumpRequired": true, "localOverridesRequired": true, "minimumTextureResolution": 1024, "preferredTextureResolution": 2048, "independentMapChannels": ["albedo", "roughness", "height", "normal", "ambient-occlusion"], "requiredSurfaceFrequencyBands": ["macro", "meso", "micro"], "geometryReliefRequiredWhenSilhouetteAffected": true, "referencePbrExtraction": {"requiredWhenSourceImagePresent": true, "targetThreshold": 0.7, "stopOnLowConfidence": true, "script": "forge/stage1_intake/extract_pbr_evidence.py", "acceptedLimitation": "single-image extraction is reference-derived inference, not exact photogrammetry"}, "mustAvoid": ["single flat albedo per material", "uniform roughness", "albedo texture reused as roughness/height/normal/AO", "single-frequency random noise", "plastic-looking smooth bark, stone, cloth, foliage, or aged material", "local color/detail described only in prose without material masks", "claiming exact PBR recovery when confidence is below the target threshold"]}, "lightingPass": {"requiredTerms": ["key light", "fill light", "rim or environment light", "exposure", "tone mapping", "background", "contact shadow"], "mustAvoid": ["ambient-only lighting", "flat value range", "missing contact shadow", "reference lighting copied without separating material readability"]}, "screenshotReview": ["Compare albedo palette and local color zones.", "Compare roughness/normal/bump response under light.", "Compare cavity dirt, edge wear, stains, moss, scratches, or other local masks.", "Compare key/fill/rim structure, exposure, tone mapping, background, and contact shadows.", "Capture a neutral-light render to verify material readability without reference lighting.", "Capture a grazing-light close-up to expose flat normals, uniform roughness, tiling, and plastic highlights.", "Capture a reference-matched render from the same camera framing as the source."]};
  return lights;
}

// PBR materials (clearcoat/iridescence/transmission/anisotropy) need an environment
// map to visually behave as intended — call this once per renderer and assign the
// result to scene.environment before rendering. No external HDR asset required.
export function createPantheonInterwovenOracleSphereEnvironment(renderer: THREE.WebGLRenderer): THREE.Texture {
  const pmrem = new THREE.PMREMGenerator(renderer);
  const texture = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  pmrem.dispose();
  return texture;
}

// Plan 1.3 §3.2 — auto-framing by bounding box. The Divine Eye can only compare a
// render to the reference if the object is FRAMED consistently (an object framed
// differently scores as wrong even when its shape is right). This positions the camera
// deterministically from the object's bounding box so it fills the frame at a stable
// margin, and sets near/far to the object scale. Call after adding the model to the
// scene, and again on resize (after updating camera.aspect).
export function framePantheonInterwovenOracleSphereCamera(
  camera: THREE.PerspectiveCamera,
  object: THREE.Object3D,
  options: { margin?: number; azimuthDeg?: number; elevationDeg?: number } = {},
): void {
  const box = new THREE.Box3().setFromObject(object);
  if (box.isEmpty()) return;
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const margin = options.margin ?? 1.15;
  const maxDim = Math.max(size.x, size.y, size.z) * margin;
  const fov = (camera.fov * Math.PI) / 180;
  // distance so the largest object dimension fits vertically in the frame
  const distance = (maxDim / 2) / Math.tan(fov / 2);
  const az = ((options.azimuthDeg ?? 0) * Math.PI) / 180;
  const el = ((options.elevationDeg ?? 0) * Math.PI) / 180;
  const dir = new THREE.Vector3(
    Math.sin(az) * Math.cos(el),
    Math.sin(el),
    Math.cos(az) * Math.cos(el),
  );
  camera.position.copy(center).addScaledVector(dir, distance);
  camera.near = Math.max(0.01, distance - maxDim);
  camera.far = distance + maxDim * 2;
  camera.lookAt(center);
  camera.updateProjectionMatrix();
}

// Plan 1.3 §3.2c — PRESENTATION composer (DOF + bloom). CRITICAL (R-POSTFX): this is
// for the showcase/hero render ONLY. The Divine Eye's EVALUATION render MUST use a
// plain renderer with NO composer — bloom blows highlights and DOF blurs edges, which
// would corrupt the deterministic IoU/DCD/edge/blowout signals. Enable dof/bloom ONLY
// when the reference photo actually exhibits them (detect_reference_effects.py authorizes).
export function createPantheonInterwovenOracleSpherePresentationComposer(
  renderer: THREE.WebGLRenderer,
  scene: THREE.Scene,
  camera: THREE.Camera,
  options: { dof?: boolean; bloom?: boolean; bloomStrength?: number; dofFocus?: number; dofAperture?: number } = {},
): EffectComposer {
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  if (options.dof) {
    composer.addPass(new BokehPass(scene, camera, {
      focus: options.dofFocus ?? 10.0,
      aperture: options.dofAperture ?? 0.0002,
      maxblur: 0.01,
    }));
  }
  if (options.bloom) {
    const size = new THREE.Vector2();
    renderer.getSize(size);
    composer.addPass(new UnrealBloomPass(size, options.bloomStrength ?? 0.4, 0.4, 0.85));
  }
  return composer;
}

export function configurePantheonInterwovenOracleSphereRenderer(renderer: THREE.WebGLRenderer): void {
  // Load-bearing for view-dependent finishes (anodized / Doppler): without ACES + sRGB
  // the environment reflection reads flat/washed instead of a believable metal response.
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
}

export function createPantheonInterwovenOracleSphereInspectControls(
  camera: THREE.Camera,
  domElement: HTMLElement,
): OrbitControls {
  // View-dependent finishes only read correctly once the user orbits — their color
  // comes from the environment reflection, not albedo, so free rotation matters here.
  const controls = new OrbitControls(camera, domElement);
  controls.enableDamping = true;
  controls.minDistance = 1.0;
  controls.maxDistance = 8.0;
  controls.autoRotate = false;
  return controls;
}
