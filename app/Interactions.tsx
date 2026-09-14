'use client';

import { useEffect } from 'react';

const details = [
  {
    title: 'Beauty / Inner Care LP',
    category: 'SAMPLE WORK / LANDING PAGE',
    concept: '「頑張る自分への投資 × 続ける美容習慣」を想定した、インナーケアブランドのコンセプトLPです。',
    challenge: '美容系でありがちな情報過多を避けながら、上品さ・安心感・購入導線をひとつの流れにまとめることをテーマに設計しました。',
    scope: '企画 / 情報設計 / コピー設計 / UIデザイン / フロントエンド想定',
    note: '特定クライアントへの納品実績ではなく、MeRGeの制作イメージを伝えるための自主制作サンプルです。',
  },
  {
    title: 'Service Promotion LP',
    category: 'SAMPLE WORK / LANDING PAGE',
    concept: '業務改善サービスを想定し、サービス内容を短時間で理解できる営業用コンセプトLPです。',
    challenge: '課題提起から解決策、導入メリット、CTAまでを迷わず追える構成にし、BtoBでも堅くなりすぎない見せ方を意識しました。',
    scope: '構成設計 / UX / UIデザイン / CTA設計 / フロントエンド想定',
    note: '特定クライアントへの納品実績ではなく、MeRGeの制作イメージを伝えるための自主制作サンプルです。',
  },
  {
    title: 'Original Web Product',
    category: 'SAMPLE WORK / WEB PRODUCT',
    concept: 'チームのタスク・進捗・予定を一画面で把握できる業務管理Webアプリを想定したUIコンセプトです。',
    challenge: '情報量が多い画面でも視線が迷わないよう、優先度・状態・操作対象が直感的に分かるレイアウトを設計しました。',
    scope: '要件整理 / 情報設計 / UI設計 / ダッシュボード設計 / Webアプリ実装想定',
    note: '特定クライアントへの納品実績ではなく、MeRGeの制作イメージを伝えるための自主制作サンプルです。',
  },
];

export default function Interactions() {
  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const reveals = Array.from(document.querySelectorAll<HTMLElement>(
      '.sectionHead, .workCard, .serviceList article, .aboutBody > *, .teamGrid article, .processPhoto, .steps article, .faq details, .contactInner > *'
    ));

    reveals.forEach((el, index) => {
      el.classList.add('revealItem');
      el.style.setProperty('--reveal-delay', `${Math.min(index % 4, 3) * 70}ms`);
    });

    if (reduceMotion) {
      reveals.forEach((el) => el.classList.add('isVisible'));
    } else {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            (entry.target as HTMLElement).classList.add('isVisible');
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.13, rootMargin: '0px 0px -7% 0px' });
      reveals.forEach((el) => observer.observe(el));
    }

    const cards = Array.from(document.querySelectorAll<HTMLElement>('.workCard'));
    cards.forEach((card, index) => {
      card.setAttribute('role', 'button');
      card.setAttribute('tabindex', '0');
      card.setAttribute('aria-label', `${details[index]?.title ?? 'Sample Work'} の詳細を見る`);
      const open = () => window.dispatchEvent(new CustomEvent('open-work-modal', { detail: index }));
      card.addEventListener('click', open);
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); }
      });
    });

    const onScroll = () => {
      if (reduceMotion) return;
      const y = window.scrollY;
      document.documentElement.style.setProperty('--scroll-y', `${y}px`);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    const handler = (event: Event) => {
      const index = (event as CustomEvent<number>).detail;
      const data = details[index];
      if (!data) return;

      const previous = document.querySelector('.workModal');
      previous?.remove();

      const modal = document.createElement('div');
      modal.className = 'workModal';
      modal.innerHTML = `
        <div class="workModalBackdrop" data-close></div>
        <section class="workModalPanel" role="dialog" aria-modal="true" aria-label="${data.title}">
          <button class="workModalClose" data-close aria-label="閉じる">×</button>
          <p class="workModalKicker">${data.category}</p>
          <h2>${data.title}</h2>
          <p class="workModalLead">${data.concept}</p>
          <div class="workModalGrid">
            <div><span>DESIGN INTENT</span><p>${data.challenge}</p></div>
            <div><span>SCOPE</span><p>${data.scope}</p></div>
          </div>
          <div class="workModalNote"><b>SAMPLE / CONCEPT WORK</b><p>${data.note}</p></div>
          <a href="#contact" class="workModalCta">このような制作を相談する <span>→</span></a>
        </section>`;
      document.body.appendChild(modal);
      requestAnimationFrame(() => modal.classList.add('isOpen'));
      document.body.classList.add('modalOpen');

      const close = () => {
        modal.classList.remove('isOpen');
        document.body.classList.remove('modalOpen');
        window.setTimeout(() => modal.remove(), 260);
      };
      modal.querySelectorAll('[data-close]').forEach((el) => el.addEventListener('click', close));
      modal.querySelector('.workModalCta')?.addEventListener('click', close);
      const keyClose = (e: KeyboardEvent) => { if (e.key === 'Escape') { close(); window.removeEventListener('keydown', keyClose); } };
      window.addEventListener('keydown', keyClose);
    };
    window.addEventListener('open-work-modal', handler);
    return () => window.removeEventListener('open-work-modal', handler);
  }, []);

  return null;
}
