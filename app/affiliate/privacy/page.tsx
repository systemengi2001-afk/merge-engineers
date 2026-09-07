import type { Metadata } from 'next';
import Link from 'next/link';
import { SITE } from '../../../lib/affiliateData';
import styles from '../styles.module.css';

export const metadata: Metadata = {
  title: `プライバシーポリシー | ${SITE.name}`,
  description: `${SITE.name}のプライバシーポリシーです。`,
  alternates: { canonical: `${SITE.baseUrl}/privacy/` },
};

export default function PrivacyPage() {
  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <article className={styles.article}>
          <nav className={styles.breadcrumb} aria-label="パンくず">
            <Link href="/affiliate/">AI Tool Select</Link><span>/</span><span>プライバシーポリシー</span>
          </nav>
          <div className={styles.eyebrow}>PRIVACY</div>
          <h1>プライバシーポリシー</h1>
          <p className={styles.lead}>AI Tool Selectは、読者が安心して比較記事を利用できるよう、アクセス情報・外部サービス・広告リンクの取り扱い方針を明示します。</p>

          <section>
            <h2>アクセス情報について</h2>
            <p>当サイトでは、サイト改善や利用状況の把握のため、アクセス解析等の仕組みを導入する場合があります。その際、閲覧ページ、端末・ブラウザ情報、参照元などが取得されることがありますが、これらは通常、個人を直接特定する目的では使用しません。</p>
          </section>

          <section>
            <h2>広告・アフィリエイトリンクについて</h2>
            <p>当サイトにはアフィリエイトリンクを含む場合があります。リンク経由で申込・購入が発生すると、当サイトが成果報酬を受け取ることがあります。広告の有無にかかわらず、比較記事では向いていないケースや注意点も記載します。</p>
          </section>

          <section>
            <h2>外部サイトについて</h2>
            <p>当サイトから遷移した外部サイトで提供されるサービス、決済、個人情報の取り扱いについては、各事業者の規約・プライバシーポリシーをご確認ください。料金・仕様・提供条件は変更される場合があります。</p>
          </section>

          <section>
            <h2>方針の更新</h2>
            <p>法令、利用サービス、運営方針の変更に応じて、本ポリシーを更新することがあります。重要な変更がある場合は、必要に応じてサイト上の表示も更新します。</p>
          </section>

          <Link className={styles.backHome} href="/affiliate/">トップへ戻る →</Link>
        </article>
      </div>
    </main>
  );
}
