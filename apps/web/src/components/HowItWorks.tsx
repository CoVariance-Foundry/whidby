'use client';

import { motion } from 'framer-motion';

const features = [
  {
    num: '01',
    title: 'Rankability: can you win this market?',
    description:
      'SERP depth, map pack saturation, incumbent domain strength. 340+ signals roll up into one rankability score so you are not guessing from keywords alone.',
  },
  {
    num: '02',
    title: 'Rentability: will businesses pay for these leads?',
    description:
      'Business density, ad spend, average ticket size by vertical. That is what tells you whether a ranked site can actually monetize.',
  },
  {
    num: '03',
    title: 'Real SERP data, not a static niche list.',
    description:
      'Live local SERPs for the markets you pick, refreshed on demand. No recycled spreadsheet and no course PDF.',
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" data-section="how-it-works" className="py-16 lg:py-24 bg-white">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="mb-16 max-w-2xl">
          <p className="text-sm font-medium uppercase tracking-[0.1em] text-neutral-400 mb-4">Why Widby</p>
          <h2 className="font-serif text-4xl md:text-5xl text-dark leading-[1.1]">
            The missing piece in most R&R{' '}
            <em className="italic text-accent">workflows.</em>
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-12">
          {features.map((feature, index) => (
            <motion.div
              key={feature.num}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: index * 0.15 }}
              className="card-gradient-border pt-8"
            >
              <span className="font-mono text-sm text-neutral-400 block mb-4">{feature.num}</span>
              <h3 className="font-sans text-lg font-bold text-dark mb-3 leading-snug">{feature.title}</h3>
              <p className="text-neutral-500 leading-relaxed">{feature.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
