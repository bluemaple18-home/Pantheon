from pathlib import Path


def test_product_gradients_have_distinct_palettes_and_motion_fallback() -> None:
    styles = Path("app/web/static/styles.css").read_text()

    for theme in ("fortune", "personality", "tarot", "astro"):
        assert f'.article-screen[data-product-theme="{theme}"]' in styles

    assert "@keyframes articleHeroGradientDrift" in styles
    assert "@keyframes articleProductGradientDrift" in styles
    assert "@keyframes productHubGradientDrift" in styles
    assert ".article-page-header::before," in styles
    assert ".article-theme-visual i," in styles
    assert ".content-hub-grid a::after" in styles
    assert "animation: none;" in styles
