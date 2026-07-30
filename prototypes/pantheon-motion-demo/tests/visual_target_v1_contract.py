from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
STYLE_SOURCE = (
    ROOT / "src/data/pantheon-style-match-profiles.ts"
).read_text(encoding="utf-8")
MATERIAL_SOURCE = (
    ROOT / "src/materials/createPantheonMaterialPrototype.ts"
).read_text(encoding="utf-8")
BAND_SOURCE = (
    ROOT / "src/data/pantheon-material-config.ts"
).read_text(encoding="utf-8")
ORBIT_SOURCE = (
    ROOT / "src/generated/createPantheonStarOrbits.ts"
).read_text(encoding="utf-8")
GEOMETRY_SOURCE = (
    ROOT / "geometry/pantheon-orbits-v1.1.json"
).read_text(encoding="utf-8")


class VisualTargetV1Contract(unittest.TestCase):
    def test_geometry_centerlines_remain_locked(self):
        self.assertIn(
            "sha256:869d8d22fddea450b4921e20c4732622e54bc1b895b1875de50f94ba076c6008",
            GEOMETRY_SOURCE,
        )
        self.assertIn(
            "sha256:9f0f15499211c8a9625524adb743fc2e017f873ebaa5f74b697ec4d35088b222",
            ORBIT_SOURCE,
        )
        self.assertIn("centerlineSignature:", ORBIT_SOURCE)
        self.assertIn("poseSignature:", ORBIT_SOURCE)

    def test_visual_target_is_the_default_style(self):
        self.assertIn('"visual-target-v1": {', STYLE_SOURCE)
        self.assertIn(
            "export const DEFAULT_STYLE_MATCH_CANDIDATE",
            STYLE_SOURCE,
        )
        self.assertIn('\n  "visual-target-v1";', STYLE_SOURCE)

    def test_bands_use_reference_weight(self):
        self.assertIn("const DESKTOP_BAND_WIDTH = 0.22;", BAND_SOURCE)
        self.assertIn("const MOBILE_BAND_WIDTH = 0.2;", BAND_SOURCE)

    def test_reference_theme_palette_and_gold_relief_are_present(self):
        for color in (
            "#204a7a",
            "#702638",
            "#0f5a61",
            "#8d989d",
            "#70411f",
        ):
            self.assertIn(color, MATERIAL_SOURCE)
        self.assertIn(
            "vec3 pantheonReliefTopColor = mix(",
            MATERIAL_SOURCE,
        )
        self.assertIn("uMarkColor", MATERIAL_SOURCE)
        self.assertIn(
            "float pantheonReliefTopMix = pantheonMark * 0.54;",
            MATERIAL_SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
