import type { Metadata } from 'next';
import Link from 'next/link';
import { articles, SITE } from '../../lib/affiliateData';
import styles from './styles.module.css';

export const metadata: Metadata = {
  title: `AI・SaaS比較 | ${SITE.name}`,
  description: SITE.description,
  alternates: { canonical: `${SITE.baseUrl}/` },
  openGraph: {
    title: `AI・SaaS比較 | ${SITE.name}`,
    description: SITE.description,
    url: `${SITE.baseUrl}/`,
    type: 'website',
  },
};

export default function AffiliateHome() {
  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <section className={styles.hero}>
          <div className={styles.eyebrow}>AI / SaaS / Automation</div>
          <h1>仕事を減らし、売上につながるツールを選ぶ。</h1>
          <p>{SITE.description}。料金の安さだけではなく、導入で減らせる作業時間と販売導線まで見て比較します。</p>
          <div className={styles.comparison}>
            <div className={styles.mini}><strong>販売導線</strong><span>LP・メール・ファネル</span></div>
            <div className={styles.mini}><strong>講座販売</strong><span>LMS・会員コンテンツ</span></div>
            <div className={styles.mini}><strong>Web運用</strong><span>WordPress・自動化</span></div>
          </div>
        </section>

        <section className={styles.grid} aria-label="おすすめ記事">
          {articles.map((article) => (
            <Link key={article.slug} className={styles.card} href={`/affiliate/${article.slug}/`}>
              <div className={styles.meta}>
                <span className={styles.pill}>{article.service}</span>
                <span className={styles.pill}>{article.intent}</span>
              </div>
              <h2>{article.title}</h2>
              <p>{article.description}</p>
              <div className={styles.link}>記事を読む →</div>
            </Link>
          ))}
        </section>

        <div className={styles.notice}>
          当サイトにはアフィリエイトリンクを含む記事があります。掲載順位は報酬額だけで決めず、用途・機能・導入負担を基準に整理します。
        </div>
        <footer className={styles.footer}>© 2026 {SITE.name}</footer>
      </div>
    </main>
  );
}
