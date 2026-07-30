import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { createPantheonProductLightingRig } from "../lighting/createPantheonProductLightingRig.ts";
import { createIdentitySwatchGeometry } from "../material-identity/createIdentitySwatchGeometry.ts";
import { createPantheonIdentityMaterial } from "../material-identity/createPantheonIdentityMaterial.ts";
import {
  PANTHEON_SURFACE_IDENTITIES,
} from "../material-identity/pantheonSurfaceIdentityPresets.ts";
import styles from "./PantheonMaterialIdentityLab.module.css";

const FORMAL_GEOMETRY_SIGNATURE =
  "sha256:869d8d22fddea450b4921e20c4732622e54bc1b895b1875de50f94ba076c6008";

const DEFAULTS = Object.freeze({
  phase: 3,
  mesoStrength: 1,
  microNormalStrength: 1,
  roughnessVariation: 1,
  reliefDepth: 1,
  reliefDensity: 1,
  brushScale: 1,
  brushIrregularity: 0,
  polishedZoneStrength: 1,
  oxidizedZoneStrength: 1,
  monochrome: true,
  noMicro: false,
  noRelief: false,
  debugMode: "beauty",
  mobilePreview: false,
  labelsVisible: true,
});

const VIEWS = {
  front: {
    position: [-0.55, 0, 8],
    target: [-0.55, 0, 0],
  },
  "forty-five": {
    position: [4.25, 0.35, 6.5],
    target: [-0.35, 0, 0],
  },
  grazing: {
    position: [6.2, 0.2, 3.5],
    target: [-0.25, 0, 0],
  },
};

function rgba(hexColor, alpha) {
  const value = Number.parseInt(hexColor.slice(1), 16);
  return `rgba(${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255}, ${alpha})`;
}

function createFormalEnvironment(renderer) {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 256;
  const context = canvas.getContext("2d");
  context.fillStyle = "#34424e";
  context.fillRect(0, 0, canvas.width, canvas.height);
  const cards = [
    [24, 18, 432, 78, "#fcf2e2", 0.96, 20],
    [390, 36, 76, 178, "#dae8ed", 0.78, 16],
    [8, 116, 164, 100, "#0c131b", 0.62, 20],
    [118, 174, 292, 46, "#bccdd5", 0.34, 24],
  ];
  cards.forEach(([x, y, width, height, color, alpha, blur]) => {
    context.save();
    context.filter = `blur(${blur}px)`;
    context.fillStyle = rgba(color, alpha);
    context.fillRect(x, y, width, height);
    context.restore();
  });
  context.save();
  context.filter = "blur(18px)";
  const warm = context.createRadialGradient(216, 112, 6, 216, 112, 74);
  warm.addColorStop(0, rgba("#ffd28b", 0.82));
  warm.addColorStop(0.5, rgba("#eeb86c", 0.4));
  warm.addColorStop(1, rgba("#bf8446", 0));
  context.fillStyle = warm;
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.restore();
  const source = new THREE.CanvasTexture(canvas);
  source.mapping = THREE.EquirectangularReflectionMapping;
  source.colorSpace = THREE.SRGBColorSpace;
  const generator = new THREE.PMREMGenerator(renderer);
  const texture = generator.fromEquirectangular(source).texture;
  source.dispose();
  generator.dispose();
  return texture;
}

function Slider({ label, value, min, max, step, onChange }) {
  return (
    <div className={styles.control}>
      <label>
        <span>{label}</span>
        <output>{Number(value).toFixed(2)}</output>
      </label>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </div>
  );
}

