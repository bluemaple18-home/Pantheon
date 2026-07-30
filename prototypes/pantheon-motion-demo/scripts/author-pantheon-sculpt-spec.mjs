import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "../../..");
const defaultEvidenceDir = path.join(
  repoRoot,
  "artifacts/pantheon_motion_img2threejs/evidence",
);
const sourcePath =
  process.argv[2] ?? path.join(defaultEvidenceDir, "sculpt-spec-pbr.json");
const outputPath =
  process.argv[3] ?? path.join(defaultEvidenceDir, "sculpt-spec.json");
const referenceImage =
  process.argv[4] ?? "app/web/static/pantheon-oracle-sphere-transparent.png";
const spec = JSON.parse(fs.readFileSync(sourcePath, "utf8"));
spec.targetName = "Pantheon Visual Target v1";
spec.targetId = "pantheon-visual-target-v1";
spec.sourceImage = referenceImage;
spec.preSpecAssessment.sourceImage = referenceImage;
const rootTemplate = spec.componentTree[0];
const materialTemplate = spec.materials[0];
const referencePbr = materialTemplate.referencePbr;

const bands = [
  { id: "gold", name: "Gold meridian", color: "#C99B4F", secondary: "#F0D18B", rotation: [0.18, 0.04, -0.55], speed: 0.055 },
  { id: "teal", name: "Jade diagonal", color: "#497F77", secondary: "#91B7A5", rotation: [1.08, 0.22, 0.42], speed: -0.043 },
  { id: "rose", name: "Rose equator", color: "#9E5960", secondary: "#D69A91", rotation: [0.55, 1.12, -0.08], speed: 0.037 },
  { id: "navy", name: "Navy ascending", color: "#263752", secondary: "#60779B", rotation: [1.16, -0.64, -0.42], speed: -0.031 },
  { id: "bronze", name: "Bronze descending", color: "#8B6249", secondary: "#C59A72", rotation: [0.76, 0.82, 0.72], speed: 0.027 }
];

function rgba(hex) {
  const value = Number.parseInt(hex.slice(1), 16);
  return `rgba(${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255}, 1.0)`;
}

function attachment(parentId) {
  return {
    parentId,
    parentSocket: `${parentId}-center`,
    contactType: "nested-transform",
    localStart: [0, 0, 0],
    localEnd: [0, 0, 0],
    contactNormal: [0, 1, 0],
    overlap: 0.02,
    gapTolerance: 0.01,
    evidenceRefs: ["full-object"]
  };
}

