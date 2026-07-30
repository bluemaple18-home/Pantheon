# Review Dispatch Receipt

- Dispatch key: `v1:8f90c26907991b53e95ed79f61c0b6deac1a80277951bef021f94b2d4012100e`
- Dispatch state: `BOUND`
- Mainline thread: `019fb165-8174-7192-b19f-4ed19ed19426`
- Formal Review thread: `019fb36b-25b3-7990-a4d7-fdb858fab6c6`
- Project binding:
  `c2xpbmdzaG90OmVudl9lXzZhMTdiMzc4MTg1ODgzMmRhZWU4Njk3YzMwZmM3ZTdjCi9Vc2Vycy9tYXR0a3VvL0RvY3VtZW50cy9QYW50aGVvbg==`
- Candidate branch:
  `codex/pantheon-p0c-locale-authority-successor-candidate`
- Verified candidate SHA:
  `1f9b9359754d4f3959ee86afcb9d5c257605f9dd`
- Candidate direct parent:
  `ce34670911a7c4691cb6a3cea851b7a805ff965e`
- Review card commit:
  `3f037bbd943d2f2836bb35b9c905bd7641953b9e`
- Review card blob:
  `56d6cbb57d2adf194f0a155a844bb5717224d9ea`
- Bootstrap: formal thread、project、isolated worktree、exact HEAD、clean state 與
  `index.lock` absence 均已驗證。
- Activation: 同一 formal thread 已接收 activation token 與完整 Review 卡契約。
- Materialization authority: Reviewer 只可從上述 mainline commit 取出上述 exact
  blob，原樣 materialize Review 卡；candidate code／tests 不得變更。
- Gate 1 — card and scope: `PASS`
- Gate 2 — implementation candidate: `PASS`
- Gate 3 — candidate verification: `PASS`
- Gate 4 — independent Review: `RUNNING`
- Gate 5 — mainline acceptance/integration: `PENDING`
- External actions: 未呼叫 provider，未讀寫 production `.work`，未 push、deploy
  或 publish。
