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
    service: 'systeme.io', intent: '購入直前', updated: '2026-09-07', affiliateUrl: SYSTEME_IO_AFFILIATE_URL, affiliatePending: false,
    intro: '「LPはA社、メールはB社、講座はC社」と増やしていく前に見てほしい候補です。systeme.ioは、販売に必要な複数機能を一つに寄せたい人ほど検討価値があります。',
    sections: [
      { heading: '先に結論：こんな人なら候補に入る', body: ['副業や個人事業で、商品・サービスを売る導線をこれから作る人には相性がいい候補です。特に「まず売れる形を作りたい。ツール選びに何日も使いたくない」という人には分かりやすい選択肢です。', '一方で、メール配信・決済・LMSなどをすでに個別サービスで最適化している人は、無理にまとめる必要はありません。'] },
      { heading: '一番のメリットは「ツールを減らせること」', body: ['販売導線は、ツールが増えるほど設定・連携・請求管理も増えます。systeme.ioはLP、メール、講座、ファネルなどを同じ場所で扱えます。'] },
      { heading: '向いていない人もいる', body: ['特定機能だけを深く使いたい人や、既存ツールで販売導線が完成している人は、専用サービスを使い続ける方が合理的なこともあります。'] },
      { heading: '無料で触ってから決めるのが一番早い', body: ['この手のツールは、記事を10本読むより管理画面を数分触った方が判断しやすいです。料金・プラン・機能は変更される可能性があるため、最新条件は公式サイトで確認してください。'] },
    ],
    cta: 'systeme.ioを無料で試して判断する',
  },
  {
    slug: 'systeme-io-pricing',
    title: 'systeme.ioの料金は高い？無料プランでどこまでできるかを判断',
    description: 'systeme.ioの無料プランと有料プランの考え方を整理。固定費を抑えたい副業・個人事業主がどこで有料化すべきかを解説します。',
    service: 'systeme.io', intent: '料金・購入直前', updated: '2026-09-07', affiliateUrl: SYSTEME_IO_AFFILIATE_URL, affiliatePending: false,
    intro: '料金を見るときは「月額いくらか」だけでなく、LP・メール・講座・ファネルを別々に契約した場合の合計と比べるのがポイントです。公式情報では永久無料プランがあり、クレジットカード不要で始められます。',
    sections: [
      { heading: '無料プランで試す価値は十分ある', body: ['公式情報では、無料プランでも2,000件のコンタクト、メール送信、セールスファネル、コース、カスタムドメインなどを試せます。最初から課金せず、自分の導線が組めるかを見るのが安全です。'] },
      { heading: '有料化は「制限に当たった時」でいい', body: ['最初から上位プランを選ぶより、ファネル数・コース数・コンタクト数などの制限に当たり始めた段階でアップグレードする方が無駄がありません。'] },
      { heading: '比較すべきはツールの合計コスト', body: ['LP作成、メール配信、オンライン講座、アフィリエイト管理を個別契約すると固定費が積み上がります。systeme.ioは複数機能を一つにまとめたい人ほど料金メリットを感じやすい設計です。'] },
      { heading: '結論：まず無料、売れ始めてから有料', body: ['売上がない段階で固定費を増やす必要はありません。無料で販売導線を作り、必要になった段階で有料化するのが最も合理的です。最新価格は公式ページで確認してください。'] },
    ],
    cta: '無料プランを公式サイトで確認する',
  },
  {
    slug: 'systeme-io-free-plan',
    title: 'systeme.io無料プランで何ができる？副業の販売導線はどこまで作れるか',
    description: 'systeme.ioの無料プランでできること・できないことを、副業やコンテンツ販売の実務目線で整理します。',
    service: 'systeme.io', intent: '無料プラン・登録直前', updated: '2026-09-07', affiliateUrl: SYSTEME_IO_AFFILIATE_URL, affiliatePending: false,
    intro: '「無料って結局ほとんど使えないのでは？」という人向けです。systeme.ioは無料プランでも販売導線の一連を試しやすく、まず売れる形を作る段階では十分候補になります。',
    sections: [
      { heading: '無料でも販売導線のテストはできる', body: ['公式情報では、無料プランでファネル、メールマーケティング、コース、カスタムドメインなど主要機能を利用できます。クレジットカードも不要です。'] },
      { heading: '無料の強みは「機能制限」より「数量制限」中心', body: ['基本機能そのものを完全に封じるより、コンタクト数やファネル数、コース数などの上限で差がつく設計です。小さく始める人には相性があります。'] },
      { heading: '無料のままでいい人', body: ['最初の商品を作っている段階、見込み客リストがまだ少ない段階、まず1つの講座や販売ページを試したい段階なら、無料のまま十分なことがあります。'] },
      { heading: '有料に変えるタイミング', body: ['顧客リストや販売導線が増え、無料枠の数量制限が事業成長を止めるようになったら有料化を検討すれば十分です。'] },
    ],
    cta: '無料アカウントを作って確認する',
  },
  {
    slug: 'systeme-io-how-to-start',
    title: 'systeme.ioの始め方｜登録後に最初に作るべき販売導線を5ステップで整理',
    description: 'systeme.ioを登録した後に何から触ればいいか迷う人向け。副業・個人サービス販売の最短導線を整理します。',
    service: 'systeme.io', intent: '使い方・登録直前', updated: '2026-09-07', affiliateUrl: SYSTEME_IO_AFFILIATE_URL, affiliatePending: false,
    intro: '機能を全部覚える必要はありません。最初は「商品を見せる → 見込み客を集める → 案内する → 売る」という最低限の流れだけ作れば十分です。',
    sections: [
      { heading: '1. まず売るものを1つ決める', body: ['講座、相談サービス、テンプレート、デジタル商品など、最初は1商品に絞る方が設定も検証も速くなります。'] },
      { heading: '2. セールスファネルを1本だけ作る', body: ['LPや登録ページを増やしすぎず、まずは1つの入口から商品案内までつなげます。'] },
      { heading: '3. メールを3〜5通だけ用意する', body: ['最初から長いステップメールは不要です。登録直後、価値提供、商品案内という最低限から始めます。'] },
      { heading: '4. 必要ならコースを載せる', body: ['オンライン講座を販売する場合は、同じ環境でコース作成・受講者管理までまとめられます。'] },
      { heading: '5. 数字を見て一つずつ改善する', body: ['アクセスが少ないのか、登録されないのか、商品ページから売れないのかを分けて見ると改善しやすくなります。'] },
    ],
    cta: '無料で登録して導線を作ってみる',
  },
  {
    slug: 'systeme-io-disadvantages',
    title: 'systeme.ioのデメリットは？登録前に確認したい「合わない人」の条件',
    description: 'systeme.ioの弱点や向いていないケースを整理。メリットだけでなく、登録後に後悔しやすいポイントを先に確認できます。',
    service: 'systeme.io', intent: 'デメリット・購入直前', updated: '2026-09-07', affiliateUrl: SYSTEME_IO_AFFILIATE_URL, affiliatePending: false,
    intro: '「全部入り」は便利ですが、万能ではありません。systeme.ioを勧めない方がいいケースを先に整理します。',
    sections: [
      { heading: '専用ツールの深さを求める人には物足りないことがある', body: ['メール、LMS、CRMなど一つの領域だけを高度に使い込みたい場合、専用サービスの方が細かな要件に合うことがあります。'] },
      { heading: '既存ツールが完成している人は移行コストがある', body: ['すでに複数ツールを使いこなし、販売導線が安定している場合は、まとめるメリットより移行の手間が上回ることがあります。'] },
      { heading: '海外サービスに慣れが必要な人もいる', body: ['日本国内サービスと同じUIやサポート体験を期待すると違いを感じる可能性があります。実際の管理画面を無料で触って判断するのが確実です。'] },
      { heading: 'それでも候補に残る人', body: ['これから販売導線を作る人、固定費を抑えたい人、複数SaaSを増やしたくない人なら、デメリットを踏まえても試す価値があります。'] },
    ],
    cta: '無料で触って合うか確認する',
  },
  {
    slug: 'systeme-io-vs-thinkific',
    title: 'systeme.ioとThinkificを比較｜講座販売ならどっちを選ぶ？',
    description: 'systeme.ioとThinkificを、講座販売・メール・ファネル・運用の考え方で比較。どちらが向くかを用途別に整理します。',
    service: 'systeme.io × Thinkific', intent: '比較・購入直前', updated: '2026-09-07', affiliateUrl: SYSTEME_IO_AFFILIATE_URL, affiliatePending: false,
    intro: '講座を売るだけなら両方候補になりますが、選び方は「講座体験を中心にするか」「集客から販売まで一つにまとめるか」で変わります。',
    sections: [
      { heading: 'systeme.io向き：販売導線をまとめたい', body: ['メール、ファネル、販売ページ、講座を一つの環境に寄せたい人はsysteme.ioが分かりやすい候補です。'] },
      { heading: 'Thinkific向き：講座プラットフォームを中心に考えたい', body: ['オンライン講座の運営を中心にサービスを選びたい場合はThinkificも比較対象です。講座管理の考え方や必要機能を先に整理してください。'] },
      { heading: '副業初期なら固定費と導線のシンプルさを優先', body: ['まだ売上が安定していない段階では、複数SaaSを契約するより、無料から販売導線を試せる方を優先した方が失敗しにくいです。'] },
      { heading: '結論', body: ['「講座だけ」ではなく集客・メール・販売までまとめたいならsysteme.io寄り。講座運営そのものを中心に細かく比較したいならThinkificも検討、という分け方がシンプルです。'] },
    ],
    cta: 'systeme.ioを無料で試して比較する',
  },
  {
    slug: 'thinkific-review',
    title: 'Thinkificの評判は？オンライン講座販売を始めたい人向けに特徴を整理',
    description: 'Thinkificの特徴、向いている人、導入前の注意点を解説。オンライン講座や会員制コンテンツを販売したい方向けです。',
    service: 'Thinkific', intent: '比較・購入検討', updated: '2026-09-07', affiliateUrl: 'https://www.thinkific.com/', affiliatePending: true,
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
    service: 'Kinsta', intent: '購入直前', updated: '2026-09-07', affiliateUrl: 'https://kinsta.com/jp/', affiliatePending: true,
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
    service: '複数', intent: '比較', updated: '2026-09-07', affiliateUrl: SYSTEME_IO_AFFILIATE_URL, affiliatePending: false,
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
