import * as THREE from "three";
import { RectAreaLightUniformsLib } from "three/examples/jsm/lights/RectAreaLightUniformsLib.js";
import { RectAreaLightHelper } from "three/examples/jsm/helpers/RectAreaLightHelper.js";

export type ProductLightingMode =
  | "environment-only"
  | "key-only"
  | "key-rim"
  | "full";

export type ProductLightingSettings = {
  enabled: boolean;
  mode: ProductLightingMode;
  keyStrength: number;
  keyWidth: number;
  keyHeight: number;
  rimStrength: number;
  topStrength: number;
  fillStrength: number;
  environmentStrength: number;
  exposure: number;
  debug: boolean;
};

export const PRODUCT_STUDIO_PRESET: Readonly<ProductLightingSettings> =
  Object.freeze({
    enabled: true,
    mode: "full",
    keyStrength: 1,
    keyWidth: 3.2,
    keyHeight: 2.4,
    rimStrength: 0.5,
    topStrength: 0.3,
    fillStrength: 0.08,
    environmentStrength: 0.48,
    exposure: 1.08,
    debug: false,
  });

export type PantheonProductLightingRig = {
  group: THREE.Group;
  keyLight: THREE.RectAreaLight;
  rimLight: THREE.RectAreaLight;
  topAccentLight: THREE.RectAreaLight;
  fillLight: THREE.RectAreaLight;
  ambientLight: THREE.AmbientLight;
  hemisphereLight: THREE.HemisphereLight;
  targets: THREE.Group;
  helpers: THREE.Group;
  settings: ProductLightingSettings;
  setSettings: (patch: Partial<ProductLightingSettings>) => void;
  snapshot: () => {
    settings: ProductLightingSettings;
    intensities: {
      key: number;
      rim: number;
      top: number;
      fill: number;
      ambient: number;
      hemisphere: number;
    };
    colors: {
      key: string;
      rim: string;
      top: string;
      fill: string;
    };
    positions: {
      key: number[];
      rim: number[];
      top: number[];
      fill: number[];
    };
  };
  dispose: () => void;
};

function disposeHelper(helper: THREE.Object3D) {
  const value = helper as THREE.Object3D & {
    geometry?: THREE.BufferGeometry;
    material?: THREE.Material | THREE.Material[];
    dispose?: () => void;
  };
  value.dispose?.();
  value.geometry?.dispose();
  if (Array.isArray(value.material)) {
    value.material.forEach((material) => material.dispose());
  } else {
    value.material?.dispose();
  }
}

