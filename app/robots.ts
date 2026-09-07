import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
    },
    sitemap: 'https://systemengi2001-afk.github.io/merge-engineers/sitemap.xml',
  };
}
