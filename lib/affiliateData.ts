export type AffiliateArticle = {
  slug: string;
  title: string;
  description: string;
  service: string;
  intent: string;
  updated: string;
  affiliateUrl: string;
  affiliatePending: boolean;
  intro: string;
  sections: { heading: string; body: string[] }[];
  cta: string;
};

export const SITE = {
  name: 'AI Tool Select',
  description: '副業・Web制作・小規模事業者向けに、AI・SaaS・自動化ツールを比較する実務メディア',
  baseUrl: 'https://systemengi2001-afk.github.io/merge-engineers/affiliate',
};

export const articles: AffiliateArticle[] = [
  {
    slug: 'systeme-io-review',
    title: 'systeme.ioの評判・料金は？無料で始めたい個人事業主向けに解説',
    description: 'systeme.ioの特徴、無料プラン、向いている人、注意点を整理。販売導線をまとめたい副業・個人事業主向けの比較記事です。',
    service: 'systeme.io',
    intent: '購入直前',
    updated: '2026-09-07',
    affiliateUrl: 'https://systeme.io/',
    affiliatePending: true,
    intro: 'LP、メール配信、オンライン講座、販売導線をできるだけ一つにまとめたい人向けのオールインワン型マーケティングツールです。',
    sections: [
      { heading: 'systeme.ioが向いている人', body: ['複数のSaaSを契約せず、まず無料で販売導線を試したい人に向いています。特に副業、コンテンツ販売、個人サービスとの相性が良いです。'] },
      { heading: 'メリット', body: ['無料から試しやすく、ファネル・メール・講座機能を一つの管理画面にまとめられる点が強みです。ツールをまたいだ設定作業を減らせます。'] },
      { heading: '注意点', body: ['海外サービスのため、日本国内向けサービスと比べるとUIやサポート面で慣れが必要な場合があります。料金・プラン内容は契約前に必ず公式ページで最新条件を確認してください。'] },
      { heading: '結論', body: ['まず小さく販売導線を作りたいなら有力候補です。無料で触って、自分の販売フローに合うかを確認してから有料化するのが安全です。'] },
    ],
    cta: 'systeme.ioを公式サイトで確認する',
  },
  {
    slug: 'thinkific-review',
    title: 'Thinkificの評判は？オンライン講座販売を始めたい人向けに特徴を整理',
    description: 'Thinkificの特徴、向いている人、導入前の注意点を解説。オンライン講座や会員制コンテンツを販売したい方向けです。',
    service: 'Thinkific',
    intent: '比較・購入検討',
    updated: '2026-09-07',
    affiliateUrl: 'https://www.thinkific.com/',
    affiliatePending: true,
    intro: 'オンライン講座を自社ブランドで販売したい講師・コーチ・教育事業者向けのプラットフォームです。',
    sections: [
      { heading: 'Thinkificが向いている人', body: ['動画講座、教材、会員コンテンツを整理し、自分のブランドで販売したい人に向いています。'] },
      { heading: 'メリット', body: ['講座作成、受講者管理、販売をまとめられるため、専用LMSを一から開発する必要がありません。'] },
      { heading: '注意点', body: ['日本語圏での情報量や国内決済・運用要件は、自分の販売方法と照らして確認が必要です。最新の料金や機能は公式情報を確認してください。'] },
      { heading: '結論', body: ['講座販売を事業として育てたい場合の有力候補です。単発教材より継続的に講座を増やす人ほど検討価値があります。'] },
    ],
    cta: 'Thinkificを公式サイトで確認する',
  },
  {
    slug: 'kinsta-review',
    title: 'Kinstaの評判は？Web制作会社・WordPress運営者向けにメリットを解説',
    description: 'Kinstaの特徴、向いている案件、一般的なレンタルサーバーとの違いをWeb制作目線で整理します。',
    service: 'Kinsta',
    intent: '購入直前',
    updated: '2026-09-07',
    affiliateUrl: 'https://kinsta.com/jp/',
    affiliatePending: true,
    intro: '速度・運用性・管理性を重視するWordPressサイト向けのマネージドホスティングです。',
    sections: [
      { heading: 'Kinstaが向いている人', body: ['企業サイト、集客サイト、複数サイトを管理する制作者など、安さだけでなく運用性やパフォーマンスを重視する人向けです。'] },
      { heading: 'メリット', body: ['WordPress運用に必要な管理機能がまとまっており、制作会社が顧客サイトを扱う場合にも管理工数を減らしやすい構成です。'] },
      { heading: '注意点', body: ['格安レンタルサーバーと比べると価格帯が上がるため、小規模な個人ブログではオーバースペックになる場合があります。'] },
      { heading: '結論', body: ['売上や問い合わせに直結するWordPressサイトでは、価格だけではなく速度・安定性・保守工数を含めて比較する価値があります。'] },
    ],
    cta: 'Kinstaを公式サイトで確認する',
  },
  {
    slug: 'marketing-tools-for-small-business',
    title: '個人事業主向けマーケティング自動化ツール4選｜集客から販売まで効率化',
    description: '個人事業主・副業向けに、集客、メール、講座、Webサイト運用を効率化するSaaSを用途別に比較します。',
    service: '複数',
    intent: '比較',
    updated: '2026-09-07',
    affiliateUrl: 'https://systeme.io/',
    affiliatePending: true,
    intro: '自動化は「全部をAIに任せる」より、集客・教育・販売・運用のボトルネックを一つずつSaaSで減らす方が失敗しにくいです。',
    sections: [
      { heading: '販売導線を一つにまとめたい：systeme.io', body: ['LP、メール、講座、ファネルをまとめたい人向け。最初の固定費を抑えやすいのが魅力です。'] },
      { heading: 'オンライン講座販売：Thinkific', body: ['講座体験や受講者管理を重視したい人向け。教育コンテンツを事業化するときの候補です。'] },
      { heading: 'WordPress運用：Kinsta', body: ['Webサイトの速度・安定性・運用効率を重視する事業者や制作会社向けです。'] },
      { heading: '選び方', body: ['月額料金だけではなく、「そのツールで毎月何時間の作業を削減できるか」「売上につながる導線を作れるか」で比較してください。'] },
    ],
    cta: 'まずsysteme.ioを無料で確認する',
  },
];

export function getArticle(slug: string) {
  return articles.find((article) => article.slug === slug);
}
