# Pantheon Sphere 視覺階段交接

## Goal

將 Pantheon 主視覺建立為五條金屬 Band 圍繞 Self Core 的品牌 Hero Image；五條中心線維持封閉星軌，主題主要由色彩與凸起金屬符文辨識。

## Root Question

如何在不重畫中心線、不增加新幾何與特效的前提下，讓 Pantheon Sphere 接近參考圖的金屬重量、主題辨識、中央呼吸感與球體完整性。

## Constraints & Preferences

- Geometry 中心線、Band 數量、Band width／thickness／bevel 與 Camera 不可重做。
- 禁止 Designer Curve、自由 spline、粒子、Bloom、Halo、Lens flare。
- 符文是與 Band 一體成形的 Raised Metallic Relief，不是白色貼圖、LED 或凹刻。
- 正式辨識順序：主題顏色、符文語言、空間位置與動畫節奏。
- Material Identity Lab 保留研究用途，不套用複雜 Meso／Micro 製造工藝。
- 正式狀態維持 `NEEDS WORK`，不可宣告 GO。

## Completed Actions

- Self Core 改為深暖古銅金 Artifact：
  - `#754315`
  - metalness `0.90`
  - roughness `0.25`
  - emissive intensity `0.012`
  - radius scale `0.96`
- 符文改為較小、較細、較低白色染色的同材質凸起浮雕。
- 符文密度由 `18` 提高為 `24`，最低符文群組由 `14` 提高為 `20`；流水命中格同步為 `24`。
- Constellation 暗面藍色可讀性提高，但外殼感尚未完全消除。
- 只對 Ziwei Bazi 做受限 pose 微調：
  - inclination `80.1° → 75.1°`
  - azimuth `214.6° → 219.6°`
  - roll 維持 `172.2°`
- 中心線簽章與姿態簽章已拆分：
  - Centerline：`sha256:869d8d22fddea450b4921e20c4732622e54bc1b895b1875de50f94ba076c6008`
  - Pose：`sha256:9f0f15499211c8a9625524adb743fc2e017f873ebaa5f74b697ec4d35088b222`
- 固定 Runtime frame 的 Self Core 可見比例為 `79.77%`。

## Verification

- `python3 -m unittest tests/theme_rune_language_contract.py tests/visual_target_v1_contract.py`：9/9 通過。
- `pnpm run typecheck`：通過。
- `pnpm run build`：通過；僅有既存 bundle 大小警告。
- `git diff --check`：通過。
- Runtime console error：0。
- Runtime page error：0。
- Runtime network failure：0。

## Evidence

- `prototypes/pantheon-motion-demo/artifacts/pantheon_visual_target_v1/evidence/final-balance-pass/desktop-orbit.png`
- `prototypes/pantheon-motion-demo/artifacts/pantheon_visual_target_v1/evidence/final-balance-pass/desktop-front.png`
- `prototypes/pantheon-motion-demo/artifacts/pantheon_visual_target_v1/evidence/final-balance-pass/desktop-front-left.png`
- `prototypes/pantheon-motion-demo/artifacts/pantheon_visual_target_v1/evidence/final-balance-pass/desktop-right.png`
- `prototypes/pantheon-motion-demo/artifacts/pantheon_visual_target_v1/evidence/final-balance-pass/mobile-orbit.png`

## Active State

- 工作目錄：`<repo-root>`
- Prototype：`prototypes/pantheon-motion-demo`
- 本機 dev server 已於收尾時停止。
- Worktree 原本即存在大量未提交／未追蹤內容；本階段未清除、覆寫或提交其他人的變更。

## Blocker

`desktop-front-left.png` 仍暴露明顯 Band 接縫／切面與局部硬亮面，斜角尚未維持完整精品金屬球體。此問題不能再用顏色、亮度或 pose 掩蓋。

## Candidate Fork

- Fork A：先修 Band mesh seam／frame closure；不改中心線。
- Fork B：先完成符文精緻度與同材質浮雕一致性；保留目前密度 24。
- Fork C：先改善 Constellation 外殼感；只允許局部材質平衡或極小 pose，不重排五條。

## In Progress / Remaining Work

1. 釐清 front-left 的可見切面是 Band mesh seam、frame closure、UV seam 或材質硬切。
2. 修正後重新驗證 front、front-left、side、mobile。
3. 符文在高光區仍偶爾偏白；需繼續保持同材質感。
4. Constellation 仍有外框／外殼感。
5. 完成以上項目後，才重新做整體 Reference Compare。

## Next Step

下次恢復時先做「Band Seam Runtime Diagnosis」，只讀取目前 mesh／frame／shader seam 流程並固定重現 `desktop-front-left`；在根因確認前不調整 Lighting、PMREM、色票或 Orbit。

## Waiting Condition

等待使用者重新開工；若沒有新的優先順序，預設從 Band seam／切面診斷開始。

## Limits

- 不修改中心線或 Band 尺寸。
- 不以重新排 pose 掩蓋 seam。
- 不加入新特效。
- 不把 build／contract test 當成視覺通過。
- 沒有新的 Runtime 截圖前，狀態保持 `NEEDS WORK`。

## Key Decisions & Resolved Questions

- Geometry centerline 可保留；整體差距不應全部歸因於 Geometry。
- Band 寬度已足夠，不再增加。
- Core、符文、Constellation 與 pose 必須分開驗收。
- 符文密度 24 已在固定 Runtime 畫面確認，比 18 更符合目前方向。
- 下一階段不再繼續盲調 Lighting／PMREM／全域 Style Layer。
