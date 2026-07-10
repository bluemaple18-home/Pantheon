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

  return { width, height };
}

function mountPantheonLogo(root) {
  if (root.dataset.pantheonLogoMounted === "true") return;
  root.dataset.pantheonLogoMounted = "true";

  const canvas = root.querySelector("[data-pantheon-logo-canvas]");
  const ctx = canvas?.getContext("2d", { alpha: true });
  if (!canvas || !ctx) return;

  const runes = createRunes(Number(root.dataset.runeCount) || DEFAULT_RUNE_COUNT);
  const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  let prefersReducedMotion = mediaQuery.matches;
  let isInView = false;
  let isPageVisible = !document.hidden;
  let frameId = null;
  let lastTime = performance.now();
  let canvasSize = setupCanvas(canvas, ctx);

  const updatePausedClass = () => {
    root.classList.toggle("is-paused", !shouldAnimate());
    root.classList.toggle("is-reduced-motion", prefersReducedMotion);
  };

  const shouldAnimate = () => isInView && isPageVisible && !prefersReducedMotion;

  const stop = () => {
    if (frameId) cancelAnimationFrame(frameId);
    frameId = null;
    ctx.clearRect(0, 0, canvasSize.width, canvasSize.height);
    updatePausedClass();
  };

  const draw = (now) => {
    if (!shouldAnimate()) {
      stop();
      return;
    }

    const delta = Math.min(now - lastTime, 48);
    lastTime = now;
    const { width, height } = canvasSize;

    ctx.clearRect(0, 0, width, height);
    ctx.globalCompositeOperation = "screen";

    for (const rune of runes) {
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
    frameId = requestAnimationFrame(draw);
  };

  const start = () => {
    updatePausedClass();
    if (!shouldAnimate() || frameId) return;
    lastTime = performance.now();
    frameId = requestAnimationFrame(draw);
  };

  const resize = () => {
    canvasSize = setupCanvas(canvas, ctx);
    if (!shouldAnimate()) ctx.clearRect(0, 0, canvasSize.width, canvasSize.height);
  };

  const observer = new IntersectionObserver(
    ([entry]) => {
      isInView = entry.isIntersecting;
      if (shouldAnimate()) start();
      else stop();
    },
    { threshold: 0.1 },
  );

  const resizeObserver = new ResizeObserver(resize);
  const handleVisibilityChange = () => {
    isPageVisible = !document.hidden;
    if (shouldAnimate()) start();
    else stop();
  };
  const handleMotionChange = (event) => {
    prefersReducedMotion = event.matches;
    if (shouldAnimate()) start();
    else stop();
  };

  observer.observe(root);
  resizeObserver.observe(root);
  document.addEventListener("visibilitychange", handleVisibilityChange);
  if (mediaQuery.addEventListener) mediaQuery.addEventListener("change", handleMotionChange);
  else mediaQuery.addListener(handleMotionChange);

  updatePausedClass();
}

export function initPantheonAnimatedLogos(scope = document) {
  scope.querySelectorAll("[data-pantheon-animated-logo]").forEach(mountPantheonLogo);
}
