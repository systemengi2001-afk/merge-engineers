import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { articles, getArticle, SITE } from '../../../lib/affiliateData';
import styles from '../styles.module.css';

type Props = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return articles.map(({ slug }) => ({ slug }));
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
            <Link href="/affiliate/">AI Tool Select</Link> / {article.service}
          </nav>
          <div className={styles.meta}>
            <span className={styles.pill}>{article.service}</span>
            <span className={styles.pill}>{article.intent}</span>
          </div>
          <h1>{article.title}</h1>
          <div className={styles.updated}>最終更新: {article.updated}</div>
          <p>{article.intro}</p>

          {article.sections.map((section) => (
            <section key={section.heading}>
              <h2>{section.heading}</h2>
              {section.body.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
            </section>
          ))}

          <a className={styles.cta} href={article.affiliateUrl} target="_blank" rel="nofollow sponsored noopener noreferrer">
            {article.cta}
          </a>
          {article.affiliatePending && (
            <p className={styles.disclosure}>現在は公式サイトへの通常リンクです。提携承認後は、アフィリエイトリンクであることを明示したうえで差し替えます。</p>
          )}
          <p className={styles.disclosure}>広告・アフィリエイトについて：当サイトは一部リンクから成果報酬を受け取る場合があります。料金・仕様・提供条件は変更される可能性があるため、契約前に必ず公式サイトで最新情報をご確認ください。</p>
          <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
        </article>
      </div>
    </main>
  );
}
