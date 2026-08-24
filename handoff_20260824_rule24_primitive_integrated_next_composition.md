# Pantheon Rule24 trust primitive 已整合 → Evidence Composition 換手

## Goal

收斂 `CONTENT-P0-01`：沿用既有 Rule24 capacity evaluator 與已整合的 DSSE/OpenSSL trust primitive，建立 signed evidence composition，之後刷新 production adoption/reset readiness，直到可產出 `READY-FOR-AUTHORIZATION`。

## Root Question

如何不整合舊 candidate、不新增套件、不重造 capacity workflow，把 Pantheon-owned Rule24 DSSE/OpenSSL primitive 接到既有 capacity evaluator，形成 verifier 可驗證、target-bound、fail-closed 的 signed evidence receipt？

## Constraints & Preferences

- 先查既有能力與 prior art；能合法沿用就沿用，禁止盲測重造。
- 不安裝、vendor 或複製第三方套件／crypto implementation；只用 Python stdlib 與機器既有 OpenSSL Ed25519。
- `6de8e4874d` 不整合；`0af881df2a` 不整合，也不得作下一張卡 baseline。
- 下一張卡只做 Rule24 signed evidence composition；禁止順手擴建 G8、改 production、執行 adoption/reset、canary、deploy、tag 或 push。
- 正式派工先建立實體 `.md` 卡並 commit，再建立側邊欄可見正式 thread 與獨立 worktree。
- 缺文獻或既有能力證據時立即提出，讓使用者另請 GPT 研究；不得自行猜測 crypto／supply-chain 契約。
- 原未追蹤檔屬使用者資產，禁止加入、修改或刪除。

## Completed Actions

- Rule24 DSSE/OpenSSL trust primitive 已完成獨立 Reviewer GO，無未解 P0/P1。
- 完整 candidate chain 已整合至 `main`：
  - `21abe88620` — initial primitive
  - `530497e5d3` — replay 與 keypair checks
  - `2b9bb0f116` — observer ordering
  - `11bf0aee99` — non-UTF-8 fail-closed
- 遠端兩個 patch-equivalent content commits 已用非破壞性 merge 收斂；merge tree 與 merge 前 tree 相同。
- `main` 已 push；本機 `main` 與 `origin/main` 均為 `91095924b1fe06955f525310b62cc0cfbf7948cd`。
- Pre-push release record gate：PASS。
- 主線 focused suite：`43 passed`；syntax compile、JSON parse、`git diff --check`、dependency/vendor/private-key audit：PASS。
- Production、deployment、tag：未碰。

## Active State

- Branch：`main`。
- Canonical Git authority：`origin/main@91095924b1fe06955f525310b62cc0cfbf7948cd`。
- Tracked tree：已同步；只有本換手檔待 commit。
- 使用者既有未追蹤檔仍存在且未碰，包含舊 G8／Publisher 卡、evidence directory 與 `handoff_20260817_*`、`handoff_20260820_*`。
- 可見 Implementer／Reviewer tasks 已交付，目前沒有執行中的正式 task。
- Backlog frontier：仍在 `CONTENT-P0-01`；`P0-02` 被 P0-01＋人工授權阻擋，`P0-03` 被 P0-02 阻擋，尚未進 P1。

## Evidence

- Implementation card：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0370-RULE24-DSSE-OPENSSL-ATTESTATION-20260824.md`
- Result：`artifacts/fortune_council/four_lane_runtime_execution/CARD-PANTHEON-G8-V0370-RULE24-DSSE-OPENSSL-ATTESTATION-20260824-RESULT.md`
- Validation receipt：`artifacts/fortune_council/four_lane_runtime_execution/g8_v0370_rule24_dsse_openssl_attestation_20260824/validation_receipt.json`
- Primitive：`scripts/pantheon_rule24_dsse_attestation.py`
- Tests：`tests/test_pantheon_rule24_dsse_attestation.py`
- Master backlog：`docs/content_expansion_backlog.md`

## In Progress / Remaining Work

1. 第一拍只讀：核對本 handoff、`AGENTS.md`、Rule24 primitive public interface、既有 capacity evaluator 與相關 tests。
2. 用 CodeGraph 做 task-semantic query；無命中／失敗才限域 `rg`。
3. 開一張 bounded `Rule24 signed evidence composition` 實體卡；鎖定輸入、輸出、authority、replay、target/policy/two-measurement binding、NO-GO zero-release 與 ownership。
4. Commit 卡片後建立側邊欄可見正式 Implementer thread；主線保留 review、整合與驗收。
5. Composition 驗收整合後，另開 bounded readiness refresh 卡，使用當下 `origin/main` authority 重產 preauthorization evidence。
6. 只有 `READY-FOR-AUTHORIZATION` 成立後，才向使用者請求一次 adoption/reset 授權。
7. Adoption/reset 成功後 fresh read-only reconciliation 必須 GO，才可請求 `CONTENT-P0-02` bounded publishing canary 授權。

## Current Blocker

Rule24 trust primitive 已解除；目前 blocker 是尚未有已驗收整合的 signed evidence composition。舊 readiness evidence 綁定過期 source SHA，不能因本次 push 自動升格為 current authority。

## Candidate Fork

- `FORK-A / current`：建立 composition 卡，沿用已整合 primitive＋既有 capacity evaluator。
- `FORK-B / gated`：composition GO 後刷新 readiness／authorization packet。
- `FORK-C / gated`：`READY-FOR-AUTHORIZATION` 後等待使用者明確授權 adoption/reset。
- `FORK-D / gated`：fresh reconciliation GO 後等待使用者明確授權單次 publishing canary。

## Waiting Conditions

- Composition 未驗收整合前：不得刷新成可執行 production authorization envelope。
- `READY-FOR-AUTHORIZATION` 未成立前：不得執行 production mutation。
- 使用者未明確授權 adoption/reset 或 canary：不得執行。
- P0-02 未成功：不得宣稱 G8 freeze，也不得進入 sustained 10K publishing。

## Known Residual Risk

- Replay claim create 後若 claim body write 失敗，可能留下 0-byte claim；此為既有 P2、fail-closed、非目前 blocker。下一張 composition 卡不得順手修它。

## Key Decisions & Resolved Questions

- Evidence receipt 採 in-toto Statement v1＋DSSE PAE；不以 SLSA Provenance 硬套 Rule24 schema，也不採 `JSON + SHA256` 自證。
- Authority 來自 verifier-owned trust policy 與 pinned public key，不信任 receipt 內自述 key identity。
- Protocol glue 為 Pantheon-owned minimal implementation；crypto primitive 只呼叫既有 OpenSSL，不抄第三方 crypto code。
- `6de8e4874d` 與 `0af881df2a` 均正式排除，不因其部分能力看似接近而整合。

## 下一手第一拍

`讀 handoff_20260824_rule24_primitive_integrated_next_composition.md，第一拍只讀盤點 Rule24 primitive 與既有 capacity evaluator，然後開 signed evidence composition 卡；不要整合 0af881df 或 6de8e487。`
