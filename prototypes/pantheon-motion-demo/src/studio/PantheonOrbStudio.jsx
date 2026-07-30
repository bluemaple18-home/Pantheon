import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import {
  createPantheonOrbModel,
  getPantheonOrbRuntime,
  PANTHEON_LOOP_SECONDS,
} from "../generated/createPantheonOrbModel.ts";
import { createSingleMobiusPrototype } from "../generated/createSingleMobiusPrototype.ts";
import { createTwoMobiusPrototype } from "../generated/createTwoMobiusPrototype.ts";
import { createFiveMobiusSpherePrototype } from "../generated/createFiveMobiusSpherePrototype.ts";
import {
  createControlledTwelveMobiusPrototype,
  LAYERED_QUATERNIONS,
} from "../generated/createControlledSevenMobiusPrototype.ts";
import { createMobiusPatchSpherePrototype } from "../generated/createMobiusPatchSpherePrototype.ts";
import { createWovenSpherePrototype } from "../generated/createWovenSpherePrototype.ts";
import { createPantheonThemeSpherePrototype } from "../generated/createPantheonThemeSpherePrototype.ts";
import { createPantheonSphereManualBlockout } from "../generated/createPantheonSphereManualBlockout.ts";
import {
  createPantheonFiveOrbitSphere,
  RECOMMENDED_ORBIT_CONFIGS,
} from "../generated/createPantheonFiveOrbitSphere.ts";
import styles from "./PantheonOrbStudio.module.css";

const FRAME_WIDTH = 720;
const FRAME_HEIGHT = 864;

function applyView(camera, view) {
  if (view === "orbit") {
    camera.position.set(3.55, 1.1, 6.15);
  } else if (view === "side") {
    camera.position.set(6.6, 0.35, 2.25);
  } else {
    camera.position.set(0, 0.15, 9.35);
  }
  camera.lookAt(0, 0, 0);
}

function applySingleMobiusView(camera, view) {
  if (view === "orbit") {
    camera.position.set(4.8, 1.5, 8.3);
  } else if (view === "side") {
    camera.position.set(8.5, 0.5, 3);
  } else {
    camera.position.set(0, 0.1, 8.8);
  }
  camera.lookAt(0, 0, 0);
}

function applyPatchSphereView(camera, view) {
  if (view === "orbit") {
    camera.position.set(5.1, 1.6, 8.6);
  } else if (view === "side") {
    camera.position.set(8.8, 0.5, 3.1);
  } else {
    camera.position.set(0, 0.1, 8.4);
  }
  camera.lookAt(0, 0, 0);
}

function applySymmetricMobiusView(camera, view) {
  if (view === "orbit") {
    camera.position.set(4.8, 1.5, 8.3);
  } else if (view === "side") {
    camera.position.set(8.5, 0.5, 3);
  } else {
    camera.position.set(0, 0, 8.8);
  }
  camera.lookAt(0, 0, 0);
}

function applyBlockoutView(camera, view) {
  if (view === "orbit") {
    camera.position.set(4.7, 1.55, 8.15);
  } else if (view === "side") {
    camera.position.set(8.8, 0.2, 0);
  } else if (view === "back") {
    camera.position.set(0, 0.1, -8.8);
  } else {
    camera.position.set(0, 0.1, 8.8);
  }
  camera.lookAt(0, 0, 0);
}

const PHASE_A_VIEWS = {
  front: [0, 0, 4.8],
  back: [0, 0, -4.8],
  left: [-4.8, 0, 0],
  right: [4.8, 0, 0],
  top: [0, 4.8, 0.001],
  bottom: [0, -4.8, 0.001],
  "front-left": [-3.35, 0.55, 3.35],
  "front-right": [3.35, 0.55, 3.35],
};

function applyPhaseAView(camera, view) {
  const position = PHASE_A_VIEWS[view] || PHASE_A_VIEWS.front;
  camera.position.set(...position);
  camera.lookAt(0, 0, 0);
}

const PHASE_A_FIELDS = [
  ["baseRadius", "半徑", 0.001],
  ["coreApproachRadius", "核心接近半徑", 0.01],
  ["pathPhase", "路徑相位", 0.1],
  ["inclination", "傾角", 1],
  ["azimuth", "方位", 1],
  ["latitudeBias", "緯度偏移", 0.01],
  ["latitudeAmplitude", "緯度振幅", 0.01],
  ["tubeRadius", "線徑", 0.001],
];

