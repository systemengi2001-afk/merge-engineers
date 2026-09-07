import type { Metadata } from 'next';
import Link from 'next/link';
import { SITE } from '../../../lib/affiliateData';
import styles from '../styles.module.css';

export const metadata: Metadata = {
  title: `広告・編集ポリシー | ${SITE.name}`,
  description: `${SITE.name}の広告、アフィリエイト、編集ポリシーについて説明します。`,
  alternates: { canonical: `${SITE.baseUrl}/policy/` },
};

export default function PolicyPage() {
  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <article className={styles.article}>
          <nav className={styles.breadcrumb}><Link href="/affiliate/">AI Tool Select</Link><span>/</span><span>広告・編集ポリシー</span></nav>
          <div className={styles.eyebrow}>DISCLOSURE / POLICY</div>
          <h1>報酬があっても、比較の結論は報酬額だけで決めません。</h1>
          <p className={styles.lead}>当サイトにはアフィリエイトリンクが含まれる場合があります。リンク経由で申込・購入が成立すると、当サイトが成果報酬を受け取ることがあります。</p>

          <section><h2>アフィリエイトリンクについて</h2><p>成果報酬の対象となるリンクは、記事内で分かるように表示します。未提携・未承認のサービスについては通常の公式リンクを使用します。</p></section>
          <section><h2>掲載順位の決め方</h2><p>報酬額だけで順位を決めません。用途との適合、料金、導入負担、機能、運用のしやすさ、対象ユーザーを総合して掲載します。</p></section>
          <section><h2>料金・仕様について</h2><p>できる限り公式情報を確認しますが、料金・機能・キャンペーン・提供条件は変更される可能性があります。契約前には必ず各サービスの公式サイトで最新情報をご確認ください。</p></section>
          <section><h2>免責事項</h2><p>当サイトの情報は一般的な比較・検討材料として提供しています。導入や契約の最終判断は、利用者自身で公式条件を確認したうえで行ってください。</p></section>

          <div className={styles.finalCta}><span>EDITORIAL</span><h2>運営方針も公開しています。</h2><Link className={styles.cta} href="/affiliate/about/">運営方針を見る</Link></div>
        </article>
      </div>
    </main>
  );
}
