'use client';

import { motion } from 'framer-motion';
import { CheckIcon } from 'lucide-react';
import { trackCTAClick } from '@/lib/analytics';

interface CTASectionProps {
  onOpenWaitlist: (source: string) => void;
}

export function CTASection({ onOpenWaitlist }: CTASectionProps) {
  const handleRequestAccess = () => {
    trackCTAClick('request_early_access', 'cta_section');
    onOpenWaitlist('cta_section');
  };

  return (
    <section data-section="cta" className="py-20 lg:py-28 bg-white">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 text-center">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center"
        >
          <h2 className="font-serif text-3xl md:text-4xl text-dark mb-6 leading-tight">
            Stop guessing. Start <em className="italic text-accent">scoring.</em>
          </h2>
          <p className="text-neutral-500 max-w-md mb-8 leading-relaxed">
            Validate a market in minutes instead of days. Request access and we will
            email you when your spot opens.
          </p>
          <button
            onClick={handleRequestAccess}
            className="px-6 py-3 text-base font-medium rounded-lg bg-dark text-white hover:bg-neutral-800 transition-colors mb-6"
          >
            Request Early Access &rarr;
          </button>
          <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-accent/30 bg-accent-bg text-sm text-accent font-medium">
            <CheckIcon className="w-3.5 h-3.5" strokeWidth={3} />
            Early access open now
          </span>
        </motion.div>
      </div>
    </section>
  );
}