function component({
  id,
  name,
  level,
  role,
  primitive,
  parent,
  material,
  rotation = [0, 0, 0],
  scale = [1, 1, 1],
  animationRole = "static",
  localFeatures = [],
  torusTubeRatio = 0.18
}) {
  const node = structuredClone(rootTemplate);
  node.id = id;
  node.name = name;
  node.level = level;
  node.role = role;
  node.primitive = primitive;
  node.parent = parent;
  node.attachment = parent ? attachment(parent) : null;
  node.material = material;
  node.materialLayers = material ? [material] : [];
  node.transform = { position: [0, 0, 0], rotation, scale };
  node.dimensions = { width: scale[0], height: scale[1], depth: scale[2], units: "relative", confidence: 0.82 };
  node.geometryDescriptor = {
    topologyIntent: primitive === "torus" ? "closed beveled orbital band" : "watertight procedural solid",
    edgeTreatment: { type: "bevel", bevelRadius: 0.035, segments: 4 },
    deformationStack: [],
    uvStrategy: "generated procedural coordinates",
    normalStrategy: "smooth vertex normals",
    torusTubeRatio
  };
  node.topologyClass = role === "surface-relief" ? "surface-relief" : "assembled-solid";
  node.topologyRationale = primitive === "torus"
    ? "A closed toroidal solid proves continuity from non-reference viewpoints."
    : "A watertight primitive is sufficient for this centered component.";
  node.actionProfile.animationRole = animationRole;
  node.actionProfile.pivot = {
    mode: "center",
    localPosition: [0, 0, 0],
    axis: [0, 1, 0],
    confidence: 0.95
  };
  node.actionProfile.collider = {
    type: primitive === "sphere" ? "sphere" : "compound-torus",
    offset: [0, 0, 0],
    scale: [1, 1, 1],
    isTrigger: false,
    notes: "Authoring metadata only; the deployed video has no physics runtime."
  };
  node.actionProfile.sockets = [{ id: `${id}-center`, type: "pivot", localPosition: [0, 0, 0] }];
  node.localFeatures = localFeatures;
  node.surfaceDetail = {
    macroRoughness: 0.08,
    microRoughness: 0.04,
    bumpAmplitude: 0.012,
    normalPattern: "fine directional brushing",
    displacementPattern: "raised rune relief",
    occlusionPattern: "crossing and inner-face cavity darkening",
    edgeWearPattern: "polished bevel highlights",
    notes: "Satin metal face with glossier bevel and glyph relief."
  };
  node.colorMaterialRecipe = {
    dominantAlbedo: rgba(material === "core-gold" ? "#D8A84E" : bands.find((band) => `${band.id}-band` === material)?.color || "#B08A5A"),
    secondaryAlbedo: rgba(material === "core-gold" ? "#FFE7A6" : bands.find((band) => `${band.id}-band` === material)?.secondary || "#E0C090"),
    materialClass: "metal",
    materialClassConfidence: 0.92,
    colorGradient: {
      type: "linear",
      stops: [
        { offset: 0, color: rgba(material === "core-gold" ? "#8C5C23" : bands.find((band) => `${band.id}-band` === material)?.color || "#8A6A44") },
        { offset: 1, color: rgba(material === "core-gold" ? "#FFE7A6" : bands.find((band) => `${band.id}-band` === material)?.secondary || "#E0C090") }
      ]
    },
    evidenceRefs: ["full-object"]
  };
  node.evidenceRefs = ["full-object"];
  node.confidence = parent ? 0.82 : 0.9;
  node.fidelityTier = level === "macro" ? "blockout" : level === "meso" ? "structural-pass" : "form-refinement";
  return node;
}

function material(id, name, color, secondary, roughness, metalness, emissive = false) {
  const item = structuredClone(materialTemplate);
  item.id = id;
  item.name = name;
  item.type = "physical";
  item.baseColor = color;
  item.color = color;
  item.albedo = {
    dominant: color,
    secondary: [secondary, "#2D2626"],
    samplingNotes: "Palette is matched by host vision to visible reference zones."
  };
  item.colorVariation = {
    palette: [color, secondary],
    pattern: "directional brushed gradient",
    amplitude: 0.12,
    heightCorrelation: 0.2
  };
  item.textureResolution = 1024;
  item.roughness = { base: roughness, variation: 0.1, map: "reference-independent-roughness", localResponse: "lower on bevels and raised glyphs" };
  item.metalness = { base: metalness, variation: 0.04 };
  item.normal = { pattern: "directional-brush", strength: 0.16, scale: 72, space: "tangent" };
  item.bump = { pattern: "rune-relief", amplitude: 0.018, scale: 1 };
  item.ambientOcclusion = { cavityStrength: 0.38, contactShadowBias: 0.42, notes: "Preserve depth at crossings and inner faces." };
  item.wear = { edgeWear: 0.12, scratches: ["subtle longitudinal hairlines"], chips: [] };
  item.dirt = { amount: 0.02, cavityBias: 0.35, color: "#2D2626" };
  item.localOverrides = [
    { id: `${id}-bevel-gloss`, mask: "bevel", roughness: Math.max(0.12, roughness - 0.16), evidenceRefs: ["full-object"] },
    { id: `${id}-rune-relief`, mask: "rune-glyphs", roughness: 0.18, metalness: 1, evidenceRefs: ["full-object"] }
  ];
  item.referencePbr = structuredClone(referencePbr);
  if (emissive) {
    item.emissive = { color: "#A86F22", intensity: 0.16 };
    item.clearcoat = { base: 0.62, roughness: 0.15 };
  } else {
    item.clearcoat = { base: 0.24, roughness: 0.28 };
  }
  item.notes = "Reference-derived full-image PBR is treated as evidence, while final per-band color is host-observed and procedurally authored.";
  return item;
}

