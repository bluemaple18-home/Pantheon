# Repair-2 root cause

Generation: `Repair-2`（final repair）

Parent candidate: `878ad3872e2fbf8bf135ddbff2a6fb596e7c96df`

## F002

Provider projection v1原本只有全域關鍵字allowlist，沒有依目前schema type限制
關鍵字，也沒有驗證enum值、format或numeric bounds。這使boolean搭配enum、
string搭配minimum、number搭配format仍能進入provider payload。

修正後每個type有獨立closed keyword set：

- object：properties、required、additionalProperties
- array：items、minItems、maxItems
- string：enum、format；caller另保留minLength、maxLength
- number／integer：enum、minimum、maximum
- boolean／null：只有common metadata與type

String format只接受date、date-time、time。Enum值必須符合schema type，bool不視為
integer。Number值與bounds必須有限；integer enum與bounds必須是exact integer。
完整caller schema仍包含minLength／maxLength，但projection不傳送這兩項。

## F003

Python標準JSON decoder預設接受NaN、Infinity與-Infinity，標準encoder也會輸出；
NaN和minimum／maximum比較均為false，因此舊numeric gate可能把非法JSON判為
VALID。

修正後target與broker的canonical serializer都設定allow_nan=False；target request、
provider envelope、provider text、broker frame／ledger／anchor及target stdout都用
拒絕非有限constant的strict loader。Broker numeric validator另行檢查value與bounds
有限，不轉null、不clamp、不做tolerant parse。

## Preserved findings

F001、F004、F005已由同一Reviewer關閉。本輪未修改runner、outbox或SEO pipeline；
五套回歸仍覆蓋structured-only routing、credential-free replay及maxItems bounded
traversal。
