import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import {
  createPantheonStarOrbits,
  getPantheonStarOrbitRuntime,
  SELF_CORE_RADIUS,
} from "../generated/createPantheonStarOrbits.ts";
import {
  PANTHEON_THEME_BY_ID,
  PANTHEON_THEME_CONFIGS,
} from "../data/pantheon-theme-config.ts";
import { PANTHEON_MATERIAL_CONFIGS } from "../data/pantheon-material-config.ts";
import {
  DEFAULT_REFLECTION_CANDIDATE,
} from "../data/pantheon-reflection-profiles.ts";
import {
  DEFAULT_STYLE_MATCH_CANDIDATE,
  PANTHEON_STYLE_BACKGROUND,
  PANTHEON_STYLE_MATCH_CANDIDATES,
} from "../data/pantheon-style-match-profiles.ts";
import {
  createPantheonMaterialPrototype,
  DEFAULT_METAL_HIGHLIGHT_STRENGTH,
  PANTHEON_BAND_ENVIRONMENT_BASELINE,
} from "../materials/createPantheonMaterialPrototype.ts";
import { configurePantheonSelfCoreEffect } from "../effects/configurePantheonSelfCoreEffect.ts";
import { configurePantheonCoreRuneRelationship } from "../effects/configurePantheonCoreRuneRelationship.ts";
import {
  DEFAULT_SELF_CORE_ARTIFACT_CANDIDATE,
  PANTHEON_SELF_CORE_ARTIFACT_PRESETS,
} from "../data/pantheon-self-core-artifact.ts";
import {
  createPantheonProductLightingRig,
  PRODUCT_STUDIO_PRESET,
} from "../lighting/createPantheonProductLightingRig.ts";
import ribbonFrameSearch from "../../geometry/pantheon-ribbon-frame-v2.json";
import styles from "./PantheonStarOrbitStudio.module.css";

const VIEWS = {
  front: [0, 0, 4.25],
  back: [0, 0, -4.25],
  left: [-4.25, 0, 0],
  right: [4.25, 0, 0],
  top: [0, 4.25, 0.001],
  bottom: [0, -4.25, 0.001],
  "front-left": [-2.85, 0.65, 3.2],
  "front-right": [2.85, 0.65, 3.2],
  orbit: [2.85, 0.65, 3.2],
};

const REFLECTION_LIGHTING_BASELINE = Object.freeze({
  exposure: { desktop: 0.98, mobile: 0.96 },
  ambient: { desktop: 0.22, mobile: 0.24 },
  keyIntensity: { desktop: 1.3, mobile: 1.18 },
  fillIntensity: { desktop: 0.55, mobile: 0.49 },
  rimIntensity: { desktop: 1.12, mobile: 1.02 },
  environmentIntensity: 0.86,
  toneMapping: "AgX",
  keyPosition: [-4.6, 4.55, 4.6],
  keyTarget: [-0.78, 0.52, 0.12],
  sharedPmremSoftboxCount: 1,
});

const STYLE_MATCH_LIGHTING = Object.freeze({
  exposure: { desktop: 1.08, mobile: 1.04 },
  ambient: { desktop: 0.36, mobile: 0.38 },
  hemisphere: { desktop: 0.86, mobile: 0.9 },
  keyIntensity: { desktop: 2.2, mobile: 1.85 },
  fillIntensity: { desktop: 0.85, mobile: 0.72 },
  rimIntensity: { desktop: 0.78, mobile: 0.66 },
  environmentIntensity: 0.9,
  toneMapping: "AgX",
  background: PANTHEON_STYLE_BACKGROUND,
});
const DEFAULT_FIELD_LIGHT_STRENGTH = PRODUCT_STUDIO_PRESET.environmentStrength;
const STYLE_MATCH_CORE_BASELINE = Object.freeze({
  color: "#c9a154",
  emissiveColor: "#52370d",
  emissiveIntensity: 0.07,
  metalness: 0.76,
  roughness: 0.3,
  clearcoat: 0,
  clearcoatRoughness: 0.28,
  envMapIntensity: 0.9,
});

const PMREM_REFLECTION_FIELD_CANDIDATES = Object.freeze({
  current: {
    id: "current",
    label: "Current Baseline",
    baseColor: "#34424e",
    cards: [
      {
        id: "main-softbox",
        label: "Main Softbox",
        type: "rect",
        x: 24,
        y: 18,
        width: 432,
        height: 78,
        color: "#fcf2e2",
        alpha: 0.96,
        blur: 20,
      },
      {
        id: "right-strip",
        label: "Right Strip",
        type: "rect",
        x: 390,
        y: 36,
        width: 76,
        height: 178,
        color: "#dae8ed",
        alpha: 0.78,
        blur: 16,
      },
      {
        id: "left-dark-card",
        label: "Left Dark Card",
        type: "rect",
        x: 8,
        y: 116,
        width: 164,
        height: 100,
        color: "#0c131b",
        alpha: 0.62,
        blur: 20,
      },
      {
        id: "lower-fill",
        label: "Lower Fill",
        type: "rect",
        x: 118,
        y: 174,
        width: 292,
        height: 46,
        color: "#bccdd5",
        alpha: 0.34,
        blur: 24,
      },
      {
        id: "warm-core-card",
        label: "Warm Core Card",
        type: "radial",
        centerX: 216,
        centerY: 112,
        innerRadius: 6,
        outerRadius: 74,
        blur: 18,
        stops: [
          { offset: 0, color: "#ffd28b", alpha: 0.82 },
          { offset: 0.5, color: "#eeb86c", alpha: 0.4 },
          { offset: 1, color: "#bf8446", alpha: 0 },
        ],
      },
    ],
  },
  "candidate-a": {
    id: "candidate-a",
    label: "Candidate A · Contrast Studio",
    baseColor: "#18232d",
    cards: [
      {
        id: "main-softbox",
        label: "Main Softbox",
        type: "rect",
        x: 74,
        y: 20,
        width: 218,
        height: 50,
        color: "#fff2dc",
        alpha: 0.95,
        blur: 8,
      },
      {
        id: "right-strip",
        label: "Right Strip",
        type: "rect",
        x: 392,
        y: 48,
        width: 46,
        height: 132,
        color: "#d4e6f0",
        alpha: 0.82,
        blur: 6,
      },
      {
        id: "secondary-card",
        label: "Secondary Card",
        type: "rect",
        x: 20,
        y: 50,
        width: 88,
        height: 56,
        color: "#b6b3a8",
        alpha: 0.44,
        blur: 9,
      },
      {
        id: "lower-fill",
        label: "Lower Fill",
        type: "rect",
        x: 184,
        y: 194,
        width: 152,
        height: 28,
        color: "#748f9d",
        alpha: 0.26,
        blur: 9,
      },
      {
        id: "left-dark-card",
        label: "Left Dark Card",
        type: "rect",
        x: 0,
        y: 118,
        width: 134,
        height: 104,
        color: "#03070c",
        alpha: 0.9,
        blur: 6,
      },
      {
        id: "right-dark-strip",
        label: "Right Dark Strip",
        type: "rect",
        x: 456,
        y: 84,
        width: 54,
        height: 134,
        color: "#05090f",
        alpha: 0.82,
        blur: 5,
      },
      {
        id: "warm-core-card",
        label: "Warm Core Card",
        type: "radial",
        centerX: 216,
        centerY: 110,
        innerRadius: 5,
        outerRadius: 40,
        blur: 0,
        stops: [
          { offset: 0, color: "#ffdda5", alpha: 0.68 },
          { offset: 1, color: "#ffdda5", alpha: 0 },
        ],
      },
    ],
  },
  "candidate-b": {
    id: "candidate-b",
    label: "Candidate B · Soft Contrast Studio",
    baseColor: "#18232d",
    cards: [
      {
        id: "main-softbox",
        label: "Main Softbox",
        type: "rect",
        x: 74,
        y: 20,
        width: 235,
        height: 50,
        color: "#fff2dc",
        alpha: 0.874,
        blur: 10,
      },
      {
        id: "right-strip",
        label: "Right Strip",
        type: "rect",
        x: 392,
        y: 48,
        width: 46,
        height: 132,
        color: "#d4e6f0",
        alpha: 0.754,
        blur: 8,
      },
      {
        id: "secondary-card",
        label: "Secondary Card",
        type: "rect",
        x: 20,
        y: 50,
        width: 88,
        height: 56,
        color: "#b6b3a8",
        alpha: 0.405,
        blur: 11,
      },
      {
        id: "lower-fill",
        label: "Lower Fill",
        type: "rect",
        x: 184,
        y: 194,
        width: 152,
        height: 28,
        color: "#748f9d",
        alpha: 0.239,
        blur: 11,
      },
      {
        id: "left-dark-card",
        label: "Left Dark Card",
        type: "rect",
        x: 0,
        y: 118,
        width: 134,
        height: 104,
        color: "#03070c",
        alpha: 0.855,
        blur: 6,
      },
      {
        id: "right-dark-strip",
        label: "Right Dark Strip",
        type: "rect",
        x: 456,
        y: 84,
        width: 54,
        height: 134,
        color: "#05090f",
        alpha: 0.779,
        blur: 5,
      },
      {
        id: "warm-core-card",
        label: "Warm Core Card",
        type: "radial",
        centerX: 216,
        centerY: 110,
        innerRadius: 5,
        outerRadius: 40,
        blur: 2,
        stops: [
          { offset: 0, color: "#ffdda5", alpha: 0.626 },
          { offset: 1, color: "#ffdda5", alpha: 0 },
        ],
      },
    ],
  },
});