const components = [
  component({ id: "root", name: "Pantheon oracle sphere root", level: "macro", role: "root", primitive: "sphere", parent: null, material: "core-gold", scale: [0.01, 0.01, 0.01], animationRole: "root" }),
  component({ id: "core", name: "Warm gold oracle core", level: "macro", role: "core", primitive: "sphere", parent: "root", material: "core-gold", scale: [0.58, 0.58, 0.58], animationRole: "pulse", localFeatures: [{ id: "core-gloss", kind: "gloss", description: "Bright warm highlight and soft reflected fill." }] }),
  component({ id: "core-glow", name: "Core glow shell", level: "meso", role: "effect-shell", primitive: "sphere", parent: "core", material: "core-glow", scale: [0.69, 0.69, 0.69], animationRole: "pulse" })
];

for (const band of bands) {
  const pivotId = `${band.id}-pivot`;
  components.push(component({
    id: pivotId,
    name: `${band.name} pivot`,
    level: "macro",
    role: "band-pivot",
    primitive: "torus",
    parent: "root",
    material: `${band.id}-band`,
    rotation: band.rotation,
    scale: [3.0, 3.0, 0.42],
    animationRole: "independent-orbit",
    localFeatures: [
      { id: `${band.id}-closed-loop`, kind: "contour", description: "Continuous closed loop with a readable side silhouette." },
      { id: `${band.id}-beveled-edge`, kind: "bevel", description: "Rounded polished edges catch narrow highlights." }
    ]
  }));
  components.push(
    component({ id: `${band.id}-shell`, name: `${band.name} visible shell`, level: "meso", role: "band-shell", primitive: "torus", parent: pivotId, material: `${band.id}-band`, scale: [1, 1, 1], torusTubeRatio: 0.17 }),
    component({ id: `${band.id}-inner`, name: `${band.name} inner face`, level: "meso", role: "inner-face", primitive: "torus", parent: pivotId, material: `${band.id}-band`, scale: [0.985, 0.985, 0.94], torusTubeRatio: 0.16 }),
    component({ id: `${band.id}-runes`, name: `${band.name} rune relief`, level: "meso", role: "surface-relief", primitive: "instanced-cluster", parent: pivotId, material: "rune-gold", scale: [1, 1, 1], localFeatures: [{ id: `${band.id}-rune-path`, kind: "linework", description: "Procedural diamonds, forks, nodes and connecting strokes." }] })
  );
}

spec.componentTree = components;
spec.materials = [
  material("gold-band", "Warm brushed gold", "#C99B4F", "#F0D18B", 0.32, 0.96),
  material("teal-band", "Muted jade metal", "#497F77", "#91B7A5", 0.38, 0.9),
  material("rose-band", "Rose copper metal", "#9E5960", "#D69A91", 0.36, 0.9),
  material("navy-band", "Deep navy metal", "#263752", "#60779B", 0.3, 0.84),
  material("bronze-band", "Champagne bronze metal", "#8B6249", "#C59A72", 0.35, 0.92),
  material("core-gold", "Oracle core gold", "#D8A84E", "#FFE7A6", 0.2, 1, true),
  material("core-glow", "Core translucent glow", "#D8A84E", "#FFE7A6", 0.18, 0.5, true),
  material("rune-gold", "Raised rune gold", "#E8C675", "#FFF0B8", 0.18, 1)
];
spec.repetitionSystems = [
  {
    id: "rune-lines",
    name: "Connected rune path strokes",
    componentRefs: bands.map((band) => `${band.id}-runes`),
    distribution: "arc-length placements around each closed band with deterministic phase offsets",
    instances: 70,
    geometry: "thin raised line segments conforming to the band face",
    buildsGeometry: true,
    realization: "instanced-geometry",
    variation: { scale: [0.8, 1.2], rotationJitter: 0.12, spacingJitter: 0.08 },
    evidenceRefs: ["full-object"]
  },
  {
    id: "rune-glyphs",
    name: "Diamond fork chevron and node glyphs",
    componentRefs: bands.map((band) => `${band.id}-runes`),
    distribution: "alternating motif sequence with at least eight glyph clusters per band",
    instances: 45,
    geometry: "raised curve and diamond primitives",
    buildsGeometry: true,
    realization: "instanced-geometry",
    variation: { motifs: ["diamond", "fork", "chevron", "node"], scale: [0.75, 1.15] },
    evidenceRefs: ["full-object"]
  }
];

