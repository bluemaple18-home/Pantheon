import React, { useEffect, useMemo, useRef, useState } from "react";
import styles from "./PantheonAnimatedLogo.module.css";

const RUNE_PATHS = [
  { p0: [0.16, 0.64], p1: [0.3, 0.25], p2: [0.78, 0.23], p3: [0.83, 0.52] },
  { p0: [0.21, 0.37], p1: [0.46, 0.12], p2: [0.8, 0.28], p3: [0.68, 0.72] },
  { p0: [0.28, 0.76], p1: [0.58, 0.86], p2: [0.86, 0.6], p3: [0.62, 0.34] },
  { p0: [0.35, 0.18], p1: [0.2, 0.5], p2: [0.42, 0.85], p3: [0.72, 0.78] },
  { p0: [0.76, 0.2], p1: [0.56, 0.38], p2: [0.42, 0.62], p3: [0.2, 0.83] },
  { p0: [0.18, 0.51], p1: [0.38, 0.72], p2: [0.7, 0.7], p3: [0.84, 0.43] },
];

const RUNE_COLORS = [
  "rgba(198, 161, 91, 0.82)",
  "rgba(47, 124, 116, 0.68)",
  "rgba(44, 53, 95, 0.64)",
  "rgba(122, 46, 58, 0.64)",
  "rgba(139, 168, 157, 0.72)",
  "rgba(238, 220, 180, 0.72)",
];

const DEFAULT_RUNE_COUNT = 64;
const MAX_DPR = 2;

function createRunes(count = DEFAULT_RUNE_COUNT) {
  return Array.from({ length: count }, (_, index) => ({
    pathIndex: index % RUNE_PATHS.length,
    progress: (index * 0.61803398875) % 1,
    speed: 0.00012 + (index % 9) * 0.000018,
    color: RUNE_COLORS[index % RUNE_COLORS.length],
    size: 1.05 + (index % 5) * 0.42,
    type: index % 5,
    depthPhase: index * 0.47,
  }));
}

function cubicBezierPoint(t, p0, p1, p2, p3) {
  const mt = 1 - t;
  const mt2 = mt * mt;
  const t2 = t * t;

  return [
    mt2 * mt * p0[0] + 3 * mt2 * t * p1[0] + 3 * mt * t2 * p2[0] + t2 * t * p3[0],
    mt2 * mt * p0[1] + 3 * mt2 * t * p1[1] + 3 * mt * t2 * p2[1] + t2 * t * p3[1],
  ];
}

function drawRune(ctx, rune) {
  const size = rune.size;

  ctx.beginPath();
  if (rune.type === 0) {
    ctx.arc(0, 0, size, 0, Math.PI * 2);
    ctx.fill();
    return;
  }

  if (rune.type === 1) {
    ctx.moveTo(0, -size * 1.6);
    ctx.lineTo(size * 1.35, 0);
    ctx.lineTo(0, size * 1.6);
    ctx.lineTo(-size * 1.35, 0);
    ctx.closePath();
    ctx.stroke();
    return;
  }

  if (rune.type === 2) {
    ctx.moveTo(-size * 1.7, -size);
    ctx.lineTo(size * 1.7, size);
    ctx.stroke();
    return;
  }

  if (rune.type === 3) {
    ctx.moveTo(-size * 1.45, -size * 1.45);
    ctx.lineTo(size * 1.45, size * 1.45);
    ctx.moveTo(size * 1.45, -size * 1.45);
    ctx.lineTo(-size * 1.45, size * 1.45);
    ctx.stroke();
    return;
  }

  ctx.moveTo(-size * 2, 0);
  ctx.lineTo(size * 2, 0);
  ctx.moveTo(size * 0.6, -size * 1.3);
  ctx.lineTo(size * 2, 0);
  ctx.lineTo(size * 0.6, size * 1.3);
  ctx.stroke();
}

function setupCanvas(canvas, ctx) {
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(1, rect.width);
  const height = Math.max(1, rect.height);
  const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR);

  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  return { width, height, dpr };
}

