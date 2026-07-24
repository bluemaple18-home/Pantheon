# Gemini V4 Shadow-002｜Preflight

## Startup identity

- Chain：`CONTENT-GEMINI-V4-ROLLOUT-002`
- Starting HEAD：`6706ae3a28eb601fdf4c8b97531173138f67ef37`
- Starting HEAD唯一parent：`1dd80978dc4c6facbb588aa8869bec8362e606a3`
- Source branch：`codex/gemini-v4-rollout-shadow-002-source`
- Source branch在啟動時指向starting HEAD：`PASS`
- 獨立detached worktree：`PASS`
- 啟動時working tree clean：`PASS`
- Git index lock absent：`PASS`
- Shadow-002卡在starting HEAD可讀：`PASS`

## Lineage

- Upstream integrated main：
  `1dd80978dc4c6facbb588aa8869bec8362e606a3`
- Output-binding Repair：
  `4e04e82506c4a1c2a3846640f9504fca972ae9fd`
- Independent Review evidence／verdict：
  `1dd80978dc4c6facbb588aa8869bec8362e606a3 / GO`
- Repair是starting HEAD ancestor：`PASS`
- Integrated main是starting HEAD ancestor：`PASS`
- Previous blocked rollout：
  `90559641a9460c26eb7c168ebbb78ce4be2a51fa`
- Previous blocked rollout不是本新lineage的ancestor：`PASS`
- 舊operation／ledger／attempt未重用：`PASS`

## Required reads

- `AGENTS.md`：complete
- Shadow-002卡：complete
- Output-binding Repair／Review cards與全部evidence：complete
- 舊blocked rollout card、decision、real bundle、real verification與verifier：read-only
- Production broker／runner：complete
- V4 focused、legacy publishing與coordinator tests：complete

## Final external canary package

固定包執行前狀態：`BLOCKED / EXTERNAL_CANARY_FINAL_CONFIRMATION`

- Tool basename：`agy`
- `agy --version`：`1.1.5`
- Executable SHA-256：
  `6509d6ca54a66e3eaf61dfe35308ba1dfa1e6b552ef5c4f5f861562c6811ecaf`
- Task shell PATH lookup：未命中；以既有本機executable唯讀解析版本與digest，未修改
  PATH、全域CLI設定或環境。
- Model：`gemini-3.5-flash`
- Model label：`Gemini 3.5 Flash (Low)`
- Production entrypoint：`scripts.agy_gemini_v4_broker:run_single_shot`
- Target profile：`antigravity_cli_v1`
- Item ID：`gemini-v4-rollout-shadow-canary-002`
- Attempt ID：`shadow-002-attempt-1`
- Operation ID：`5317d8ebdb3e52f47924bf8bf6266163a2496031`
- Request SHA-256：
  `5317d8ebdb3e52f47924bf8bf6266163a24960317e9c8cdeb4d3f0a4cc13753a`
- Timeout：`120000 ms`
- Maximum：`1` production target invocation
- Retry／fallback／automatic resend：全部禁止

### Fixed prompt

```text
Return exactly one JSON object and no prose. The object must be {"ok":true,"transport":"agy-v4-rollout-shadow-canary-002"}. Do not add keys. This is a public sanitized synthetic canary.
```

### Closed result schema

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "ok": {
      "type": "boolean",
      "enum": [true]
    },
    "transport": {
      "type": "string",
      "enum": ["agy-v4-rollout-shadow-canary-002"]
    }
  },
  "required": ["ok", "transport"]
}
```

### CLI contract

```text
agy --model "Gemini 3.5 Flash (Low)" --mode plan --sandbox \
  --log-file <ephemeral-log> --print-timeout 120s --print <fixed-prompt>
```

`<ephemeral-log>`只存在於broker temporary directory，不保存到evidence。

### Accepted stdout encodings

只有以下三種：

1. `canonical-json-v1`
2. `canonical-json-newline-v1`
3. `sorted-indent2-json-newline-v1`

Verifier只從closed-schema parsed result與encoding label重建完整bytes，再比對
`byte_count`與`stdout_sha256`。Evidence bundle不保存raw stdout。

## Offline command and effect summary

- Pytest commands：`4`
  - Targeted flag regression：`6 passed`
  - V4 focused：`74 passed`
  - Legacy publishing：`57 passed`
  - Coordinator：`6 passed`
  - Unique pytest total：`137 passed`；targeted 6已包含於V4 focused，不重複計數。
- Synthetic recorder invocations：`3`；各自只啟動一個本機synthetic fixture process。
- Independent verifier invocations：`5`；不import、不呼叫production broker或CLI。
- Encoding acceptance：`3/3 PASS`
- Mutation rejection：`13/13 PASS`
- `py_compile`：`2` evidence-owned Python files
- External Gemini／agy generations：`0`
- 單次production canary預期影響：一次公開sanitized generation；不發布、不修改遠端
  設定、不改預設transport、不寫article／queue／automation。

## Authorization and execution record

- 主線已完整展示本文件固定包。
- 使用者在該固定包後明確回覆「繼續」。
- 主線將該回覆授權綁定到本Shadow-002唯一一次production canary。
- Authorization：`CONSUMED_ONE_INVOCATION`
- Production invocation：`1`
- Production process count：`1`
- Retry／fallback／automatic resend：`0`
- 第二次呼叫：禁止
- Execution result：`COMPLETE/1 / SUCCESS`
- Independent verification：`PASS`
