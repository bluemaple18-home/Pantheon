# Root cause

## 事實

- Legacy Gemini CLI transport 對 executable 缺失、nonzero exit 與 envelope error 皆使用一般 `RuntimeError`。
- Timeout 未在 transport 邊界轉換，會直接以 `TimeoutExpired` 逸出。
- Nonzero 與 envelope error 曾把 CLI 原始 detail 放入 exception message；runner 雖未保存 message，但沒有可安全區分原因的欄位。
- Runner failed receipt 只保存 `error_type`；outbox consumer 與 coordinator state 也沒有 closed failure code。
- Coordinator 會繼續推進同輪其他 active run，且 failed state 不再列入 active queue；新增 regression 已鎖定此行為。

## 判定

本機可修復根因是 transport failure taxonomy 在 CLI 邊界遺失，導致 downstream 只能看到泛化例外。修復方式是在最靠近 subprocess/envelope 的接縫建立固定 code，並只讓 allowlist code 通過 runner、outbox、operation receipt 與 coordinator。

JSON parse/schema validation 保持原有例外類別，未合併成 transport code。此次未執行真實 Gemini probe，因此沒有證據判定當時大量失敗究竟由 quota、login 或 backend outage 觸發。

## 已排除

- Seeder deadlock：既有 evidence 顯示 coordinator 持續建立 run。
- Failed run 永久卡住後續 run：synthetic coordinator regression 證明同輪第二個 run 可完成，failed state 不回 active 前排。
- V4 fallback：既有 V4 fail-closed tests 全數通過，未加入 legacy fallback。
