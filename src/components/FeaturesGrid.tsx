'use client';

import { motion } from 'framer-motion';
import { CheckIcon } from 'lucide-react';
import { trackCTAClick } from '@/lib/analytics';

const capabilities = [
  { name: 'Rankability scoring', rankread: true, others: true },
  { name: 'Rentability analysis', rankread: true, others: false },
  { name: 'Business density signals', rankread: true, others: false },
  { name: 'Ad spend indicators', rankread: true, others: false },
  { name: 'R&R-specific scoring', rankread: true, others: false },
  { name: 'Live SERP analysis', rankread: true, others: false },
];

interface FeaturesGridProps {
  onOpenWaitlist: () => void;
}

export function FeaturesGrid({ onOpenWaitlist }: FeaturesGridProps) {
  const handleStopGuessing = () => {
    trackCTAClick('stop_guessing', 'features_grid');
    onOpenWaitlist();
  };

  return (
    <section data-section="features-grid" className="py-16 lg:py-24 bg-dark">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20 items-center">
          {/* Left — Copy */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <p className="text-sm font-medium uppercase tracking-[0.1em] text-neutral-500 mb-4">The Old Way</p>
            <h2 className="font-serif text-3xl md:text-4xl lg:text-5xl text-white leading-[1.1] mb-6">
              Five tabs. Three tools. A spreadsheet.
              <br />
              <em className="italic text-accent">And you still weren&apos;t sure.</em>
            </h2>
            <p className="text-neutral-400 leading-relaxed max-w-md mb-8">
              The average R&R practitioner spends 18+ hours manually validating a single market — bouncing between
              keyword tools, checking map packs, counting reviews, estimating ticket values. And still gets it wrong
              half the time.
            </p>
            <button
              onClick={handleStopGuessing}
              className="px-6 py-3 text-base font-medium rounded-lg border border-neutral-600 text-white hover:bg-white/5 transition-colors"
            >
              Stop guessing &rarr;
            </button>
          </motion.div>

          {/* Right — Comparison Table */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.15 }}
          >
            <div className="bg-dark-card rounded-2xl overflow-hidden border border-neutral-800">
              <div className="grid grid-cols-[1fr_100px_100px] px-6 py-4 border-b border-neutral-800">
                <span className="text-xs font-medium uppercase tracking-wider text-neutral-500">Capability</span>
                <span className="text-xs font-medium uppercase tracking-wider text-accent text-center">Rankread</span>
                <span className="text-xs font-medium uppercase tracking-wider text-neutral-500 text-center">Others</span>
              </div>

              {capabilities.map((cap, i) => (
                <div
                  key={cap.name}
                  className={`grid grid-cols-[1fr_100px_100px] px-6 py-4 ${i < capabilities.length - 1 ? 'border-b border-neutral-800/60' : ''}`}
                >
                  <span className="text-sm text-neutral-300">{cap.name}</span>
                  <div className="flex justify-center">
                    {cap.rankread && <CheckIcon className="w-4 h-4 text-accent" strokeWidth={3} />}
                  </div>
                  <div className="flex justify-center">
                    {cap.others ? (
                      <CheckIcon className="w-4 h-4 text-neutral-500" strokeWidth={3} />
                    ) : (
                      <span className="text-neutral-600">&mdash;</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
