'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { MenuIcon, XIcon } from 'lucide-react';
import { trackCTAClick } from '@/lib/analytics';

const navLinks = [
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Pricing', href: '#pricing' },
  { label: 'About', href: '#about' },
];

interface NavbarProps {
  onOpenWaitlist: () => void;
}

export function Navbar({ onOpenWaitlist }: NavbarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleWaitlistClick = () => {
    trackCTAClick('join_waitlist', 'navbar');
    onOpenWaitlist();
  };

  return (
    <motion.nav
      initial={{ y: -10, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200"
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <a href="#" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-dark flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="6" stroke="#10B981" strokeWidth="2" />
                <circle cx="8" cy="8" r="2.5" fill="#10B981" />
              </svg>
            </div>
            <span className="font-sans font-bold text-lg text-dark tracking-tight">
              Rankread
            </span>
          </a>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-sm font-medium text-neutral-600 hover:text-dark transition-colors"
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* CTA */}
          <div className="hidden md:block">
            <button
              onClick={handleWaitlistClick}
              className="px-5 py-2.5 text-sm font-medium rounded-lg bg-dark text-white hover:bg-neutral-800 transition-colors"
            >
              Join Waitlist
            </button>
          </div>

          {/* Mobile toggle */}
          <button
            className="md:hidden p-2 text-neutral-600 hover:text-dark"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <XIcon className="w-5 h-5" /> : <MenuIcon className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="md:hidden bg-white border-t border-gray-100 px-6 py-4 space-y-3"
        >
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="block text-sm font-medium text-neutral-600 py-2"
              onClick={() => setMobileOpen(false)}
            >
              {link.label}
            </a>
          ))}
          <button
            onClick={handleWaitlistClick}
            className="w-full mt-2 px-5 py-2.5 text-sm font-medium rounded-lg bg-dark text-white"
          >
            Join Waitlist
          </button>
        </motion.div>
      )}
    </motion.nav>
  );
}
