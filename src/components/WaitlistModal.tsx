'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { XIcon, CheckIcon, Loader2Icon, ArrowLeftIcon } from 'lucide-react';
import { getStoredUTMParams } from '@/lib/utm';
import { trackWaitlistSignup, trackEvent } from '@/lib/analytics';

interface WaitlistModalProps {
  isOpen: boolean;
  onClose: () => void;
  source: string;
}

const BUSINESS_SIZES = [
  { value: 'solo', label: 'Solo practitioner', desc: 'Just me' },
  { value: 'small-team', label: 'Small team', desc: '2-5 people' },
  { value: 'agency', label: 'Agency', desc: '6-20 people' },
  { value: 'enterprise', label: 'Enterprise', desc: '20+ people' },
];

const SITES_MANAGED = [
  { value: '0', label: 'Just starting', desc: 'No sites yet' },
  { value: '1-5', label: '1-5 sites', desc: 'Getting going' },
  { value: '6-20', label: '6-20 sites', desc: 'Growing portfolio' },
  { value: '20+', label: '20+ sites', desc: 'Scaled operation' },
];

const USE_CASES = [
  { value: 'niche-discovery', label: 'Niche discovery', desc: 'Find profitable niches' },
  { value: 'market-validation', label: 'Market validation', desc: 'Score before you build' },
  { value: 'competitor-analysis', label: 'Competitor analysis', desc: 'Understand the landscape' },
  { value: 'portfolio-management', label: 'Portfolio management', desc: 'Track existing sites' },
];

type Status = 'idle' | 'loading' | 'error' | 'duplicate';

