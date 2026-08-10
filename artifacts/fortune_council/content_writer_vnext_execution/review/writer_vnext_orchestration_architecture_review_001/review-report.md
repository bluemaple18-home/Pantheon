# Writer vNext Orchestration Architecture Review 001

## Verdict

`REVIEW_GO`

候選：`4cd768e353e6e349d15f57c5366a3275f7eefb8c`

本審查未發現可重現 P0/P1。候選維持在架構與 evidence allowlist 內，沒有修改 `scripts/**`、`tests/**`、`app/**`、設定、production artifact 或既有卡片；也沒有新增第二套 queue、approval、publication、deployment 或 retry authority。

## Findings

### WVO-REVIEW-001｜P2｜Composition gate 應 pin 到 final REVIEW_GO evidence path

Blocking: false

Affected: `WVO-ARCH-006`, `WVO-SLICE-001`, `WVO-INV-012`

候選文件在 `docs/pantheon_writer_vnext_orchestration_architecture.md:200` 到 `216` 定義 reviewed-commit composition gate，要求 Writer contract 與 Runtime Authority review evidence 皆為 `REVIEW_GO`。這個方向正確，但目前只 pin review commit SHA；實際 Git 物件中，Writer review commit `038cf4d2979bf2a1a8ceaf4d44964c3fde5816c6` 同時包含早期 `writer_vnext_contract_review_001` 的 `REVIEW_NO_GO` 與後續 `writer_vnext_contract_review_002` 的 `REVIEW_GO`，Runtime Authority review commit `38774ddf1bccc77a0b40917322bb100d238469d7` 也同時包含 `runtime_authority_activation_review_001/002` 的 `REVIEW_NO_GO` 與 `runtime_authority_activation_review_003` 的 `REVIEW_GO`。

這不阻斷本架構，因為候選已要求 integration card 檢查 `Review evidence has REVIEW_GO`，且把 composition 放在 `WVO-SLICE-001`。但後續 slice 的 preflight 應明確 pin final review evidence path 或 generation，避免自動化只依 commit 文字搜尋時誤讀舊 NO_GO artifact。

Recommended disposition: 在 `WVO-SLICE-001` integration card 的 input contract 補上 final review evidence path，例如 Writer 使用 `review/writer_vnext_contract_review_002/findings.json`，Runtime Authority 使用 `review/runtime_authority_activation_review_003/findings.json`，並要求 verdict 唯一選自該 final artifact。

## Source Confirmation

CodeGraph 任務語意查詢已執行，但本 thread 實際回傳的是無關的 AGY broker / SEO pipeline symbols，未定位到本卡要求的 outbox、coordinator、Publisher、Runtime Authority seam。因此本審查把 CodeGraph 狀態記為 `CONTEXT_DEGRADED / semantic mismatch`，並改用限域 `rg`、`nl`、`git show` 直接查原始碼。

原始碼確認結果：

- Outbox request envelope 只允許 `writer` / `reviewer`，並以 canonical request bytes 產生 `request_sha256` 與 `job_id`：`scripts/agy_gemini_outbox.py:154`、`scripts/agy_gemini_outbox.py:183`。
- Outbox collision、response/failure binding 與 bounded retry 存在：`scripts/agy_gemini_outbox.py:230`、`scripts/agy_gemini_outbox.py:356`、`scripts/agy_gemini_outbox.py:397`。
- Coordinator 是 active state / tick owner，持有 coordinator lock，並將 pending/failed/complete 寫回 run state：`scripts/agy_gemini_coordinator.py:64`、`scripts/agy_gemini_coordinator.py:100`、`scripts/agy_gemini_coordinator.py:538`。
- Publisher collect-ready 只接受 complete state、candidate/review validation、clean approval 與 deterministic quality pass；publication transaction / commit / tag / push 仍由 Publisher 擁有：`scripts/agy_content_publisher.py:744`、`scripts/agy_content_publisher.py:809`、`scripts/agy_content_publisher.py:1557`.
- Writer vNext contract validator已有 `ArticleBriefV2`、selected stages、artifact SHA、final candidate SHA 與 legacy candidate compatibility gates：`scripts/agy_editorial_contracts.py:50`、`scripts/agy_editorial_contracts.py:68`、`scripts/agy_editorial_contracts.py:130`。
- Runtime Authority candidate 的 Publisher preflight 要求 runtime identity digest、sandbox authority、bounded select/publish/transaction/tag/push dry-run，並阻止 production mutation：`e6d93fba050eac7c22e1a34bf52d8ac4c707a1b3:scripts/agy_content_publisher.py:116`、`:203`、`:240`、`:327`、`:403`。

## Requirement Coverage

- `WVO-ARCH-001..006`：完整存在，分別回答 transport mapping、artifact ledger / reconstruction、dedupe / tamper、Publisher adapter、legacy opt-in / rollback identity、reviewed-commit composition gate。
- `WVO-INV-001..012`：完整存在，皆 trace 到 stable decisions，且可轉成後續 public behavior tests。
- `WVO-SLICE-001..008`：完整存在，唯一 frontier 為 `WVO-SLICE-001`；blocking edges 無 dangling reference。
- 反證風險：未發現第二控制面、固定 editorial template、free state source of truth、重送/collision fail-open、manifest publication authority、rollback in-place rewrite 或 publication bypass。

## Residual Risk

本候選是架構卡，不修改 executable behavior；Publisher optional sidecar revalidation、vNext coordinator tick、runtime digest checks 都仍在後續 slices。這些不是本卡阻斷，但後續 implementation 必須以 public-behavior RED/GREEN 驗證。
