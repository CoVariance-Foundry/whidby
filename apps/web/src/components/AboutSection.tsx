'use client';

import { motion } from 'framer-motion';
import { Brain, Target, BarChart3 } from 'lucide-react';

const pillars = [
  {
    icon: Brain,
    title: 'One viability score',
    description:
      'Not another keyword tool. Widby folds 340+ ranking signals and local business data into a single score so you know before you build.',
  },
  {
    icon: Target,
    title: 'Built for rank & rent',
    description:
      'Generic SEO tools stay generic. Widby focuses on two questions: can you rank it, and will someone pay for the leads?',
  },
  {
    icon: BarChart3,
    title: 'Live SERP analysis',
    description:
      'Real-time, geo-specific SERP pulls instead of static niche lists or stale exports. When the market moves, your read should too.',
  },
];

export function AboutSection() {
  return (
    <section id="about" data-section="about" className="py-16 lg:py-24 bg-[#fafafa]">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="mb-16 max-w-2xl">
          <motion.p
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4 }}
            className="text-sm font-medium uppercase tracking-[0.1em] text-neutral-400 mb-4"
          >
            About Widby
          </motion.p>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="font-serif text-4xl md:text-5xl text-dark leading-[1.1] mb-6"
          >
            Market intelligence, <em className="italic text-accent">purpose-built</em> for R&R.
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-neutral-500 text-lg leading-relaxed"
          >
            Most practitioners spend days pulling keyword exports, eyeballing SERPs,
            and guessing at monetization. Widby scores any niche and city pair in
            minutes instead.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-12">
          {pillars.map((pillar, index) => (
            <motion.div
              key={pillar.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: index * 0.15 }}
              className="card-gradient-border pt-8"
            >
              <pillar.icon className="w-5 h-5 text-accent mb-4" strokeWidth={2} />
              <h3 className="font-sans text-lg font-bold text-dark mb-3 leading-snug">
                {pillar.title}
              </h3>
              <p className="text-neutral-500 leading-relaxed">{pillar.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
