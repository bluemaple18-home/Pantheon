import { deflateSync } from "node:zlib";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const OUTPUT = resolve(ROOT, "public/material-identity");
const WIDTH = 1024;
const MASK_HEIGHT = 256;
const NORMAL_HEIGHT = 512;
const TILE_WIDTH = WIDTH / 5;
const TAU = Math.PI * 2;

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const label = Buffer.from(type);
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length);
  const checksum = Buffer.alloc(4);
  checksum.writeUInt32BE(crc32(Buffer.concat([label, data])));
  return Buffer.concat([length, label, data, checksum]);
}

function writePng(path, width, height, pixels) {
  const raw = Buffer.alloc((width * 4 + 1) * height);
  for (let y = 0; y < height; y += 1) {
    const row = y * (width * 4 + 1);
    raw[row] = 0;
    pixels.copy(raw, row + 1, y * width * 4, (y + 1) * width * 4);
  }
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;
  ihdr[9] = 6;
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(
    path,
    Buffer.concat([
      signature,
      chunk("IHDR", ihdr),
      chunk("IDAT", deflateSync(raw, { level: 9 })),
      chunk("IEND", Buffer.alloc(0)),
    ]),
  );
}

function fract(value) {
  return value - Math.floor(value);
}

function noise(x, y, seed) {
  return fract(Math.sin(x * 127.1 + y * 311.7 + seed * 74.7) * 43758.5453);
}

function smoothstep(a, b, value) {
  const t = Math.max(0, Math.min(1, (value - a) / (b - a)));
  return t * t * (3 - 2 * t);
}

function line(value, center, width) {
  return 1 - smoothstep(width * 0.35, width, Math.abs(value - center));
}

function identityFields(id, u, v) {
  const n = noise(Math.floor(u * 84), Math.floor(v * 92), id + 1);
  let brush = 0;
  let roughness = 0.5;
  let polished = 0;
  let oxidized = 0;
  let micro = 0;
  let relief = 0;

  if (id === 0) {
    const longGrain = Math.pow(0.5 + 0.5 * Math.sin(v * 920 + noise(u * 18, 1, 2) * 5), 8);
    const quietGate = smoothstep(0.2, 0.34, Math.sin(u * TAU * 2.1) * 0.5 + 0.5);
    brush = longGrain * (0.18 + quietGate * 0.54);
    polished = line(fract(u * 2.2), 0.52, 0.12) * 0.7;
    roughness = 0.48 - polished * 0.2 + brush * 0.08;
    const pit = n > 0.996 ? 1 : 0;
    micro = brush * 0.28 + pit;
    relief = pit * 0.55;
  } else if (id === 1) {
    const x = (u - 0.5) * 1.7;
    const y = v - 0.5;
    const radius = Math.hypot(x, y);
    const arc = Math.pow(0.5 + 0.5 * Math.sin(radius * 96), 12);
    const frameU = Math.max(line(fract(u * 3), 0.12, 0.035), line(fract(u * 3), 0.88, 0.035));
    const frameV = Math.max(line(v, 0.16, 0.025), line(v, 0.84, 0.025));
    brush = arc * 0.7;
    polished = Math.max(frameU, frameV);
    oxidized = smoothstep(0.48, 0.82, noise(u * 8, v * 5, 8)) * 0.56;
    roughness = 0.58 + oxidized * 0.18 - polished * 0.34;
    micro = arc * 0.46 + noise(u * 230, v * 170, 3) * 0.1;
    relief = Math.max(frameU, frameV) * 0.82;
  } else if (id === 2) {
    const cell = fract(u * 12);
    const segment = smoothstep(0.06, 0.1, cell) * (1 - smoothstep(0.82, 0.94, cell));
    const row = Math.floor(v * 6) % 2;
    brush = Math.pow(0.5 + 0.5 * Math.sin(v * 680), 10) * segment;
    polished = segment * (row ? 0.5 : 0.78);
    roughness = 0.5 - polished * 0.2 + (1 - segment) * 0.12;
    const slot = line(v, row ? 0.34 : 0.66, 0.025) * segment;
    const node = Math.hypot(fract(u * 8) - 0.5, (v - 0.5) * 1.8) < 0.055 ? 1 : 0;
    micro = brush * 0.36 + slot * 0.6;
    relief = Math.max(slot, node * 0.7);
  } else if (id === 3) {
    const channelA = line(v, 0.32 + Math.sin(u * TAU * 1.25) * 0.1, 0.055);
    const channelB = line(v, 0.7 + Math.cos(u * TAU * 1.05) * 0.08, 0.045);
    polished = Math.max(channelA, channelB);
    brush = noise(u * 460, v * 420, 5);
    roughness = 0.68 - polished * 0.42 + (brush - 0.5) * 0.08;
    micro = (noise(u * 540, v * 510, 7) - 0.5) * 0.9;
    relief = polished * 0.22;
  } else {
    const handA = Math.pow(0.5 + 0.5 * Math.sin((u * 1.8 + v * 0.42) * 180), 8);
    const handB = Math.pow(0.5 + 0.5 * Math.sin((u * 1.2 - v * 0.65) * 136), 10);
    const turning = Math.pow(0.5 + 0.5 * Math.sin(Math.hypot(u - 0.48, (v - 0.5) * 0.5) * 170), 12);
    brush = Math.max(handA * 0.62, handB * 0.5);
    oxidized = smoothstep(0.42, 0.76, noise(u * 7, v * 5, 11));
    polished = smoothstep(0.68, 0.9, noise(u * 4, v * 4, 14)) * 0.75;
    roughness = 0.53 + oxidized * 0.28 - polished * 0.26;
    micro = brush * 0.42 + turning * 0.18;
    const stamp = Math.max(line(fract(u * 5), 0.12, 0.035), line(fract(u * 5), 0.88, 0.035));
    relief = stamp * (0.35 + turning * 0.5);
  }

  return {
    brush: Math.max(0, Math.min(1, brush)),
    roughness: Math.max(0.06, Math.min(0.94, roughness)),
    polished: Math.max(0, Math.min(1, polished)),
    oxidized: Math.max(0, Math.min(1, oxidized)),
    micro: Math.max(-1, Math.min(1, micro)),
    relief: Math.max(0, Math.min(1, relief)),
  };
}

