import type { Metadata } from 'next';
import MotionController from './animations';
import Interactions from './Interactions';
import './globals.css';
import './mobile-fixes.css';
import './works.css';
import './animations.css';
import './interactions.css';
import './services-static.css';
import './illustration-override.css';

export const metadata: Metadata = {
  metadataBase: new URL('https://systemengi2001-afk.github.io/merge-engineers/'),
  title: 'MeRGe | 伝わる設計を、使われるWebへ。',
  description: 'Webサイト・LP・Webシステムを、企画から実装まで。二人の視点で、相談しやすく、動きやすい制作を。',
  verification: {
    google: 'c2oRKzBaZH_rR59yinrDaBdQkyiW7RdB-dm5mKydi_E',
  },
  openGraph: {
    title: 'MeRGe | 伝わる設計を、使われるWebへ。',
    description: 'Webサイト・LP・Webシステムを、企画から実装まで。二人の制作チームMeRGe。',
    images: [{ url: 'og.png', width: 1200, height: 630, alt: 'MeRGe — 伝わる設計を、使われるWebへ。' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'MeRGe | 伝わる設計を、使われるWebへ。',
    description: 'Webサイト・LP・Webシステムを、企画から実装まで。二人の制作チームMeRGe。',
    images: ['og.png'],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ja"><body><MotionController /><Interactions />{children}</body></html>;
}
