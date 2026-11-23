import ast
import inspect
import json
from pathlib import Path
import re
import subprocess

import pytest

from scripts import prerender_article_shells as prerenderer
from scripts.prerender_article_shells import PRERENDER_ARTICLES, render_article_specific_shell


ROOT = Path(__file__).resolve().parents[1]


def payload_from_markup(markup: str) -> dict:
    match = re.search(
        r'<script type="application/json" id="article-content-payload">(.*?)</script>',
        markup,
        re.S,
    )
    assert match, "預渲染單篇缺少 payload，瀏覽器仍須下載全站文章模組"
    return json.loads(match.group(1))


def run_loader(path: str, payload: object, *, origin: str = "https://www.mysticpantheon.com", compare: bool = False, locale: str | None = None) -> dict:
    result = subprocess.run(
        ["node", "--experimental-vm-modules", "tests/fixtures/article_resource_fanout.mjs"],
        input=json.dumps({"path": path, "payload": payload, "origin": origin, "compare": compare, "locale": locale}),
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=90,
    )
    return json.loads(result.stdout)


def test_registry_builder_carries_content_in_one_pass() -> None:
    tree = ast.parse(inspect.getsource(prerenderer.registry_articles))
    script = next(node.value for node in ast.walk(tree)
                  if isinstance(node, ast.Constant) and isinstance(node.value, str)
                  and "const records = listArticleRecords().map" in node.value)
    result = subprocess.run(
        ["node", "--experimental-vm-modules", "tests/fixtures/article_resource_fanout.mjs"],
        input=json.dumps({"mode": "registry", "source": script}),
        cwd=ROOT, capture_output=True, text=True, check=True, timeout=15,
    )
    data = json.loads(result.stdout)
    assert data["buildCalls"] == len(data["records"]) == 2
    assert all("content" in record for record in data["records"]), "既有 builder 結果被丟棄"
    assert all(record["content"]["bodySections"] == record["bodySections"] for record in data["records"])


