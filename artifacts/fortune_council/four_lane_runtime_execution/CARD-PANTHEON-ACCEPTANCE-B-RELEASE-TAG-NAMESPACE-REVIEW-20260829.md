# Pantheon Acceptance B：Release Tag Namespace 獨立複審卡

## Root question

唯一 bounded Repair 是否把正式 release version authority 收斂到同一個 shared、read-only、first-free SemVer namespace plan，並在任何 mutation 前 freeze；同時保留 commit 前 drift fail-closed、promotion tag-disabled、既有 Gen06 candidate／seal identity 與 production bytes？

## Review boundary

- RCA：`pantheon_acceptance_b_release_tag_namespace_rca_20260829/RESULT.md`
- Repair：`pantheon_acceptance_b_release_tag_namespace_repair_20260829/RESULT.md`
- Source allowlist：
  - `scripts/agy_content_publisher.py`
  - `scripts/pantheon_content_runtime_promotion.py`
  - `tests/test_agy_content_publisher.py`
  - `tests/test_pantheon_content_runtime_promotion.py`
- Reviewer 只可新增本卡、同名 review evidence 與 RESULT；不得修改 source/tests、commit、push、tag、publish、promotion 或 production state。

## P0/P1 acceptance

1. package／pyproject 一致性與 local／remote strict `vX.Y.Z` tags 共同形成 first-free plan。
2. create／rewrite／translation 共用同一 planner，且 ready selection 後、`journal.begin` 前 freeze。
3. exact collision 兩跑同 plan；provider、apply、prerender、feed、tests、commit、tag、push 與 journal begin 皆為零，protected bytes 不變。
4. commit/tag 前版本或 tag namespace drift fail closed，Git mutation 為零；既有 recovery seam 不被繞過。
5. promotion plan 明確 `git_tag_policy=DISABLED`，不輸出 release tag 欄位，不新增 registry／ledger／authority service。
6. Gen06 retry candidate、review、seal identity 與 production state bytes 保留；Gen07 不存在。
7. focused tests、affected publisher/promotion suites、`py_compile`、`git diff --check` 通過。

## Verdict contract

- 任一 P0/P1 或 production immutability 缺口：`NO_GO`。
- 所有 acceptance 有可重現證據且無阻塞 finding：`GO`。
