'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { XIcon, CheckIcon, Loader2Icon } from 'lucide-react';
import { getStoredUTMParams } from '@/lib/utm';
import { trackWaitlistSignup } from '@/lib/analytics';

interface WaitlistModalProps {
  isOpen: boolean;
  onClose: () => void;
  source: string;
}

export function WaitlistModal({ isOpen, onClose, source }: WaitlistModalProps) {
  const [email, setEmail] = useState('');
  const [portfolioSize, setPortfolioSize] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error' | 'duplicate'>('idle');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || status === 'loading') return;

    setStatus('loading');
    const utm = getStoredUTMParams();

    try {
      const res = await fetch('/api/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          utm_source: utm.utm_source,
          utm_medium: utm.utm_medium,
          utm_campaign: utm.utm_campaign,
          referrer: document.referrer || null,
          signup_source: source,
          portfolio_size: portfolioSize || null,
        }),
      });

      if (res.status === 409) {
        setStatus('duplicate');
        return;
      }

      if (!res.ok) throw new Error('Failed');

      setStatus('success');
      trackWaitlistSignup(email, source, portfolioSize);
    } catch {
      setStatus('error');
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-60 flex items-center justify-center px-4"
          onClick={onClose}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/50" />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2 }}
            className="relative bg-white rounded-2xl shadow-xl max-w-md w-full p-8"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={onClose}
              className="absolute top-4 right-4 p-1 text-neutral-400 hover:text-dark transition-colors"
              aria-label="Close"
            >
              <XIcon className="w-5 h-5" />
            </button>

            {status === 'success' ? (
              <div className="text-center py-4">
                <div className="w-12 h-12 rounded-full bg-accent mx-auto flex items-center justify-center mb-4">
                  <CheckIcon className="w-6 h-6 text-white" strokeWidth={3} />
                </div>
                <h3 className="font-serif text-2xl text-dark mb-2">You&apos;re on the list!</h3>
                <p className="text-neutral-500">
                  We&apos;ll be in touch soon with early access details.
                </p>
              </div>
            ) : (
              <>
                <h3 className="font-serif text-2xl text-dark mb-2">Join the Waitlist</h3>
                <p className="text-neutral-500 mb-6">
                  Get early access to Widby and start scoring markets before anyone else.
                </p>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => { setEmail(e.target.value); setStatus('idle'); }}
                      placeholder="you@example.com"
                      required
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 text-dark placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent transition-colors"
                    />
                    {status === 'duplicate' && (
                      <p className="text-sm text-accent mt-2">You&apos;re already on the list!</p>
                    )}
                    {status === 'error' && (
                      <p className="text-sm text-red-500 mt-2">Something went wrong. Please try again.</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-dark mb-1.5">
                      How many R&R sites do you currently manage?
                    </label>
                    <select
                      value={portfolioSize}
                      onChange={(e) => setPortfolioSize(e.target.value)}
                      className={`w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent transition-colors ${portfolioSize ? 'text-dark' : 'text-neutral-400'}`}
                    >
                      <option value="" disabled>Select your experience level</option>
                      <option value="0">None yet — just getting started</option>
                      <option value="1-5">1–5 sites</option>
                      <option value="6-20">6–20 sites</option>
                      <option value="20+">20+ sites</option>
                    </select>
                  </div>

                  <button
                    type="submit"
                    disabled={status === 'loading'}
                    className="w-full px-6 py-3 text-base font-medium rounded-lg bg-dark text-white hover:bg-neutral-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {status === 'loading' ? (
                      <>
                        <Loader2Icon className="w-4 h-4 animate-spin" />
                        Submitting...
                      </>
                    ) : (
                      'Request Early Access'
                    )}
                  </button>
                </form>
              </>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
