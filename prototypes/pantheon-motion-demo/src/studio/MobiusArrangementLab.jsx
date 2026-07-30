import { useState } from "react";

import {
  PANTHEON_THEME_PARAMS,
  PANTHEON_THEMES,
} from "../generated/createPantheonThemeSpherePrototype.ts";
import PantheonOrbStudio from "./PantheonOrbStudio.jsx";
import styles from "./MobiusArrangementLab.module.css";

const VIEWS = [
  { id: "front", label: "正面" },
  { id: "orbit", label: "斜角" },
  { id: "side", label: "側面" },
];

const PARAMETER_ROWS = [
  ["主題數量", String(PANTHEON_THEME_PARAMS.themeCount)],
  ["主帶／伴生帶", "5 / 5"],
  ["暗球半徑", PANTHEON_THEME_PARAMS.innerSphereRadius.toFixed(2)],
  ["核心半徑", PANTHEON_THEME_PARAMS.coreRadius.toFixed(2)],
  ["星盤半徑", PANTHEON_THEME_PARAMS.astrolabeRadius.toFixed(2)],
  ["完整扭轉", "180°"],
];

function colorToHex(color) {
  return `#${color.toString(16).padStart(6, "0")}`;
}

export default function MobiusArrangementLab() {
  const [activeView, setActiveView] = useState("front");
  const [visibleCount, setVisibleCount] = useState(
    PANTHEON_THEME_PARAMS.themeCount,
  );
  const [coreVisible, setCoreVisible] = useState(true);
  const [echoVisible, setEchoVisible] = useState(true);
  const [debugMode, setDebugMode] = useState(false);

  const changeView = (view) => {
    setActiveView(view);
    window.__PANTHEON_STUDIO__?.setView?.(view);
  };

  const changeVisibleCount = (count) => {
    setVisibleCount(count);
    window.__PANTHEON_STUDIO__?.setThemeVisibleCount?.(count);
  };

  const changeCoreVisibility = (visible) => {
    setCoreVisible(visible);
    window.__PANTHEON_STUDIO__?.setCoreVisible?.(visible);
  };

  const changeEchoVisibility = (visible) => {
    setEchoVisible(visible);
    window.__PANTHEON_STUDIO__?.setEchoVisible?.(visible);
  };

  const changeDebugMode = (enabled) => {
    setDebugMode(enabled);
    window.__PANTHEON_STUDIO__?.setThemeSphereDebugMode?.(enabled);
  };

  return (
    <main className={styles.lab}>
      <section className={styles.viewport} aria-label="Pantheon 五主題球預覽">
        <div className={styles.viewportHeader}>
          <div>
            <p className={styles.eyebrow}>Pantheon art-directed study</p>
            <h1>五主題 Möbius 球</h1>
          </div>
          <span className={styles.liveStatus}>
            <i aria-hidden="true" />
            本機即時預覽
          </span>
        </div>
        <div className={styles.canvasFrame}>
          <PantheonOrbStudio
            embedded
            prototypeOverride="pantheon-theme-sphere"
          />
          <div className={styles.canvasLegend} aria-label="五個主題配色">
            {PANTHEON_THEMES.map((theme) => (
              <span key={theme.id}>
                <i style={{ background: colorToHex(theme.color) }} />
                {theme.label}
              </span>
            ))}
          </div>
        </div>
      </section>

      <aside className={styles.controls} aria-label="五主題球控制">
        <header className={styles.controlsHeader}>
          <p>視覺模型</p>
          <strong>五組真正 Möbius 系統</strong>
          <span>
            每個主題包含一條 180° 扭轉主帶與一條窄伴生帶；
            暗色內球負責整理後方遮擋。
          </span>
        </header>

        <section className={styles.controlSection}>
          <div className={styles.sectionHeading}>
            <div>
              <p>主題拆解</p>
              <h2>顯示主題數</h2>
            </div>
            <output className={styles.countOutput}>
              {visibleCount} / {PANTHEON_THEME_PARAMS.themeCount}
            </output>
          </div>
          <div className={styles.countControl}>
            {PANTHEON_THEMES.map((theme, index) => (
              <button
                aria-label={`顯示前 ${index + 1} 個主題`}
                aria-pressed={visibleCount === index + 1}
                key={theme.id}
                type="button"
                onClick={() => changeVisibleCount(index + 1)}
              >
                {index + 1}
              </button>
            ))}
          </div>
          <div className={styles.toggleStack}>
            <label className={styles.linkToggle}>
              <input
                type="checkbox"
                checked={echoVisible}
                onChange={(event) =>
                  changeEchoVisibility(event.target.checked)
                }
              />
              <span>顯示伴生帶</span>
            </label>
            <label className={styles.linkToggle}>
              <input
                type="checkbox"
                checked={coreVisible}
                onChange={(event) =>
                  changeCoreVisibility(event.target.checked)
                }
              />
              <span>顯示時間核心</span>
            </label>
            <label className={styles.linkToggle}>
              <input
                type="checkbox"
                checked={debugMode}
                onChange={(event) => changeDebugMode(event.target.checked)}
              />
              <span>顯示球面與中心線</span>
            </label>
          </div>
        </section>

        <section className={styles.controlSection}>
          <div className={styles.sectionHeading}>
            <div>
              <p>模型契約</p>
              <h2>幾何參數</h2>
            </div>
          </div>
          <dl className={styles.parameterGrid}>
            {PARAMETER_ROWS.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
          <ul className={styles.validationList}>
            <li>語意固定為五個主題，不增加第六主題</li>
            <li>每條主帶在封口處左右邊交換</li>
            <li>整體旋轉，單帶只做極小呼吸</li>
          </ul>
        </section>

        <section className={styles.controlSection}>
          <div className={styles.sectionHeading}>
            <div>
              <p>360° 檢查</p>
              <h2>相機視角</h2>
            </div>
          </div>
          <div className={styles.segmentedControl}>
            {VIEWS.map((view) => (
              <button
                aria-pressed={activeView === view.id}
                key={view.id}
                type="button"
                onClick={() => changeView(view.id)}
              >
                {view.label}
              </button>
            ))}
          </div>
        </section>

        <div className={styles.controlsFooter}>
          <button
            className={styles.resetButton}
            type="button"
            onClick={() => {
              changeVisibleCount(PANTHEON_THEME_PARAMS.themeCount);
              changeEchoVisibility(true);
              changeCoreVisibility(true);
              changeDebugMode(false);
              changeView("front");
            }}
          >
            重設美術預覽
          </button>
          <p>
            拖曳可檢查完整 360°；主帶與伴生帶都屬於同一主題，
            中央核心代表時間。
          </p>
        </div>
      </aside>
    </main>
  );
}
