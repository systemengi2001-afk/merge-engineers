import { ImageResponse } from 'next/og';

export const alt = 'MeRGe — 伝わる設計を、使われるWebへ。';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          position: 'relative',
          overflow: 'hidden',
          background:
            'radial-gradient(circle at 82% 24%, rgba(0,190,255,.34), transparent 30%), radial-gradient(circle at 95% 72%, rgba(255,25,160,.32), transparent 34%), linear-gradient(135deg,#02050b 0%,#050b16 58%,#090312 100%)',
          color: '#fff',
          fontFamily: 'sans-serif',
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            background:
              'linear-gradient(128deg, transparent 0 64%, rgba(0,210,255,.85) 64.3%, transparent 64.8%), linear-gradient(150deg, transparent 0 76%, rgba(255,38,172,.8) 76.3%, transparent 77%)',
            opacity: .9,
          }}
        />
        <div
          style={{
            position: 'absolute',
            right: -80,
            top: -80,
            width: 540,
            height: 760,
            display: 'flex',
            transform: 'rotate(16deg)',
            border: '2px solid rgba(72,202,255,.7)',
            background: 'linear-gradient(160deg,rgba(0,177,255,.22),rgba(255,29,165,.18))',
            boxShadow: '0 0 80px rgba(0,174,255,.18)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            right: 34,
            bottom: -160,
            width: 360,
            height: 560,
            display: 'flex',
            transform: 'rotate(-25deg)',
            border: '2px solid rgba(255,67,184,.75)',
            background: 'linear-gradient(160deg,rgba(255,29,165,.24),rgba(0,177,255,.08))',
          }}
        />

        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            padding: '72px 84px',
            width: 900,
            zIndex: 2,
          }}
        >
          <div style={{ fontSize: 104, fontWeight: 800, letterSpacing: '-5px', lineHeight: 1 }}>
            MeRGe
          </div>
          <div style={{ marginTop: 30, fontSize: 50, fontWeight: 750, lineHeight: 1.35 }}>
            伝わる設計を、使われるWebへ。
          </div>
          <div style={{ marginTop: 24, fontSize: 27, color: '#cbd5e1', lineHeight: 1.5 }}>
            Webサイト・LP・Webシステムを、企画から実装まで。
          </div>
          <div style={{ marginTop: 58, display: 'flex', alignItems: 'center', gap: 18 }}>
            <div style={{ width: 74, height: 2, display: 'flex', background: '#fff', opacity: .9 }} />
            <div style={{ fontSize: 20, letterSpacing: '7px', color: '#d9e2ec' }}>
              WEB DESIGN / DEVELOPMENT
            </div>
          </div>
        </div>
      </div>
    ),
    { ...size }
  );
}
