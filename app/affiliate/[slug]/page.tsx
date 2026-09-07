import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { articles, SITE } from '../../../lib/affiliateData';
import { extraArticles } from '../../../lib/affiliateExtraData';
import styles from '../styles.module.css';

type Props = { params: Promise<{ slug: string }> };
const allArticles = [...articles, ...extraArticles];

export function generateStaticParams() {
  return allArticles.map(({ slug }) => ({ slug }));
}

function getArticle(slug: string) {
  return allArticles.find((article) => article.slug === slug);
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const article = getArticle(slug);
  if (!article) return {};
  const url = `${SITE.baseUrl}/${article.slug}/`;
  return {
    title: article.title,
    description: article.description,
    alternates: { canonical: url },
    openGraph: {
      title: article.title,
      description: article.description,
      url,
      type: 'article',
      modifiedTime: article.updated,
    },
  };
}

export default async function AffiliateArticlePage({ params }: Props) {
  const { slug } = await params;
  const article = getArticle(slug);
  if (!article) notFound();

  const related = allArticles.filter((item) => item.slug !== article.slug).slice(0, 3);
  const linkRel = article.affiliatePending ? 'noopener noreferrer' : 'nofollow sponsored noopener noreferrer';
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: article.title,
    description: article.description,
    dateModified: article.updated,
    datePublished: article.updated,
    mainEntityOfPage: `${SITE.baseUrl}/${article.slug}/`,
    author: { '@type': 'Organization', name: SITE.name },
    publisher: { '@type': 'Organization', name: SITE.name },
  };

  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <article className={styles.article}>
          <nav className={styles.breadcrumb} aria-label="パンくず">
            <Link href="/affiliate/">AI Tool Select</Link><span>/</span><span>{article.service}</span>
          </nav>
          <div className={styles.meta}>
            <span className={styles.pill}>{article.service}</span>
            <span className={styles.pill}>{article.intent}</span>
          </div>
          <h1>{article.title}</h1>
          <div className={styles.updated}>最終更新: {article.updated}</div>
          <p className={styles.lead}>{article.intro}</p>

          <div className={styles.decisionBox}>
            <span>QUICK DECISION</span>
            <strong>先に結論だけ知りたい人へ</strong>
            <p>この記事は、機能を全部覚えるためではなく「自分に合うか」を判断するためのものです。合いそうなら公式サイトで実際の画面・料金を確認し、合わなければ関連記事から別候補へ進んでください。</p>
            <a className={styles.ctaInline} href={article.affiliateUrl} target="_blank" rel={linkRel}>{article.cta} ↗</a>
            {!article.affiliatePending && <small>※ このリンクはアフィリエイトリンクです。</small>}
          </div>

          {article.sections.map((section) => (
            <section key={section.heading}>
              <h2>{section.heading}</h2>
              {section.body.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
            </section>
          ))}

          <div className={styles.finalCta}>
            <span>NEXT STEP</span>
            <h2>読むだけで終わらせず、合うかを実物で確認する。</h2>
            <p>料金・仕様・使い勝手は変わることがあります。最終判断は公式サイトの最新情報と、実際の操作感で決めるのが安全です。</p>
            <a className={styles.cta} href={article.affiliateUrl} target="_blank" rel={linkRel}>{article.cta}</a>
          </div>

          {article.affiliatePending && (
            <p className={styles.disclosure}>現在は公式サイトへの通常リンクです。提携承認後は、アフィリエイトリンクであることを明示したうえで差し替えます。</p>
          )}
          <p className={styles.disclosure}>広告・アフィリエイトについて：当サイトは一部リンクから成果報酬を受け取る場合があります。料金・仕様・提供条件は変更される可能性があるため、契約前に必ず公式サイトで最新情報をご確認ください。</p>

          <aside className={styles.related} aria-label="関連記事">
            <div className={styles.relatedHead}><span>RELATED</span><h2>次に読む記事</h2></div>
            <div className={styles.relatedList}>
              {related.map((item, index) => (
                <Link href={`/affiliate/${item.slug}/`} key={item.slug}>
                  <span>{String(index + 1).padStart(2, '0')}</span>
                  <div><strong>{item.title}</strong><small>{item.service} / {item.intent}</small></div>
                  <b>↗</b>
                </Link>
              ))}
            </div>
            <Link className={styles.backHome} href="/affiliate/">すべての記事を見る →</Link>
          </aside>

          <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
        </article>
      </div>
    </main>
  );
}