export function createPantheonProductLightingRig(
  scene: THREE.Scene,
  options: {
    mobile?: boolean;
    initial?: Partial<ProductLightingSettings>;
    onEnvironmentStrengthChange?: (value: number) => void;
    onExposureChange?: (value: number) => void;
  } = {},
): PantheonProductLightingRig {
  RectAreaLightUniformsLib.init();

  const settings: ProductLightingSettings = {
    ...PRODUCT_STUDIO_PRESET,
    ...options.initial,
  };
  const recoveryBaseline = options.mobile
    ? {
        key: 7,
        rim: 1.9,
        top: 0.95,
        fill: 1.4,
        ambient: 0.14,
        hemisphere: 0.35,
      }
    : {
        key: 8,
        rim: 2.2,
        top: 1.1,
        fill: 1.6,
        ambient: 0.12,
        hemisphere: 0.32,
      };

  const group = new THREE.Group();
  group.name = "PantheonProductLightingRig";
  scene.add(group);

  const targets = new THREE.Group();
  targets.name = "PantheonProductLightingTargets";
  group.add(targets);

  const keyLight = new THREE.RectAreaLight("#fff0d8", 0, 3.2, 2.4);
  keyLight.name = "PantheonKeyLight";
  keyLight.position.set(-2.8, 3.4, 3.8);
  keyLight.lookAt(0, 0.1, 0);
  group.add(keyLight);

  const rimLight = new THREE.RectAreaLight("#bdd8ff", 0, 2.2, 3);
  rimLight.name = "PantheonRimLight";
  rimLight.position.set(3.4, 2.2, -3.2);
  rimLight.lookAt(0, 0, 0);
  group.add(rimLight);

  const topAccentLight = new THREE.RectAreaLight("#fff7e8", 0, 3.6, 3.6);
  topAccentLight.name = "PantheonTopAccentLight";
  topAccentLight.position.set(0.8, 4.2, 1.5);
  topAccentLight.lookAt(0, 0.15, 0);
  group.add(topAccentLight);

  const fillLight = new THREE.RectAreaLight("#dce7ff", 0, 2.5, 2.5);
  fillLight.name = "PantheonFillLight";
  fillLight.position.set(-2, -1.2, 2);
  fillLight.lookAt(0, 0, 0);
  group.add(fillLight);

  const ambientLight = new THREE.AmbientLight("#ffffff", 0);
  ambientLight.name = "PantheonAmbientSupport";
  group.add(ambientLight);

  const hemisphereLight = new THREE.HemisphereLight(
    "#d8e4e8",
    "#111820",
    0,
  );
  hemisphereLight.name = "PantheonHemisphereSupport";
  group.add(hemisphereLight);

  const helpers = new THREE.Group();
  helpers.name = "PantheonProductLightingHelpers";
  const keyHelper = new RectAreaLightHelper(keyLight);
  const rimHelper = new RectAreaLightHelper(rimLight);
  const fillHelper = new RectAreaLightHelper(fillLight);
  const topHelper = new RectAreaLightHelper(topAccentLight);
  helpers.add(keyHelper, rimHelper, fillHelper, topHelper);
  group.add(helpers);

  const apply = () => {
    const directEnabled = settings.enabled;
    const keyEnabled =
      directEnabled &&
      ["key-only", "key-rim", "full"].includes(settings.mode);
    const rimEnabled =
      directEnabled && ["key-rim", "full"].includes(settings.mode);
    const fullEnabled = directEnabled && settings.mode === "full";

    keyLight.intensity = keyEnabled
      ? recoveryBaseline.key * settings.keyStrength
      : 0;
    rimLight.intensity = rimEnabled
      ? recoveryBaseline.rim * (settings.rimStrength / 0.5)
      : 0;
    topAccentLight.intensity = fullEnabled
      ? recoveryBaseline.top * (settings.topStrength / 0.3)
      : 0;
    fillLight.intensity = fullEnabled
      ? recoveryBaseline.fill * (settings.fillStrength / 0.08)
      : 0;
    ambientLight.intensity = directEnabled
      ? recoveryBaseline.ambient
      : 0;
    hemisphereLight.intensity = directEnabled
      ? recoveryBaseline.hemisphere
      : 0;
    keyLight.width = settings.keyWidth;
    keyLight.height = settings.keyHeight;

    options.onEnvironmentStrengthChange?.(
      settings.environmentStrength,
    );
    options.onExposureChange?.(settings.exposure);

    helpers.visible = settings.debug;
  };

  const setSettings = (patch: Partial<ProductLightingSettings>) => {
    Object.assign(settings, patch);
    apply();
  };

  apply();

  return {
    group,
    keyLight,
    rimLight,
    topAccentLight,
    fillLight,
    ambientLight,
    hemisphereLight,
    targets,
    helpers,
    settings,
    setSettings,
    snapshot: () => ({
      settings: { ...settings },
      intensities: {
        key: keyLight.intensity,
        rim: rimLight.intensity,
        top: topAccentLight.intensity,
        fill: fillLight.intensity,
        ambient: ambientLight.intensity,
        hemisphere: hemisphereLight.intensity,
      },
      colors: {
        key: `#${keyLight.color.getHexString()}`,
        rim: `#${rimLight.color.getHexString()}`,
        top: `#${topAccentLight.color.getHexString()}`,
        fill: `#${fillLight.color.getHexString()}`,
      },
      positions: {
        key: keyLight.position.toArray(),
        rim: rimLight.position.toArray(),
        top: topAccentLight.position.toArray(),
        fill: fillLight.position.toArray(),
      },
    }),
    dispose: () => {
      [keyHelper, rimHelper, fillHelper, topHelper].forEach(disposeHelper);
      group.removeFromParent();
      group.clear();
    },
  };
}
