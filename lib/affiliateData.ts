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

const SYSTEME_IO_AFFILIATE_URL = 'https://systeme.io/jp?sa=sa0280926250afeb54ccbe34abfc78fa154603223e';

export const articles: AffiliateArticle[] = [
  {
    slug: 'systeme-io-review',
    title: 'systeme.ioは使うべき？「LP・メール・講座を別々に契約したくない人」向けに判断',
    description: 'systeme.ioが自分に合うかを最短で判断。向いている人、向いていない人、導入前に見るべきポイントを個人事業・副業目線で整理します。',
    service: 'systeme.io',
    intent: '購入直前',
    updated: '2026-09-07',
    affiliateUrl: SYSTEME_IO_AFFILIATE_URL,
    affiliatePending: false,
    intro: '「LPはA社、メールはB社、講座はC社」と増やしていく前に見てほしい候補です。systeme.ioは、販売に必要な複数機能を一つに寄せたい人ほど検討価値があります。逆に、すでに各ツールを使い込んでいる人には乗り換えコストが合わないこともあります。',
    sections: [
      {
        heading: '先に結論：こんな人なら候補に入る',
        body: [
          '副業や個人事業で、商品・サービスを売る導線をこれから作る人には相性がいい候補です。特に「まず売れる形を作りたい。ツール選びに何日も使いたくない」という人には分かりやすい選択肢です。',
          '一方で、メール配信・決済・LMSなどをすでに個別サービスで最適化している人は、無理にまとめる必要はありません。便利さより既存環境の完成度を優先した方がいい場合があります。'
        ]
      },
      {
        heading: '一番のメリットは「ツールを減らせること」',
        body: [
          '販売導線は、ツールが増えるほど設定・連携・請求管理も増えます。systeme.ioの魅力は、LP、メール、講座、ファネルなどを同じ場所で扱えることです。',
          '機能が多いこと自体より、「別サービスを行き来する回数を減らせる」という点の方が、少人数で動く副業・個人事業では実務上のメリットになりやすいです。'
        ]
      },
      {
        heading: '向いていない人もいる',
        body: [
          '「全部入り」だから全員に最適、というわけではありません。特定機能だけを深く使いたい人や、既存ツールで販売導線が完成している人は、専用サービスを使い続ける方が合理的なこともあります。',
          'また海外サービスなので、日本国内サービスと同じ感覚で使えるとは限りません。UI、サポート、決済や運用条件など、自分の用途で困らないかは実際に確認しておくべきです。'
        ]
      },
      {
        heading: '無料で触ってから決めるのが一番早い',
        body: [
          'この手のツールは、記事を10本読むより管理画面を数分触った方が判断しやすいです。必要な導線を作れそうか、操作が苦にならないか、自分の販売方法に合うかを確認してください。',
          '合わなければ別候補へ移ればいいので、最初から「これに決める」と考える必要はありません。料金・プラン・機能は変更される可能性があるため、最新条件は必ず公式サイトで確認してください。'
        ]
      },
      {
        heading: '最終判断：何を売るかが決まっている人ほど使いやすい',
        body: [
          '「いつか何か売りたい」段階より、講座・相談サービス・デジタル商品など、売るものがある程度決まっている人の方が導入効果を判断しやすいです。',
          '販売ページを作り、見込み客を集め、案内し、商品につなげる。その流れを一つの環境で試したいなら、systeme.ioは比較リストに入れていい候補です。'
        ]
      },
    ],
    cta: 'systeme.ioを無料で試して判断する',
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
    affiliateUrl: SYSTEME_IO_AFFILIATE_URL,
    affiliatePending: false,
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
