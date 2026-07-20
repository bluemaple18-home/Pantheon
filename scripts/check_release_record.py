#!/usr/bin/env python3
"""驗證版本、文章發布記錄與 annotated tag 契約。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib


REPO_ROOT = Path(__file__).resolve().parents[1]
ZERO_SHA = "0" * 40
RELEASE_HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$", re.MULTILINE)
ARTICLE_SOURCE_PATTERNS = (
    re.compile(r"^app/web/static/article-(?:bodies|card-face|expansion|meta|registry|rewrite)[^/]*\.js$"),
    re.compile(r"^app/web/seo/articles/.+/index\.html$"),
)


class ReleaseContractError(ValueError):
    """發布契約不完整。"""


def run_git(*args: str, input_text: str | None = None) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        input=input_text,
    ).stdout.strip()


def file_at(ref: str | None, path: str) -> bytes:
    if ref:
        return subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
        ).stdout
    return (REPO_ROOT / path).read_bytes()


def versions_at(ref: str | None = None) -> tuple[str, str]:
    python_version = str(tomllib.loads(file_at(ref, "pyproject.toml").decode())["project"]["version"])
    node_version = str(json.loads(file_at(ref, "package.json"))["version"])
    return python_version, node_version


def semantic_version(value: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise ReleaseContractError(f"版本不是 SemVer：{value}")
    return tuple(int(part) for part in value.split("."))  # type: ignore[return-value]


def release_section(changelog: str, version: str) -> str:
    matches = list(RELEASE_HEADING.finditer(changelog))
    if not matches or matches[0].group(1) != version:
        raise ReleaseContractError(f"CHANGELOG 最新版本必須是 {version}")
    start = matches[0].start()
    end = matches[1].start() if len(matches) > 1 else len(changelog)
    section = changelog[start:end]
    required = (
        f"Release tag：`v{version}`",
        "公開文章總數：",
        "發布範圍：",
        "驗證：",
        "證據：",
    )
    missing = [item for item in required if item not in section]
    if missing:
        raise ReleaseContractError(f"CHANGELOG {version} 缺少欄位：{', '.join(missing)}")
    return section


def is_article_release_path(path: str) -> bool:
    return any(pattern.fullmatch(path) for pattern in ARTICLE_SOURCE_PATTERNS)


def changed_files(base_ref: str, target_ref: str) -> list[str]:
    if base_ref == ZERO_SHA:
        output = run_git("ls-tree", "-r", "--name-only", target_ref)
    else:
        output = run_git("diff", "--name-only", f"{base_ref}..{target_ref}")
    return [line for line in output.splitlines() if line]


def validate_tag(version: str, target_ref: str) -> None:
    tag = f"v{version}"
    try:
        tag_type = run_git("cat-file", "-t", f"refs/tags/{tag}")
        tagged_commit = run_git("rev-list", "-n", "1", tag)
        target_commit = run_git("rev-parse", f"{target_ref}^{{commit}}")
    except subprocess.CalledProcessError as exc:
        raise ReleaseContractError(f"缺少 annotated tag：{tag}") from exc
    if tag_type != "tag":
        raise ReleaseContractError(f"{tag} 必須是 annotated tag")
    if tagged_commit != target_commit:
        raise ReleaseContractError(f"{tag} 未指向 release commit {target_commit}")


def validate_release(base_ref: str | None, target_ref: str, require_tag: bool) -> tuple[str, bool]:
    python_version, node_version = versions_at(target_ref)
    if python_version != node_version:
        raise ReleaseContractError(f"版本未對齊：pyproject={python_version}, package={node_version}")
    semantic_version(python_version)
    changelog = file_at(target_ref, "CHANGELOG.md").decode()
    release_section(changelog, python_version)

    article_release = False
    if base_ref:
        article_release = any(is_article_release_path(path) for path in changed_files(base_ref, target_ref))
        if article_release:
            base_versions = versions_at(base_ref)
            if base_versions[0] != base_versions[1]:
                raise ReleaseContractError("遠端基準版本原本就未對齊")
            if semantic_version(python_version) <= semantic_version(base_versions[0]):
                raise ReleaseContractError("文章發布必須提升版本號")
    if require_tag or article_release:
        validate_tag(python_version, target_ref)
    return python_version, article_release


def validate_pre_push(lines: list[str]) -> None:
    updates = [line.split() for line in lines if line.strip()]
    main_updates = [item for item in updates if len(item) == 4 and item[0] == "refs/heads/main" and item[1] != ZERO_SHA]
    for _, local_sha, _, remote_sha in main_updates:
        version, article_release = validate_release(remote_sha, local_sha, require_tag=False)
        if article_release and not any(item[0] == f"refs/tags/v{version}" for item in updates):
            raise ReleaseContractError(f"文章發布必須在同一次 push 帶上 refs/tags/v{version}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref")
    parser.add_argument("--target-ref", default="HEAD")
    parser.add_argument("--require-head-tag", action="store_true")
    parser.add_argument("--pre-push", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.pre_push:
            validate_pre_push(sys.stdin.read().splitlines())
            print("release record pre-push gate: PASS")
            return 0
        version, article_release = validate_release(args.base_ref, args.target_ref, args.require_head_tag)
        print(json.dumps({"version": version, "article_release": article_release, "status": "PASS"}, ensure_ascii=False))
        return 0
    except (ReleaseContractError, FileNotFoundError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"release record gate: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
