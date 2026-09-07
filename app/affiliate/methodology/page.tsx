import type { Metadata } from 'next';
import Link from 'next/link';
import { SITE } from '../../../lib/affiliateData';
import styles from '../styles.module.css';

export const metadata: Metadata = {
  title: `比較方法 | ${SITE.name}`,
  description: `${SITE.name}の記事・比較順位の決め方を公開します。`,
  alternates: { canonical: `${SITE.baseUrl}/methodology/` },
};

export default function MethodologyPage() {
  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <article className={styles.article}>
          <nav className={styles.breadcrumb} aria-label="パンくず">
            <Link href="/affiliate/">AI Tool Select</Link><span>/</span><span>比較方法</span>
          </nav>
          <div className={styles.eyebrow}>METHODOLOGY</div>
          <h1>比較方法</h1>
          <p className={styles.lead}>AI Tool Selectでは「機能が多い順」ではなく、読者が実際に導入判断できるかを基準に比較します。広告報酬だけで順位を決めません。</p>

          <section>
            <h2>1. まず利用目的を分ける</h2>
            <p>副業、オンライン講座、Web制作、WordPress運用など、用途が違えば最適なサービスも変わります。同じ土俵で無理に順位付けせず、用途別に向き・不向きを整理します。</p>
          </section>

          <section>
            <h2>2. 価格だけでなく総コストを見る</h2>
            <p>月額料金だけでなく、複数ツールを併用した場合の固定費、設定・連携の手間、移行コストも含めて考えます。無料プランがある場合は、まず検証できる範囲も重視します。</p>
          </section>

          <section>
            <h2>3. 導入後に減る作業を見る</h2>
            <p>LP、メール、講座、顧客管理、ホスティングなど、導入によって何の作業が減るかを重視します。高機能でも、少人数運用で手間が増えるなら評価を上げません。</p>
          </section>

          <section>
            <h2>4. 向いていない人も書く</h2>
            <p>万能なSaaSはありません。既存環境が完成している人、専用機能を深く使いたい人、高度な運用が必要な人など、別サービスの方が適する条件も明示します。</p>
          </section>

          <section>
            <h2>5. 最新条件は公式情報を優先する</h2>
            <p>料金・機能・提供条件は変更されるため、更新時は公式情報を優先します。記事内の数値は参考として扱い、契約前には必ず公式サイトの最新条件を確認してください。</p>
          </section>

          <section>
            <h2>アフィリエイト報酬との関係</h2>
            <p>当サイトは一部サービスから成果報酬を受け取る場合があります。ただし、報酬の有無だけで評価や掲載順位を決めることはありません。読者の利用目的、導入負担、コスト、代替候補を含めて判断します。</p>
          </section>

          <Link className={styles.backHome} href="/affiliate/">トップへ戻る →</Link>
        </article>
      </div>
    </main>
  );
}