function heightAt(id, u, v, includeRelief) {
  const fields = identityFields(id, u, v);
  return fields.micro * 0.38 + (includeRelief ? fields.relief * 0.62 : 0);
}

const mask = Buffer.alloc(WIDTH * MASK_HEIGHT * 4);
for (let y = 0; y < MASK_HEIGHT; y += 1) {
  const v = y / (MASK_HEIGHT - 1);
  for (let x = 0; x < WIDTH; x += 1) {
    const id = Math.min(4, Math.floor(x / TILE_WIDTH));
    const u = (x - id * TILE_WIDTH) / TILE_WIDTH;
    const fields = identityFields(id, u, v);
    const offset = (y * WIDTH + x) * 4;
    mask[offset] = Math.round(fields.brush * 255);
    mask[offset + 1] = Math.round(fields.roughness * 255);
    mask[offset + 2] = Math.round(fields.polished * 255);
    mask[offset + 3] = Math.round(fields.oxidized * 255);
  }
}

const normal = Buffer.alloc(WIDTH * NORMAL_HEIGHT * 4);
for (let y = 0; y < NORMAL_HEIGHT; y += 1) {
  const lower = y >= NORMAL_HEIGHT / 2;
  const localY = y % (NORMAL_HEIGHT / 2);
  const v = localY / (NORMAL_HEIGHT / 2 - 1);
  for (let x = 0; x < WIDTH; x += 1) {
    const id = Math.min(4, Math.floor(x / TILE_WIDTH));
    const u = (x - id * TILE_WIDTH) / TILE_WIDTH;
    const du = 1 / TILE_WIDTH;
    const dv = 1 / (NORMAL_HEIGHT / 2);
    const hx =
      heightAt(id, Math.min(1, u + du), v, lower) -
      heightAt(id, Math.max(0, u - du), v, lower);
    const hy =
      heightAt(id, u, Math.min(1, v + dv), lower) -
      heightAt(id, u, Math.max(0, v - dv), lower);
    const strength = id === 3 ? 2.4 : 3.2;
    let nx = -hx * strength;
    let ny = -hy * strength;
    let nz = 1;
    const length = Math.hypot(nx, ny, nz);
    nx /= length;
    ny /= length;
    nz /= length;
    const offset = (y * WIDTH + x) * 4;
    normal[offset] = Math.round((nx * 0.5 + 0.5) * 255);
    normal[offset + 1] = Math.round((ny * 0.5 + 0.5) * 255);
    normal[offset + 2] = Math.round((nz * 0.5 + 0.5) * 255);
    normal[offset + 3] = 255;
  }
}

writePng(resolve(OUTPUT, "pantheon-identity-mask-atlas.png"), WIDTH, MASK_HEIGHT, mask);
writePng(resolve(OUTPUT, "pantheon-identity-normal-atlas.png"), WIDTH, NORMAL_HEIGHT, normal);
console.log(JSON.stringify({
  output: OUTPUT,
  mask: [WIDTH, MASK_HEIGHT],
  normal: [WIDTH, NORMAL_HEIGHT],
  tiles: 5,
}, null, 2));
