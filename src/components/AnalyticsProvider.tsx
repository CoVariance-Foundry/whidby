'use client';

import { useEffect, useRef } from 'react';
import { initAnalytics, trackPageView, trackScrollDepth, trackSectionView } from '@/lib/analytics';
import { captureUTMParams } from '@/lib/utm';

const SCROLL_MILESTONES = [25, 50, 75, 100];
const SECTION_IDS = ['hero', 'stats-bar', 'how-it-works', 'features-grid', 'cta', 'footer'];

export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  const trackedScrollDepths = useRef(new Set<number>());
  const trackedSections = useRef(new Set<string>());

  useEffect(() => {
    initAnalytics();
    captureUTMParams();
    trackPageView();

    // Scroll depth tracking
    const handleScroll = () => {
      const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
      if (scrollHeight <= 0) return;
      const scrollPercent = Math.round((window.scrollY / scrollHeight) * 100);

      for (const milestone of SCROLL_MILESTONES) {
        if (scrollPercent >= milestone && !trackedScrollDepths.current.has(milestone)) {
          trackedScrollDepths.current.add(milestone);
          trackScrollDepth(milestone);
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });

    // Section visibility tracking via IntersectionObserver
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const sectionId = entry.target.getAttribute('data-section');
          if (entry.isIntersecting && sectionId && !trackedSections.current.has(sectionId)) {
            trackedSections.current.add(sectionId);
            trackSectionView(sectionId);
          }
        }
      },
      { threshold: 0.5 }
    );

    // Observe all sections
    for (const id of SECTION_IDS) {
      const el = document.querySelector(`[data-section="${id}"]`);
      if (el) observer.observe(el);
    }

    return () => {
      window.removeEventListener('scroll', handleScroll);
      observer.disconnect();
    };
  }, []);

  return <>{children}</>;
}
