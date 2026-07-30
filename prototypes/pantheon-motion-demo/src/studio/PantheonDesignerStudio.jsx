import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import {
  createPantheonDesignerCurves,
  getPantheonDesignerRuntime,
  PANTHEON_DESIGNER_CURVES,
} from "../generated/createPantheonDesignerCurves.ts";
import {
  createPantheonDesignerComposition,
  getPantheonDesignerCompositionRuntime,
  PANTHEON_TRACK_CURVES_3D,
} from "../generated/createPantheonDesignerComposition.ts";
import styles from "./PantheonDesignerStudio.module.css";

const FRAME_SIZE = 720;
const COMPOSITION_VIEWS = {
  front: [0, 0, 4.6],
  back: [0, 0, -4.6],
  left: [-4.6, 0, 0],
  right: [4.6, 0, 0],
  top: [0, 4.6, 0.001],
  bottom: [0, -4.6, 0.001],
  "front-left": [-3.25, 0.55, 3.25],
  "front-right": [3.25, 0.55, 3.25],
};

export default function PantheonDesignerStudio() {
  const mountRef = useRef(null);
  const params = new URLSearchParams(window.location.search);
  const isComposition =
    params.get("prototype") === "pantheon-designer-composition";
  const [activeCurve, setActiveCurve] = useState(PANTHEON_DESIGNER_CURVES[0].id);
  const [debugMode, setDebugMode] = useState("line");
  const [monochrome, setMonochrome] = useState(false);
  const [compositionDebug, setCompositionDebug] = useState("none");
  const [soloTrack, setSoloTrack] = useState(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      preserveDrawingBuffer: true,
      alpha: false,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(FRAME_SIZE, FRAME_SIZE, false);
    renderer.setClearColor(0x07090c, 1);
    mount.append(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = isComposition
      ? new THREE.PerspectiveCamera(32, 1, 0.1, 100)
      : new THREE.OrthographicCamera(-1.2, 1.2, 1.2, -1.2, 0.1, 10);
    camera.position.set(0, 0, isComposition ? 4.6 : 4);
    camera.lookAt(0, 0, 0);

    const curves = isComposition
      ? createPantheonDesignerComposition()
      : createPantheonDesignerCurves();
    scene.add(curves);
    const runtime = isComposition
      ? getPantheonDesignerCompositionRuntime(curves)
      : getPantheonDesignerRuntime(curves);
    const controls = isComposition
      ? new OrbitControls(camera, renderer.domElement)
      : null;
    if (controls) {
      controls.enableDamping = true;
      controls.dampingFactor = 0.08;
      controls.enablePan = false;
      controls.minDistance = 3.1;
      controls.maxDistance = 7.5;
      controls.update();
    }

    if (isComposition) {
      const ambient = new THREE.HemisphereLight(0xe9edf4, 0x111820, 1.15);
      scene.add(ambient);
      const key = new THREE.DirectionalLight(0xffffff, 2.4);
      key.position.set(-3.8, 4.8, 5.2);
      scene.add(key);
      const rim = new THREE.DirectionalLight(0xaac7ff, 1.25);
      rim.position.set(3.4, 1.8, -4.5);
      scene.add(rim);
    }
    const render = () => renderer.render(scene, camera);
    controls?.addEventListener("change", render);

    window.__PANTHEON_DESIGNER__ = {
      renderer,
      scene,
      camera,
      curves,
      setSoloCurve(id) {
        if (isComposition) return false;
        const changed = runtime.setSoloCurve(id);
        render();
        return changed;
      },
      setDebugMode(mode) {
        if (isComposition) return;
        runtime.setDebugMode(mode);
        render();
      },
      setMonochrome(enabled) {
        if (!isComposition) return;
        runtime.setMonochrome(enabled);
        render();
      },
      setCompositionDebugMode(mode) {
        if (!isComposition) return;
        runtime.setDebugMode(mode);
        render();
      },
      setSoloTrack(id) {
        if (!isComposition) return false;
        const changed = runtime.setSoloTrack(id);
        render();
        return changed;
      },
      setView(view) {
        if (!isComposition) return;
        const position = COMPOSITION_VIEWS[view] || COMPOSITION_VIEWS.front;
        camera.position.set(...position);
        camera.lookAt(0, 0, 0);
        controls?.target.set(0, 0, 0);
        controls?.update();
        render();
      },
      getMetrics() {
        return runtime.metrics;
      },
      getConfigs() {
        return runtime.getConfigs();
      },
      exportJSON() {
        return runtime.exportJSON();
      },
      render,
    };

    render();
    return () => {
      delete window.__PANTHEON_DESIGNER__;
      controls?.removeEventListener("change", render);
      controls?.dispose();
      runtime.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [isComposition]);

  const selectCurve = (id) => {
    setActiveCurve(id);
    window.__PANTHEON_DESIGNER__?.setSoloCurve(id);
  };

  const selectDebugMode = (mode) => {
    setDebugMode(mode);
    window.__PANTHEON_DESIGNER__?.setDebugMode(mode);
  };

  const activeConfig = PANTHEON_DESIGNER_CURVES.find(
    (curve) => curve.id === activeCurve,
  );

  return (
    <main
      className={styles.studio}
      aria-label={
        isComposition
          ? "Pantheon Designer Curves Composition"
          : "Pantheon Designer Curves B0"
      }
    >
      <section className={styles.canvasColumn}>
        <div className={styles.canvasHeader}>
          <div>
            <p>
              {isComposition
                ? "Phase C3 · Geometry-first Track Sphere"
                : "Phase B0 · 2D Silhouette Design"}
            </p>
            <h1>{isComposition ? "五線整合預覽" : activeConfig?.label}</h1>
          </div>
          <span>
            {isComposition
              ? "5 explicit 3D tracks · 1 time core"
              : `${activeConfig?.controlPoints2D.length} control points`}
          </span>
        </div>
        <div ref={mountRef} className={styles.canvasMount} />
        <p className={styles.direction}>
          {isComposition
            ? "拖曳檢查 360° · 沒有 Inner Sphere、Aperture、Fade 或 Ribbon"
            : activeConfig?.primaryDirection}
        </p>
      </section>
      <aside className={styles.panel}>
        <div>
          <p className={styles.eyebrow}>Designer Mode</p>
          <h2>
            {isComposition ? "五條中心線整合" : "五條獨立品牌曲線"}
          </h2>
          <p className={styles.note}>
            {isComposition
              ? "幾何只負責球體、流動與交織；主題材質與動畫延後。"
              : "先驗證單條 2D 輪廓；不以球體構圖掩蓋單條造型問題。"}
          </p>
        </div>
        {isComposition ? (
          <>
            <div className={styles.viewGrid} aria-label="固定視角">
              {Object.keys(COMPOSITION_VIEWS).map((view) => (
                <button
                  key={view}
                  type="button"
                  onClick={() =>
                    window.__PANTHEON_DESIGNER__?.setView(view)
                  }
                >
                  {view}
                </button>
              ))}
            </div>
            <div className={styles.debugModes} aria-label="構圖 Debug">
              {[
                ["none", "Final"],
                ["reference-sphere", "Reference"],
                ["radius-heat", "Radius heat"],
                ["curvature", "Curvature"],
                ["control-points", "Control points"],
                ["density-grid", "Density"],
              ].map(([mode, label]) => (
                <button
                  key={mode}
                  type="button"
                  className={
                    compositionDebug === mode ? styles.active : ""
                  }
                  onClick={() => {
                    setCompositionDebug(mode);
                    window.__PANTHEON_DESIGNER__?.setCompositionDebugMode(
                      mode,
                    );
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className={styles.curveList} aria-label="單條顯示">
              <button
                type="button"
                className={soloTrack === null ? styles.active : ""}
                onClick={() => {
                  setSoloTrack(null);
                  window.__PANTHEON_DESIGNER__?.setSoloTrack(null);
                }}
              >
                <span>ALL</span>
                五條合成
              </button>
              {PANTHEON_TRACK_CURVES_3D.map((curve, index) => (
                <button
                  key={curve.id}
                  type="button"
                  className={soloTrack === curve.id ? styles.active : ""}
                  onClick={() => {
                    setSoloTrack(curve.id);
                    window.__PANTHEON_DESIGNER__?.setSoloTrack(curve.id);
                  }}
                >
                  <span>0{index + 1}</span>
                  {curve.label}
                </button>
              ))}
            </div>
            <label className={styles.toggle}>
              <input
                type="checkbox"
                checked={monochrome}
                onChange={(event) => {
                  setMonochrome(event.target.checked);
                  window.__PANTHEON_DESIGNER__?.setMonochrome(
                    event.target.checked,
                  );
                }}
              />
              Monochrome All
            </label>
            <a
              className={styles.modeLink}
              href="?prototype=pantheon-designer-b0"
            >
              回到單條 Designer 檢查
            </a>
          </>
        ) : (
          <>
            <div className={styles.curveList} aria-label="曲線選擇">
              {PANTHEON_DESIGNER_CURVES.map((curve, index) => (
                <button
                  key={curve.id}
                  type="button"
                  className={activeCurve === curve.id ? styles.active : ""}
                  onClick={() => selectCurve(curve.id)}
                >
                  <span>0{index + 1}</span>
                  {curve.label}
                </button>
              ))}
            </div>
            <div className={styles.debugModes} aria-label="Debug 模式">
              {[
                ["line", "White line"],
                ["control-points", "Control points"],
                ["curvature", "Curvature heat"],
              ].map(([mode, label]) => (
                <button
                  key={mode}
                  type="button"
                  className={debugMode === mode ? styles.active : ""}
                  onClick={() => selectDebugMode(mode)}
                >
                  {label}
                </button>
              ))}
            </div>
            <button
              type="button"
              className={styles.modeLink}
              onClick={() => {
                window.location.href =
                  "?prototype=pantheon-designer-composition";
              }}
            >
              查看五線整合預覽
            </button>
          </>
        )}
        <button
          type="button"
          className={styles.exportButton}
          onClick={() => {
            const data = window.__PANTHEON_DESIGNER__?.exportJSON();
            if (!data) return;
            const blob = new Blob([data], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = "pantheon-designer-curves.json";
            anchor.click();
            URL.revokeObjectURL(url);
          }}
        >
          Export JSON
        </button>
        <dl className={styles.contract}>
          <div><dt>Geometry</dt><dd>Closed centripetal Catmull-Rom</dd></div>
          <div><dt>Depth</dt><dd>{isComposition ? "Explicit controlPoints3D" : "B0 flat · z = 0"}</dd></div>
          <div><dt>Formal meshes</dt><dd>{isComposition ? "5 tracks + time core" : "5 solo curves only"}</dd></div>
          <div><dt>Excluded</dt><dd>Inner Sphere · Aperture · Fade · Ribbon</dd></div>
        </dl>
      </aside>
    </main>
  );
}
