# Pantheon Motion Demo

React + Vite 的動態主視覺範例。透明 WebM 負責中央 3D 球體，SVG + CSS 負責三層同心軌道、符號與互動視差。

## 執行

```bash
pnpm install
pnpm dev
```

正式建置：

```bash
pnpm build
```

## 核心檔案

- `src/components/PantheonMotionVisual.jsx`：透明影片、三圈 SVG、離屏暫停、分頁暫停、Reduced Motion 與省流量降級。
- `src/components/PantheonMotionVisual.module.css`：影片遮罩、軌道動畫、光暈、節點與游標視差。
- `src/App.jsx`：品牌 Hero 與渲染架構說明。
- `public/pantheon-orb-alpha-v2.webm`：720×864、16 FPS、含 Alpha 的 VP9 動畫。
- `public/pantheon-orb-alpha-poster.webp`：首屏透明 WebP poster。

## 媒體資產

目前部署媒體預算：

- 透明 WebM：約 1.72 MB。
- WebP poster：約 88 KB。
- 原始影片與中間素材放在 `source-assets/`，已由 `.gitignore` 排除，不會進入部署包。

移植到其他頁面時，複製 `PantheonMotionVisual.jsx`、對應 CSS Module，以及上述兩個 `public/` 媒體檔即可。

## 效能策略

- 不使用持續執行的 Canvas/WebGL render loop。
- `IntersectionObserver` 在主視覺離開畫面時暫停影片。
- 分頁進入背景時暫停。
- `prefers-reduced-motion` 或省流量模式下不建立 `<video>`，只顯示 poster。
- Poster 預載並提供固定寬高，降低 LCP 與 CLS；影片開始播放後 poster 會淡出，避免重疊混色。
- 媒體使用版本化檔名，方便設定長效 Cache-Control。
- 游標視差只在 pointer event 發生時更新，並用 `requestAnimationFrame` 合併更新。