const slideVariants = {
  enter: (direction: number) => ({ x: direction > 0 ? 80 : -80, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (direction: number) => ({ x: direction > 0 ? -80 : 80, opacity: 0 }),
};

export function WaitlistModal({ isOpen, onClose, source }: WaitlistModalProps) {
  const [step, setStep] = useState(1);
  const [direction, setDirection] = useState(1);
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<Status>('idle');
  const [contactId, setContactId] = useState<number | null>(null);
  const [businessSize, setBusinessSize] = useState('');
  const [sitesManaged, setSitesManaged] = useState('');
  const [useCases, setUseCases] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const totalSteps = 4;

  const goTo = (next: number) => {
    setDirection(next > step ? 1 : -1);
    setStep(next);
    trackEvent('onboarding_step_viewed', { step: next });
  };

  const handleEmailSubmit = async (e: React.FormEvent) => {
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
        }),
      });

      if (res.status === 409) {
        setStatus('duplicate');
        return;
      }
      if (!res.ok) throw new Error('Failed');

      const data = await res.json();
      setContactId(data.contactId ?? null);
      trackEvent('onboarding_step_completed', { step: 1, answer: email, source });
      goTo(2);
      setStatus('idle');
    } catch {
      setStatus('error');
    }
  };

  const handleBusinessSize = (value: string) => {
    setBusinessSize(value);
    trackEvent('onboarding_step_completed', { step: 2, answer: value });
    goTo(3);
  };

  const handleSitesManaged = (value: string) => {
    setSitesManaged(value);
    trackEvent('onboarding_step_completed', { step: 3, answer: value });
    goTo(4);
  };

  const toggleUseCase = (value: string) => {
    setUseCases((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  };

  const handleUseCasesSubmit = async () => {
    if (useCases.length === 0 || submitting) return;
    setSubmitting(true);

    try {
      await fetch('/api/onboarding', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          contactId,
          businessSize,
          sitesManaged,
          useCases,
        }),
      });

      trackWaitlistSignup(email, source, sitesManaged);
      trackEvent('onboarding_complete', {
        business_size: businessSize,
        sites_managed: sitesManaged,
        use_cases: useCases,
      });
    } catch {
      // Non-blocking — still show thank you
    }

    setSubmitting(false);
    goTo(5);
  };

  const handleClose = () => {
    onClose();
    setTimeout(() => {
      setStep(1);
      setEmail('');
      setStatus('idle');
      setContactId(null);
      setBusinessSize('');
      setSitesManaged('');
      setUseCases([]);
    }, 300);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-60 flex items-center justify-center px-4"
          onClick={handleClose}
        >
          <div className="absolute inset-0 bg-black/50" />

          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2 }}
            className="relative bg-white rounded-2xl shadow-xl max-w-md w-full p-8 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={handleClose}
              className="absolute top-4 right-4 p-1 text-neutral-400 hover:text-dark transition-colors z-10"
              aria-label="Close"
            >
              <XIcon className="w-5 h-5" />
            </button>

            {step >= 2 && step <= 4 && (
              <button
                onClick={() => goTo(step - 1)}
                className="absolute top-4 left-4 p-1 text-neutral-400 hover:text-dark transition-colors z-10"
                aria-label="Back"
              >
                <ArrowLeftIcon className="w-5 h-5" />
              </button>
            )}

            {step <= 4 && (
              <div className="flex items-center justify-center gap-2 mb-6">
                {Array.from({ length: totalSteps }, (_, i) => (
                  <div
                    key={i}
                    className={`h-1.5 rounded-full transition-all duration-300 ${
                      i + 1 === step
                        ? 'w-6 bg-accent'
                        : i + 1 < step
                          ? 'w-1.5 bg-accent/40'
                          : 'w-1.5 bg-gray-200'
                    }`}
                  />
                ))}
              </div>
            )}

            <AnimatePresence mode="wait" custom={direction}>
              {step === 1 && (
                <motion.div
                  key="step1"
                  custom={direction}
                  variants={slideVariants}
                  initial="enter"
                  animate="center"
                  exit="exit"
                  transition={{ duration: 0.25 }}
                >
                  <h3 className="font-serif text-2xl text-dark mb-2">Join the Waitlist</h3>
                  <p className="text-neutral-500 mb-6">
                    Get early access to Rankread and start scoring markets before anyone else.
                  </p>
                  <form onSubmit={handleEmailSubmit} className="space-y-4">
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
                </motion.div>
              )}

              {step === 2 && (
                <motion.div
                  key="step2"
                  custom={direction}
                  variants={slideVariants}
                  initial="enter"
                  animate="center"
                  exit="exit"
                  transition={{ duration: 0.25 }}
                >
                  <h3 className="font-serif text-2xl text-dark mb-2">What size is your business?</h3>
                  <p className="text-neutral-500 mb-6">Help us tailor the experience for you.</p>
                  <div className="space-y-3">
                    {BUSINESS_SIZES.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => handleBusinessSize(opt.value)}
                        className="w-full text-left px-4 py-3.5 rounded-xl border border-gray-200 hover:border-accent hover:bg-accent-bg transition-all group"
                      >
                        <span className="font-medium text-dark group-hover:text-accent transition-colors">{opt.label}</span>
                        <span className="text-sm text-neutral-400 ml-2">{opt.desc}</span>
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}

              {step === 3 && (
                <motion.div
                  key="step3"
                  custom={direction}
                  variants={slideVariants}
                  initial="enter"
                  animate="center"
                  exit="exit"
                  transition={{ duration: 0.25 }}
                >
                  <h3 className="font-serif text-2xl text-dark mb-2">How many R&R sites do you manage?</h3>
                  <p className="text-neutral-500 mb-6">We&apos;ll prioritize features that matter for your scale.</p>
                  <div className="space-y-3">
                    {SITES_MANAGED.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => handleSitesManaged(opt.value)}
                        className="w-full text-left px-4 py-3.5 rounded-xl border border-gray-200 hover:border-accent hover:bg-accent-bg transition-all group"
                      >
                        <span className="font-medium text-dark group-hover:text-accent transition-colors">{opt.label}</span>
                        <span className="text-sm text-neutral-400 ml-2">{opt.desc}</span>
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}

              {step === 4 && (
                <motion.div
                  key="step4"
                  custom={direction}
                  variants={slideVariants}
                  initial="enter"
                  animate="center"
                  exit="exit"
                  transition={{ duration: 0.25 }}
                >
                  <h3 className="font-serif text-2xl text-dark mb-2">What do you want help with?</h3>
                  <p className="text-neutral-500 mb-6">Select all that apply.</p>
                  <div className="space-y-3 mb-6">
                    {USE_CASES.map((opt) => {
                      const selected = useCases.includes(opt.value);
                      return (
                        <button
                          key={opt.value}
                          onClick={() => toggleUseCase(opt.value)}
                          className={`w-full text-left px-4 py-3.5 rounded-xl border transition-all ${
                            selected
                              ? 'border-accent bg-accent-bg'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <span className={`font-medium ${selected ? 'text-accent' : 'text-dark'}`}>
                                {opt.label}
                              </span>
                              <span className="text-sm text-neutral-400 ml-2">{opt.desc}</span>
                            </div>
                            {selected && (
                              <CheckIcon className="w-4 h-4 text-accent shrink-0" strokeWidth={3} />
                            )}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                  <button
                    onClick={handleUseCasesSubmit}
                    disabled={useCases.length === 0 || submitting}
                    className="w-full px-6 py-3 text-base font-medium rounded-lg bg-dark text-white hover:bg-neutral-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {submitting ? (
                      <>
                        <Loader2Icon className="w-4 h-4 animate-spin" />
                        Finishing up...
                      </>
                    ) : (
                      'Continue \u2192'
                    )}
                  </button>
                </motion.div>
              )}

              {step === 5 && (
                <motion.div
                  key="step5"
                  custom={direction}
                  variants={slideVariants}
                  initial="enter"
                  animate="center"
                  exit="exit"
                  transition={{ duration: 0.25 }}
                  className="text-center py-4"
                >
                  <div className="w-12 h-12 rounded-full bg-accent mx-auto flex items-center justify-center mb-4">
                    <CheckIcon className="w-6 h-6 text-white" strokeWidth={3} />
                  </div>
                  <h3 className="font-serif text-2xl text-dark mb-2">You&apos;re all set!</h3>
                  <p className="text-neutral-500 mb-1">
                    We&apos;ll be in touch soon with early access details.
                  </p>
                  <p className="text-sm text-neutral-400">
                    Keep an eye on your inbox at <strong className="text-dark">{email}</strong>
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
