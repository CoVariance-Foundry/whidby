'use client';

import { motion } from 'framer-motion';

const tags = [
  'Rank & Rent',
  'Local Lead Gen',
  'Digital Landlords',
  'Local SEO',
  'Portfolio Operators',
];

export function StatsBar() {
  return (
    <motion.section
      data-section="stats-bar"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, delay: 0.4 }}
      className="py-5 border-y border-gray-200 bg-white"
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-6">
          <span className="text-sm text-neutral-400 shrink-0">
            Built for practitioners who know
          </span>
          <div className="hidden sm:block w-px h-5 bg-gray-200" />
          <div className="flex flex-wrap items-center gap-2.5">
            {tags.map((tag) => (
              <span
                key={tag}
                className="px-4 py-1.5 rounded-full border border-gray-300 text-sm font-mono text-neutral-600"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>
    </motion.section>
  );
}
