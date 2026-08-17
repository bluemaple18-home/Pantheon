import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIGHTING_SOURCE = (
    ROOT / "src/lighting/createPantheonProductLightingRig.ts"
).read_text()
STUDIO_SOURCE = (
    ROOT / "src/studio/PantheonStarOrbitStudio.jsx"
).read_text()
MATERIAL_SOURCE = (
    ROOT / "src/data/pantheon-material-config.ts"
).read_text()
MATERIAL_RUNTIME_SOURCE = (
    ROOT / "src/materials/createPantheonMaterialPrototype.ts"
).read_text()


class ProductLightingAcceptance(unittest.TestCase):
    def test_geometry_signature_remains_locked(self):
        geometry = json.loads(
            (ROOT / "geometry/pantheon-orbits-v1.1.json").read_text()
        )
        self.assertEqual(
            geometry["centerlineSignature"],
            "sha256:869d8d22fddea450b4921e20c4732622e54bc1b895b1875de50f94ba076c6008",
        )

    def test_product_lighting_rig_is_centralized(self):
        for token in (
            'group.name = "PantheonProductLightingRig"',
            'keyLight.position.set(-2.8, 3.4, 3.8)',
            'rimLight.position.set(3.4, 2.2, -3.2)',
            'topAccentLight.position.set(0.8, 4.2, 1.5)',
            'fillLight.position.set(-2, -1.2, 2)',
            "RectAreaLightUniformsLib.init()",
        ):
            self.assertIn(token, LIGHTING_SOURCE)
        self.assertEqual(
            STUDIO_SOURCE.count("createPantheonProductLightingRig("),
            1,
        )

    def test_renderer_recovers_style_match_defaults(self):
        self.assertIn(
            "renderer.outputColorSpace = THREE.SRGBColorSpace",
            STUDIO_SOURCE,
        )
        self.assertIn(
            "renderer.toneMapping = THREE.AgXToneMapping",
            STUDIO_SOURCE,
        )
        self.assertIn("environmentStrength: 0.48", LIGHTING_SOURCE)
        self.assertIn("exposure: 1.08", LIGHTING_SOURCE)

    def test_materials_recover_style_match_baseline(self):
        for value in (
            "metalness: 0.91",
            "metalness: 0.89",
            "metalness: 0.92",
            "roughness: 0.56",
            "roughness: 0.54",
            "roughness: 0.58",
            "roughness: 0.55",
            "clearcoat: 0",
        ):
            self.assertIn(value, MATERIAL_SOURCE)
        for value in (
            "topBottom: 1.288",
            "bevel: 1.365",
            "edge: 1.133",
            "DEFAULT_METAL_HIGHLIGHT_STRENGTH = 1",
        ):
            self.assertIn(value, MATERIAL_RUNTIME_SOURCE)

    def test_recovery_light_intensities_are_low_and_directional(self):
        for value in (
            "key: 8",
            "rim: 2.2",
            "top: 1.1",
            "fill: 1.6",
            "ambient: 0.12",
            "hemisphere: 0.32",
            "key: 7",
            "rim: 1.9",
            "top: 0.95",
            "fill: 1.4",
            "ambient: 0.14",
            "hemisphere: 0.35",
        ):
            self.assertIn(value, LIGHTING_SOURCE)

    def test_top_accent_is_a_wide_soft_area_light(self):
        self.assertIn(
            'new THREE.RectAreaLight("#fff7e8", 0, 3.6, 3.6)',
            LIGHTING_SOURCE,
        )
        self.assertNotIn("new THREE.SpotLight(", LIGHTING_SOURCE)

    def test_runtime_initial_values_are_asserted(self):
        self.assertIn(
            "Pantheon Lighting Recovery runtime assertion",
            STUDIO_SOURCE,
        )
        self.assertIn(
            "get frameIndex()",
            STUDIO_SOURCE,
        )

    def test_four_acceptance_modes_exist(self):
        for mode in (
            '"environment-only"',
            '"key-only"',
            '"key-rim"',
            '"full"',
        ):
            self.assertIn(mode, LIGHTING_SOURCE)


if __name__ == "__main__":
    unittest.main()
