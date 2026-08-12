---
id: CARD-CONTENT-WRITER-VNEXT-INTEGRATION-003
card_id: CARD-CONTENT-WRITER-VNEXT-INTEGRATION-003
status: ready
type: implementation
chain: PANTHEON-WRITER-VNEXT-ORCHESTRATION
role: implementation
cycle: 3
strictness: strict
model: gpt-5.5
reasoning: high
source_commit: e6d93fba050eac7c22e1a34bf52d8ac4c707a1b3
supersedes: CARD-CONTENT-WRITER-VNEXT-INTEGRATION-002
traces_to:
  - WVO-SLICE-001
  - WVO-ARCH-006
  - WVO-INV-012
---

# Writer vNext Integration 003：恢復正式派工並執行純新增 Overlay

## 目的

在完整 Runtime reviewed candidate `e6d93fba050eac7c22e1a34bf52d8ac4c707a1b3` 上，疊加 Writer vNext 的 37 個純新增檔並產出 integration candidate。完整 composition、allowlist、驗證與交付契約以同一 source commit 內的 `CARD-CONTENT-WRITER-VNEXT-INTEGRATION-002.md` 為準；本卡只取代其失敗的 control-plane dispatch identity，不改任何實作範圍或驗收標準。

Integration-002 曾在 create endpoint 回 `Unknown projectId`，未建立 formal thread、未建立 worktree、未執行實作。使用者已於平台投影恢復後明確要求依新流程重新開卡派工，因此本卡是新的正式執行入口；不得重送舊 reservation。

## 固定輸入

- Runtime base：`e6d93fba050eac7c22e1a34bf52d8ac4c707a1b3`
- Writer overlay base：`e4df0fc4349568cb0a7df2de56a4865885361494`
- Writer overlay tip：`c7ad4881eabc47cbf43e5053f1ac79d7e70af546`
- Overlay identity：`git diff --name-status <overlay-base> <overlay-tip>` 必須正好 37 列且全部為 `A`
- Runtime final review：`38774ddf1bccc77a0b40917322bb100d238469d7`，verdict 必須為 `REVIEW_GO`

## 唯一工作

1. 完整讀取本卡與 Integration-002 卡。
2. 先做 CodeGraph 任務語意查詢，再由固定 Git objects 驗證。
3. 只把 37 個 overlay 路徑 materialize 為 `c7ad4881...` exact blobs。
4. `scripts/agy_content_publisher.py` 與全部既有 Runtime paths 必須保持 source parent bytes；禁止任何 Publisher 解衝突或 stale Writer tree merge。
5. 跑 Integration-002 所列全部驗證，寫入 `artifacts/fortune_council/content_writer_vnext_execution/evidence/writer_vnext_integration_003/**`。
6. 全部通過才建立單一 candidate commit；parent 必須是本卡 source commit，worktree clean。

## 禁止範圍

- 不讀取或搬運 Integration-001 的 dirty staged state。
- 不修改 37 overlay 與 integration-003 evidence 以外的路徑。
- 不 merge 主線、不 push、不 deploy、不 publish、不 canary、不 tag、不啟停服務、不寫 production state。
- 不自行 Review、不另開 task、不宣稱 production ready。

## Evidence 與交付

至少包含：

- `overlay-manifest.json`
- `composition-receipt.md`
- `verification-receipt.md`
- `changed-files.json`

回報 candidate SHA、parent SHA、37/37 blob equality、Publisher/source equality、changed files、測試數量與結果、clean state，以及唯一 verdict `CANDIDATE_READY_FOR_REVIEW` 或 `BLOCKED`。
