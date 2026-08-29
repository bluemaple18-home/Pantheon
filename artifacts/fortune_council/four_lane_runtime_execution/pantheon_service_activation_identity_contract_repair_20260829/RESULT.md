# RESULT：Pantheon Service Activation Shared Identity Contract Bounded Repair

## Verdict

`RE_REVIEW_REQUESTED`

DESIGN_GO revision已完成。第一次candidate的shared actor-prefix parser與其legacy identity機械改寫已完整撤回；runtime manifest恢復既有nonempty/trimmed opaque identity＋separate `actor_head` contract。唯一source行為修正是capacity停止私自解析activation-only suffix與停止unreadable live plist時的identity mode fallback。

## Final contract

- `identity`：nonempty、trimmed opaque correlation；`g8-live`、`g8-staged`與operation-specific identity均合法。
- actor authority：separate `actor_head`；既有git head/root validation、`manifest_digest`與`runtime_identity_digest`保持fail closed。
- mode authority：explicit arguments及plist/stage/live topology；identity suffix不承載mode。
- capacity仍保留manifest digest、barrier、stage/live tuple、Rule24、recovery-from-normal與wrong-mode checks。

## First candidate withdrawal

- withdrawn candidate：shared parser要求identity內嵌actor SHA，廣域結果 `406 passed / 44 failed`。
- parent baseline：`442 passed / 8 failed`。
- measured regression：新增36個G8 production preactivation failures。
- final candidate：同一command、interpreter、selection與environment回到 `442 passed / 8 failed`；failure node set及逐node normalized error digest與parent exact identical。
- 不以 `g8-live`白名單修補；shared parser與embedded actor validation均已移除。

## Verification

- targeted runtime manifest＋capacity：`114 passed`。
- promotion downstream：`65 passed`。
- coordinator installer／aggregate affected selection：`11 passed`。
- exact broad selection：`442 passed / 8 failed`，`BASELINE_IDENTICAL`。
- broad command SHA-256：`1dc2e990d89de20bcd82d5f9f7e6c6a68182695073c6d4bc7f91cca60f3559e0`。
- broad environment SHA-256：`650bdc1ba45db6a0bc8bbc729713b12f06be6372affeb4415d14ce55b16b7bce`。
- py_compile、JSON parse、`git diff --check`：PASS。

## Diff and scope

- source＋test changed LOC：`128`（115 additions／13 deletions），低於上限220。
- source files changed：`1`（capacity）；runtime manifest source與accepted parent byte-equivalent。
- test files changed：`2`；新增opaque identity及no-mode-fallback精確coverage。
- final source/test diff SHA-256：`f754f483762b271275aff113947cff0731cbdb05dbcf0441315652dcae7ca553`。
- allowlist外修改：`0`。
- promotion/coordinator/publisher source修改：`0`。
- queue/registry/ledger/FSM/DB/migration修改：`0`。
- production/live/provider/reviewer/publisher mutation或call：`0`。
- commit/push/promotion/install/activate/tag/deploy：`0`。

## Minimum sufficient

- `why_not_less`：只移除transition regex仍會保留unreadable plist時從suffix猜mode；兩個capacity私有語義點必須一起撤回。
- `why_not_more`：既有actor_head、digests、barrier、stage/live tuple與explicit mode topology已完整擁有authority；runtime manifest不需新parser或schema。
- `do_not_absorb`：identity whitelist、per-service identity、generic union、new registry/FSM/DB/ledger、migration、live rewrite、capacity-first bypass。

請獨立Reviewer依 `EVIDENCE.md` 重跑 final gates；第一次candidate僅保留為已撤回歷史證據。
