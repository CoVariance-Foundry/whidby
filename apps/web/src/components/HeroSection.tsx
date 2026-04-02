'use client';

import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { CheckIcon } from 'lucide-react';
import { trackCTAClick } from '@/lib/analytics';

const metrics = [
  { label: 'Search demand', value: 91, color: '#10B981' },
  { label: 'Map pack gap', value: 78, color: '#3B82F6' },
  { label: 'Competition depth', value: 62, color: '#F59E0B' },
  { label: 'Rentability signal', value: 84, color: '#14B8A6' },
];

function ProgressBar({ label, value, color, delay }: { label: string; value: number; color: string; delay: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true });
  return (
    <div ref={ref} className="flex items-center gap-4">
      <span className="text-sm text-neutral-500 w-36 shrink-0">{label}</span>
      <div className="progress-track">
        <motion.div
          className="progress-fill"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={inView ? { width: `${value}%` } : { width: 0 }}
          transition={{ duration: 0.8, delay, ease: 'easeOut' }}
        />
      </div>
      <span className="text-sm font-semibold text-dark w-8 text-right">{value}</span>
    </div>
  );
}

interface HeroSectionProps {
  onOpenWaitlist: (source: string) => void;
}

export function HeroSection({ onOpenWaitlist }: HeroSectionProps) {
  const handleRequestAccess = () => {
    trackCTAClick('request_early_access', 'hero');
    onOpenWaitlist('hero');
  };

  const handleSeeHowItWorks = () => {
    trackCTAClick('see_how_it_works', 'hero');
    document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section data-section="hero" className="pt-28 pb-8 lg:pt-36 lg:pb-12 bg-white">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20 items-center">
          {/* Left column: headline and CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <span className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-gray-200 text-sm text-neutral-700 mb-8">
              <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
              Now in early access
            </span>

            <h1 className="font-serif text-5xl md:text-6xl lg:text-[3.75rem] leading-[1.1] text-dark mb-6">
              You can rank it.
              <br />
              <em className="not-italic italic">But can you</em>
              <br />
              <span className="line-through decoration-neutral-400 decoration-2">guess</span>{' '}
              <em className="italic text-accent">rent it?</em>
            </h1>

            <p className="text-base md:text-lg text-neutral-500 leading-relaxed max-w-md mb-8">
              Score any niche and city for rankability and rentability before you
              ship a page. Built for rank-and-rent operators.
            </p>

            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={handleRequestAccess}
                className="px-6 py-3 text-base font-medium rounded-lg bg-dark text-white hover:bg-neutral-800 transition-colors"
              >
                Request Early Access &rarr;
              </button>
              <button
                onClick={handleSeeHowItWorks}
                className="px-6 py-3 text-base font-medium rounded-lg border border-gray-300 text-neutral-600 hover:bg-gray-50 transition-colors"
              >
                See how it works
              </button>
            </div>
          </motion.div>

          {/* Right column: example score card */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="relative"
          >
            <div className="absolute -top-3 right-4 z-10">
              <span className="inline-block px-3.5 py-1.5 bg-accent text-white text-sm font-semibold rounded-lg shadow-md">
                87 / 100 · Build here
              </span>
            </div>

            <div className="bg-white rounded-2xl border border-gray-200 shadow-lg p-6 md:p-8">
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h3 className="text-xl font-bold text-dark">Tree Service</h3>
                  <p className="text-sm text-neutral-400 mt-0.5">Austin, TX &middot; analyzed just now</p>
                </div>
                <div className="score-circle">
                  <span className="text-2xl font-bold text-accent leading-none">87</span>
                  <span className="text-[9px] font-semibold text-accent uppercase tracking-wider">Score</span>
                </div>
              </div>

              <div className="space-y-4 mb-6">
                {metrics.map((m, i) => (
                  <ProgressBar key={m.label} label={m.label} value={m.value} color={m.color} delay={0.3 + i * 0.1} />
                ))}
              </div>

              <div className="bg-accent-bg border border-accent/20 rounded-xl p-4 flex gap-3">
                <div className="w-5 h-5 rounded-full bg-accent flex items-center justify-center shrink-0 mt-0.5">
                  <CheckIcon className="w-3 h-3 text-white" strokeWidth={3} />
                </div>
                <p className="text-sm text-neutral-700 leading-relaxed">
                  <strong className="font-semibold">Strong opportunity.</strong>{' '}
                  12 local businesses running paid ads. High ticket value ($1,200+ avg job). Map pack has 2 weak incumbents. Build here.
                </p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