export default function PantheonMaterialIdentityLab() {
  const mountRef = useRef(null);
  const runtimeRef = useRef(null);
  const [settings, setSettings] = useState(DEFAULTS);
  const [view, setViewState] = useState("front");
  const [theme, setTheme] = useState("all");
  const [metrics, setMetrics] = useState({
    drawCalls: 0,
    triangles: 0,
    materialInstances: 1,
  });

  const selectedPreset = useMemo(
    () => PANTHEON_SURFACE_IDENTITIES.find((item) => item.id === theme),
    [theme],
  );

  useEffect(() => {
    document.documentElement.classList.add(
      "pantheon-material-identity-lab-mode",
    );
    return () => {
      document.documentElement.classList.remove(
        "pantheon-material-identity-lab-mode",
      );
    };
  }, []);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;
    let active = true;
    let animationFrame = 0;
    let resizeObserver;
    let disposeRuntime = () => {};

    const boot = async () => {
      const renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: false,
        powerPreference: "high-performance",
        preserveDrawingBuffer: true,
      });
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.AgXToneMapping;
      renderer.toneMappingExposure = 1.08;
      renderer.shadowMap.enabled = false;
      renderer.setClearColor("#1b2024");
      mount.append(renderer.domElement);

      const scene = new THREE.Scene();
      scene.background = new THREE.Color("#242b30");
      const environment = createFormalEnvironment(renderer);
      scene.environment = environment;
      scene.environmentIntensity = 0.48;
      const lighting = createPantheonProductLightingRig(scene, {
        initial: { exposure: 1.08 },
        onEnvironmentStrengthChange: (value) => {
          scene.environmentIntensity = value;
        },
        onExposureChange: (value) => {
          renderer.toneMappingExposure = value;
        },
      });

      const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 30);
      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.08;
      controls.enablePan = false;
      controls.minDistance = 3.4;
      controls.maxDistance = 8.5;

      const geometry = createIdentitySwatchGeometry();
      const identityMaterial = await createPantheonIdentityMaterial(environment);
      if (!active) {
        geometry.dispose();
        identityMaterial.dispose();
        renderer.dispose();
        renderer.domElement.remove();
        return;
      }
      const mesh = new THREE.Mesh(geometry, identityMaterial.material);
      mesh.name = "PantheonIdentitySwatches";
      scene.add(mesh);

      const applyView = (nextView) => {
        const selected = VIEWS[nextView] ?? VIEWS.front;
        camera.position.fromArray(selected.position);
        controls.target.fromArray(selected.target);
        if (mount.clientWidth < 640) {
          camera.position.y += 0.42;
          controls.target.y += 0.42;
        }
        controls.update();
      };
      applyView("front");

      const resize = () => {
        const width = Math.max(1, mount.clientWidth);
        const height = Math.max(1, mount.clientHeight);
        const mobile = width < 640;
        renderer.setPixelRatio(
          Math.min(window.devicePixelRatio || 1, mobile ? 1.25 : 1.75),
        );
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
      };
      resizeObserver = new ResizeObserver(resize);
      resizeObserver.observe(mount);
      resize();

      const renderOnce = () => {
        controls.update();
        renderer.render(scene, camera);
      };
      const render = () => {
        renderOnce();
        animationFrame = requestAnimationFrame(render);
      };
      render();

      const measurePerformance = async (frames = 90) => {
        const cpuSamples = [];
        for (let index = 0; index < frames; index += 1) {
          const start = performance.now();
          renderer.render(scene, camera);
          cpuSamples.push(performance.now() - start);
        }
        const gl = renderer.getContext();
        const extension = gl.getExtension("EXT_disjoint_timer_query_webgl2");
        let gpuMs = null;
        if (extension && typeof gl.createQuery === "function") {
          const query = gl.createQuery();
          gl.beginQuery(extension.TIME_ELAPSED_EXT, query);
          renderer.render(scene, camera);
          gl.endQuery(extension.TIME_ELAPSED_EXT);
          for (let attempt = 0; attempt < 120; attempt += 1) {
            const available = gl.getQueryParameter(
              query,
              gl.QUERY_RESULT_AVAILABLE,
            );
            const disjoint = gl.getParameter(extension.GPU_DISJOINT_EXT);
            if (available && !disjoint) {
              gpuMs = gl.getQueryParameter(query, gl.QUERY_RESULT) / 1e6;
              break;
            }
            await new Promise((resolve) => setTimeout(resolve, 8));
          }
          gl.deleteQuery(query);
        }
        return {
          cpuRenderMs:
            cpuSamples.reduce((sum, sample) => sum + sample, 0) /
            cpuSamples.length,
          gpuFrameMs: gpuMs,
          source: gpuMs == null ? "CPU submission fallback" : "EXT_disjoint_timer_query_webgl2",
        };
      };

      const api = {
        renderer,
        scene,
        camera,
        controls,
        mesh,
        geometry,
        material: identityMaterial,
        presets: PANTHEON_SURFACE_IDENTITIES,
        geometrySignature: FORMAL_GEOMETRY_SIGNATURE,
        setPhase: (phase) => identityMaterial.setControls({ phase }),
        setControls: (patch) => identityMaterial.setControls(patch),
        setView: (nextView) => applyView(nextView),
        setRotation: (radians) => {
          mesh.rotation.y = radians;
          renderOnce();
        },
        setTheme: (identityId) => {
          if (identityId === "all") {
            identityMaterial.setSelectedIdentity(null);
            applyView("front");
            return;
          }
          const identity = PANTHEON_SURFACE_IDENTITIES.findIndex(
            (item) => item.id === identityId,
          );
          identityMaterial.setSelectedIdentity(identity);
          camera.position.set(-0.42, (2 - identity) * 0.63, 3.15);
          controls.target.set(-0.42, (2 - identity) * 0.63, 0.12);
          controls.update();
        },
        render: renderOnce,
        measurePerformance,
        snapshot: () => ({
          version: "Pantheon Material Identity Lab v1",
          formalSphereStatus: "NEEDS WORK",
          formalGeometryUntouched: true,
          geometrySignature: FORMAL_GEOMETRY_SIGNATURE,
          drawCalls: renderer.info.render.calls,
          triangles: renderer.info.render.triangles,
          materialInstances: 1,
          meshes: 1,
          pmremUuid: environment.uuid,
          lighting: lighting.snapshot(),
          material: identityMaterial.snapshot(),
          presets: PANTHEON_SURFACE_IDENTITIES,
        }),
      };
      runtimeRef.current = api;
      window.__PANTHEON_MATERIAL_IDENTITY_LAB__ = api;
      identityMaterial.setControls(settings);
      renderer.render(scene, camera);
      setMetrics({
        drawCalls: renderer.info.render.calls,
        triangles: renderer.info.render.triangles,
        materialInstances: 1,
      });

      disposeRuntime = () => {
        cancelAnimationFrame(animationFrame);
        resizeObserver?.disconnect();
        controls.dispose();
        lighting.dispose();
        geometry.dispose();
        identityMaterial.dispose();
        environment.dispose();
        renderer.dispose();
        renderer.domElement.remove();
        delete window.__PANTHEON_MATERIAL_IDENTITY_LAB__;
      };
    };
    boot();
    return () => {
      active = false;
      disposeRuntime();
    };
  }, []);

  useEffect(() => {
    runtimeRef.current?.setControls(settings);
  }, [settings]);

  const patch = (next) => setSettings((current) => ({ ...current, ...next }));
  const setView = (nextView) => {
    setViewState(nextView);
    runtimeRef.current?.setView(nextView);
  };
  const chooseTheme = (nextTheme) => {
    setTheme(nextTheme);
    runtimeRef.current?.setTheme(nextTheme);
  };
  const reset = () => {
    setSettings(DEFAULTS);
    setTheme("all");
    setView("front");
    runtimeRef.current?.setTheme("all");
  };

  return (
    <main className={styles.lab}>
      <section
        className={`${styles.viewport} ${
          settings.mobilePreview ? styles.mobileViewport : ""
        }`}
        aria-label="材質製造工藝比較畫布"
      >
        <div className={styles.canvas} ref={mountRef} />
        <header className={styles.heading}>
          <span>Pantheon Surface Identity Lab · v1</span>
          <h1>Five processes. One metal baseline.</h1>
          <p>同色、同光、同曲率，只比較加工語言。</p>
        </header>
        <ol
          className={`${styles.labels} ${
            settings.labelsVisible ? "" : styles.labelsHidden
          }`}
          aria-hidden={!settings.labelsVisible}
        >
          {PANTHEON_SURFACE_IDENTITIES.map((preset, index) => (
            <li key={preset.id}>
              <b>{String(index + 1).padStart(2, "0")}</b>
              <span>
                <strong>{preset.label}</strong>
                <small>{preset.process}</small>
              </span>
            </li>
          ))}
        </ol>
        <div className={styles.status}>
          <span>Geometry v1.1 untouched</span>
          <strong>
            {metrics.drawCalls} draw · {metrics.materialInstances} material ·{" "}
            {metrics.triangles.toLocaleString()} tris
          </strong>
        </div>
      </section>

      <aside className={styles.panel} aria-label="Material Identity Lab 控制台">
        <header className={styles.panelHeader}>
          <span>Surface manufacturing study</span>
          <h2>Material Identity Lab</h2>
          <p>
            正式球體保持鎖定。本頁只產出 Surface Identity Preset，不會回寫正式材質。
          </p>
        </header>

        <section className={styles.section}>
          <h3>Phase</h3>
          <div className={styles.segmented}>
            {[1, 2, 3].map((phase) => (
              <button
                key={phase}
                type="button"
                aria-pressed={settings.phase === phase}
                onClick={() => patch({ phase })}
              >
                {phase === 1 ? "Meso" : phase === 2 ? "Micro" : "Relief"}
              </button>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <h3>Theme Identity Preset</h3>
          <select
            className={styles.select}
            value={theme}
            onChange={(event) => chooseTheme(event.target.value)}
          >
            <option value="all">All five processes</option>
            {PANTHEON_SURFACE_IDENTITIES.map((preset) => (
              <option key={preset.id} value={preset.id}>
                {preset.label} · {preset.brushDirection}
              </option>
            ))}
          </select>
          {selectedPreset && (
            <p>{selectedPreset.process}</p>
          )}
        </section>

        <section className={styles.section}>
          <h3>Identity Controls</h3>
          <Slider label="Meso Strength" value={settings.mesoStrength} min={0} max={1.6} step={0.02} onChange={(value) => patch({ mesoStrength: value })} />
          <Slider label="Micro Normal Strength" value={settings.microNormalStrength} min={0} max={1.8} step={0.02} onChange={(value) => patch({ microNormalStrength: value })} />
          <Slider label="Roughness Variation" value={settings.roughnessVariation} min={0} max={1.6} step={0.02} onChange={(value) => patch({ roughnessVariation: value })} />
          <Slider label="Relief Depth" value={settings.reliefDepth} min={0} max={1.8} step={0.02} onChange={(value) => patch({ reliefDepth: value })} />
          <Slider label="Relief Density" value={settings.reliefDensity} min={0.3} max={1.6} step={0.02} onChange={(value) => patch({ reliefDensity: value })} />
          <Slider label="Brush Scale" value={settings.brushScale} min={0.5} max={1.8} step={0.02} onChange={(value) => patch({ brushScale: value })} />
          <Slider label="Brush Irregularity" value={settings.brushIrregularity} min={0} max={1} step={0.02} onChange={(value) => patch({ brushIrregularity: value })} />
          <Slider label="Polished Zone" value={settings.polishedZoneStrength} min={0} max={1.5} step={0.02} onChange={(value) => patch({ polishedZoneStrength: value })} />
          <Slider label="Oxidized Zone" value={settings.oxidizedZoneStrength} min={0} max={1.5} step={0.02} onChange={(value) => patch({ oxidizedZoneStrength: value })} />
        </section>

        <section className={styles.section}>
          <h3>Comparison Modes</h3>
          <div className={styles.toggleGrid}>
            <label><input type="checkbox" checked={settings.monochrome} onChange={(event) => patch({ monochrome: event.target.checked })} />Monochrome</label>
            <label><input type="checkbox" checked={!settings.labelsVisible} onChange={(event) => patch({ labelsVisible: !event.target.checked })} />Blind identity</label>
            <label><input type="checkbox" checked={settings.noMicro} onChange={(event) => patch({ noMicro: event.target.checked })} />No Micro</label>
            <label><input type="checkbox" checked={settings.noRelief} onChange={(event) => patch({ noRelief: event.target.checked })} />No Relief</label>
            <label><input type="radio" name="debug" checked={settings.debugMode === "roughness"} onChange={() => patch({ debugMode: "roughness" })} />Roughness Only</label>
            <label><input type="radio" name="debug" checked={settings.debugMode === "normal"} onChange={() => patch({ debugMode: "normal" })} />Normal Only</label>
            <label><input type="radio" name="debug" checked={settings.debugMode === "brush"} onChange={() => patch({ debugMode: "brush" })} />Brush Mask Only</label>
            <label><input type="radio" name="debug" checked={settings.debugMode === "beauty"} onChange={() => patch({ debugMode: "beauty" })} />Beauty</label>
            <label><input type="checkbox" checked={settings.mobilePreview} onChange={(event) => patch({ mobilePreview: event.target.checked })} />Mobile Preview</label>
          </div>
        </section>

        <section className={styles.section}>
          <h3>View</h3>
          <div className={styles.viewButtons}>
            {Object.keys(VIEWS).map((item) => (
              <button
                key={item}
                type="button"
                aria-pressed={view === item}
                onClick={() => setView(item)}
              >
                {item === "forty-five" ? "45° angle" : item}
              </button>
            ))}
          </div>
          <button className={styles.reset} type="button" onClick={reset}>
            Reset Identity
          </button>
        </section>
      </aside>
    </main>
  );
}