export default function PantheonOrbStudio({
  embedded = false,
  prototypeOverride = null,
}) {
  const mountRef = useRef(null);
  const requestedPrototype =
    prototypeOverride ||
    new URLSearchParams(window.location.search).get("prototype");
  const isPhaseAOrbit = requestedPrototype === "pantheon-five-orbit-phase-a";
  const [phaseAConfigs, setPhaseAConfigs] = useState(() =>
    RECOMMENDED_ORBIT_CONFIGS.map((config) => ({ ...config })),
  );
  const [phaseAConfigJson, setPhaseAConfigJson] = useState("");
  const [phaseAConfigError, setPhaseAConfigError] = useState("");

  const syncPhaseAConfigs = (configs) => {
    setPhaseAConfigs(configs.map((config) => ({ ...config })));
    setPhaseAConfigError("");
  };

  const callPhaseARuntime = (method, ...args) => {
    const result = window.__PANTHEON_STUDIO__?.[method]?.(...args);
    if (Array.isArray(result)) syncPhaseAConfigs(result);
    return result;
  };

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;

    const documentModeClass = embedded
      ? "pantheon-lab-mode"
      : "pantheon-studio-mode";
    document.documentElement.classList.add(documentModeClass);

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      preserveDrawingBuffer: true,
      premultipliedAlpha: false,
    });
    renderer.setPixelRatio(1);
    renderer.setSize(FRAME_WIDTH, FRAME_HEIGHT, false);
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.08;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    mount.append(renderer.domElement);

    const scene = new THREE.Scene();
    const blockoutMaterial = new THREE.MeshStandardMaterial({
      color: 0xb7b1a6,
      metalness: 0,
      roughness: 0.82,
    });
    const camera = new THREE.PerspectiveCamera(30, FRAME_WIDTH / FRAME_HEIGHT, 0.1, 100);
    const params = new URLSearchParams(window.location.search);
    const view = params.get("view") || "front";
    const prototype = prototypeOverride || params.get("prototype");
    const isSingleMobius = prototype === "single-mobius";
    const isTwoMobius = prototype === "two-mobius";
    const isFiveMobius = prototype === "five-mobius";
    const isControlledMobius =
      prototype === "twelve-layered-mobius" ||
      prototype === "nine-controlled-mobius" ||
      prototype === "twelve-controlled-mobius" ||
      prototype === "seven-controlled-mobius" ||
      prototype === "five-controlled-mobius";
    const isWovenSphere = prototype === "woven-sphere";
    const isThemeSphere = prototype === "pantheon-theme-sphere";
    const isSphereBlockout =
      prototype === "pantheon-phase2-blockout";
    const isFiveOrbitPhaseA =
      prototype === "pantheon-five-orbit-phase-a";
    const isPatchSphere = prototype === "mobius-patch-sphere";
    if (isSphereBlockout || isFiveOrbitPhaseA) {
      renderer.setClearColor(0x0b0d0f, 1);
      renderer.toneMappingExposure = 0.92;
    }
    if (isFiveOrbitPhaseA) {
      camera.fov = 32;
      camera.updateProjectionMatrix();
      applyPhaseAView(camera, view);
    } else if (isSphereBlockout) {
      applyBlockoutView(camera, view);
    } else if (isPatchSphere) {
      applyPatchSphereView(camera, view);
    } else if (isControlledMobius || isWovenSphere || isThemeSphere) {
      applySymmetricMobiusView(camera, view);
    } else if (isSingleMobius || isTwoMobius || isFiveMobius) {
      applySingleMobiusView(camera, view);
      if (isFiveMobius && view === "front") {
        camera.position.set(0, 0.1, 9.4);
        camera.lookAt(0, 0, 0);
      }
    } else {
      applyView(camera, view);
    }

    const pmrem = new THREE.PMREMGenerator(renderer);
    const environment = pmrem.fromScene(new RoomEnvironment(), 0.04);
    scene.environment = environment.texture;

    const key = new THREE.DirectionalLight(
      isSphereBlockout || isFiveOrbitPhaseA ? 0xffffff : 0xffd99c,
      isSphereBlockout || isFiveOrbitPhaseA ? 1.8 : 4.5,
    );
    key.position.set(-3.8, 5.2, 5.8);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    scene.add(key);

    const fill = new THREE.DirectionalLight(
      isSphereBlockout || isFiveOrbitPhaseA ? 0xd5dce2 : 0xb8d8d3,
      isSphereBlockout || isFiveOrbitPhaseA ? 0.65 : 2.1,
    );
    fill.position.set(4.8, -1.4, 4.2);
    scene.add(fill);

    const rim = new THREE.DirectionalLight(
      isSphereBlockout || isFiveOrbitPhaseA ? 0xffffff : 0xffefd2,
      isSphereBlockout || isFiveOrbitPhaseA ? 1.2 : 3.3,
    );
    rim.position.set(1.2, 3.6, -5.5);
    scene.add(rim);

    const orb = isSingleMobius
      ? createSingleMobiusPrototype()
      : isTwoMobius
        ? createTwoMobiusPrototype()
        : isFiveMobius
          ? createFiveMobiusSpherePrototype()
          : isWovenSphere
            ? createWovenSpherePrototype()
            : isThemeSphere
              ? createPantheonThemeSpherePrototype()
            : isSphereBlockout
              ? createPantheonSphereManualBlockout()
            : isFiveOrbitPhaseA
              ? createPantheonFiveOrbitSphere()
            : isControlledMobius
            ? createControlledTwelveMobiusPrototype()
            : isPatchSphere
              ? createMobiusPatchSpherePrototype()
              : createPantheonOrbModel();
    orb.scale.setScalar(
      isSingleMobius || isTwoMobius
        ? 1.15
        : isWovenSphere
          ? 1.62
        : isThemeSphere
          ? 1.35
        : isSphereBlockout
          ? 1.38
        : isFiveOrbitPhaseA
          ? 1
        : isControlledMobius
          ? 1.05
        : isFiveMobius
          ? 0.95
          : isPatchSphere
            ? 1
            : 0.88,
    );
    scene.add(orb);
    const runtime = getPantheonOrbRuntime(orb);
    const cameraControls = isControlledMobius || isWovenSphere || isThemeSphere || isSphereBlockout || isFiveOrbitPhaseA
      ? new OrbitControls(camera, renderer.domElement)
      : null;
    if (cameraControls) {
      cameraControls.target.set(0, 0, 0);
      cameraControls.enableDamping = true;
      cameraControls.dampingFactor = 0.08;
      cameraControls.enablePan = false;
      cameraControls.minDistance = isFiveOrbitPhaseA ? 2.8 : 5.4;
      cameraControls.maxDistance = isFiveOrbitPhaseA ? 8 : 13;
      cameraControls.minPolarAngle = 0.08;
      cameraControls.maxPolarAngle = Math.PI - 0.08;
      cameraControls.update();
    }

    let captureTime = Number(params.get("time") || "0");
    let captureMode = params.get("capture") === "1";
    let animationFrame = 0;
    const startedAt = performance.now() / 1000 - captureTime;

    const renderAt = (time) => {
      captureTime = time;
      runtime.tick(time);
      renderer.render(scene, camera);
    };
    const renderOrbitView = () => renderAt(captureTime);
    cameraControls?.addEventListener("change", renderOrbitView);

    const animate = () => {
      cameraControls?.update();
      if (!captureMode) renderAt(performance.now() / 1000 - startedAt);
      animationFrame = requestAnimationFrame(animate);
    };

    window.__PANTHEON_STUDIO__ = {
      width: FRAME_WIDTH,
      height: FRAME_HEIGHT,
      loopSeconds: PANTHEON_LOOP_SECONDS,
      renderer,
      scene,
      camera,
      cameraControls,
      orb,
      setTime(time) {
        captureMode = true;
        renderAt(time);
      },
      setView(view) {
        if (isFiveOrbitPhaseA) {
          applyPhaseAView(camera, view);
        } else if (isSphereBlockout) {
          applyBlockoutView(camera, view);
        } else if (isPatchSphere) {
          applyPatchSphereView(camera, view);
        } else if (isControlledMobius || isWovenSphere || isThemeSphere) {
          applySymmetricMobiusView(camera, view);
        } else if (isSingleMobius || isTwoMobius || isFiveMobius) {
          applySingleMobiusView(camera, view);
          if (isFiveMobius && view === "front") {
            camera.position.set(0, 0.1, 9.4);
            camera.lookAt(0, 0, 0);
          }
        } else {
          applyView(camera, view);
        }
        cameraControls?.target.set(0, 0, 0);
        cameraControls?.update();
        renderAt(captureTime);
      },
      setMaterialMode(mode) {
        scene.overrideMaterial = mode === "blockout" ? blockoutMaterial : null;
        renderAt(captureTime);
      },
      setBandRotation(id, rotation) {
        const pivot = runtime.bandPivots[id];
        if (!pivot) return false;
        pivot.rotation.set(
          THREE.MathUtils.degToRad(rotation.x),
          THREE.MathUtils.degToRad(rotation.y),
          THREE.MathUtils.degToRad(rotation.z),
        );
        renderAt(captureTime);
        return true;
      },
      setMobiusArrangement(stepRotation) {
        Object.values(runtime.bandPivots).forEach((pivot, index) => {
          pivot.rotation.set(
            THREE.MathUtils.degToRad(stepRotation.x * index),
            THREE.MathUtils.degToRad(stepRotation.y * index),
            THREE.MathUtils.degToRad(stepRotation.z * index),
          );
        });
        renderAt(captureTime);
      },
      setMobiusSphericalArrangement() {
        Object.values(runtime.bandPivots).forEach((pivot, index) => {
          pivot.quaternion.copy(LAYERED_QUATERNIONS[index]);
        });
        renderAt(captureTime);
      },
      setMobiusVisibleCount(count) {
        Object.values(runtime.bandPivots).forEach((pivot, index) => {
          pivot.visible = index < count;
        });
        renderAt(captureTime);
      },
      setCoreVisible(visible) {
        const core = runtime.meshes.core;
        const coreGlow = runtime.meshes.coreGlow;
        if (core) core.visible = visible;
        if (coreGlow) coreGlow.visible = visible;
        renderAt(captureTime);
      },
      setWovenDebugMode(enabled) {
        runtime.setDebugMode?.(enabled);
        renderAt(captureTime);
      },
      setThemeSphereDebugMode(enabled) {
        runtime.setDebugMode?.(enabled);
        renderAt(captureTime);
      },
      setPhaseADebugMode(enabled) {
        runtime.setDebugMode?.(enabled);
        renderAt(captureTime);
      },
      setPhaseADebugVisualization(mode) {
        runtime.setDebugVisualization?.(mode);
        renderAt(captureTime);
      },
      setPhaseAMonochromeMode(enabled) {
        runtime.setMonochromeMode?.(enabled);
        renderAt(captureTime);
      },
      setPhaseAPresentationMode(mode) {
        runtime.setPresentationMode?.(mode);
        renderAt(captureTime);
      },
      setPhaseAApertureDebugMode(enabled) {
        runtime.setApertureDebugMode?.(enabled);
        renderAt(captureTime);
      },
      setPhaseAOcclusionSoloMode(enabled) {
        runtime.setOcclusionSoloMode?.(enabled);
        renderAt(captureTime);
      },
      setPhaseAVisibleCrossingsDebugMode(enabled) {
        runtime.setVisibleCrossingsDebugMode?.(enabled);
        renderAt(captureTime);
      },
      getOrbitConfigs() {
        return runtime.getConfigs?.() ?? [];
      },
      getOrbitMetrics() {
        return runtime.metrics;
      },
      updateOrbitConfig(id, patch) {
        const result = runtime.updateConfig?.(id, patch) ?? [];
        renderAt(captureTime);
        return result;
      },
      resetOrbitConfigs() {
        const result = runtime.resetConfigs?.() ?? [];
        renderAt(captureTime);
        return result;
      },
      loadRecommendedOrbitPreset() {
        const result = runtime.loadRecommendedPreset?.() ?? [];
        renderAt(captureTime);
        return result;
      },
      exportOrbitConfigJSON() {
        return runtime.exportConfigJSON?.() ?? "[]";
      },
      importOrbitConfigJSON(value) {
        const result = runtime.importConfigJSON?.(value) ?? [];
        renderAt(captureTime);
        return result;
      },
      setEchoVisible(visible) {
        runtime.setEchoVisible?.(visible);
        renderAt(captureTime);
      },
      setThemeVisibleCount(count) {
        runtime.setThemeVisibleCount?.(count);
        renderAt(captureTime);
      },
      resume() {
        captureMode = false;
      },
    };

    renderAt(captureTime);
    animate();

    return () => {
      cancelAnimationFrame(animationFrame);
      cameraControls?.removeEventListener("change", renderOrbitView);
      cameraControls?.dispose();
      delete window.__PANTHEON_STUDIO__;
      runtime.dispose();
      blockoutMaterial.dispose();
      environment.dispose();
      pmrem.dispose();
      renderer.dispose();
      renderer.domElement.remove();
      document.documentElement.classList.remove(documentModeClass);
    };
  }, [embedded, prototypeOverride]);

  const StudioTag = embedded ? "section" : "main";
  return (
    <StudioTag
      className={`${styles.studio} ${embedded ? styles.embeddedStudio : ""} ${isPhaseAOrbit ? styles.phaseAStudio : ""}`}
      aria-label="Pantheon 程序化 3D 主視覺製作畫布"
    >
      <div ref={mountRef} className={styles.canvasMount} data-pantheon-orb-studio />
      {isPhaseAOrbit ? (
        <aside className={styles.phaseAPanel} aria-label="Phase A 軌道調整面板">
          <div className={styles.phaseAPanelHeader}>
            <p>Phase A · Five Orbits</p>
            <button
              type="button"
              onClick={() => {
                const json = callPhaseARuntime("exportOrbitConfigJSON");
                setPhaseAConfigJson(json);
              }}
            >
              Export Config JSON
            </button>
          </div>
          <div className={styles.phaseAViews} aria-label="固定視角">
            {Object.keys(PHASE_A_VIEWS).map((view) => (
              <button
                key={view}
                type="button"
                onClick={() => window.__PANTHEON_STUDIO__?.setView(view)}
              >
                {view}
              </button>
            ))}
          </div>
          <label className={styles.phaseAToggle}>
            <input
              type="checkbox"
              onChange={(event) =>
                callPhaseARuntime(
                  "setPhaseADebugMode",
                  event.target.checked,
                )
              }
            />
            Debug sphere／原點／控制點／tangent
          </label>
          <label className={styles.phaseAToggle}>
            <span>Presentation Mode</span>
            <select
              aria-label="Presentation Mode"
              defaultValue="final-occluded"
              onChange={(event) =>
                callPhaseARuntime(
                  "setPhaseAPresentationMode",
                  event.target.value,
                )
              }
            >
              <option value="final-occluded">Final Occluded</option>
              <option value="xray">X-ray Debug</option>
              <option value="monochrome-occluded">
                Monochrome Occluded
              </option>
              <option value="monochrome-xray">
                Monochrome X-ray
              </option>
            </select>
          </label>
          <div className={styles.phaseAToolbar}>
            <button
              type="button"
              onClick={() => callPhaseARuntime("resetOrbitConfigs")}
            >
              Reset
            </button>
            <button
              type="button"
              onClick={() =>
                callPhaseARuntime("loadRecommendedOrbitPreset")
              }
            >
              Load Recommended Preset
            </button>
          </div>
          <div className={styles.phaseATrackList}>
            {phaseAConfigs.map((config) => (
              <fieldset key={config.id} className={styles.phaseATrack}>
                <legend>{config.id} · {config.label}</legend>
                <label className={styles.phaseAToggle}>
                  <input
                    type="checkbox"
                    aria-label={`${config.id} visible`}
                    checked={config.visible}
                    onChange={(event) =>
                      callPhaseARuntime("updateOrbitConfig", config.id, {
                        visible: event.target.checked,
                      })
                    }
                  />
                  visible
                </label>
                <label>
                  <span>color</span>
                  <input
                    type="color"
                    aria-label={`${config.id} color`}
                    value={config.color}
                    onChange={(event) =>
                      callPhaseARuntime("updateOrbitConfig", config.id, {
                        color: event.target.value,
                      })
                    }
                  />
                </label>
                {PHASE_A_FIELDS.map(([field, label, step]) => (
                  <label key={field}>
                    <span>{label}</span>
                    <input
                      type="number"
                      aria-label={`${config.id} ${field}`}
                      step={step}
                      value={config[field]}
                      onChange={(event) =>
                        callPhaseARuntime("updateOrbitConfig", config.id, {
                          [field]: Number(event.target.value),
                        })
                      }
                    />
                  </label>
                ))}
              </fieldset>
            ))}
          </div>
          <label className={styles.phaseAJson}>
            <span>Config JSON</span>
            <textarea
              value={phaseAConfigJson}
              onChange={(event) => setPhaseAConfigJson(event.target.value)}
              rows={7}
            />
          </label>
          <button
            type="button"
            onClick={() => {
              try {
                callPhaseARuntime(
                  "importOrbitConfigJSON",
                  phaseAConfigJson,
                );
              } catch (error) {
                setPhaseAConfigError(String(error));
              }
            }}
          >
            Import Config JSON
          </button>
          {phaseAConfigError ? (
            <p className={styles.phaseAError}>{phaseAConfigError}</p>
          ) : null}
        </aside>
      ) : null}
      {embedded ? (
        <p className={styles.orbitHint}>拖曳旋轉 360° · 滾輪縮放</p>
      ) : null}
    </StudioTag>
  );
}
