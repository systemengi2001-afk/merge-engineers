const services = [
  { no: '01', title: 'Webサイト制作', sub: 'WEB DESIGN / DEVELOPMENT', text: 'コーポレートサイト、店舗サイト、採用サイトまで。目的整理・情報設計・デザイン・実装を一貫して対応します。', tags: ['コーポレート', '店舗サイト', '採用サイト'] },
  { no: '02', title: 'LP制作', sub: 'LANDING PAGE', text: '商品やサービスの魅力を伝え、問い合わせ・申込みにつながる1ページを設計します。', tags: ['サービスLP', '商品LP', 'キャンペーン'] },
  { no: '03', title: 'Web開発・自動化', sub: 'SYSTEM / AUTOMATION', text: '予約、顧客管理、社内ツール、Google Apps Scriptなど、業務に合う仕組みをつくります。', tags: ['Webアプリ', 'GAS', 'API連携'] },
  { no: '04', title: '改修・運用支援', sub: 'SUPPORT / IMPROVEMENT', text: '既存サイトの修正、スマホ対応、機能追加、表示改善など、必要な部分から柔軟に対応します。', tags: ['保守・運用', '機能追加', 'レスポンシブ'] },
];

const works = [
  { no: '01', title: 'Beauty / Inner Care LP', type: 'LANDING PAGE', text: '美容・インナーケア商材を想定し、高級感と読みやすさを両立した営業用LP。', role: 'PLANNING / UI / DEVELOPMENT' },
  { no: '02', title: 'Service Promotion LP', type: 'LANDING PAGE', text: '異なる業種にも展開できるよう、訴求・導線・CTA設計まで含めて制作した営業用サンプル。', role: 'DESIGN / FRONTEND' },
  { no: '03', title: 'Original Web Product', type: 'WEB PRODUCT', text: '業務課題を整理し、操作性と実装の両方を意識して設計したオリジナルWebプロダクト。', role: 'PLANNING / UI / DEVELOPMENT' },
];

const workflow = [
  { no: '01', title: 'CONTACT', text: 'まずは課題や作りたいものを聞かせてください。要件が固まっていなくても大丈夫です。' },
  { no: '02', title: 'HEARING', text: '目的・予算・納期・必要な機能を整理し、制作の方向性を合わせます。' },
  { no: '03', title: 'PROPOSAL', text: '構成・進め方・お見積もりをご提案します。' },
  { no: '04', title: 'DESIGN / DEVELOPMENT', text: '途中段階から共有し、認識を合わせながら制作します。' },
  { no: '05', title: 'REVIEW', text: '確認・修正を行い、公開に向けて最終調整します。' },
  { no: '06', title: 'LAUNCH', text: '公開・納品後の改修や運用相談にも対応します。' },
];

const faqs = [
  ['まだ要件が固まっていません。相談できますか？', 'もちろんです。「何を作ればよいか」から一緒に整理します。課題や実現したいことだけをお聞かせください。'],
  ['原稿や写真がなくても依頼できますか？', 'はい。必要な素材を整理し、準備方法も含めてご相談いただけます。'],
  ['小規模な修正だけでも依頼できますか？', 'はい。既存サイトの部分修正、機能追加、スマホ対応、原因調査などにも柔軟に対応します。'],
  ['費用や期間はどのように決まりますか？', '内容・規模・希望納期を伺ったうえで、作業範囲とお見積もりをご提示します。相談とお見積もりは無料です。'],
  ['遠方からでも依頼できますか？', 'はい。オンラインでの打ち合わせと進行に対応しています。地域を問わずご相談いただけます。'],
  ['公開後の修正や運用もお願いできますか？', 'はい。更新・改修・機能追加など、公開後も必要な形で継続支援できます。'],
];

