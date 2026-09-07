import type { MetadataRoute } from 'next';
import { articles, SITE } from '../lib/affiliateData';
import { extraArticles } from '../lib/affiliateExtraData';

export const dynamic = 'force-static';

export default function sitemap(): MetadataRoute.Sitemap {
  const allArticles = [...articles, ...extraArticles];
  return [
    {
      url: 'https://systemengi2001-afk.github.io/merge-engineers/',
      lastModified: new Date('2026-09-07'),
      changeFrequency: 'monthly',
      priority: 0.6,
    },
    {
      url: `${SITE.baseUrl}/`,
      lastModified: new Date('2026-09-07'),
      changeFrequency: 'weekly',
      priority: 1,
    },
    ...allArticles.map((article) => ({
      url: `${SITE.baseUrl}/${article.slug}/`,
      lastModified: new Date(article.updated),
      changeFrequency: 'monthly' as const,
      priority: article.intent.includes('購入直前') ? 0.9 : 0.8,
    })),
  ];
}
