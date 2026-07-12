from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from main import render_article_shell  # noqa: E402


WEB_DIR = Path("app/web")

PRERENDER_ROUTES = {
    "/articles/tarot/tarot-0001": "seo/articles/tarot/tarot-0001.html",
    "/articles/personality/personality-0001": "seo/articles/personality/personality-0001.html",
    "/articles/fortune/fortune-0001": "seo/articles/fortune/fortune-0001.html",
    "/articles/interpersonal/interpersonal-0001": "seo/articles/interpersonal/interpersonal-0001.html",
    "/articles/life-direction": "seo/articles/life-direction.html",
}


def prerender() -> list[Path]:
    written: list[Path] = []
    for route, target in PRERENDER_ROUTES.items():
        output_path = WEB_DIR / target
        output_path.parent.mkdir(parents=True, exist_ok=True)
        response = render_article_shell(route)
        output_path.write_text(response.body.decode("utf-8"), encoding="utf-8")
        written.append(output_path)
    return written


def main() -> None:
    for output_path in prerender():
        print(output_path)


if __name__ == "__main__":
    main()
