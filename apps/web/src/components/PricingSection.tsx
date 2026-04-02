'use client';

import { motion } from 'framer-motion';
import { CheckIcon } from 'lucide-react';
import { trackEvent } from '@/lib/analytics';

const tiers = [
  {
    name: 'Starter',
    price: 29,
    slug: 'starter',
    features: [
      '10 niche analyses / month',
      'Basic rankability scoring',
      'Email support',
    ],
    highlighted: false,
  },
  {
    name: 'Pro',
    price: 79,
    slug: 'pro',
    badge: 'Most Popular',
    features: [
      '50 niche analyses / month',
      'Full rankability + rentability scoring',
      'Lead list generation',
      'Priority support',
    ],
    highlighted: true,
  },
  {
    name: 'Scale',
    price: 199,
    slug: 'scale',
    features: [
      'Unlimited analyses',
      'Full scoring suite',
      'Lead lists + API access',
      'Dedicated support',
    ],
    highlighted: false,
  },
];

interface PricingSectionProps {
  onOpenWaitlist: (source: string) => void;
}

export function PricingSection({ onOpenWaitlist }: PricingSectionProps) {
  const handleTierClick = (slug: string, price: number) => {
    trackEvent('pricing_tier_click', { tier: slug, price });
    onOpenWaitlist(`pricing_${slug}`);
  };

  return (
    <section id="pricing" data-section="pricing" className="py-16 lg:py-24 bg-white">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="text-center mb-16">
          <p className="text-sm font-medium uppercase tracking-[0.1em] text-neutral-400 mb-4">Pricing</p>
          <h2 className="font-serif text-4xl md:text-5xl text-dark leading-[1.1]">
            Simple pricing. <em className="italic text-accent">Serious</em> tools.
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-10">
          {tiers.map((tier, index) => (
            <motion.div
              key={tier.slug}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: index * 0.15 }}
              className={`relative bg-white rounded-2xl border p-8 flex flex-col ${
                tier.highlighted
                  ? 'border-accent ring-2 ring-accent'
                  : 'border-gray-200'
              }`}
            >
              {tier.badge && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-accent text-white text-xs font-semibold rounded-full">
                  {tier.badge}
                </span>
              )}

              <h3 className="font-sans text-lg font-bold text-dark mb-2">{tier.name}</h3>
              <div className="mb-6">
                <span className="font-serif text-4xl text-dark">${tier.price}</span>
                <span className="text-neutral-400 text-sm">/mo</span>
              </div>

              <ul className="space-y-3 mb-8 flex-1">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2.5">
                    <CheckIcon className="w-4 h-4 text-accent shrink-0 mt-0.5" strokeWidth={3} />
                    <span className="text-sm text-neutral-600">{feature}</span>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleTierClick(tier.slug, tier.price)}
                className={`w-full px-6 py-3 text-base font-medium rounded-lg transition-colors ${
                  tier.highlighted
                    ? 'bg-dark text-white hover:bg-neutral-800'
                    : 'border border-gray-300 text-neutral-600 hover:bg-gray-50'
                }`}
              >
                Join Waitlist
              </button>
            </motion.div>
          ))}
        </div>

        <p className="text-center text-sm text-neutral-400 mt-10">
          All plans include a 14-day free trial. No credit card required.
        </p>
      </div>
    </section>
  );
}
