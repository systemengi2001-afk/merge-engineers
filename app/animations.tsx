'use client';

import { useEffect } from 'react';

export default function MotionController() {
  useEffect(() => {
    const root = document.documentElement;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    root.classList.add('motion-ready');

    if (prefersReducedMotion) {
      root.classList.add('reduce-motion');
      return;
    }

    const groups = [
      '.sectionHead',
      '.workCard',
      '.serviceList article',
      '.aboutBody > h2',
      '.aboutGrid > p',
      '.aboutPhoto',
      '.strengths article',
      '.teamGrid article',
      '.processPhoto',
      '.steps article',
      '.faq details',
      '.contactInner > *',
    ];

    const revealNodes = Array.from(document.querySelectorAll<HTMLElement>(groups.join(',')));
    revealNodes.forEach((node, index) => {
      node.classList.add('motion-reveal');
      node.style.setProperty('--reveal-delay', `${Math.min(index % 6, 5) * 55}ms`);
    });

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          (entry.target as HTMLElement).classList.add('in-view');
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -8% 0px' },
    );

    revealNodes.forEach((node) => observer.observe(node));

    const heroNodes = Array.from(document.querySelectorAll<HTMLElement>('.heroCopy > *'));
    heroNodes.forEach((node, index) => {
      node.classList.add('hero-reveal');
      node.style.setProperty('--hero-delay', `${120 + index * 85}ms`);
    });
    requestAnimationFrame(() => root.classList.add('hero-loaded'));

    const parallaxNodes = Array.from(
      document.querySelectorAll<HTMLElement>('.heroBackdrop, .aboutPhoto, .processPhoto'),
    );

    let ticking = false;
    const updateParallax = () => {
      const viewportCenter = window.innerHeight / 2;
      parallaxNodes.forEach((node) => {
        const rect = node.getBoundingClientRect();
        const center = rect.top + rect.height / 2;
        const strength = node.classList.contains('heroBackdrop') ? 0.035 : 0.022;
        const max = node.classList.contains('heroBackdrop') ? 18 : 12;
        const value = Math.max(-max, Math.min(max, (viewportCenter - center) * strength));
        node.style.setProperty('--parallax-y', `${value.toFixed(2)}px`);
      });
      ticking = false;
    };

    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(updateParallax);
    };

    updateParallax();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);

    return () => {
      observer.disconnect();
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
    };
  }, []);

  return null;
}
