# Pantheon 目前實際渲染參數包

用途：提供 GPT 檢查目前 Pantheon 球體為什麼仍可能偏暗、偏霧面，以及應如何調整燈光與金屬反射。

## 鎖定範圍

- Geometry：v1.1，禁止修改
- Band width：Desktop `0.18`、Mobile `0.16`
- Band thickness：`0.02`
- Bevel width：`0.0024`
- Bevel segments：`2`
- Self Core 尺寸與位置：鎖定
- 本次只允許建議 Lighting、PMREM、Material、Shader response

## Renderer

```ts
toneMapping = THREE.AgXToneMapping
toneMappingExposure.desktop = 1.08
toneMappingExposure.mobile = 1.04
outputColorSpace = THREE.SRGBColorSpace
shadows = false
DPR.desktop <= 2
DPR.mobile <= 1.5
```

## 全局控制

```ts
fieldLightStrength = 5.20
metalHighlightStrength = 1.40
```

## 燈光 Baseline

```ts
ambient.desktop = 0.36
ambient.mobile = 0.38

hemisphere.desktop = 0.86
hemisphere.mobile = 0.90

key.desktop = 2.20
key.mobile = 1.85

fill.desktop = 0.85
fill.mobile = 0.72

rim.desktop = 0.78
rim.mobile = 0.66

sceneEnvironmentIntensity = 0.90
```

## 燈光位置、顏色與尺寸

```ts
Hemisphere:
  skyColor = #d8e4e8
  groundColor = #111820

Ambient:
  color = #ffffff

Key RectAreaLight:
  color = #ffe7c2
  position = [0, 4.9, 4.5]
  target = [0, 0, 0]
  size = [6.4, 3.2]

Fill RectAreaLight:
  color = #dde6ee
  position = [4.8, 0.4, 3.2]
  target = [0.48, -0.12, 0]
  size = [4.8, 4.2]

Rim RectAreaLight:
  color = #e7edf3
  position = [-0.35, 1.7, -5.2]
  target = [0, 0.2, 0]
  size = [5.0, 3.2]
```

## 全局控制實際換算

```ts
ambientLift =
  clamp(0.9 + (fieldLightStrength - 1) * 0.18, 0.8, 1.28)

hemisphereLift =
  clamp(0.95 + (fieldLightStrength - 1) * 0.22, 0.82, 1.3)

key =
  keyBaseline * fieldLightStrength * metalHighlightStrength

fill =
  fillBaseline * (0.65 + fieldLightStrength * 0.35)

rim =
  rimBaseline *
  (0.7 + fieldLightStrength * 0.3) *
  metalHighlightStrength

sceneEnvironment =
  environmentBaseline *
  (0.75 + fieldLightStrength * 0.25) *
  metalHighlightStrength
```

目前換算後：

| 項目 | Desktop | Mobile |
|---|---:|---:|
| Ambient | 0.461 | 0.486 |
| Hemisphere | 1.118 | 1.170 |
| Key | 16.016 | 13.468 |
| Fill | 2.100 | 1.778 |
| Rim | 2.468 | 2.088 |
| Scene environment | 2.583 | 2.583 |

## PMREM Studio Environment

```ts
resolution = 512 × 256
baseColor = #34424e

horizontalSoftbox:
  rect = [24, 18, 432, 78]
  blur = 20px
  color = rgba(252, 242, 226, 0.96)

verticalStrip:
  rect = [390, 36, 76, 178]
  blur = 16px
  color = rgba(218, 232, 237, 0.78)

darkRearCard:
  rect = [8, 116, 164, 100]
  blur = 20px
  color = rgba(12, 19, 27, 0.62)

lowerFillCard:
  rect = [118, 174, 292, 46]
  blur = 24px
  color = rgba(188, 205, 213, 0.34)

warmCoreCircle:
  center = [216, 112]
  innerRadius = 6
  outerRadius = 74
  blur = 18px
  stops:
    0.00 = rgba(255, 210, 139, 0.82)
    0.50 = rgba(238, 184, 108, 0.40)
    1.00 = rgba(191, 132, 70, 0)
```

只有一份共享 PMREM，沒有 per-band envMap rotation。

## 背景

```ts
center = #0e151d
middle = #0b1118
edge = #080d13
```

## 正式 Style Candidate

目前使用：

```ts
Candidate B = "soft-metal"

wrap = 0.48
wrapStrength = 0.34
viewGradientStrength = 0.17
rimStrength = 0.052
colorLift = 0.11
emissiveLift = 0.045
gradientStrength = 0.46
backBrightness = 0.90
roughnessOffset = -0.10
metalnessScale = 0.95
envMapIntensity = 0.92
```

## 五個主題基礎 PBR

| Theme | Base color | Accent | Metalness | Roughness | Anisotropy | 原始 envMap |
|---|---|---|---:|---:|---:|---:|
| Constellation | `#294f87` | `#c7a96a` | 0.91 | 0.56 | 0.42 | 0.66 |
| Tarot | `#8a3b4a` | `#d1a06f` | 0.91 | 0.54 | 0.38 | 0.67 |
| MBTI | `#276f69` | `#d1b274` | 0.89 | 0.58 | 0.36 | 0.64 |
| Human Design | `#c5ced0` | `#afc5ce` | 0.91 | 0.55 | 0.34 | 0.66 |
| Ziwei Bazi | `#80513a` | `#d8ae67` | 0.92 | 0.56 | 0.44 | 0.68 |

