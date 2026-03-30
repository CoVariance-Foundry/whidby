'use client';

import { useEffect, useRef } from 'react';
import { initAnalytics, trackPageView, trackScrollDepth, trackSectionView } from '@/lib/analytics';
import { captureUTMParams, getSessionId } from '@/lib/utm';

const SCROLL_MILESTONES = [25, 50, 75, 100];
const SECTION_IDS = ['hero', 'stats-bar', 'how-it-works', 'features-grid', 'cta', 'footer'];

export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  const scrollMilestonesReached = useRef(new Set<number>());
  const sectionsViewed = useRef(new Set<string>());

  useEffect(() => {
    // Initialize analytics
    initAnalytics();
    getSessionId();
    captureUTMParams();
    trackPageView();

    // Scroll depth tracking
    function handleScroll() {
      const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
      if (scrollHeight <= 0) return;
      const percent = Math.round((window.scrollY / scrollHeight) * 100);

      for (const milestone of SCROLL_MILESTONES) {
        if (percent >= milestone && !scrollMilestonesReached.current.has(milestone)) {
          scrollMilestonesReached.current.add(milestone);
          trackScrollDepth(milestone);
        }
      }
    }

    // Section visibility tracking
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const sectionId = entry.target.getAttribute('data-section');
          if (entry.isIntersecting && sectionId && !sectionsViewed.current.has(sectionId)) {
            sectionsViewed.current.add(sectionId);
            trackSectionView(sectionId);
          }
        }
      },
      { threshold: 0.5 }
    );

    // Observe sections after a short delay to let DOM render
    const timer = setTimeout(() => {
      for (const id of SECTION_IDS) {
        const el = document.querySelector(`[data-section="${id}"]`);
        if (el) observer.observe(el);
      }
    }, 100);

    window.addEventListener('scroll', handleScroll, { passive: true });

    return () => {
      window.removeEventListener('scroll', handleScroll);
      observer.disconnect();
      clearTimeout(timer);
    };
  }, []);

  return <>{children}</>;
}
