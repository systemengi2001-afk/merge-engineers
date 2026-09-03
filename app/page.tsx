const services = [
  { no: '01', title: 'Webサイト制作', sub: 'WEB DESIGN / DEVELOPMENT', text: '目的整理、情報設計、デザイン、実装まで一貫対応。見た目だけでなく、問い合わせにつながる導線を設計します。', tags: ['コーポレートサイト', 'LP', '採用サイト'], href: '#works', action: '制作実績を見る' },
  { no: '02', title: 'Webシステム開発', sub: 'SYSTEM / APPLICATION', text: '予約・顧客管理・社内ツールなど、現場に合う仕組みをオーダーメイドで。複雑な業務をシンプルにします。', tags: ['業務システム', 'Webアプリ', 'API連携'], href: '#contact', action: '相談する' },
  { no: '03', title: '改善・技術支援', sub: 'SUPPORT / IMPROVEMENT', text: '既存サイトの改修、機能追加、表示速度の改善、運用相談にも対応。必要な部分だけでも気軽に頼めます。', tags: ['保守・運用', '機能追加', '技術相談'], href: '#contact', action: '相談する' },
];

const process = [
  { no: '01', title: 'まず、聞く。', text: '決まっていないことも含めて、目的や課題を丁寧に伺います。相談段階でも構いません。' },
  { no: '02', title: '一緒に、考える。', text: '予算や納期を踏まえ、やるべきことを整理。無理のない進め方をご提案します。' },
  { no: '03', title: '早く、見せる。', text: '完成まで待たせず、途中の状態から共有。認識を合わせながら形にします。' },
  { no: '04', title: '育てていく。', text: '公開・納品がゴールではありません。反応を見ながら継続的な改善にも伴走します。' },
];

const portfolio = [
  {
    type: 'ELECTRICAL COMPANY',
    title: '光栄電設株式会社',
    text: '採用と法人問い合わせの獲得を想定した、電気工事会社向けコーポレートサイト。事業内容・施工実績・会社案内まで設計したデモです。',
    href: 'https://systemengi2001-afk.github.io/fieldworks-showcase/denki/',
    accent: 'cyan',
    before: ['会社情報が伝わりにくい', '実績が見つけづらい', '採用導線が弱い'],
    after: ['強みを最初に提示', '施工実績を分類して掲載', '応募まで迷わない導線'],
  },
  {
    type: 'HVAC COMPANY',
    title: '蒼空テクノ株式会社',
    text: '技術力と対応領域を伝える、空調設備会社向けコーポレートサイト。施工実績・採用・問い合わせ導線を含むデモです。',
    href: 'https://systemengi2001-afk.github.io/fieldworks-showcase/air/',
    accent: 'orange',
    before: ['対応範囲が不明確', '技術力を訴求できない', '問い合わせ先が分散'],
    after: ['サービスを用途別に整理', '数字と事例で信頼を可視化', '相談窓口を一本化'],
  },
];

const skills = [
  { category: 'FRONTEND', items: ['HTML', 'CSS', 'JavaScript', 'React'] },
  { category: 'BACKEND', items: ['Python', 'PHP', 'Node.js'] },
  { category: 'CMS / NO CODE', items: ['WordPress', 'STUDIO'] },
  { category: 'DESIGN', items: ['Figma', 'Canva'] },
  { category: 'TOOLS', items: ['GitHub', 'VS Code', 'GitHub Actions'] },
];

const faqs = [
  ['まだ要件が固まっていません。相談できますか？', 'もちろんです。「何を作ればよいか」から一緒に整理します。課題や実現したいことだけをお聞かせください。'],
  ['小規模な修正だけでも依頼できますか？', 'はい。既存サイトの部分修正、機能追加、原因調査など、小さなご相談にも柔軟に対応します。'],
  ['費用や期間はどのように決まりますか？', '内容・規模・希望納期を伺ったうえで、作業範囲とお見積もりをご提示します。相談とお見積もりは無料です。'],
  ['遠方からでも依頼できますか？', 'はい。オンラインでの打ち合わせと進行に対応しています。地域を問わずご相談いただけます。'],
];

