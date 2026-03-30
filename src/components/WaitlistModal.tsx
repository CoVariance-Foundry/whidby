'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { XIcon, CheckIcon } from 'lucide-react';
import { trackWaitlistSignup } from '@/lib/analytics';
import { captureUTMParams } from '@/lib/utm';

interface WaitlistModalProps {
  isOpen: boolean;
  onClose: () => void;
  source: string;
}

export function WaitlistModal({ isOpen, onClose, source }: WaitlistModalProps) {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || status === 'loading') return;

    setStatus('loading');
    const utm = captureUTMParams();

    try {
      const res = await fetch('/api/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          ...utm,
          referrer: document.referrer || null,
        }),
      });

      const data = await res.json();

      if (res.ok) {
        setStatus('success');
        setMessage(data.message || 'You\'re on the list!');
        trackWaitlistSignup(email, source);
      } else {
        setStatus('error');
        setMessage(data.error || 'Something went wrong');
      }
    } catch {
      setStatus('error');
      setMessage('Network error. Please try again.');
    }
  }

  function handleClose() {
    setEmail('');
    setStatus('idle');
    setMessage('');
    onClose();
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-60 flex items-center justify-center px-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/50"
            onClick={handleClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2 }}
            className="relative bg-white rounded-2xl shadow-xl w-full max-w-md p-8"
          >
            <button
              onClick={handleClose}
              className="absolute top-4 right-4 text-neutral-400 hover:text-dark transition-colors"
              aria-label="Close modal"
            >
              <XIcon className="w-5 h-5" />
            </button>

            {status === 'success' ? (
              <div className="text-center py-4">
                <div className="w-12 h-12 rounded-full bg-accent flex items-center justify-center mx-auto mb-4">
                  <CheckIcon className="w-6 h-6 text-white" strokeWidth={3} />
                </div>
                <h3 className="font-serif text-2xl text-dark mb-2">You&apos;re in!</h3>
                <p className="text-neutral-500">{message}</p>
              </div>
            ) : (
              <>
                <h3 className="font-serif text-2xl text-dark mb-2">
                  Request Early Access
                </h3>
                <p className="text-neutral-500 text-sm mb-6">
                  Join the waitlist and be first to score niches with Rankread.
                </p>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      required
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 text-dark placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent transition-colors"
                    />
                  </div>

                  {status === 'error' && (
                    <p className="text-sm text-red-500">{message}</p>
                  )}

                  <button
                    type="submit"
                    disabled={status === 'loading'}
                    className="w-full px-6 py-3 text-base font-medium rounded-lg bg-dark text-white hover:bg-neutral-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {status === 'loading' ? 'Joining...' : 'Join Waitlist'}
                  </button>
                </form>

                <p className="text-xs text-neutral-400 text-center mt-4">
                  No spam. We&apos;ll only email you when access is ready.
                </p>
              </>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
