import type { Metadata } from 'next';
import Link from 'next/link';
import { articles, SITE } from '../../lib/affiliateData';
import { extraArticles } from '../../lib/affiliateExtraData';
import { highValueArticles } from '../../lib/affiliateHighValueData';
import styles from './styles.module.css';

const allArticles = [...articles, ...extraArticles, ...highValueArticles];

const monetizationOrder = [
  'systeme-io-review',
  'systeme-io-pricing',
  'systeme-io-annual-plan',
  'systeme-io-free-plan',
  'systeme-io-disadvantages',
  'systeme-io-vs-thinkific',
  'systeme-io-alternatives',
  'systeme-io-vs-kajabi',
  'systeme-io-vs-clickfunnels',
  'online-course-platform-free',
  'systeme-io-how-to-start',
  'thinkific-pricing',
  'thinkific-vs-systeme-io-for-course-creators',
  'thinkific-review',
  'kinsta-pricing-for-wordpress',
  'kinsta-for-web-agencies',
  'kinsta-review',
  'marketing-tools-for-small-business',
];

const rankedArticles = monetizationOrder.map((slug) => allArticles.find((article) => article.slug === slug)).filter((article): article is (typeof allArticles)[number] => Boolean(article));
const unrankedArticles = allArticles.filter((article) => !monetizationOrder.includes(article.slug));
const displayArticles = [...rankedArticles, ...unrankedArticles];

export const metadata: Metadata = { title: `AI・SaaS比較 | ${SITE.name}`, description: SITE.description, alternates: { canonical: `${SITE.baseUrl}/` }, openGraph: { title: `AI・SaaS比較 | ${SITE.name}`, description: SITE.description, url: `${SITE.baseUrl}/`, type: 'website' } };

export default function AffiliateHome() {
  const featured = allArticles.find((article) => article.slug === 'systeme-io-review');
  return (
    <main className={styles.page}><div className={styles.shell}>
      <section className={styles.hero}><div className={styles.eyebrow}>AI / SaaS / Automation</div><h1>迷う時間を減らして、使える道具だけ選ぶ。</h1><p>副業・Web制作・小規模事業で、本当に導入候補になるAI・SaaSを比較します。機能一覧ではなく「誰に向くか」「何が減るか」「結局どれを選ぶか」まで短く判断できるように整理します。</p><div className={styles.comparison}><div className={styles.mini}><strong>販売導線</strong><span>LP・メール・ファネル</span></div><div className={styles.mini}><strong>講座販売</strong><span>LMS・会員コンテンツ</span></div><div className={styles.mini}><strong>Web運用</strong><span>WordPress・自動化</span></div></div></section>
      {featured && <section className={styles.featured} aria-label="最優先のおすすめ"><div className={styles.featuredLabel}>EDITOR&apos;S PICK / まず見るならこれ</div><div className={styles.featuredGrid}><div><p className={styles.featuredKicker}>販売導線を1つにまとめたい人向け</p><h2>LP、メール、講座、販売導線。<br />バラバラに契約する前に。</h2><p>systeme.ioは、複数ツールをまたぐ手間を減らしたい個人事業主・副業ユーザーの有力候補です。無料プランはカード不要。まず触ってから、必要になった時だけ有料化する判断ができます。</p></div><div className={styles.featuredAction}><a href={featured.affiliateUrl} target="_blank" rel="nofollow sponsored noopener noreferrer">カード不要で無料プランを試す ↗</a><Link href="/affiliate/systeme-io-pricing/">無料と有料の違いを確認する →</Link><Link href="/affiliate/systeme-io-annual-plan/">年払い・3プランを比較する →</Link><small>※ 最初のボタンは承認済みアフィリエイトリンクです。料金・仕様は契約前に公式画面をご確認ください。</small></div></div></section>}
      <div className={styles.sectionTitle}><span>GUIDES</span><h2>成約に近い順に読む</h2></div><section className={styles.grid} aria-label="おすすめ記事">{displayArticles.map((article) => <Link key={article.slug} className={styles.card} href={`/affiliate/${article.slug}/`}><div className={styles.meta}><span className={styles.pill}>{article.service}</span><span className={styles.pill}>{article.intent}</span></div><h2>{article.title}</h2><p>{article.description}</p><div className={styles.link}>判断材料を見る →</div></Link>)}</section>
      <div className={styles.notice}>当サイトにはアフィリエイトリンクを含む記事があります。報酬の有無にかかわらず、向いていないケースや注意点も記載します。料金・仕様は契約前に公式サイトで最新情報をご確認ください。</div><footer className={styles.footer}><div><Link href="/affiliate/about/">運営方針</Link> / <Link href="/affiliate/methodology/">比較方法</Link> / <Link href="/affiliate/policy/">広告・編集ポリシー</Link> / <Link href="/affiliate/privacy/">プライバシー</Link></div><div>© 2026 {SITE.name}</div></footer>
    </div></main>
  );
}
