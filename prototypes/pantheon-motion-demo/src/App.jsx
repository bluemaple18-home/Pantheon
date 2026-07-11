import PantheonMotionVisual from "./components/PantheonMotionVisual.jsx";

const layers = [
  {
    number: "01",
    title: "影片核心",
    copy: "讓瀏覽器解碼完整的緞帶、材質與遮擋關係，保留影片級細節。",
  },
  {
    number: "02",
    title: "CSS 空間層",
    copy: "以 transform 與 blend mode 疊加環線、光暈和游標視差，不建立昂貴渲染迴圈。",
  },
  {
    number: "03",
    title: "智慧降級",
    copy: "離開視窗、背景分頁、減少動態或省流量模式下，自動切換成靜態 poster。",
  },
];

export default function App() {
  return (
    <main>
      <header className="site-header">
        <a className="brand" href="#top" aria-label="Pantheon 首頁">
          <span className="brand-mark" aria-hidden="true">✦</span>
          <span>PANTHEON</span>
        </a>
        <span className="header-meta">Motion study · 01</span>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="eyebrow">Oracle interface · Motion study</p>
          <h1>
            讓指引，
            <span>以光與軌跡顯形。</span>
          </h1>
          <p className="hero-lede">
            五條生命維度交織成持續運行的神諭核心。複雜光影交給影片，互動與空間感交給瀏覽器，保留質感，也守住效能。
          </p>
          <a className="hero-link" href="#architecture">
            查看渲染結構
            <span aria-hidden="true">↘</span>
          </a>
        </div>

        <div className="hero-visual-column">
          <PantheonMotionVisual />
          <div className="visual-meta" aria-hidden="true">
            <span>Five dimensions</span>
            <span>Loop · 10 sec</span>
          </div>
        </div>
      </section>

      <section className="architecture" id="architecture" aria-labelledby="architecture-title">
        <div className="section-heading">
          <p className="eyebrow">Rendering architecture</p>
          <h2 id="architecture-title">一個主效果，三層責任。</h2>
        </div>
        <div className="layer-list">
          {layers.map((layer) => (
            <article className="layer-item" key={layer.number}>
              <span className="layer-number">{layer.number}</span>
              <h3>{layer.title}</h3>
              <p>{layer.copy}</p>
            </article>
          ))}
        </div>
      </section>

      <footer>
        <span>Pantheon Motion Prototype</span>
        <span>React · Video · CSS</span>
      </footer>
    </main>
  );
}
