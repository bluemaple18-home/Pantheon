# Production operator terminalization receipt

- card：`CARD-PANTHEON-I18N-OUTBOX-OPERATOR-TERMINALIZATION-20260801`
- executed_at：`2026-08-01T09:49:04+08:00`
- implementation commit：`cd00b007bbdeac6da39a9ebb5a5da119992e3357`
- external provider calls：`0`
- publications：`0`

## Target identity

- lane：`i18n-rewrite`
- run：`auto-i18n-ko-aff5c67c15dbae615544-replacement-01`
- job：`542e316fd596eb10e2b6501fb285c644fab640d7`
- logical request：
  `85bdb1195547608e50131faa6af239ca7484fe2c63a7d0b48a4c8be342f3afb9`
- model／role／attempt：`gemini-3.5-flash / writer / 1`
- reason：`UNSUPPORTED_MODEL_CANARY_ABORT`

## Local verification

- public command RED：argparse 原先拒絕 `terminalize-pending`。
- focused operator contract：`18 passed`。
- coordinator＋outbox：`221 passed`。
- repo-wide `pytest -qq`：exit `0`；只有既有 deprecation warnings。
- `git diff --check`：`PASS`。
- code review 修正：symlink request、decision schema version、global-state／
  lane-job split-root topology。
- review verdict：未發現阻塞問題。

## Production preflight

- global run state：`active`。
- `last_job_id`：exact match。
- target request 只存在於 `lanes/i18n-rewrite/outbox/`。
- target 沒有 inbox、failed、processing、archive、operator decision 或
  production-attempt evidence。
- exact dry-run：`dry_run / from outbox / to archive`。
- dry-run 後 request file SHA-256：
  `5180e7ef1fb0c8b7d1e9532e5fb43b29499bcdebe1ac6d4314338e828c8e8de4`。
- prior provider failure receipt SHA-256：
  `188bcdde8df33f3b2ea35c5fdfe4266acc38ad9d1931568337c5b73aafdda650`。
- 六個相關 LaunchAgents：全部 unloaded。

## Execute and postconditions

- first execute：`terminalized`。
- runnable outbox JSON：`0`。
- archived request SHA-256：
  `5180e7ef1fb0c8b7d1e9532e5fb43b29499bcdebe1ac6d4314338e828c8e8de4`。
- operator decision SHA-256：
  `47a6a741543b3008cf4f2978e80dc73e8d4ba99bbe0bf3359a03b6de0dcf5909`。
- terminal run state SHA-256：
  `5eb03cc54ef1c3510a559184ed960423bedba452940efdbf54374293c41bd4fa`。
- prior provider failure receipt SHA-256（未變）：
  `188bcdde8df33f3b2ea35c5fdfe4266acc38ad9d1931568337c5b73aafdda650`。
- second exact execute：`already_terminalized`。
- second execute 後上述四份 hashes 全部不變。
- target job 只剩 archive request 與 operator decision；不存在 provider outcome
  或 production-attempt evidence。
- 六個相關 LaunchAgents：全部仍 unloaded。

## Capacity

- filesystem：228 GiB total、159 GiB used、20 GiB available、89%。
- Gemini queue：133 MiB。
- repair worktrees：193 MiB。
- Publisher state：51 MiB。