const localFeatureIds = new Set(components.flatMap((node) => node.localFeatures.map((feature) => feature.id)));
const overrideIds = new Set(spec.materials.flatMap((item) => item.localOverrides.map((override) => override.id)));
const detailRefs = [
  ["d01", "contour", "gold-closed-loop"], ["d02", "contour", "teal-closed-loop"],
  ["d03", "contour", "rose-closed-loop"], ["d04", "contour", "navy-closed-loop"],
  ["d05", "contour", "bronze-closed-loop"], ["d06", "bevel", "gold-beveled-edge"],
  ["d07", "bevel", "teal-beveled-edge"], ["d08", "bevel", "rose-beveled-edge"],
  ["d09", "bevel", "navy-beveled-edge"], ["d10", "bevel", "bronze-beveled-edge"],
  ["d11", "linework", "gold-rune-path"], ["d12", "linework", "teal-rune-path"],
  ["d13", "linework", "rose-rune-path"], ["d14", "linework", "navy-rune-path"],
  ["d15", "linework", "bronze-rune-path"], ["d16", "gloss", "core-gloss"],
  ["d17", "gloss", "core-gold-bevel-gloss"], ["d18", "ridge", "rune-gold-rune-relief"]
];
spec.preSpecAssessment.detailInventory.details = detailRefs.map(([id, kind, ref]) => {
  if (!localFeatureIds.has(ref) && !overrideIds.has(ref)) {
    throw new Error(`Unknown detail mapping: ${ref}`);
  }
  return { id, kind, description: `Reference-observed ${kind} detail`, mapsTo: { ref }, evidenceRefs: ["full-object"] };
});
spec.preSpecAssessment.unknownsToResolveBeforeImplementation = [];
spec.assumptions = [
  "Rear-side band segments are inferred as smooth closed loops because the single front image does not expose them.",
  "Rear crossing order is authored for collision-free visual continuity, not claimed as exact hidden geometry.",
  "Full-image PBR extraction guides material response; per-band hues are host-observed procedural values."
];
spec.silhouette = {
  boundingShape: "near-spherical cage around a centered core",
  aspectRatios: [1, 1, 1],
  symmetry: "radial balance without exact bilateral symmetry",
  dominantCurves: ["five large closed orbital arcs"],
  negativeSpaces: ["irregular lens-shaped openings between crossings"],
  landmarks: ["gold center core", "front gold diagonal", "navy lower-front arc", "teal upper diagonal"]
};
spec.referenceCamera = {
  solved: false,
  fovDegrees: 32,
  aspect: 1,
  orientation: { yaw: 0, pitch: 0, roll: 0 },
  positionHint: [0, 0, 7],
  note: "Heuristic camera matched by browser comparison; source image does not provide calibration."
};
spec.qualityTargets = {
  targetFidelity: 0.82,
  mustMatch: ["five-band spherical silhouette", "gold core focal hierarchy", "band palette", "readable interwoven depth", "raised rune language"],
  niceToHave: ["exact individual rune symbols", "exact hidden crossing order"],
  fpsTarget: 30,
  reviewViewpoints: ["reference-front", "orbit-35", "side-70", "grazing-close", "deployed-720x864"]
};
spec.featureReviewTargets = [
  { id: "five-band-envelope", name: "Five-band spherical envelope", tier: "critical", passIds: ["blockout", "structural-pass"], minimumScore: 0.8, mustPass: true, componentRefs: bands.map((band) => `${band.id}-pivot`), evidenceRefs: ["full-object"] },
  { id: "closed-volume-truth", name: "Closed volume under orbit view", tier: "critical", passIds: ["structural-pass", "form-refinement"], minimumScore: 0.82, mustPass: true, componentRefs: bands.map((band) => `${band.id}-shell`), evidenceRefs: ["full-object"] },
  { id: "pantheon-palette", name: "Gold teal rose navy bronze palette", tier: "critical", passIds: ["material-pass"], minimumScore: 0.78, mustPass: true, componentRefs: bands.map((band) => `${band.id}-shell`), evidenceRefs: ["full-object"] },
  { id: "rune-language", name: "Raised connected rune language", tier: "important", passIds: ["surface-pass"], minimumScore: 0.72, mustPass: false, componentRefs: bands.map((band) => `${band.id}-runes`), evidenceRefs: ["full-object"] },
  { id: "core-hierarchy", name: "Warm gold focal core", tier: "critical", passIds: ["lighting-pass"], minimumScore: 0.8, mustPass: true, componentRefs: ["core", "core-glow"], evidenceRefs: ["full-object"] },
  { id: "independent-pivots", name: "Stable independent band pivots", tier: "critical", passIds: ["interaction-pass"], minimumScore: 0.9, mustPass: true, componentRefs: bands.map((band) => `${band.id}-pivot`), evidenceRefs: ["full-object"] }
];
spec.lightingFromPhoto = [
  "Key light: warm area light from upper-left/front, color #FFE0A3, intensity 3.2.",
  "Fill light: cool soft area light from lower-right/front, color #B7D8D2, intensity 1.1.",
  "Rim light: warm-neutral back light, color #FFF1D0, intensity 2.0.",
  "Environment light: low-intensity warm studio environment for metal readability.",
  "Exposure 1.05 with ACES filmic tone mapping; preserve band hue separation.",
  "Transparent background with soft ambient occlusion/contact shadow at band crossings; no ground plane in exported media."
];
spec.performanceBudget = {
  qualityPriority: "reference-fidelity",
  targetTriangles: 180000,
  maxDrawCalls: 48,
  textureSize: 1024,
  fpsTarget: 30,
  optimizationPolicy: "Author at high fidelity, then export 720 × 864 at 16 FPS; no Three.js runtime ships to production."
};
spec.animationAnchors = [
  "root supports whole-object idle rotation",
  ...bands.map((band) => `${band.id}-pivot rotates independently at ${band.speed} radians per second`)
];
for (const pass of spec.buildPasses) {
  pass.componentRefs = components
    .filter((node) => pass.id === "blockout" ? node.level === "macro" : pass.id === "structural-pass" ? node.level !== "micro" : true)
    .map((node) => node.id);
}
spec.proceduralStrategy = [
  "Build five closed beveled annular bands under independent pivots.",
  "Use deterministic motif placement for raised rune paths and glyph clusters.",
  "Render transparent frames with a fixed camera and studio lights.",
  "Export media for the existing WebM/poster player; do not ship Three.js to production."
];
spec.risks = [
  "Single-view source cannot prove rear crossing order.",
  "Transparent VP9 alpha support varies by browser; existing WebP poster remains the fallback.",
  "Dense glyph geometry must stay below the authoring draw-call and triangle budget."
];

fs.writeFileSync(outputPath, `${JSON.stringify(spec, null, 2)}\n`);
console.log(outputPath);
