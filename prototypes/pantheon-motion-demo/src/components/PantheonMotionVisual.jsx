import { useEffect, useRef, useState } from "react";
import styles from "./PantheonMotionVisual.module.css";

const orbitGlyphs = [
  { angle: -88, type: "asterisk", tone: "gold" },
  { angle: -68, type: "frame", tone: "ink" },
  { angle: -49, type: "fourPoint", tone: "gold" },
  { angle: -31, type: "corner", tone: "ink" },
  { angle: -11, type: "asterisk", tone: "wine" },
  { angle: 9, type: "frame", tone: "ink" },
  { angle: 29, type: "fourPoint", tone: "gold" },
  { angle: 48, type: "corner", tone: "ink" },
  { angle: 68, type: "asterisk", tone: "teal" },
  { angle: 88, type: "frame", tone: "gold" },
  { angle: 109, type: "fourPoint", tone: "ink" },
  { angle: 129, type: "corner", tone: "ink" },
  { angle: 149, type: "asterisk", tone: "wine" },
  { angle: 169, type: "frame", tone: "gold" },
  { angle: 190, type: "fourPoint", tone: "ink" },
  { angle: 210, type: "corner", tone: "teal" },
  { angle: 230, type: "asterisk", tone: "ink" },
  { angle: 250, type: "frame", tone: "gold" },
];

const middleGlyphs = [
  { angle: -79, type: "kite", tone: "ink" },
  { angle: -48, type: "bowtie", tone: "gold" },
  { angle: -17, type: "slashDiamond", tone: "teal" },
  { angle: 13, type: "needle", tone: "wine" },
  { angle: 45, type: "kite", tone: "gold" },
  { angle: 77, type: "bowtie", tone: "ink" },
  { angle: 108, type: "slashDiamond", tone: "teal" },
  { angle: 139, type: "needle", tone: "ink" },
  { angle: 170, type: "kite", tone: "wine" },
  { angle: 202, type: "bowtie", tone: "gold" },
  { angle: 233, type: "slashDiamond", tone: "ink" },
  { angle: 264, type: "needle", tone: "gold" },
];

const innerGlyphs = [
  { angle: -91, type: "bead", tone: "teal" },
  { angle: -51, type: "hollowDiamond", tone: "gold" },
  { angle: -11, type: "doubleDiamond", tone: "ink" },
  { angle: 29, type: "linkedBeads", tone: "wine" },
  { angle: 69, type: "bead", tone: "gold" },
  { angle: 109, type: "hollowDiamond", tone: "teal" },
  { angle: 149, type: "doubleDiamond", tone: "ink" },
  { angle: 189, type: "linkedBeads", tone: "gold" },
  { angle: 229, type: "bead", tone: "wine" },
];

function OrbitGlyph({ angle, type, tone, radius }) {
  const radians = (angle * Math.PI) / 180;
  const x = 360 + Math.cos(radians) * radius;
  const y = 432 + Math.sin(radians) * radius;
  const transform = `translate(${x.toFixed(2)} ${y.toFixed(2)}) rotate(${angle + 45})`;

  return (
    <g
      className={`${styles.orbitGlyph} ${styles[tone]}`}
      data-orbit-glyph
      data-glyph-type={type}
      transform={transform}
    >
      {type === "asterisk" && <path d="M -9 0 H 9 M 0 -9 V 9 M -6 -6 L 6 6 M 6 -6 L -6 6" />}
      {type === "frame" && <path d="M -8 -8 H 8 V 8 H -8 Z M -8 3 L 3 -8" />}
      {type === "fourPoint" && <path d="M 0 -10 L 3 -3 L 10 0 L 3 3 L 0 10 L -3 3 L -10 0 L -3 -3 Z" />}
      {type === "corner" && <path d="M -8 -8 H 8 V 8 M -8 -8 V 2 H 2" />}

      {type === "kite" && <path d="M -10 3 L 2 -7 L 10 -2 L -2 7 Z" />}
      {type === "bowtie" && <path d="M -9 -6 L 0 0 L -9 6 Z M 9 -6 L 0 0 L 9 6 Z" />}
      {type === "slashDiamond" && <path d="M 0 -9 L 8 0 L 0 9 L -8 0 Z M -7 6 L 7 -6" />}
      {type === "needle" && <path d="M -11 2 L 5 -5 L 11 -2 L -5 5 Z M -7 7 L 7 -7" />}

      {type === "bead" && <circle r="5" />}
      {type === "hollowDiamond" && <path d="M 0 -9 L 8 0 L 0 9 L -8 0 Z" />}
      {type === "doubleDiamond" && <path d="M 0 -10 L 9 0 L 0 10 L -9 0 Z M 0 -4 L 4 0 L 0 4 L -4 0 Z" />}
      {type === "linkedBeads" && <path d="M -10 0 H 10 M -6 -4 L -2 0 L -6 4 L -10 0 Z M 6 -4 L 10 0 L 6 4 L 2 0 Z" />}
    </g>
  );
}

