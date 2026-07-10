const tabs = [...document.querySelectorAll("[data-scene]")];
const panels = [...document.querySelectorAll("[data-scene-panel]")];

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    const scene = tab.dataset.scene;
    tabs.forEach((item) => item.classList.toggle("active", item === tab));
    const panel = panels.find((item) => item.dataset.scenePanel === scene);
    panel?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
  });
});

const canvas = document.querySelector("#starfield");
const ctx = canvas.getContext("2d");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let stars = [];
let width = 0;
let height = 0;
let animationId = 0;

function resize() {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  width = window.innerWidth;
  height = window.innerHeight;
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const count = Math.min(150, Math.floor((width * height) / 9800));
  stars = Array.from({ length: count }, (_, index) => ({
    x: Math.random() * width,
    y: Math.random() * height,
    r: 0.5 + Math.random() * 1.6,
    speed: 0.08 + Math.random() * 0.28,
    phase: index * 0.37,
  }));
}

function draw(time = 0) {
  ctx.clearRect(0, 0, width, height);
  stars.forEach((star) => {
    const pulse = 0.35 + Math.abs(Math.sin(time * 0.001 + star.phase)) * 0.65;
    ctx.beginPath();
    ctx.fillStyle = `rgba(246, 241, 232, ${0.22 + pulse * 0.5})`;
    ctx.arc(star.x, star.y, star.r * pulse, 0, Math.PI * 2);
    ctx.fill();
    if (!reducedMotion) {
      star.y += star.speed;
      if (star.y > height + 4) {
        star.y = -4;
        star.x = Math.random() * width;
      }
    }
  });
  if (!reducedMotion) {
    animationId = requestAnimationFrame(draw);
  }
}

window.addEventListener("resize", resize);
resize();
draw();

window.addEventListener("pagehide", () => cancelAnimationFrame(animationId));
