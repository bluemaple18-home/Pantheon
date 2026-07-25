# Root cause

Date: 2026-07-25

## Problem

Pantheon structured canary固定使用第一把Gemini credential。Operator確認三把key
來自不同帳號；若它們也分屬不同Google Cloud project，固定第一把會讓文章流程
與其他專案競爭同一project的RPM／TPM／RPD。

## Unsafe alternative

在429、timeout或transport error後換下一把key重送，會讓同一operation產生第二
次provider request，破壞exactly-once與network ambiguity邊界。因此本卡不實作
failure-driven rotation、retry、fallback或credential pool failover。

## Minimal correction

- Pool manifest只保存stable slot ID與credential file path。
- Manifest與credential files都必須owner-only regular non-symlink。
- `pool_id + operation_id`經SHA-256 deterministic選slot，不保存mutable cursor。
- Selection由broker lazy opener執行；existing ledger replay不讀pool。
- New structured operation將非敏感pool／slot／manifest digest寫入receipt與
  `CREDENTIAL_SELECTED` ledger event。
- Target仍只得到一個credential FD並執行一次model POST。

## Remaining boundary

不同帳號不由source直接證明不同Google Cloud project。現有本機缺少control-plane
identity，因此project mapping仍以operator assertion為前提。Pool candidate不
授權default promotion。
