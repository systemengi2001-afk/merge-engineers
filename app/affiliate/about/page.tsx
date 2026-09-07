import type { Metadata } from 'next';
import Link from 'next/link';
import { SITE } from '../../../lib/affiliateData';
import styles from '../styles.module.css';

export const metadata: Metadata = {
  title: `運営方針 | ${SITE.name}`,
  description: `${SITE.name}の運営目的、比較基準、情報更新方針について説明します。`,
  alternates: { canonical: `${SITE.baseUrl}/about/` },
};

export default function AboutPage() {
  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <article className={styles.article}>
          <nav className={styles.breadcrumb}><Link href="/affiliate/">AI Tool Select</Link><span>/</span><span>運営方針</span></nav>
          <div className={styles.eyebrow}>ABOUT / EDITORIAL</div>
          <h1>ツール選びで、時間と固定費を無駄にしないために。</h1>
          <p className={styles.lead}>AI Tool Selectは、副業・Web制作・小規模事業で使うAI・SaaS・自動化ツールを、導入判断までできる形で整理する実務メディアです。</p>

          <section><h2>比較で重視すること</h2><p>機能の多さだけではなく、誰に向くか、導入で何の作業が減るか、固定費に見合うか、販売や業務改善につながるかを重視します。</p></section>
          <section><h2>実際に使っていないものを「使った」と書かない</h2><p>架空の体験談や、確認できない成果は掲載しません。公式情報を基本にし、体験していない内容は機能・仕様・比較情報として明確に扱います。</p></section>
          <section><h2>向いていないケースも書く</h2><p>アフィリエイト報酬があるサービスでも、全員におすすめとはしません。既存環境の方が合理的な場合や、価格に見合わない場合はその条件も記載します。</p></section>
          <section><h2>更新方針</h2><p>SaaSの料金・機能・提供条件は変わります。重要な変更を確認した場合は記事を更新し、契約前には必ず公式サイトの最新条件を確認するよう案内します。</p></section>

          <div className={styles.finalCta}><span>BACK TO GUIDES</span><h2>目的に合うツールを比較する。</h2><Link className={styles.cta} href="/affiliate/">記事一覧へ戻る</Link></div>
        </article>
      </div>
    </main>
  );
}