@pytest.mark.parametrize("serial", ["personality-0049", "tarot-0106"])
def test_render_payload_uses_carried_content_without_child_process(
    serial: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    article = next(item for item in PRERENDER_ARTICLES if item["serial"] == serial)
    assert "content" in article, "record 必須承接同一次 builder 的完整結果"
    before = json.dumps(article["content"], ensure_ascii=False, sort_keys=True)
    def forbidden(*_args, **_kwargs):
        pytest.fail("單頁 render 不得重新啟動 Node 或第二輪全站 builder")
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    payload = payload_from_markup(render_article_specific_shell(article))
    assert payload["content"]["bodySections"] == article["bodySections"]
    assert payload["content"]["navigationLinks"] == article["content"]["navigationLinks"]
    assert json.dumps(article["content"], ensure_ascii=False, sort_keys=True) == before


@pytest.mark.parametrize("locale", ["en", "ja", "ko"])
def test_localized_raw_shell_preserves_real_legacy_article_parity(locale: str) -> None:
    result = run_loader("/articles", None, compare=True, locale=locale)
    assert result["path"].startswith(f"/{locale}/articles/")
    assert result["actual"] == result["expected"]
    assert result["actual"]["locale"] == locale
    assert result["actual"]["contentType"] == "Article"
    assert result["actual"]["bodySections"]
    assert len(result["legacyImports"]) == 1
    assert result["actualSeo"] == result["expectedSeo"]


@pytest.mark.parametrize("serial", ["personality-0049", "tarot-0106"])
def test_prerendered_article_carries_route_bound_complete_content(serial: str) -> None:
    article = next(item for item in PRERENDER_ARTICLES if item["serial"] == serial)
    payload = payload_from_markup(render_article_specific_shell(article))
    assert payload["path"] == article["route"]
    assert payload["content"]["bodySections"] == article["bodySections"]
    assert payload["content"]["navigationLinks"]
    assert payload["content"]["displayTagLinks"]


@pytest.mark.parametrize("serial", ["personality-0049", "tarot-0106"])
@pytest.mark.parametrize("origin", ["https://www.mysticpantheon.com", "http://localhost:8765"])
def test_real_article_payload_matches_legacy_content_and_seo(serial: str, origin: str) -> None:
    article = next(item for item in PRERENDER_ARTICLES if item["serial"] == serial)
    payload = payload_from_markup(render_article_specific_shell(article))
    result = run_loader(article["route"], payload, origin=origin, compare=True)
    expected = result["expected"]
    for field in ("published", "updated"):
        if not article[field]:
            expected.pop(field, None)
    assert result["actual"] == expected
    assert result["legacyImports"] == []
    assert result["actual"]["canonicalUrl"] == origin + article["route"]
    assert result["actualSeo"] == result["expectedSeo"]


def test_payload_escapes_script_end_and_html_parser_escape_sequences() -> None:
    article = next(item for item in PRERENDER_ARTICLES if item["serial"] == "personality-0049").copy()
    attack = '</ScRiPt><script>alert("payload")</script><!--<script>\u2028&>'
    article["answer"] = attack
    markup = render_article_specific_shell(article)
    payload = payload_from_markup(markup)
    assert payload["content"]["answer"] == attack
    raw = re.search(r'id="article-content-payload">(.*?)</script>', markup, re.S).group(1)
    assert "<" not in raw
    assert run_loader(article["route"], payload)["actual"]["answer"] == attack


@pytest.mark.parametrize("invalid", ["{", "null", "{}", "[]", '{"path":"/articles/personality/personality-0049","content":null}'])
def test_bad_payload_never_downloads_legacy_modules(invalid: str) -> None:
    result = run_loader("/articles/personality/personality-0049", invalid)
    assert result == {"actual": None, "legacyImports": []}


@pytest.mark.parametrize("mismatch", ["envelope", "content", "route"])
def test_stale_route_payload_never_downloads_legacy_modules(mismatch: str) -> None:
    article = next(item for item in PRERENDER_ARTICLES if item["serial"] == "personality-0049")
    payload = payload_from_markup(render_article_specific_shell(article))
    path = article["route"]
    if mismatch == "envelope":
        payload["path"] = "/articles/tarot/tarot-0106"
    elif mismatch == "content":
        payload["content"]["canonicalPath"] = "/articles/tarot/tarot-0106"
    else:
        path = "/articles/tarot/tarot-0106"
    assert run_loader(path, payload) == {"actual": None, "legacyImports": []}


def test_trailing_slash_accepts_same_route_payload() -> None:
    article = next(item for item in PRERENDER_ARTICLES if item["serial"] == "personality-0049")
    payload = payload_from_markup(render_article_specific_shell(article))
    result = run_loader(article["route"] + "/", payload)
    assert result["actual"] == payload["content"]
    assert result["legacyImports"] == []


@pytest.mark.parametrize("path", [
    "/articles/personality/personality-0049",
    "/articles/astro",
    "/topics/personality",
    "/ja/articles/astrology/astrology-0181",
    "/articles/personality/relationships-stuck",
])
def test_absent_payload_uses_real_legacy_builder(path: str) -> None:
    result = run_loader(path, None, compare=True)
    assert result["actual"] == result["expected"]
    assert len(result["legacyImports"]) == 1
    assert "article-meta.js" in result["legacyImports"][0]


def test_missing_dates_are_not_restored_by_payload_or_hydration() -> None:
    article = next(item for item in PRERENDER_ARTICLES if not item["published"] and not item["updated"])
    markup = render_article_specific_shell(article)
    payload = payload_from_markup(markup)
    result = run_loader(article["route"], payload, compare=True)
    assert "published" not in result["actual"]
    assert "updated" not in result["actual"]
    assert "datePublished" not in result["actualSeo"]["article"]
    assert "dateModified" not in result["actualSeo"]["article"]
    assert "2026-07-10" not in markup
    assert "更新日期待真實資料補齊" in markup


def test_article_entry_static_graph_has_no_registry_body_or_locale_imports() -> None:
    visited = set()

    def visit(path: Path) -> None:
        if path in visited:
            return
        visited.add(path)
        source = path.read_text()
        for specifier in re.findall(r'\bimport\s+[^;]*?\s+from\s+["\']([^"\']+)', source):
            visit((path.parent / specifier.split("?")[0]).resolve())

    visit(ROOT / "app/web/static/article.js")
    assert {path.name for path in visited} == {"article.js", "article-content-loader.js", "article-seo.js"}


@pytest.fixture
def next_release_repo(tmp_path: Path) -> Path:
    import shutil

    # 只複製兩個既有 web 契約測試的文字輸入，不產生任何頁面。
    paths = [
        "app/web/article.html", "app/web/articles.html", "app/web/_redirects",
        "app/web/static/article.js", "app/web/static/article-content-loader.js",
        "app/web/static/article-meta.js", "app/web/static/article-seo.js",
        "app/web/static/article-registry.js", "app/web/static/articles.js",
        "app/web/static/pantheon-motion-visual.js", "app/web/static/styles.css",
        "tests/test_web.py", "tests/fixtures/article_resource_fanout.mjs",
    ]
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    (tmp_path / "package.json").write_text('{"type":"module"}\n')
    return tmp_path


def test_next_release_bump_reaches_legacy_import(next_release_repo: Path) -> None:
    from scripts import agy_seo_copy_pipeline as pipeline

    token = "agy-i18n-next-publication-probe"
    # 用小型模組隔離 module URL 契約；更新仍呼叫真正的既有 bump。
    (next_release_repo / "app/web/static/article-meta.js").write_text(
        'export function buildArticleContent(path) { return { releaseProbe: true, path }; }\n'
    )
    pipeline._bump_article_cache_queries(next_release_repo, token)
    result = subprocess.run(
        ["node", "--experimental-vm-modules", "tests/fixtures/article_resource_fanout.mjs"],
        input=json.dumps({"path": "/articles/astro", "payload": None, "origin": "https://preview.example"}),
        cwd=next_release_repo,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    actual = json.loads(result.stdout)
    assert actual["actual"] == {"releaseProbe": True, "path": "/articles/astro"}
    assert actual["legacyImports"] == [f"./article-meta.js?v={token}"]


def test_next_release_fixture_sync_keeps_real_web_entry_tests_green(
    next_release_repo: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import runpy
    import main
    from scripts import agy_content_publisher as publisher

    token = "agy-i18n-next-publication-probe"
    publisher._sync_web_test_cache_token(next_release_repo, cache_token=token)
    assert f'static/article.js?v={token}"' in (next_release_repo / "app/web/article.html").read_text()
    monkeypatch.setattr(main, "WEB_DIR", next_release_repo / "app/web")
    monkeypatch.chdir(next_release_repo)
    namespace = runpy.run_path(str(next_release_repo / "tests/test_web.py"))
    assert namespace["ARTICLE_CACHE_TOKEN"] == token
    namespace["test_article_urls_serve_article_template"]()
    namespace["test_article_breadcrumb_uses_product_and_slug_from_url"]()