export default function Home() {
  return (
    <main id="top">
      <nav className="nav shell">
        <a className="brand" href="#top" aria-label="MeRGe トップへ">MeRGe<span>.</span></a>
        <div className="navLinks"><a href="#about">ABOUT</a><a href="#services">SERVICES</a><a href="#works">WORKS</a><a href="#skills">SKILLS</a><a href="#process">PROCESS</a><a href="#faq">FAQ</a></div>
        <a className="navCta" href="mailto:systemengi2001@gmail.com">無料相談 <span>↗</span></a>
      </nav>
      <div className="mobileNav" aria-label="スマートフォン用ナビゲーション"><a href="#works">WORKS</a><a href="#skills">SKILLS</a><a href="#contact">CONTACT</a></div>

      <section className="hero shell">
        <div className="heroCopy">
          <p className="eyebrow"><span /> TWO ENGINEERS, ONE TEAM.</p>
          <h1>想いを、<br /><em>動くカタチ</em>に。</h1>
          <p className="lead">ふたりのエンジニアが、あなたの要望にまっすぐ向き合う。<br />Web制作からシステム開発まで、欲しいものを一緒につくります。</p>
          <div className="heroActions"><a className="primary" href="mailto:systemengi2001@gmail.com">プロジェクトを相談する <span>→</span></a><a className="textLink" href="#services">できることを見る ↓</a></div>
          <div className="heroMeta"><div><b>02</b><span>ENGINEERS</span></div><div><b>01</b><span>POINT OF CONTACT</span></div><div><b>∞</b><span>POSSIBILITIES</span></div></div>
        </div>
        <div className="art" aria-hidden="true"><div className="gridPlane"/><div className="orb"/><i className="shard s1"/><i className="shard s2"/><i className="shard s3"/><i className="shard s4"/><i className="shard s5"/><div className="codeCard"><span>DESIGN</span><strong>×</strong><span>DEVELOP</span></div><p className="artLabel">MERGE / DIGITAL CRAFT / 2026</p></div>
        <p className="scrollMark">SCROLL <span>↓</span></p>
      </section>

      <div className="ticker" aria-hidden="true"><div>WEB DESIGN <i>◆</i> SYSTEM DEVELOPMENT <i>◆</i> CREATIVE TECHNOLOGY <i>◆</i> FLEXIBLE SUPPORT <i>◆</i> WEB DESIGN <i>◆</i> SYSTEM DEVELOPMENT <i>◆</i></div></div>

      <section id="about" className="about shell section">
        <div className="sideTitle"><p className="sectionTag">ABOUT US</p><span>01 — WHO WE ARE</span></div>
        <div className="aboutBody"><h2>大きすぎないチームだから、<br /><em>距離が近い。</em></h2><div className="aboutGrid"><p>私たちは、二人で活動するフリーランスエンジニアチームです。相談から制作、公開後まで担当者が変わらず、意図や背景を理解したままプロジェクトを進めます。</p><p>「これってできる？」という段階から歓迎です。技術の話を分かりやすく翻訳し、必要なものを見極め、無駄なく形にします。</p></div><div className="strengths"><article><b>01</b><h3>直接話せる</h3><p>つくる本人と話せるから、伝言ゲームがありません。</p></article><article><b>02</b><h3>二つの視点</h3><p>一人で抱え込まず、二人で考え、品質を確かめます。</p></article><article><b>03</b><h3>柔軟に動ける</h3><p>小さな改修から継続支援まで、必要な形で関わります。</p></article></div></div>
      </section>

      <section id="services" className="services section">
        <div className="shell"><div className="sectionHead"><div><p className="sectionTag">WHAT WE DO</p><span>02 — OUR SERVICES</span></div><h2>要望に、<br /><em>境界線を引かない。</em></h2><p>「Webサイトだけ」「システムだけ」と区切らず、目的の達成に必要な方法を一緒に考えます。</p></div>
        <div className="serviceList">{services.map((s)=><a className="serviceItem" href={s.href} key={s.no}><div className="serviceNo">{s.no}</div><div><p className="serviceSub">{s.sub}</p><h3>{s.title}</h3></div><div><p>{s.text}</p><div className="tags">{s.tags.map(tag=><span key={tag}>{tag}</span>)}</div><span className="serviceAction">{s.action}</span></div><b className="serviceArrow">↗</b></a>)}</div></div>
      </section>

      <section className="scope shell section">
        <div className="scopeIntro"><p className="sectionTag">SCOPE</p><h2>こんなご相談に<br />対応できます。</h2><p>ここにない内容も、まずはお問い合わせください。</p></div>
        <div className="scopeCloud">{['新規サイト制作','サイトリニューアル','ランディングページ','予約システム','顧客管理ツール','業務の自動化','フォーム改善','スマホ対応','機能追加','表示速度改善','保守・運用','技術相談'].map((item,i)=><span className={`chip c${i%4}`} key={item}>{item}<b>+</b></span>)}</div>
      </section>

      <section id="works" className="portfolio section">
        <div className="shell">
          <div className="sectionHead"><div><p className="sectionTag">SELECTED WORKS</p><span>03 — PORTFOLIO</span></div><h2>業界を理解し、<br /><em>伝わる形へ。</em></h2><p>企画・情報設計・デザイン・実装まで担当した制作例です。各サイトは別タブでご覧いただけます。</p></div>
          <div className="workGrid">{portfolio.map((work, index) => <article className={`workCard ${work.accent}`} key={work.title}><a className="workMainLink" href={work.href} target="_blank" rel="noreferrer"><div className="workVisual"><span>0{index + 1}</span><b>{work.type}</b><i aria-hidden="true" /></div><div className="workCopy"><p>{work.type}</p><h3>{work.title}</h3><span>{work.text}</span></div></a><div className="beforeAfter"><div><b>BEFORE</b>{work.before.map(item => <span key={item}>— {item}</span>)}</div><i>→</i><div><b>AFTER</b>{work.after.map(item => <span key={item}>＋ {item}</span>)}</div></div><a className="workCta" href={work.href} target="_blank" rel="noreferrer">完成サイトを見る <b>↗</b></a></article>)}</div>
          <p className="demoNote">※ ポートフォリオ内の会社名・住所・実績などは、制作例として作成した架空情報です。</p>
        </div>
      </section>

      <section id="skills" className="skills shell section">
        <div className="sideTitle"><p className="sectionTag">TECH SKILLS</p><span>04 — CAPABILITIES</span></div>
        <div className="skillsBody"><h2>つくるための技術を、<br /><em>きちんと持っている。</em></h2><p className="skillsLead">デザインだけ、実装だけではなく、公開・運用までつながる技術構成で対応します。</p><div className="skillGrid">{skills.map((skill, index)=><article key={skill.category}><span>0{index + 1}</span><p>{skill.category}</p><div>{skill.items.map(item=><b key={item}>{item}</b>)}</div></article>)}</div></div>
      </section>

      <section id="process" className="process section">
        <div className="shell"><div className="sectionHead"><div><p className="sectionTag">HOW WE WORK</p><span>05 — OUR PROCESS</span></div><h2>わかりやすく、<br /><em>同じ方向を向いて。</em></h2><p>専門用語に頼らず、途中経過をこまめに共有。初めてのご依頼でも不安なく進められます。</p></div>
        <div className="steps">{process.map((step)=><article key={step.no}><span>{step.no}</span><div className="stepDot"/><h3>{step.title}</h3><p>{step.text}</p></article>)}</div></div>
      </section>

      <section id="faq" className="faq shell section">
        <div className="sideTitle"><p className="sectionTag">FAQ</p><span>06 — QUESTIONS</span></div>
        <div><h2>依頼前の、<br /><em>よくある質問。</em></h2><div className="faqList">{faqs.map(([q,a],i)=><details key={q}><summary><span>{String(i+1).padStart(2,'0')}</span>{q}<b>＋</b></summary><p>{a}</p></details>)}</div></div>
      </section>

      <section className="connect shell section"><div><p className="sectionTag">CONNECT</p><h2>活動と実績を、<br />少しずつ発信。</h2></div><div className="socialList"><a href="https://github.com/systemengi2001-afk" target="_blank" rel="noreferrer"><span>GitHub</span><b>コードと制作物を見る ↗</b></a>{['CrowdWorks','ココナラ','X'].map(name=><div className="socialSoon" key={name}><span>{name}</span><b>COMING SOON</b></div>)}</div></section>
      <section id="contact" className="contact"><div className="contactGlow"/><div className="shell contactInner"><p className="eyebrow"><span /> LET&apos;S CREATE SOMETHING</p><h2>その「できたらいいな」を、<br /><em>聞かせてください。</em></h2><p className="contactLead">まとまっていなくても大丈夫です。課題やアイデアを伺い、最初の一歩を一緒に考えます。</p><a className="mail" href="mailto:systemengi2001@gmail.com"><span>メールで無料相談</span><b>systemengi2001@gmail.com</b><i>↗</i></a><small>通常、内容を確認後にメールでご返信します。</small></div></section>
      <footer className="shell"><a className="brand" href="#top">MeRGe<span>.</span></a><p>Two freelance engineers.<br/>Designing and developing in Japan.</p><div><a href="#services">SERVICES</a><a href="#works">WORKS</a><a href="#skills">SKILLS</a><a href="#process">PROCESS</a><a href="#faq">FAQ</a></div><small>© 2026 MeRGe</small></footer>
    </main>
  );
}

