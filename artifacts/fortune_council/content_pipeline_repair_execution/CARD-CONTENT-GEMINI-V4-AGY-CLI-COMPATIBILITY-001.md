---
card_id: CARD-CONTENT-GEMINI-V4-AGY-CLI-COMPATIBILITY-001
chain_id: CONTENT-GEMINI-V4-AGY-CLI-COMPATIBILITY-001
status: CARD_DRAFTED
role: compatibility_implementation
thickness: strict
risk: high
model: gpt-5.6-sol
reasoning: high
base_sha: 52fc176
allowlist:
  - docs/pantheon_gemini_v4_agy_cli_compatibility.md
  - scripts/agy_gemini_v4_broker.py
  - tests/test_agy_gemini_v4_broker.py
  - tests/test_agy_gemini_outbox.py
  - artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_agy_cli_compatibility_001/**
forbidden_scope:
  - scripts/agy_seo_copy_pipeline.py
  - scripts/agy_gemini_runner.py
  - app/**, articles, registry, metadata and publishing files
  - dependency, real Gemini invocation, retry or fallback
  - merge, push, deploy, publish or content-line recovery
evidence_path: artifacts/fortune_council/content_pipeline_repair_execution/evidence/gemini_v4_agy_cli_compatibility_001/
thread_id: PENDING
thread_status: CARD_DRAFTED
worktree_path: PENDING
cwd: PENDING
---

# Gemini V4｜Antigravity CLI Compatibility

## 已重現根因

- 本機既有 CLI：`~/.antigravity/bin/agy`，local `--version`回 `1.1.5`；既有 pipeline有成功 `_cli_transport` evidence。
- V4 broker目前固定 `Popen([executable], stdin=raw_request, env={})`。
- local parser dry-run `agy --print` 回 exit 2與 `flag needs an argument: -print`；代表非互動模式必須使用 `--print <prompt>`，不能直接靠 stdin。
- 因此目前真 canary只會進錯誤模式／timeout；禁止用一次真模型失敗來驗證已知介面不相容。

## 唯一目標

新增一個 closed `antigravity_cli_v1` target profile，使 broker仍只啟動一個外部 target process，但用本地固定規則建構：

```text
agy
--model <allowlisted label>
--mode plan
--sandbox
--log-file <operation-local temp path>
--print-timeout <bounded seconds>
--print <PUBLIC_SANITIZED prompt>
```

模型映射固定：

- `gemini-3.5-flash` → `Gemini 3.5 Flash (Low)`
- `gemini-3.1-pro-preview` → `Gemini 3.1 Pro (Low)`

## 契約調整

- 新 compatibility 文件明確 supersede V4架構的「target argv僅 executable／raw prompt永不進argv」一項；其他 broker、ledger、FD、replay、anchor與單次process契約不變。
- `agy --print` 的產品限制使 public prompt必須短暫存在本機process argv；只允許已經 `validate_external_request` 驗證的 `PUBLIC_SANITIZED` outbox payload。不得用此 profile處理私密 prompt。
- raw prompt不得進ledger、anchor、control frame、evidence或log摘要；測試/evidence只保存 SHA、bytes與synthetic marker。
- broker target environment為closed allowlist，只提供 CLI auth/config必要的本機環境；不得繼承 API keys、tokens或整份 parent env。需要的 key與來源必須在文件明列並用 fake CLI驗證。
- executable digest仍綁定實際 `agy` binary；model label、profile version與prompt SHA必須納入 command/receipt binding，防止 replay換參數。
- 未知 model/profile、未標 PUBLIC_SANITIZED、超長 prompt、禁用pattern、無 executable均在fork前 fail closed，target count 0。

## RED／GREEN

1. Current V4 fake `agy`要求 `--print`/`--model`時RED，證明現行只傳 executable不相容。
2. GREEN fake CLI觀察精確 argv、model、mode、sandbox、timeout；只啟動一個 process並回strict JSON。
3. writer/reviewer兩個model mapping；unknown model=0 process。
4. PUBLIC_SANITIZED gate與既有 outbox forbidden patterns；私密路徑/credential marker=0 process。
5. env allowlist：fake CLI只能看見明列key，不能看見注入的credential sentinel。
6. success/nonzero/timeout、replay no-resend、FD `[0,1,2]`、pre-fork abort、invalid controls不得回歸。
7. flag-off runner行為不變；本卡不得呼叫真實 `agy`。

## 驗證與交付

- broker/outbox focused、全套tests、py_compile、fake trace兩次 byte-identical、allowlist/privacy、`git diff --check`。
- evidence至少 `root-cause.md`、`red-green.txt`、`verification.txt`、`external-tool-gate.md`、`decision.md`。
- 單一 compatibility candidate commit，狀態只能 `READY_FOR_REVIEW / BLOCKED`，不得自審 GO。
- Reviewer GO後另開真實 canary卡；canary固定一次呼叫、合成公開JSON、無retry、無文章、無publish。
