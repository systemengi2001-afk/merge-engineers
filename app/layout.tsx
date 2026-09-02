import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'MeRGe | ふたりのフリーランスエンジニア',
  description: 'Web制作からシステム開発まで。二人のフリーランスエンジニアが、あなたの要望を動くカタチにします。',
  openGraph: {
    title: 'MeRGe | 想いを、動くカタチに。',
    description: '二人のフリーランスエンジニアが、Web制作からシステム開発まで柔軟に対応します。',
    images: [{ url: '/og.png', width: 1200, height: 630, alt: 'MeRGe — 想いを、動くカタチに。' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'MeRGe | 想いを、動くカタチに。',
    description: '二人のフリーランスエンジニアが、Web制作からシステム開発まで柔軟に対応します。',
    images: ['/og.png'],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ja"><body>{children}</body></html>;
}
