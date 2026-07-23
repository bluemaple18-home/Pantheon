# Decision

status: `DELIVERED_CANDIDATE`

Repair-2 僅修 `P1_TRUSTED_RESULT_SCHEMA`。固定 trusted closed schema 已在 standalone
verifier 內建立；bundle schema 必須完全相等，execution／inbox result 必須符合該 contract，
canonical result bytes 亦與 byte count及 stdout SHA綁定。

RED 已證明舊 verifier 接受 wrong-schema 與 coherent weakened-schema tamper；相同 probes 在
GREEN 後皆被拒絕。合法 real／synthetic bundle仍 PASS，舊 summary仍 REJECTED，14/14
mutation controls皆 rejected。

本輪未修改真實 bundle、recorder、broker、production code／tests或已 resolved P2；未呼叫
外部 agy／Gemini，未執行 retry、fallback、merge、push、deploy、publish或預設 transport
切換。

本狀態只表示 candidate 已交付同一 canonical Reviewer 重審；不代表 GO、ACCEPTED、
INTEGRATED、production rollout或預設 transport promotion。