function rgba(hexColor, alpha) {
  const value = Number.parseInt(hexColor.slice(1), 16);
  const red = (value >> 16) & 255;
  const green = (value >> 8) & 255;
  const blue = value & 255;
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function createPantheonStudioEnvironment(renderer, candidateId = "current") {
  const candidate =
    PMREM_REFLECTION_FIELD_CANDIDATES[candidateId] ??
    PMREM_REFLECTION_FIELD_CANDIDATES.current;
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 256;
  const context = canvas.getContext("2d");
  context.fillStyle = candidate.baseColor;
  context.fillRect(0, 0, canvas.width, canvas.height);

  candidate.cards.forEach((card) => {
    context.save();
    context.filter = card.blur > 0 ? `blur(${card.blur}px)` : "none";
    if (card.type === "rect") {
      context.fillStyle = rgba(card.color, card.alpha);
      context.fillRect(card.x, card.y, card.width, card.height);
    } else {
      const gradient = context.createRadialGradient(
        card.centerX,
        card.centerY,
        card.innerRadius,
        card.centerX,
        card.centerY,
        card.outerRadius,
      );
      card.stops.forEach((stop) => {
        gradient.addColorStop(
          stop.offset,
          rgba(stop.color, stop.alpha),
        );
      });
      context.fillStyle = gradient;
      context.fillRect(0, 0, canvas.width, canvas.height);
    }
    context.restore();
  });

  const source = new THREE.CanvasTexture(canvas);
  source.mapping = THREE.EquirectangularReflectionMapping;
  source.colorSpace = THREE.SRGBColorSpace;
  const pmrem = new THREE.PMREMGenerator(renderer);
  const texture = pmrem.fromEquirectangular(source).texture;
  source.dispose();
  pmrem.dispose();
  return {
    texture,
    sourceCanvas: canvas,
    candidate,
  };
}

function createPantheonStyleBackground() {
  const canvas = document.createElement("canvas");
  canvas.width = 768;
  canvas.height = 768;
  const context = canvas.getContext("2d");
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const draw = (darkness = 1) => {
    const brightness = THREE.MathUtils.clamp(1 / darkness, 0.72, 1.18);
    const center = new THREE.Color(
      PANTHEON_STYLE_BACKGROUND.center,
    ).multiplyScalar(brightness);
    const middle = new THREE.Color("#0b1928").multiplyScalar(brightness);
    const edge = new THREE.Color(
      PANTHEON_STYLE_BACKGROUND.edge,
    ).multiplyScalar(brightness);
    const gradient = context.createRadialGradient(
      384,
      350,
      24,
      384,
      350,
      520,
    );
    gradient.addColorStop(0, `#${center.getHexString()}`);
    gradient.addColorStop(0.56, `#${middle.getHexString()}`);
    gradient.addColorStop(1, `#${edge.getHexString()}`);
    context.fillStyle = gradient;
    context.fillRect(0, 0, canvas.width, canvas.height);
    texture.needsUpdate = true;
  };
  draw();
  return {
    texture,
    setDarkness: draw,
    dispose: () => texture.dispose(),
  };
}

function setCameraView(camera, controls, view) {
  camera.position.set(...(VIEWS[view] || VIEWS.orbit));
  camera.lookAt(0, 0, 0);
  controls.target.set(0, 0, 0);
  controls.update();
}

function RangeControl({ label, value, min, max, step, onChange }) {
  return (
    <label className={styles.range}>
      <span>
        {label}
        <output>{Number(value).toFixed(step < 0.01 ? 3 : 2)}</output>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={min === max}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

export default function PantheonStarOrbitStudio() {
  const freezeOrbitOnLoad =
    new URLSearchParams(window.location.search).get("freezeOrbit") ===
    "1";
  const mountRef = useRef(null);
  const runtimeRef = useRef(null);
  const materialRef = useRef(null);
  const coreEffectRef = useRef(null);
  const coreRelationshipRef = useRef(null);
  const cameraViewRef = useRef(null);
  const lightingRef = useRef(null);
  const [selectedTheme, setSelectedTheme] = useState(null);
  const [hoveredTheme, setHoveredTheme] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [monochrome, setMonochrome] = useState(false);
  const [paused, setPaused] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [mobileQuality, setMobileQuality] = useState(false);
  const [debugTheme, setDebugTheme] = useState("constellation");
  const [debugState, setDebugState] = useState("Idle");
  const [reflectionCandidate, setReflectionCandidate] = useState(
    DEFAULT_REFLECTION_CANDIDATE,
  );
  const [styleMatchCandidate, setStyleMatchCandidate] = useState(
    DEFAULT_STYLE_MATCH_CANDIDATE,
  );
  const [selfCoreCandidate, setSelfCoreCandidate] = useState(
    DEFAULT_SELF_CORE_ARTIFACT_CANDIDATE,
  );
  const [cameraView, setCameraViewState] = useState("orbit");
  const [productLighting, setProductLighting] = useState(() => ({
    ...PRODUCT_STUDIO_PRESET,
    exposure: window.matchMedia("(max-width: 760px)").matches
      ? STYLE_MATCH_LIGHTING.exposure.mobile
      : STYLE_MATCH_LIGHTING.exposure.desktop,
    backgroundDarkness: 1,
  }));
  const [debug, setDebug] = useState({
    ribbonProgress: 1,
    opacity: 1,
    speed: 1,
    brightness: 1,
    saturation: 1,
    showUV: false,
    showFrame: false,
    showSeam: false,
    showTubeLine: false,
    showRibbon: true,
    showBand: true,
    showCore: true,
    showPhase: false,
    validationMode: "material-v3",
    enableRunes: false,
    markOpacity: 1,
    markDepth: 0.15,
    markRoughnessDelta: -0.045,
    markMetalnessDelta: 0,
    markEmissive: 0.004,
    fieldLightStrength: DEFAULT_FIELD_LIGHT_STRENGTH,
    metalHighlightStrength: DEFAULT_METAL_HIGHLIGHT_STRENGTH,
    flowIntensity: 1,
    forceCoreTheme: "auto",
    edgeBrightness: 0.91,
    edgeRoughness: 0.1,
    flatMaterial: false,
    showTopBottom: true,
    showEdges: true,
    showBevel: true,
  });
  const [desktopWidths, setDesktopWidths] = useState({
    idle: 0.22,
    hover: 0.22,
    selected: 0.22,
  });
  const [mobileWidths, setMobileWidths] = useState({
    idle: 0.2,
    hover: 0.2,
    selected: 0.2,
  });
  const [materialDrafts, setMaterialDrafts] = useState(() =>
    Object.fromEntries(
      Object.entries(PANTHEON_MATERIAL_CONFIGS).map(([id, config]) => [
        id,
        { ...config },
      ]),
    ),
  );

  const applyHover = (themeId) => {
    materialRef.current?.setHoveredTheme(themeId);
    setHoveredTheme(themeId);
  };

  const applySelection = (themeId) => {
    materialRef.current?.selectTheme(themeId);
    setSelectedTheme(themeId);
    setHoveredTheme(null);
  };

  const applyDebugPatch = (patch) => {
    const next = { ...debug, ...patch };
    setDebug(next);
    materialRef.current?.setDebugOverrides(next);
    if (patch.fieldLightStrength != null) {
      lightingRef.current?.setSettings({
        environmentStrength: next.fieldLightStrength,
      });
      setProductLighting((current) => ({
        ...current,
        environmentStrength: next.fieldLightStrength,
      }));
    }
    coreRelationshipRef.current?.setForceTheme(
      next.forceCoreTheme === "auto" ? null : next.forceCoreTheme,
    );
  };
  const applyProductLightingPatch = (patch) => {
    setProductLighting((current) => ({ ...current, ...patch }));
    if (patch.backgroundDarkness != null) {
      lightingRef.current?.setBackgroundDarkness(
        patch.backgroundDarkness,
      );
    }
    const {
      backgroundDarkness: _backgroundDarkness,
      ...lightingPatch
    } = patch;
    lightingRef.current?.setSettings(lightingPatch);
    if (patch.environmentStrength != null) {
      setDebug((current) => ({
        ...current,
        fieldLightStrength: patch.environmentStrength,
      }));
    }
  };
  const resetProductLighting = () => {
    const next = {
      ...PRODUCT_STUDIO_PRESET,
      exposure: window.matchMedia("(max-width: 760px)").matches
        ? STYLE_MATCH_LIGHTING.exposure.mobile
        : STYLE_MATCH_LIGHTING.exposure.desktop,
      backgroundDarkness: 1,
    };
    setProductLighting(next);
    lightingRef.current?.setBackgroundDarkness(1);
    lightingRef.current?.setSettings(PRODUCT_STUDIO_PRESET);
    setDebug((current) => ({
      ...current,
      fieldLightStrength:
        PRODUCT_STUDIO_PRESET.environmentStrength,
    }));
  };
  const applyBandWidthPreview = (value) => {
    const target = mobileQuality ? "mobile" : "desktop";
    const next = {
      idle: value,
      hover: value,
      selected: value,
    };
    materialRef.current?.setWidthProfile(target, next);
    if (target === "mobile") {
      setMobileWidths(next);
    } else {
      setDesktopWidths(next);
    }
  };
  const resetBandWidthPreview = () => {
    const desktop = { idle: 0.22, hover: 0.22, selected: 0.22 };
    const mobile = { idle: 0.2, hover: 0.2, selected: 0.2 };
    materialRef.current?.setWidthProfile("desktop", desktop);
    materialRef.current?.setWidthProfile("mobile", mobile);
    setDesktopWidths(desktop);
    setMobileWidths(mobile);
  };
  const applyMaterialPatch = (patch) => {
    const next = {
      ...materialDrafts[debugTheme],
      ...patch,
      ...(patch.baseColor ? { color: patch.baseColor } : {}),
    };
    setMaterialDrafts((current) => ({
      ...current,
      [debugTheme]: next,
    }));
    materialRef.current?.setThemeMaterial(debugTheme, patch);
  };
  const applyStyleMatchCandidate = (candidateId) => {
    const candidate = PANTHEON_STYLE_MATCH_CANDIDATES[candidateId];
    if (!candidate) return;
    materialRef.current?.setStyleMatchCandidate(candidateId);
    setStyleMatchCandidate(candidateId);
  };
  const applySelfCoreCandidate = (candidateId) => {
    if (
      !Object.hasOwn(
        PANTHEON_SELF_CORE_ARTIFACT_PRESETS,
        candidateId,
      )
    ) {
      return;
    }
    const artifact =
      coreEffectRef.current?.setArtifactCandidate(candidateId);
    const runtime = runtimeRef.current;
    if (artifact && runtime) {
      const coreNode = runtime.getThemeNodes().core;
      coreNode.scale.setScalar(artifact.radiusScale);
      coreNode.userData.radius =
        SELF_CORE_RADIUS * artifact.radiusScale;
    }
    setSelfCoreCandidate(candidateId);
  };

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;

    const params = new URLSearchParams(window.location.search);
    const requestedCoreCandidate = params.get("coreCandidate");
    const coreCandidateId =
      requestedCoreCandidate &&
      Object.hasOwn(
        PANTHEON_SELF_CORE_ARTIFACT_PRESETS,
        requestedCoreCandidate,
      )
        ? requestedCoreCandidate
        : DEFAULT_SELF_CORE_ARTIFACT_CANDIDATE;
    const requestedPmremCandidate = params.get("pmremCandidate");
    const pmremCandidateId =
      requestedPmremCandidate &&
      Object.hasOwn(
        PMREM_REFLECTION_FIELD_CANDIDATES,
        requestedPmremCandidate,
      )
        ? requestedPmremCandidate
        : "current";
    document.documentElement.classList.add("pantheon-star-orbit-mode");
    const isMobile = window.matchMedia("(max-width: 760px)").matches;
    const systemReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const renderer = new THREE.WebGLRenderer({
      antialias: !isMobile,
      preserveDrawingBuffer: true,
      powerPreference: "high-performance",
    });
    renderer.setClearColor(0x0b1118, 1);
    renderer.setPixelRatio(
      Math.min(window.devicePixelRatio || 1, isMobile ? 1.5 : 2),
    );
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    const recoveryExposure = isMobile
      ? STYLE_MATCH_LIGHTING.exposure.mobile
      : STYLE_MATCH_LIGHTING.exposure.desktop;
    renderer.toneMapping = THREE.AgXToneMapping;
    renderer.toneMappingExposure = recoveryExposure;
    renderer.shadowMap.enabled = false;
    mount.append(renderer.domElement);

    const scene = new THREE.Scene();
    const styleBackground = createPantheonStyleBackground();
    scene.background = styleBackground.texture;
    const reflectionField = createPantheonStudioEnvironment(
      renderer,
      pmremCandidateId,
    );
    const environment = reflectionField.texture;
    scene.environment = environment;
    scene.environmentIntensity =
      PRODUCT_STUDIO_PRESET.environmentStrength;
    const productLightingRig = createPantheonProductLightingRig(
      scene,
      {
        mobile: isMobile,
        initial: {
          exposure: recoveryExposure,
        },
        onEnvironmentStrengthChange: (value) => {
          scene.environmentIntensity = value;
        },
        onExposureChange: (value) => {
          renderer.toneMappingExposure = value;
        },
      },
    );
    lightingRef.current = {
      ...productLightingRig,
      setBackgroundDarkness: styleBackground.setDarkness,
    };

    const camera = new THREE.PerspectiveCamera(31, 1, 0.1, 20);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = false;
    controls.minDistance = 2.8;
    controls.maxDistance = 7;
    cameraViewRef.current = (view) => {
      setCameraView(camera, controls, view);
      renderer.render(scene, camera);
      setCameraViewState(view);
    };

    const geometryVersion =
      params.get("geometryVersion") === "v1.0" ? "v1.0" : "v1.1";
    const requestedFrameMode = params.get("frameMode");
    const ribbonFrameMode = ["selected", "fixed", "legacy"].includes(
      requestedFrameMode,
    )
      ? requestedFrameMode
      : "selected";
    const orbits = createPantheonStarOrbits({
      ribbonFrameMode,
      geometryVersion,
    });
    const runtime = getPantheonStarOrbitRuntime(orbits);
    const setCoreArtifactRadius = (radiusScale) => {
      const coreNode = runtime.getThemeNodes().core;
      coreNode.scale.setScalar(radiusScale);
      coreNode.userData.radius = SELF_CORE_RADIUS * radiusScale;
      return coreNode.userData.radius;
    };
    const material = createPantheonMaterialPrototype(runtime, {
      mobileQuality: isMobile,
      environmentMap: environment,
    });
    material.setDebugOverrides({
      metalHighlightStrength: DEFAULT_METAL_HIGHLIGHT_STRENGTH,
    });
    const coreEffect = configurePantheonSelfCoreEffect(
      runtime.getThemeNodes().core,
      { environmentMap: environment },
    );
    const coreRelationship =
      configurePantheonCoreRuneRelationship({
        root: orbits,
        core: runtime.getThemeNodes().core,
        camera,
        viewport: renderer.domElement,
        centerlineSamples: runtime.getCenterlineSamples(720),
        coreEffect,
      });
    const initialCoreArtifact =
      coreEffect.setArtifactCandidate(coreCandidateId);
    setCoreArtifactRadius(initialCoreArtifact.radiusScale);
    setSelfCoreCandidate(coreCandidateId);
    const recoveryMaterialSnapshot = material.getSnapshot();
    const recoveryEnvironmentValues = Object.values(
      recoveryMaterialSnapshot.visuals,
    ).map(({ envMapIntensity }) => envMapIntensity);
    const recoveryRuntimeAssertion =
      recoveryMaterialSnapshot.debug.metalHighlightStrength ===
        DEFAULT_METAL_HIGHLIGHT_STRENGTH &&
      recoveryEnvironmentValues.every(
        (value) =>
          Math.abs(
            value -
              PANTHEON_BAND_ENVIRONMENT_BASELINE.topBottom,
          ) < 1e-6,
      ) &&
      Math.abs(
        coreEffect.snapshot().envMapIntensity -
          STYLE_MATCH_CORE_BASELINE.envMapIntensity,
      ) < 1e-6 &&
      coreEffect.snapshot().explicitEnvironmentMap &&
      coreEffect.snapshot().envMapUuid === environment.uuid;
    console.assert(
      recoveryRuntimeAssertion,
      "Pantheon Lighting Recovery runtime 初值不同步",
    );
    console.info("Pantheon Lighting Recovery runtime assertion", {
      passed: recoveryRuntimeAssertion,
      metalHighlightStrength: {
        ui: DEFAULT_METAL_HIGHLIGHT_STRENGTH,
        runtime:
          recoveryMaterialSnapshot.debug.metalHighlightStrength,
      },
      bandEnvMapIntensity: {
        ...PANTHEON_BAND_ENVIRONMENT_BASELINE,
      },
      selfCoreEnvMapIntensity:
        coreEffect.snapshot().envMapIntensity,
      selfCoreEnvironmentContract: {
        explicitEnvironmentMap:
          coreEffect.snapshot().explicitEnvironmentMap,
        environmentUuid: environment.uuid,
        materialEnvMapUuid: coreEffect.snapshot().envMapUuid,
      },
    });
    runtimeRef.current = runtime;
    materialRef.current = material;
    coreEffectRef.current = coreEffect;
    coreRelationshipRef.current = coreRelationship;
    scene.add(orbits);
    orbits.rotation.x = THREE.MathUtils.degToRad(-8);

    const initialCameraView = params.get("view") || "orbit";
    setCameraView(camera, controls, initialCameraView);
    setCameraViewState(initialCameraView);

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const hitAreas = [
      ...runtime.getThemeNodes().hitAreaMeshes.values(),
    ];
    const pick = (event) => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.set(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -((event.clientY - rect.top) / rect.height) * 2 + 1,
      );
      raycaster.setFromCamera(pointer, camera);
      return raycaster.intersectObjects(hitAreas, false)[0]?.object
        ?.userData.id;
    };
    const themeFromOrbit = (orbitId) =>
      PANTHEON_THEME_CONFIGS.find((theme) => theme.orbitId === orbitId)
        ?.id || null;
    const onPointerMove = (event) => {
      if (isMobile || material.state.selectedTheme) return;
      const themeId = themeFromOrbit(pick(event));
      material.setHoveredTheme(themeId);
      setHoveredTheme(themeId);
    };
    const onPointerLeave = () => {
      if (material.state.selectedTheme) return;
      material.setHoveredTheme(null);
      setHoveredTheme(null);
    };
    const onClick = (event) => {
      const themeId = themeFromOrbit(pick(event));
      if (!themeId) return;
      material.selectTheme(themeId);
      setSelectedTheme(themeId);
      setHoveredTheme(null);
    };
    renderer.domElement.addEventListener("pointermove", onPointerMove);
    renderer.domElement.addEventListener("pointerleave", onPointerLeave);
    renderer.domElement.addEventListener("click", onClick);

    let dragPaused = false;
    let resumeTimer = 0;
    controls.addEventListener("start", () => {
      dragPaused = true;
      window.clearTimeout(resumeTimer);
    });
    controls.addEventListener("end", () => {
      resumeTimer = window.setTimeout(() => {
        dragPaused = false;
      }, 1100);
    });

    const resize = () => {
      const { width, height } = mount.getBoundingClientRect();
      renderer.setSize(Math.max(1, width), Math.max(1, height), false);
      camera.aspect = Math.max(1, width) / Math.max(1, height);
      camera.updateProjectionMatrix();
      renderer.render(scene, camera);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(mount);

    const animationStartedAt = performance.now();
    let previousFrameAt = animationStartedAt;
    let animationFrame = 0;
    let frameCount = 0;
    let orbitMotionPaused = freezeOrbitOnLoad;
    const render = (frameAt = performance.now()) => {
      const delta = Math.min(
        Math.max(0, frameAt - previousFrameAt) / 1000,
        0.05,
      );
      const elapsed = (frameAt - animationStartedAt) / 1000;
      previousFrameAt = frameAt;
      material.update(delta);
      const frameSnapshot = material.getSnapshot();
      const motionOff =
        systemReducedMotion || frameSnapshot.reducedMotionPreview;
      if (
        !motionOff &&
        !dragPaused &&
        !orbitMotionPaused &&
        !frameSnapshot.paused
      ) {
        orbits.rotation.y += delta * ((Math.PI * 2) / 60);
        orbits.rotation.z = Math.sin(elapsed * 0.08) * 0.006;
      }
      controls.update();
      coreRelationship.update(
        frameSnapshot,
        motionOff || frameSnapshot.paused,
      );
      coreEffect.update(
        elapsed,
        motionOff || frameSnapshot.paused,
        delta,
      );
      renderer.render(scene, camera);
      frameCount += 1;
      if (frameCount % 12 === 0) {
        setSnapshot({
          ...frameSnapshot,
          coreRuneRelationship: coreRelationship.snapshot(),
          selfCore: coreEffect.snapshot(),
        });
      }
      animationFrame = requestAnimationFrame(render);
    };

    const settle = () => {
      material.update(2);
      renderer.render(scene, camera);
      const value = material.getSnapshot();
      setSnapshot(value);
      return value;
    };
    window.__PANTHEON_STAR_ORBITS__ = {
      renderer,
      scene,
      camera,
      controls,
      orbits,
      themes: PANTHEON_THEME_CONFIGS,
      materials: PANTHEON_MATERIAL_CONFIGS,
      get configs() {
        return runtime.getExportConfigs();
      },
      get metrics() {
        return runtime.metrics;
      },
      get ribbonMetrics() {
        return runtime.ribbonMetrics;
      },
      get bandMetrics() {
        return runtime.bandMetrics;
      },
      get ribbonFrameMode() {
        return runtime.ribbonFrameMode;
      },
      get geometryLock() {
        return runtime.getGeometryLock();
      },
      get interaction() {
        return material.getSnapshot();
      },
      get effects() {
        return {
          ...material.getSnapshot().effects,
          selfCore: coreEffect.snapshot(),
        };
      },
      get performance() {
        return {
          dpr: renderer.getPixelRatio(),
          calls: renderer.info.render.calls,
          triangles: renderer.info.render.triangles,
          geometries: renderer.info.memory.geometries,
          textures: renderer.info.memory.textures,
          shadows: renderer.shadowMap.enabled,
        };
      },
      get lightingBaseline() {
        return {
          ...REFLECTION_LIGHTING_BASELINE,
          fillToKeyRatio: isMobile
            ? REFLECTION_LIGHTING_BASELINE.fillIntensity.mobile /
              REFLECTION_LIGHTING_BASELINE.keyIntensity.mobile
            : REFLECTION_LIGHTING_BASELINE.fillIntensity.desktop /
              REFLECTION_LIGHTING_BASELINE.keyIntensity.desktop,
        };
      },
      get styleMatchLighting() {
        return {
          ...STYLE_MATCH_LIGHTING,
          model:
            "shared-three-point-soft-light-plus-stylized-material",
          perBandLightLinking: false,
        };
      },
      get productLighting() {
        return productLightingRig.snapshot();
      },
      get reflectionField() {
        return {
          version: "Pantheon PMREM Reflection Field Pass v1",
          candidateId: reflectionField.candidate.id,
          label: reflectionField.candidate.label,
          sourceSize: {
            width: reflectionField.sourceCanvas.width,
            height: reflectionField.sourceCanvas.height,
          },
          sourceColorSpace: THREE.SRGBColorSpace,
          textureUuid: environment.uuid,
          textureMapping: environment.mapping,
          textureColorSpace: environment.colorSpace,
          sceneEnvironmentUuid: scene.environment?.uuid ?? null,
          baseColor: reflectionField.candidate.baseColor,
          cards: reflectionField.candidate.cards.map((card) => ({
            ...card,
            stops: card.stops?.map((stop) => ({ ...stop })),
          })),
        };
      },
      getReflectionFieldSourceDataUrl() {
        return reflectionField.sourceCanvas.toDataURL("image/png");
      },
      get frameIndex() {
        return frameCount;
      },
      setProductLighting(patch) {
        productLightingRig.setSettings(patch);
        if (patch.backgroundDarkness != null) {
          styleBackground.setDarkness(patch.backgroundDarkness);
        }
        setProductLighting((current) => ({
          ...current,
          ...patch,
        }));
        renderer.render(scene, camera);
        return productLightingRig.snapshot();
      },
      getCenterlineSamples: (count) =>
        runtime.getCenterlineSamples(count),
      get coreRuneRelationship() {
        return coreRelationship.snapshot();
      },
      get selfCoreEffect() {
        return coreEffect.snapshot();
      },
      setSelfCoreArtifactCandidate(candidateId) {
        if (
          !Object.hasOwn(
            PANTHEON_SELF_CORE_ARTIFACT_PRESETS,
            candidateId,
          )
        ) {
          throw new Error(
            `Unknown Self Core artifact candidate: ${candidateId}`,
          );
        }
        const artifact =
          coreEffect.setArtifactCandidate(candidateId);
        setCoreArtifactRadius(artifact.radiusScale);
        setSelfCoreCandidate(candidateId);
        renderer.render(scene, camera);
        return coreEffect.snapshot();
      },
      forceCoreTheme(themeId) {
        coreRelationship.setForceTheme(themeId);
        return coreRelationship.snapshot();
      },
      measureCoreVisibility(sampleGrid = 36) {
        const nodes = runtime.getThemeNodes();
        orbits.updateMatrixWorld(true);
        camera.updateMatrixWorld(true);
        const coreCenter = nodes.core
          .getWorldPosition(new THREE.Vector3())
          .project(camera);
        const cameraRight = new THREE.Vector3(1, 0, 0)
          .applyQuaternion(camera.quaternion);
        const edge = nodes.core
          .getWorldPosition(new THREE.Vector3())
          .addScaledVector(
            cameraRight,
            nodes.core.userData.radius ?? SELF_CORE_RADIUS,
          )
          .project(camera);
        const radius = Math.hypot(
          edge.x - coreCenter.x,
          edge.y - coreCenter.y,
        );
        const raycaster = new THREE.Raycaster();
        const candidates = [
          nodes.core,
          ...nodes.ribbonMeshes.values(),
        ];
        let visible = 0;
        let total = 0;
        for (let row = 0; row < sampleGrid; row += 1) {
          for (let column = 0; column < sampleGrid; column += 1) {
            const x = ((column + 0.5) / sampleGrid) * 2 - 1;
            const y = ((row + 0.5) / sampleGrid) * 2 - 1;
            if (x * x + y * y > 1) continue;
            total += 1;
            raycaster.setFromCamera(
              new THREE.Vector2(
                coreCenter.x + x * radius,
                coreCenter.y + y * radius,
              ),
              camera,
            );
            const first = raycaster.intersectObjects(candidates, false)[0];
            if (first?.object === nodes.core) visible += 1;
          }
        }
        return {
          visibleRatio: total ? visible / total : 0,
          visibleSamples: visible,
          totalSamples: total,
        };
      },
      setView(view) {
        setCameraView(camera, controls, view);
        renderer.render(scene, camera);
        setCameraViewState(view);
      },
      setHoveredTheme(themeId) {
        material.setHoveredTheme(themeId);
        setHoveredTheme(themeId);
        return settle();
      },
      previewHoverEffect(themeId, elapsedSeconds = 0.3) {
        material.setHoveredTheme(themeId);
        setHoveredTheme(themeId);
        material.update(
          Math.min(
            Math.max(0, elapsedSeconds),
            0.6,
          ),
        );
        renderer.render(scene, camera);
        const value = material.getSnapshot();
        setSnapshot(value);
        return value;
      },
      selectTheme(themeId) {
        material.selectTheme(themeId);
        setSelectedTheme(themeId);
        setHoveredTheme(null);
        return settle();
      },
      clearSelection() {
        material.selectTheme(null);
        setSelectedTheme(null);
        return settle();
      },
      setTwist(themeId, value) {
        material.setTwist(themeId, value);
        return settle();
      },
      setMonochrome(value) {
        material.setMonochrome(value);
        setMonochrome(value);
        return settle();
      },
      setPaused(value) {
        material.setPaused(value);
        setPaused(value);
        return settle();
      },
      setReducedMotionPreview(value) {
        material.setReducedMotionPreview(value);
        setReducedMotion(value);
        return settle();
      },
      setOrbitMotionPaused(value) {
        orbitMotionPaused = Boolean(value);
        return settle();
      },
      setMobileQualityPreview(value) {
        material.setMobileQualityPreview(value);
        setMobileQuality(value);
        renderer.setPixelRatio(
          Math.min(window.devicePixelRatio || 1, value ? 1.5 : 2),
        );
        resize();
        return settle();
      },
      setRibbonWidthProfile(target, patch) {
        material.setWidthProfile(target, patch);
        return settle();
      },
      setBandWidthProfile(target, patch) {
        material.setWidthProfile(target, patch);
        return settle();
      },
      setThemeMaterial(themeId, patch) {
        material.setThemeMaterial(themeId, patch);
        return settle();
      },
      setReflectionCandidate(candidateId) {
        const value = material.setReflectionCandidate(candidateId);
        setReflectionCandidate(candidateId);
        renderer.render(scene, camera);
        setSnapshot(value);
        return value;
      },
      setStyleMatchCandidate(candidateId) {
        const value = material.setStyleMatchCandidate(candidateId);
        const candidate = PANTHEON_STYLE_MATCH_CANDIDATES[candidateId];
        if (candidate) {
          setStyleMatchCandidate(candidateId);
        }
        renderer.render(scene, camera);
        setSnapshot(value);
        return value;
      },
      setDirectSpecularCompressionCandidate(candidateId) {
        const value =
          material.setDirectSpecularCompressionCandidate(candidateId);
        renderer.render(scene, camera);
        setSnapshot(value);
        return value;
      },
      setStyleColorLiftCandidate(candidateId) {
        const value = material.setStyleColorLiftCandidate(candidateId);
        renderer.render(scene, camera);
        setSnapshot(value);
        return value;
      },
      setHumanDesignIndirectSpecularCandidate(candidateId) {
        const value =
          material.setHumanDesignIndirectSpecularCandidate(candidateId);
        renderer.render(scene, camera);
        setSnapshot(value);
        return value;
      },
      setMetalColorDensityCandidate(candidateId) {
        const value =
          material.setMetalColorDensityCandidate(candidateId);
        renderer.render(scene, camera);
        setSnapshot(value);
        return value;
      },
      setDebugDisplay(patch) {
        material.setDebugOverrides(patch);
        if (
          patch.fieldLightStrength != null ||
          patch.metalHighlightStrength != null
        ) {
          if (patch.fieldLightStrength != null) {
            productLightingRig.setSettings({
              environmentStrength: patch.fieldLightStrength,
            });
          }
        }
        setDebug((current) => ({ ...current, ...patch }));
        return settle();
      },
      attemptGeometryMutation(id, patch) {
        return runtime.updateAngles(id, patch);
      },
      unlockGeometry(confirmation) {
        return runtime.unlockGeometry(confirmation);
      },
      settle,
      render: settle,
    };

    if (systemReducedMotion) {
      material.setReducedMotionPreview(true);
      setReducedMotion(true);
    }
    resize();
    settle();
    render();

    return () => {
      cancelAnimationFrame(animationFrame);
      window.clearTimeout(resumeTimer);
      observer.disconnect();
      renderer.domElement.removeEventListener(
        "pointermove",
        onPointerMove,
      );
      renderer.domElement.removeEventListener(
        "pointerleave",
        onPointerLeave,
      );
      renderer.domElement.removeEventListener("click", onClick);
      controls.dispose();
      material.dispose();
      runtime.dispose();
      productLightingRig.dispose();
      renderer.dispose();
      environment.dispose();
      styleBackground.dispose();
      renderer.domElement.remove();
      runtimeRef.current = null;
      materialRef.current = null;
      lightingRef.current = null;
      coreEffectRef.current = null;
      coreRelationshipRef.current = null;
      cameraViewRef.current = null;
      delete window.__PANTHEON_STAR_ORBITS__;
      document.documentElement.classList.remove(
        "pantheon-star-orbit-mode",
      );
    };
  }, []);

  const activeTheme = selectedTheme
    ? PANTHEON_THEME_BY_ID[selectedTheme]
    : hoveredTheme
      ? PANTHEON_THEME_BY_ID[hoveredTheme]
      : null;

  const setInteractionPreview = (value) => {
    setDebugState(value);
    materialRef.current?.setDebugOverrides({
      ribbonProgress:
        value === "Debug Override" ? debug.ribbonProgress : null,
    });
    if (value === "Selected") applySelection(debugTheme);
    else if (value === "Hovered") {
      applySelection(null);
      applyHover(debugTheme);
    } else if (value === "Background") {
      const alternate =
        PANTHEON_THEME_CONFIGS.find(({ id }) => id !== debugTheme)?.id;
      applySelection(alternate);
    } else {
      applySelection(null);
      applyHover(null);
    }
  };

  return (
    <main className={styles.stage} aria-label="Pantheon Sphere">
      <section className={styles.viewport} aria-label="Pantheon 互動星軌">
        <div
          ref={mountRef}
          className={styles.canvas}
          data-pantheon-star-orbits
        />
        <div className={styles.brand}>
          <span>Pantheon Sphere</span>
          <strong>Five systems · One self</strong>
        </div>
        <nav className={styles.themeRail} aria-label="選擇人生解讀系統">
          {PANTHEON_THEME_CONFIGS.map((theme) => (
            <button
              key={theme.id}
              type="button"
              aria-pressed={selectedTheme === theme.id}
              data-theme={theme.id}
              onPointerEnter={() => {
                if (!selectedTheme) applyHover(theme.id);
              }}
              onPointerLeave={() => {
                if (!selectedTheme) applyHover(null);
              }}
              onClick={() =>
                applySelection(
                  selectedTheme === theme.id ? null : theme.id,
                )
              }
            >
              <span>{theme.symbol}</span>
              {theme.shortLabel}
            </button>
          ))}
        </nav>
        <article
          className={`${styles.themeCard} ${
            activeTheme ? styles.themeCardVisible : ""
          }`}
          aria-live="polite"
        >
          {activeTheme ? (
            <>
              <small>
                {selectedTheme ? "Selected system" : "Observe"}
              </small>
              <h2>{activeTheme.label}</h2>
              <p>{activeTheme.description}</p>
              {selectedTheme ? (
                <div className={styles.themeActions}>
                  <button type="button">{activeTheme.action}</button>
                  <button
                    type="button"
                    onClick={() => applySelection(null)}
                  >
                    返回
                  </button>
                </div>
              ) : null}
            </>
          ) : null}
        </article>
        {debug.showPhase ? (
          <aside className={styles.phaseLegend} aria-label="Phase search">
            <strong>Phase search · {ribbonFrameSearch.phaseStepDegrees}°</strong>
            {ribbonFrameSearch.orbits.map((orbit) => (
              <span key={orbit.id}>
                {orbit.id} {orbit.phaseDegrees}°
                {orbit.naturalRoll ? " · roll 8°" : " · fixed"}
                <small>
                  candidates {orbit.candidatePhases.join(" / ")}
                </small>
              </span>
            ))}
          </aside>
        ) : null}
      </section>

      <aside className={styles.panel} aria-label="Pantheon Band Material Lab">
        <header className={styles.panelHeader}>
          <p>Pantheon Style Match Final Balance Pass v1</p>
          <h1>Geometry v1.1 — LOCKED</h1>
          <span>
            Balanced color weights · Shared shading · Geometry locked
          </span>
        </header>

        <section className={styles.controlSection}>
          <label className={styles.select}>
            <span>Style Match candidate</span>
            <select
              value={styleMatchCandidate}
              onChange={(event) => {
                const candidateId = event.target.value;
                applyStyleMatchCandidate(candidateId);
              }}
            >
              {Object.values(PANTHEON_STYLE_MATCH_CANDIDATES).map(
                (candidate) => (
                  <option key={candidate.id} value={candidate.id}>
                    {candidate.label}
                  </option>
                ),
              )}
            </select>
          </label>
          <label className={styles.select}>
            <span>Self Core identity</span>
            <select
              value={selfCoreCandidate}
              onChange={(event) =>
                applySelfCoreCandidate(event.target.value)
              }
            >
              {Object.values(
                PANTHEON_SELF_CORE_ARTIFACT_PRESETS,
              ).map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {candidate.label}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.select}>
            <span>Camera view</span>
            <select
              value={cameraView}
              onChange={(event) => {
                const view = event.target.value;
                cameraViewRef.current?.(view);
              }}
            >
              {[
                "front",
                "front-left",
                "right",
                "back",
                "top",
                "orbit",
              ].map((view) => (
                <option key={view} value={view}>
                  {view}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.select}>
            <span>Theme selector</span>
            <select
              value={debugTheme}
              onChange={(event) => setDebugTheme(event.target.value)}
            >
              {PANTHEON_THEME_CONFIGS.map((theme) => (
                <option key={theme.id} value={theme.id}>
                  {theme.label}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.select}>
            <span>State</span>
            <select
              value={debugState}
              onChange={(event) =>
                setInteractionPreview(event.target.value)
              }
            >
              {[
                "Idle",
                "Hovered",
                "Selected",
                "Background",
                "Debug Override",
              ].map((state) => (
                <option key={state}>{state}</option>
              ))}
            </select>
          </label>
          <details className={styles.productLighting} open>
            <summary>Product Lighting</summary>
            <label className={styles.toggleRow}>
              <input
                type="checkbox"
                checked={productLighting.enabled}
                onChange={(event) =>
                  applyProductLightingPatch({
                    enabled: event.target.checked,
                  })
                }
              />
              Lighting Enabled
            </label>
            <label className={styles.select}>
              <span>Lighting Test State</span>
              <select
                value={productLighting.mode}
                onChange={(event) =>
                  applyProductLightingPatch({
                    mode: event.target.value,
                  })
                }
              >
                <option value="environment-only">
                  A · Environment Only
                </option>
                <option value="key-only">B · Key Only</option>
                <option value="key-rim">C · Key + Rim</option>
                <option value="full">D · Full Product Studio</option>
              </select>
            </label>
            <RangeControl
              label="Key Strength"
              value={productLighting.keyStrength}
              min={0}
              max={2}
              step={0.05}
              onChange={(value) =>
                applyProductLightingPatch({ keyStrength: value })
              }
            />
            <RangeControl
              label="Key Width"
              value={productLighting.keyWidth}
              min={2.8}
              max={4}
              step={0.1}
              onChange={(value) =>
                applyProductLightingPatch({ keyWidth: value })
              }
            />
            <RangeControl
              label="Key Height"
              value={productLighting.keyHeight}
              min={1.8}
              max={3}
              step={0.1}
              onChange={(value) =>
                applyProductLightingPatch({ keyHeight: value })
              }
            />
            <RangeControl
              label="Rim Strength"
              value={productLighting.rimStrength}
              min={0}
              max={2}
              step={0.05}
              onChange={(value) =>
                applyProductLightingPatch({ rimStrength: value })
              }
            />
            <RangeControl
              label="Top Accent Strength"
              value={productLighting.topStrength}
              min={0}
              max={2}
              step={0.05}
              onChange={(value) =>
                applyProductLightingPatch({ topStrength: value })
              }
            />
            <RangeControl
              label="Fill Strength"
              value={productLighting.fillStrength}
              min={0}
              max={1}
              step={0.02}
              onChange={(value) =>
                applyProductLightingPatch({ fillStrength: value })
              }
            />
            <RangeControl
              label="Environment Reflection"
              value={productLighting.environmentStrength}
              min={0}
              max={1.5}
              step={0.05}
              onChange={(value) =>
                applyProductLightingPatch({
                  environmentStrength: value,
                })
              }
            />
            <RangeControl
              label="Exposure"
              value={productLighting.exposure}
              min={0.6}
              max={1.5}
              step={0.01}
              onChange={(value) =>
                applyProductLightingPatch({ exposure: value })
              }
            />
            <RangeControl
              label="Background Darkness"
              value={productLighting.backgroundDarkness}
              min={0.8}
              max={1.3}
              step={0.01}
              onChange={(value) =>
                applyProductLightingPatch({
                  backgroundDarkness: value,
                })
              }
            />
            <label className={styles.toggleRow}>
              <input
                type="checkbox"
                checked={productLighting.debug}
                onChange={(event) =>
                  applyProductLightingPatch({
                    debug: event.target.checked,
                  })
                }
              />
              Lighting Debug
            </label>
            <button
              className={styles.resetControl}
              type="button"
              onClick={resetProductLighting}
            >
              Reset Product Lighting
            </button>
          </details>
          <label className={styles.select}>
            <span>Band validation</span>
            <select
              value={debug.validationMode}
              onChange={(event) =>
                applyDebugPatch({
                  validationMode: event.target.value,
                })
              }
            >
              <option value="material-v3">Luxury Material v3</option>
              <option value="baseline-linked-compare">
                Reflection v1 Archive
              </option>
              <option value="luxury-metal">Quiet Metal</option>
              <option value="brushed-metal">Brushed Metal</option>
              <option value="engraving-reveal">Raised Relief Reveal</option>
              <option value="front-back">Front / Back</option>
              <option value="normal">Surface Normal</option>
              <option value="tangent">Tangent / Side / Normal</option>
              <option value="edge">Top / Bevel / Edge</option>
              <option value="uv">UV Checker</option>
              <option value="roughness">Roughness</option>
              <option value="metalness">Metalness</option>
              <option value="marks">Surface Marks</option>
              <option value="flow">Surface Light Flow</option>
              <option value="bevel">Bevel Debug</option>
              <option value="outer-isolation">Outer Orbit Isolation</option>
              <option value="outer-intersections">Outer Intersections</option>
              <option value="over-under">Over / Under</option>
              <option value="mark-density">Surface Mark Density</option>
              <option value="engraving">Raised Relief Only</option>
              <option value="background-weight">Background Weight</option>
              <option value="physical-specular">Physical Specular Only</option>
              <option value="highlight-mask">Highlight Mask Only</option>
              <option value="core-suppression">Core Suppression Debug</option>
              <option value="grazing-response">Grazing Response Debug</option>
              <option value="dark-side-lift">Dark Side Lift Debug</option>
              <option value="reflection-rotation">Reflection Rotation Debug</option>
              <option value="luminance-heatmap">Luminance Heatmap</option>
              <option value="overexposure-mask">Overexposure Mask</option>
              <option value="reflection-profile">Per-Band Reflection Profile</option>
            </select>
          </label>
          <RangeControl
            label="Environment Reflection · legacy alias"
            value={debug.fieldLightStrength}
            min={0}
            max={1.5}
            step={0.05}
            onChange={(value) =>
              applyDebugPatch({ fieldLightStrength: value })
            }
          />
          <RangeControl
            label="Material Specular Response"
            value={debug.metalHighlightStrength}
            min={0.8}
            max={1.2}
            step={0.05}
            onChange={(value) =>
              applyDebugPatch({ metalHighlightStrength: value })
            }
          />
          <RangeControl
            label="Rune Flow Light Strength · all bands"
            value={debug.flowIntensity}
            min={0}
            max={2}
            step={0.05}
            onChange={(value) =>
              applyDebugPatch({ flowIntensity: value })
            }
          />
          <label className={styles.select}>
            <span>Core–Rune Relationship Debug</span>
            <select
              value={debug.forceCoreTheme}
              onChange={(event) =>
                applyDebugPatch({
                  forceCoreTheme: event.target.value,
                })
              }
            >
              <option value="auto">Auto · Surface Energy</option>
              {PANTHEON_THEME_CONFIGS.map((theme) => (
                <option key={theme.id} value={theme.id}>
                  Force · {theme.label}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.select}>
            <span>baseColor</span>
            <input
              type="color"
              value={materialDrafts[debugTheme].color}
              onChange={(event) =>
                applyMaterialPatch({ baseColor: event.target.value })
              }
            />
          </label>
          {[
            ["metalness", 0.55, 0.8, 0.01],
            ["roughness", 0.22, 0.38, 0.01],
            ["clearcoat", 0.35, 0.65, 0.01],
            ["clearcoatRoughness", 0.12, 0.25, 0.01],
            ["anisotropy", 0.25, 0.5, 0.01],
            ["envMapIntensity", 0.55, 0.8, 0.01],
          ].map(([key, min, max, step]) => (
            <RangeControl
              key={key}
              label={key}
              value={materialDrafts[debugTheme][key]}
              min={min}
              max={max}
              step={step}
              onChange={(value) => applyMaterialPatch({ [key]: value })}
            />
          ))}
          {[
            ["markOpacity", 0, 1, 0.01],
            ["markDepth", 0, 0.3, 0.01],
            ["markRoughnessDelta", -0.2, 0.3, 0.01],
            ["markMetalnessDelta", -0.2, 0.2, 0.01],
            ["markEmissive", 0, 0.01, 0.001],
            ["edgeBrightness", 0.86, 0.94, 0.01],
            ["edgeRoughness", 0.06, 0.12, 0.01],
          ].map(([key, min, max, step]) => (
            <RangeControl
              key={key}
              label={key}
              value={debug[key]}
              min={min}
              max={max}
              step={step}
              onChange={(value) => applyDebugPatch({ [key]: value })}
            />
          ))}
          <RangeControl
            label={`Band Width Preview · ${mobileQuality ? "Mobile" : "Desktop"}`}
            value={mobileQuality ? mobileWidths.idle : desktopWidths.idle}
            min={0.06}
            max={0.36}
            step={0.001}
            onChange={applyBandWidthPreview}
          />
          <button
            className={styles.resetControl}
            type="button"
            onClick={resetBandWidthPreview}
          >
            Reset Band Width
          </button>
          <RangeControl
            label="bandThickness · locked"
            value={0.02}
            min={0.02}
            max={0.02}
            step={0.0001}
            onChange={() => {}}
          />
          <RangeControl
            label="bevelWidth · locked"
            value={0.0024}
            min={0.0024}
            max={0.0024}
            step={0.0001}
            onChange={() => {}}
          />
          <RangeControl
            label="Opacity · opaque"
            value={debug.opacity}
            min={1}
            max={1}
            step={0.01}
            onChange={(value) => applyDebugPatch({ opacity: value })}
          />
        </section>

        <section className={styles.toggles}>
          {[
            ["showUV", "Show UV", debug.showUV],
            ["showFrame", "Show frame", debug.showFrame],
            ["showSeam", "Show seam", debug.showSeam],
            ["showTubeLine", "Debug tube", debug.showTubeLine],
            ["showBand", "Show Band", debug.showBand],
            ["showTopBottom", "Top / Bottom", debug.showTopBottom],
            ["showBevel", "Bevel", debug.showBevel],
            ["showEdges", "Edges", debug.showEdges],
            ["flatMaterial", "Flat Metal", debug.flatMaterial],
            ["showCore", "Show core", debug.showCore],
            ["showPhase", "Band phase", debug.showPhase],
            ["monochrome", "Monochrome", monochrome],
            ["paused", "Pause", paused],
            ["reduced", "Reduced motion", reducedMotion],
            ["mobile", "Mobile quality", mobileQuality],
          ].map(([key, label, checked]) => (
            <label key={key}>
              <input
                type="checkbox"
                checked={checked}
                onChange={(event) => {
                  const value = event.target.checked;
                  if (key === "monochrome") {
                    materialRef.current?.setMonochrome(value);
                    setMonochrome(value);
                  } else if (key === "paused") {
                    materialRef.current?.setPaused(value);
                    setPaused(value);
                  } else if (key === "reduced") {
                    materialRef.current?.setReducedMotionPreview(value);
                    setReducedMotion(value);
                  } else if (key === "mobile") {
                    materialRef.current?.setMobileQualityPreview(value);
                    setMobileQuality(value);
                  } else if (key === "showUV") {
                    applyDebugPatch({
                      showUV: value,
                      validationMode: value ? "uv" : "flat-pbr",
                    });
                  } else {
                    applyDebugPatch({ [key]: value });
                  }
                }}
              />
              {label}
            </label>
          ))}
        </section>

        <details className={styles.geometryLock}>
          <summary>Shared Style Match profile</summary>
          {snapshot?.styleMatch?.profile ? (
            Object.entries(snapshot.styleMatch.profile).map(([key, value]) => (
              <p key={key}>
                {key}{" "}
                <code>
                  {typeof value === "number"
                    ? Number(value).toFixed(3)
                    : String(value)}
                </code>
              </p>
            ))
          ) : (
            <p>Main-site profile initializing…</p>
          )}
        </details>

        <details className={styles.geometryLock}>
          <summary>Reflection v1 · Debug Archive</summary>
          <p>
            Per-band envMapRotation、highlight mask 與中心抑制保留供比較，
            正式 Style Match 候選不啟用。
          </p>
          <code>{reflectionCandidate}</code>
        </details>

        <details className={styles.geometryLock}>
          <summary>Geometry controls · locked</summary>
          <p>
            中心線、比例與 Self 半徑維持 Geometry v1.1 鎖定；
            Orbit Pose 以獨立簽章管理。
          </p>
          <code>
            Centerline ·{" "}
            {runtimeRef.current?.getGeometryLock().centerlineSignature ||
              "sha256:869d…6008"}
          </code>
          <code>
            Pose ·{" "}
            {runtimeRef.current?.getGeometryLock().poseSignature ||
              "sha256:9f0f15…b222"}
          </code>
          <p>
            受限姿態修正只調整 Ziwei Bazi 的 inclination／azimuth；
            中心線、Band 尺寸、Self Core 位置與 frame 均未改動。
          </p>
        </details>

        <footer className={styles.metrics}>
          <span>Pantheon Band profile</span>
          <span>{snapshot?.geometryBuilds ?? 1} build · 0 per frame</span>
          <span>Desktop width · all states</span>
          <span>
            {desktopWidths.idle.toFixed(3)}
          </span>
          <span>Mobile width · all states</span>
          <span>
            {mobileWidths.idle.toFixed(3)}
          </span>
          <span>Thickness / bevel</span>
          <span>0.0200 / 0.0024 × 2</span>
        </footer>
      </aside>
    </main>
  );
}