export default function Home() {
  const assetPath = process.env.NEXT_PUBLIC_BASE_PATH ?? '';

  return (
    <main id="top">
      <nav className="nav shell">
        <a className="brand" href="#top" aria-label="MeRGe トップへ">MeRGe<span>.</span></a>
        <div className="navLinks"><a href="#works">WORKS</a><a href="#services">SERVICES</a><a href="#about">ABOUT</a><a href="#team">TEAM</a></div>
        <a className="navCta" href="#contact">制作について相談する <span>↗</span></a>
      </nav>

      <section className="hero shell">
        <div className="heroBackdrop" aria-hidden="true"><img src={`${assetPath}/hero-studio.webp`} alt="" width="1536" height="1024" loading="eager" decoding="async" /></div>
        <div className="heroCopy">
          <p className="eyebrow"><span /> WEB DESIGN / DEVELOPMENT</p>
          <h1>伝わる設計を、<br /><em>使われるWebへ。</em></h1>
          <p className="lead">ホームページ・LP・Webシステムを、企画から実装まで。<br />二人の視点で、相談しやすく、動きやすい制作を。</p>
          <div className="heroActions"><a className="primary" href="#contact">制作について相談する <span>→</span></a><a className="textLink" href="#works">制作実績を見る ↓</a></div>
          <div className="heroMeta"><div><b>02</b><span>MEMBERS</span></div><div><b>01</b><span>TEAM</span></div><div><b>∞</b><span>POSSIBILITIES</span></div></div>
        </div>
        <p className="heroMediaNote"><span>01</span> DESIGN / DEVELOPMENT / 2026</p><p className="scrollMark">SCROLL <span>↓</span></p>
      </section>

      <div className="ticker" aria-hidden="true"><div>WEB DESIGN <i>◆</i> LANDING PAGE <i>◆</i> WEB DEVELOPMENT <i>◆</i> AUTOMATION <i>◆</i> WEB DESIGN <i>◆</i> LANDING PAGE <i>◆</i></div></div>

      <section id="works" className="works shell section">
        <div className="sectionHead"><div><p className="sectionTag">SELECTED WORKS</p><span>01 — WHAT WE CREATE</span></div><h2>まず、<br /><em>つくれるものを見る。</em></h2><p>実績の数ではなく、どう考え、どう形にしたかまで伝わる制作を目指しています。</p></div>
        <div className="workGrid">{works.map((work)=><article className="workCard" key={work.no}><div className="workVisual"><span>{work.no}</span><b>{work.type}</b></div><div className="workBody"><p>{work.role}</p><h3>{work.title}</h3><span>{work.text}</span><a href="#contact">PROJECT DETAILS ↗</a></div></article>)}</div>
      </section>

      <section id="services" className="services section"><div className="shell"><div className="sectionHead"><div><p className="sectionTag">WHAT WE DO</p><span>02 — OUR SERVICES</span></div><h2>必要なものを、<br /><em>必要な形で。</em></h2><p>サイト制作から開発・改修まで、目的に合わせて柔軟に対応します。</p></div><div className="serviceList">{services.map((s)=><article key={s.no}><div className="serviceNo">{s.no}</div><div><p className="serviceSub">{s.sub}</p><h3>{s.title}</h3></div><div><p>{s.text}</p><div className="tags">{s.tags.map(tag=><span key={tag}>{tag}</span>)}</div></div><b className="serviceArrow">↗</b></article>)}</div></div></section>

      <section id="about" className="about shell section"><div className="sideTitle"><p className="sectionTag">WHY MERGE</p><span>03 — WHO WE ARE</span></div><div className="aboutBody"><h2>営業・設計・制作・開発を、<br /><em>二人でつなぐ。</em></h2><div className="aboutGrid"><p>MeRGeは、営業・顧客対応と、デザイン・開発を分断せずに進める二人の制作チームです。相談時の意図を制作までつなげ、途中で話が変わりにくい進行を大切にしています。</p><p>「何を作ればいいか分からない」という段階からでも大丈夫です。必要なものを整理し、目的に合う形へ落とし込みます。</p></div><figure className="aboutPhoto"><img src={`${assetPath}/about-worktable.webp`} alt="2人でWeb制作の設計を進めるイメージ" width="1448" height="1086" loading="lazy" decoding="async" /><figcaption><span>DESIGN × DEVELOPMENT</span><b>考えるところから、実装まで。</b></figcaption></figure><div className="strengths"><article><b>01</b><h3>直接話せる</h3><p>つくる側まで意図が届き、伝言ゲームが起きにくい。</p></article><article><b>02</b><h3>二つの視点</h3><p>顧客目線と制作目線の両方から、より良い形を考えます。</p></article><article><b>03</b><h3>柔軟に動ける</h3><p>新規制作から小さな改修まで、必要な範囲で対応します。</p></article></div></div></section>

      <section id="team" className="team section"><div className="shell"><div className="sectionHead"><div><p className="sectionTag">TEAM</p><span>04 — TWO PEOPLE, ONE TEAM</span></div><h2>役割は分ける。<br /><em>目的はひとつ。</em></h2><p>営業・顧客対応と制作・開発、それぞれの強みを持ち寄って進めます。</p></div><div className="teamGrid"><article><span>01</span><p>DESIGN / DEVELOPMENT</p><h3>Takimoto</h3><ul><li>Web Design</li><li>Frontend Development</li><li>System Development</li><li>Automation</li></ul></article><article><span>02</span><p>SALES / PROJECT COMMUNICATION</p><h3>Matsuyama</h3><ul><li>Client Communication</li><li>Requirement Discovery</li><li>Project Coordination</li><li>Sales</li></ul></article></div></div></section>

      <section id="process" className="process section"><div className="shell"><div className="sectionHead"><div><p className="sectionTag">HOW WE WORK</p><span>05 — OUR PROCESS</span></div><h2>わかりやすく、<br /><em>同じ方向を向いて。</em></h2><p>専門用語に頼りすぎず、途中経過を共有しながら進めます。</p></div><figure className="processPhoto"><img src={`${assetPath}/process-wall.webp`} alt="設計資料を確認しながら制作を進めるイメージ" width="1672" height="941" loading="lazy" decoding="async" /><figcaption><span>ONE DIRECTION</span><b>見える状態で、認識を重ねる。</b></figcaption></figure><div className="steps">{workflow.map((step)=><article key={step.no}><span>{step.no}</span><div className="stepDot"/><h3>{step.title}</h3><p>{step.text}</p></article>)}</div></div></section>

      <section className="price shell section"><div className="sectionHead"><div><p className="sectionTag">PRICE GUIDE</p><span>06 — ESTIMATE</span></div><h2>まずは、<br /><em>相談から。</em></h2><p>内容に合わせて個別にお見積もりします。相談・見積もりは無料です。</p></div><div className="priceGrid"><article><p>LANDING PAGE</p><h3>LP制作</h3><span>内容に応じて個別見積</span></article><article><p>WEBSITE</p><h3>Webサイト制作</h3><span>内容に応じて個別見積</span></article><article><p>SUPPORT</p><h3>改修・運用</h3><span>小規模なご相談も対応</span></article></div></section>

      <section id="faq" className="faq shell section"><div className="sideTitle"><p className="sectionTag">FAQ</p><span>07 — QUESTIONS</span></div><div><h2>依頼前の、<br /><em>よくある質問。</em></h2><div className="faqList">{faqs.map(([q,a],i)=><details key={q}><summary><span>{String(i+1).padStart(2,'0')}</span>{q}<b>＋</b></summary><p>{a}</p></details>)}</div></div></section>

      <section id="contact" className="contact"><div className="contactGlow"/><div className="shell contactInner"><p className="eyebrow"><span /> LET&apos;S CREATE SOMETHING</p><h2>その「できたらいいな」を、<br /><em>聞かせてください。</em></h2><p className="contactLead">まとまっていなくても大丈夫です。課題やアイデアを伺い、最初の一歩を一緒に考えます。</p><a className="mail" href="mailto:systemengi2001@gmail.com?subject=MeRGe%20制作相談"><span>制作について相談する</span><b>systemengi2001@gmail.com</b><i>↗</i></a><small>相談・お見積もりは無料です。内容を確認後、メールでご返信します。</small></div></section>
      <footer className="shell"><a className="brand" href="#top">MeRGe<span>.</span></a><p>Web design, development and automation.<br/>Two people, one team.</p><div><a href="#works">WORKS</a><a href="#services">SERVICES</a><a href="#team">TEAM</a><a href="#contact">CONTACT</a></div><small>© 2026 MeRGe</small></footer>
    </main>
  );
}
