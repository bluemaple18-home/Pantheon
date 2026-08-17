from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MATERIAL_SOURCE = (
    ROOT / "src/materials/createPantheonMaterialPrototype.ts"
).read_text(encoding="utf-8")
EFFECTS_SOURCE = (
    ROOT / "src/data/pantheon-effects-config.ts"
).read_text(encoding="utf-8")
STUDIO_SOURCE = (
    ROOT / "src/studio/PantheonStarOrbitStudio.jsx"
).read_text(encoding="utf-8")
MOTION_SOURCE = (
    ROOT / "src/motion/pantheonBandMotion.ts"
).read_text(encoding="utf-8")
GEOMETRY_LOCK = (
    ROOT / "geometry/pantheon-orbits-v1.1.json"
).read_text(encoding="utf-8")


class ThemeRuneLanguageContract(unittest.TestCase):
    def test_geometry_signature_remains_locked(self):
        self.assertIn(
            "sha256:869d8d22fddea450b4921e20c4732622e54bc1b895b1875de50f94ba076c6008",
            GEOMETRY_LOCK,
        )

    def test_five_theme_languages_share_one_material_pipeline(self):
        for function_name in (
            "constellationGlyph",
            "tarotGlyph",
            "mbtiGlyph",
            "humanDesignGlyph",
            "ziweiGlyph",
        ):
            self.assertEqual(
                MATERIAL_SOURCE.count(f"float {function_name}("),
                1,
                function_name,
            )
        self.assertIn(
            "float bandThemeGlyph(vec2 point, float variant, float style)",
            MATERIAL_SOURCE,
        )
        self.assertIn("themeSpecificGlyphs: true", MATERIAL_SOURCE)

    def test_marks_are_raised_metal_not_white_stickers(self):
        self.assertIn(
            'system: "pantheon-theme-raised-metal-relief-v1"',
            EFFECTS_SOURCE,
        )
        self.assertIn(
            'reliefModel: "shallow-cast-raised-metal"',
            EFFECTS_SOURCE,
        )
        self.assertIn("roughnessTopDelta: -0.018", EFFECTS_SOURCE)
        self.assertIn("metalnessDelta: 0", EFFECTS_SOURCE)
        self.assertIn("cellCount: 30", EFFECTS_SOURCE)
        self.assertIn("minimumGlyphClusters: 26", EFFECTS_SOURCE)
        self.assertEqual(MATERIAL_SOURCE.count("float cellCount = 30.0;"), 2)
        self.assertNotIn(
            "float pantheonEngravingTint",
            MATERIAL_SOURCE,
        )
        self.assertIn(
            "vec3 pantheonBandMetalColor = diffuseColor.rgb;",
            MATERIAL_SOURCE,
        )

    def test_front_and_back_share_fixed_uv_marks(self):
        self.assertIn(
            'renderedSurfaces: ["top", "bottom"]',
            MATERIAL_SOURCE,
        )
        self.assertIn("samePatternOnBothSurfaces: true", MATERIAL_SOURCE)
        self.assertIn("fixedToBandUv: true", EFFECTS_SOURCE)
        self.assertIn("wholeTextureTranslation: false", MATERIAL_SOURCE)

    def test_energy_moves_over_fixed_glyphs_without_global_mark_emissive(self):
        self.assertIn(
            "binding.ribbonUniforms.markEmissive.value = 0;",
            MATERIAL_SOURCE,
        )
        self.assertIn(
            "float pantheonLitMark = pantheonMarkPattern * pantheonEnergy;",
            MATERIAL_SOURCE,
        )
        self.assertIn(
            "marksRemainFixedWhileLightMoves: true",
            MATERIAL_SOURCE,
        )
        self.assertIn("debug.flowIntensity *\n            1.05", MATERIAL_SOURCE)
        self.assertIn(
            "float fadeIn = 1.0 - smoothstep(\n    0.006,\n    0.028,",
            MATERIAL_SOURCE,
        )
        self.assertIn(
            "float fadeOut = 1.0 - smoothstep(\n    0.012,\n    0.055,",
            MATERIAL_SOURCE,
        )
        self.assertIn(
            "vec3 pantheonMetalFlowColor = mix(",
            MATERIAL_SOURCE,
        )
        self.assertIn(
            "reflectedLight.directSpecular +=",
            MATERIAL_SOURCE,
        )
        self.assertIn(
            "pantheonMetalFlowColor * pantheonMetalPulse * 0.82",
            MATERIAL_SOURCE,
        )
        self.assertIn(
            "pantheonMetalFlowColor * pantheonMetalPulse * 1.48",
            MATERIAL_SOURCE,
        )

    def test_bands_self_rotate_while_the_system_revolves_around_core(self):
        self.assertIn("PANTHEON_BAND_MOTION_LOOP_SECONDS = 60", MOTION_SOURCE)
        self.assertIn("resolvePantheonSystemMotion", STUDIO_SOURCE)
        self.assertIn("resolvePantheonBandSelfRotation", STUDIO_SOURCE)
        self.assertIn("orbitNodes.ribbonMeshes.get(theme.orbitId)", STUDIO_SOURCE)
        self.assertIn(".multiply(bandSpinQuaternion)", STUDIO_SOURCE)

    def test_rune_energy_cycles_close_on_the_sixty_second_loop(self):
        for cycle_seconds in (10, 12, 15, 20):
            self.assertEqual(60 % cycle_seconds, 0)
            self.assertIn(f"cycleSeconds: {cycle_seconds}", EFFECTS_SOURCE)
        self.assertIn(
            "reflectedLight.indirectSpecular +=",
            MATERIAL_SOURCE,
        )
        self.assertNotIn(
            "reflectedLight.directDiffuse +=\n  pantheonSurfaceLightColor",
            MATERIAL_SOURCE,
        )
        self.assertIsNone(
            re.search(
                r"binding\.ribbonUniforms\.markEmissive\.value\s*=\s*selected",
                MATERIAL_SOURCE,
            )
        )


if __name__ == "__main__":
    unittest.main()