export default function PantheonAnimatedLogo({
  baseImageSrc,
  baseImageWebpSrc,
  baseImageAvifSrc,
  altText = "Pantheon Brand Logo",
  className = "",
  runeCount = DEFAULT_RUNE_COUNT,
}) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const requestRef = useRef(null);
  const runesRef = useRef(null);
  const canvasSizeRef = useRef({ width: 1, height: 1, dpr: 1 });

  const [isInView, setIsInView] = useState(false);
  const [isPageVisible, setIsPageVisible] = useState(true);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  const shouldAnimate = isInView && isPageVisible && !prefersReducedMotion;
  const rootClassName = useMemo(
    () =>
      [
        styles.logoContainer,
        className,
        !shouldAnimate ? styles.paused : "",
        prefersReducedMotion ? styles.reducedMotion : "",
      ]
        .filter(Boolean)
        .join(" "),
    [className, prefersReducedMotion, shouldAnimate],
  );

  if (!runesRef.current) {
    runesRef.current = createRunes(runeCount);
  }

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const handleMotionChange = (event) => setPrefersReducedMotion(event.matches);

    setPrefersReducedMotion(mediaQuery.matches);
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener("change", handleMotionChange);
    } else {
      mediaQuery.addListener(handleMotionChange);
    }

    return () => {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener("change", handleMotionChange);
      } else {
        mediaQuery.removeListener(handleMotionChange);
      }
    };
  }, []);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return undefined;

    const observer = new IntersectionObserver(
      ([entry]) => setIsInView(entry.isIntersecting),
      { threshold: 0.1 },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const handleVisibilityChange = () => setIsPageVisible(!document.hidden);
    handleVisibilityChange();

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return undefined;

    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return undefined;

    const resize = () => {
      canvasSizeRef.current = setupCanvas(canvas, ctx);
    };

    resize();
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);

    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;

    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return undefined;

    if (!shouldAnimate) {
      cancelAnimationFrame(requestRef.current);
      requestRef.current = null;
      const { width, height } = canvasSizeRef.current;
      ctx.clearRect(0, 0, width, height);
      return undefined;
    }

    let lastTime = performance.now();

    const draw = (now) => {
      const { width, height } = canvasSizeRef.current;
      const delta = Math.min(now - lastTime, 48);
      lastTime = now;

      ctx.clearRect(0, 0, width, height);
      ctx.globalCompositeOperation = "screen";

      for (const rune of runesRef.current) {
        rune.progress = (rune.progress + rune.speed * delta) % 1;
        const path = RUNE_PATHS[rune.pathIndex];
        const [relX, relY] = cubicBezierPoint(rune.progress, path.p0, path.p1, path.p2, path.p3);

        const edgeFade = Math.sin(rune.progress * Math.PI);
        const depth = 0.58 + 0.42 * Math.sin(rune.progress * Math.PI * 2 + rune.depthPhase);
        const opacity = edgeFade * (0.14 + depth * 0.48);
        const scale = 0.82 + depth * 0.56;

        ctx.save();
        ctx.translate(relX * width, relY * height);
        ctx.rotate((depth - 0.5) * 0.85);
        ctx.scale(scale, scale);
        ctx.globalAlpha = opacity;
        ctx.fillStyle = rune.color;
        ctx.strokeStyle = rune.color;
        ctx.lineWidth = 1.15;
        drawRune(ctx, rune);
        ctx.restore();
      }

      ctx.globalCompositeOperation = "source-over";
      requestRef.current = requestAnimationFrame(draw);
    };

    requestRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(requestRef.current);
      requestRef.current = null;
    };
  }, [shouldAnimate]);

  return (
    <div ref={containerRef} className={rootClassName}>
      <div className={styles.aura} />

      <picture className={styles.baseImageContainer}>
        {baseImageAvifSrc && <source srcSet={baseImageAvifSrc} type="image/avif" />}
        {baseImageWebpSrc && <source srcSet={baseImageWebpSrc} type="image/webp" />}
        <img src={baseImageSrc} alt={altText} className={styles.baseImage} loading="eager" decoding="async" />
      </picture>

      <div className={styles.coreGlow} />
      <canvas ref={canvasRef} className={styles.runesCanvas} aria-hidden="true" />
    </div>
  );
}