export default function PantheonMotionVisual() {
  const visualRef = useRef(null);
  const videoRef = useRef(null);
  const pointerFrameRef = useRef(0);
  const [reducedMotion, setReducedMotion] = useState(
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const [playbackFailed, setPlaybackFailed] = useState(false);
  const [videoReady, setVideoReady] = useState(false);
  const saveData = navigator.connection?.saveData === true;
  const staticMode = reducedMotion || saveData || playbackFailed;

  useEffect(() => {
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const handleMotionChange = (event) => setReducedMotion(event.matches);
    motionQuery.addEventListener("change", handleMotionChange);
    return () => motionQuery.removeEventListener("change", handleMotionChange);
  }, []);

  useEffect(() => {
    const visual = visualRef.current;
    const video = videoRef.current;
    if (!visual || !video || staticMode) return undefined;

    let isInView = false;

    const syncPlayback = () => {
      const shouldPause = document.hidden || !isInView;

      if (shouldPause) {
        video.pause();
        return;
      }

      video.play().catch(() => setPlaybackFailed(true));
    };

    const observer = new IntersectionObserver(
      ([entry]) => {
        isInView = entry.isIntersecting;
        syncPlayback();
      },
      { rootMargin: "120px", threshold: 0.12 },
    );

    observer.observe(visual);
    document.addEventListener("visibilitychange", syncPlayback);

    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", syncPlayback);
      video.pause();
    };
  }, [staticMode]);

  useEffect(() => {
    const visual = visualRef.current;
    if (!visual || staticMode) return undefined;

    const updatePointer = (event) => {
      cancelAnimationFrame(pointerFrameRef.current);
      pointerFrameRef.current = requestAnimationFrame(() => {
        const bounds = visual.getBoundingClientRect();
        const x = (event.clientX - bounds.left) / bounds.width - 0.5;
        const y = (event.clientY - bounds.top) / bounds.height - 0.5;
        visual.style.setProperty("--tilt-x", `${(-y * 4).toFixed(2)}deg`);
        visual.style.setProperty("--tilt-y", `${(x * 5).toFixed(2)}deg`);
        visual.style.setProperty("--shift-x", `${(x * 8).toFixed(2)}px`);
        visual.style.setProperty("--shift-y", `${(y * 8).toFixed(2)}px`);
      });
    };

    const resetPointer = () => {
      visual.style.setProperty("--tilt-x", "0deg");
      visual.style.setProperty("--tilt-y", "0deg");
      visual.style.setProperty("--shift-x", "0px");
      visual.style.setProperty("--shift-y", "0px");
    };

    visual.addEventListener("pointermove", updatePointer);
    visual.addEventListener("pointerleave", resetPointer);

    return () => {
      visual.removeEventListener("pointermove", updatePointer);
      visual.removeEventListener("pointerleave", resetPointer);
      cancelAnimationFrame(pointerFrameRef.current);
    };
  }, [staticMode]);

  return (
    <div
      ref={visualRef}
      className={`${styles.visual} ${staticMode ? styles.staticMode : ""}`}
      role="img"
      aria-label="五條彩色符文緞帶圍繞金色核心緩慢旋轉"
    >
      <div className={styles.aura} aria-hidden="true" />

      <div className={styles.mediaFrame}>
        <img
          className={`${styles.poster} ${videoReady && !staticMode ? styles.posterHidden : ""}`}
          src="/pantheon-orb-alpha-poster.webp"
          alt=""
          aria-hidden="true"
          width="720"
          height="864"
          decoding="async"
          fetchPriority="high"
        />
        {!staticMode && (
          <video
            ref={videoRef}
            className={`${styles.video} ${videoReady ? styles.videoReady : ""}`}
            muted
            loop
            playsInline
            preload="metadata"
            width="720"
            height="864"
            disablePictureInPicture
            aria-hidden="true"
            tabIndex="-1"
            onPlaying={() => setVideoReady(true)}
            onError={() => setPlaybackFailed(true)}
          >
            <source src="/pantheon-orb-alpha-v2.webm" type="video/webm" />
          </video>
        )}
      </div>

      <svg
        className={styles.orbitalField}
        data-orbital-field
        viewBox="0 0 720 864"
        aria-hidden="true"
        focusable="false"
      >
        <g className={styles.outerOrbit} data-orbit-layer data-orbit-kind="outer">
          <circle className={`${styles.orbitTrack} ${styles.outerTrack}`} data-orbit-track data-radius="315.62496" cx="360" cy="432" r="315.62496" />
          {orbitGlyphs.map((glyph) => (
            <OrbitGlyph key={`${glyph.angle}-${glyph.type}`} radius={315.62496} {...glyph} />
          ))}
        </g>

        <g className={styles.middleOrbit} data-orbit-layer data-orbit-kind="middle">
          <circle className={`${styles.orbitTrack} ${styles.middleTrack}`} data-orbit-track data-radius="283.06656" cx="360" cy="432" r="283.06656" />
          {middleGlyphs.map((glyph) => (
            <OrbitGlyph key={`${glyph.angle}-${glyph.type}`} radius={283.06656} {...glyph} />
          ))}
        </g>

        <g className={styles.innerOrbit} data-orbit-layer data-orbit-kind="inner">
          <circle className={`${styles.orbitTrack} ${styles.innerTrack}`} data-orbit-track data-radius="250.50816" cx="360" cy="432" r="250.50816" />
          {innerGlyphs.map((glyph) => (
            <OrbitGlyph key={`${glyph.angle}-${glyph.type}`} radius={250.50816} {...glyph} />
          ))}
        </g>

        <g className={styles.microStars}>
          <circle cx="188" cy="168" r="2.3" />
          <circle cx="548" cy="181" r="1.7" />
          <circle cx="659" cy="329" r="2.1" />
          <circle cx="615" cy="673" r="1.8" />
          <circle cx="205" cy="719" r="2.2" />
          <circle cx="73" cy="535" r="1.6" />
          <path d="M 513 112 l 4 8 l 8 4 l -8 4 l -4 8 l -4 -8 l -8 -4 l 8 -4 z" />
          <path d="M 125 655 l 3 6 l 6 3 l -6 3 l -3 6 l -3 -6 l -6 -3 l 6 -3 z" />
        </g>
      </svg>

      <div className={`${styles.node} ${styles.nodeOne}`} aria-hidden="true" />
      <div className={`${styles.node} ${styles.nodeTwo}`} aria-hidden="true" />
      <div className={`${styles.node} ${styles.nodeThree}`} aria-hidden="true" />
    </div>
  );
}