共用：

```ts
clearcoat = 0
clearcoatRoughness = 0.27～0.30
```

## 雙色漸層

```ts
Constellation: #132b50 → #667fa3
Tarot:         #762d40 → #b55f70
MBTI:          #1d5957 → #4f8781
Human Design:  #c5ced0 → #afc5ce
Ziwei Bazi:    #704730 → #b38455
```

## Candidate B 每主題權重

| Theme | Brightness | Saturation | Roughness offset | Metalness scale | Highlight strength | Gradient | Back brightness | Bevel brightness |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Constellation | 0.92 | 0.86 | 0.00 | 1.00 | 0.82 | 0.40 | 0.72 | 1.06 |
| Tarot | 0.72 | 0.90 | 0.00 | 0.94 | 0.38 | 0.42 | 0.82 | 1.06 |
| MBTI | 0.82 | 0.86 | +0.05 | 0.90 | 0.55 | 0.36 | 0.80 | 1.04 |
| Human Design | 0.82 | 0.68 | -0.04 | 0.90 | 0.60 | 0.16 | 0.80 | 1.10 |
| Ziwei Bazi | 0.82 | 0.82 | -0.01 | 0.92 | 0.45 | 0.40 | 0.81 | 1.06 |

## 實際 Band PBR 結果

計算方式：

```ts
finalRoughness =
  clamp(
    baseRoughness +
    candidateRoughnessOffset +
    themeRoughnessOffset,
    0.42,
    0.60
  )

finalMetalness =
  baseMetalness *
  candidateMetalnessScale *
  themeMetalnessScale
```

| Theme | 實際 Roughness | 實際 Metalness |
|---|---:|---:|
| Constellation | 0.46 | 0.865 |
| Tarot | 0.44 | 0.812 |
| MBTI | 0.53 | 0.761 |
| Human Design | 0.42（clamp） | 0.778 |
| Ziwei Bazi | 0.45 | 0.804 |

Band environment：

```ts
Desktop top/bottom envMapIntensity = 0.92 * 1.40 = 1.288
Desktop bevel envMapIntensity = 1.288 * 1.06 = 1.365
Desktop edge envMapIntensity = 1.288 * 0.88 = 1.133

Mobile 額外乘 qualityEnvironmentBoost = 1.22
```

## Shader 中的額外 Style Shaping

```glsl
specularRetention =
  mix(0.72, 1.0, themeHighlightStrength);

directSpecular *= depthBrightness * 0.82;
indirectSpecular *= depthBrightness * 0.90;

specularTint =
  mix(white, themeGradient, 0.28);
```

自製 `Broad Highlight` 已停用。正式畫面目前只使用 PBR
Specular、共享 PMREM 與既有的 Style Match 色彩／深度 shaping。

## Self Core

```ts
baseColor = #c9a154
emissiveColor = #52370d
emissiveIntensity = 0.07
metalness = 0.76
roughness = 0.30

reflectionFrequencyHz = 0.42
normalStrength = 0.032
roughnessVariation = 0.028
```

## Surface Marks

```ts
cellCount = 36
minimumGlyphClusters = 30

Idle opacity = 0.42
Hovered opacity = 0.56
Selected opacity = 0.68
Background opacity = 0.30

markDepth = 0.16
markRoughnessDelta = 0.09
markMetalnessDelta = -0.04

Idle mark emissive = 0
Hovered mark emissive = 0.02
Selected mark emissive = 0.035
```

## Surface Energy

| Theme | Cycle | Pulse count | Intensity | Direction | Rhythm warp |
|---|---:|---:|---:|---:|---:|
| Constellation | 18s | 2 | 0.36 | +1 | 0.16 |
| Tarot | 13s | 1 | 0.46 | -1 | 0.30 |
| MBTI | 16s | 2 | 0.34 | +1 | 0.08 |
| Human Design | 12s | 1 | 0.32 | -1 | 0.22 |
| Ziwei Bazi | 20s | 1 | 0.42 | +1 | 0.36 |

## 請 GPT 主要檢查

1. 新的水平／垂直／深色／暖色四區 PMREM 是否已提供足夠的精品攝影棚反射。
2. Candidate B 的 `themeHighlightStrength` 是否仍過低，尤其 Tarot `0.38`、Ziwei Bazi `0.45`。
3. `specularRetention`、`depthBrightness`、`0.82/0.90` 是否仍把金屬反射壓得太多。
4. PMREM base `#2a3540` 與四塊 Reflection Area 的尺寸、位置及 alpha 是否合理。
5. 應優先調整 PMREM、roughness 或 themeHighlightStrength；Broad Highlight 維持關閉。
6. 如何在不增加曝光、不改 Geometry、不使用 Bloom 的前提下，讓五條 Band 都具有清楚但不爆白的金屬光澤。

## 不允許建議

- 不修改 Geometry
- 不修改軌道姿態
- 不修改 Band 寬度、厚度、倒角
- 不加入 Bloom、Halo、粒子、Lens flare
- 不使用 per-band light linking
- 不讓 Band 變成純白鉻金屬
