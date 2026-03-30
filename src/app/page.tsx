'use client';

import { useState } from 'react';
import { Navbar } from '@/components/Navbar';
import { HeroSection } from '@/components/HeroSection';
import { StatsBar } from '@/components/StatsBar';
import { HowItWorks } from '@/components/HowItWorks';
import { FeaturesGrid } from '@/components/FeaturesGrid';
import { CTASection } from '@/components/CTASection';
import { Footer } from '@/components/Footer';
import { WaitlistModal } from '@/components/WaitlistModal';
import { AnalyticsProvider } from '@/components/AnalyticsProvider';

export default function Home() {
  const [waitlistOpen, setWaitlistOpen] = useState(false);

  return (
    <AnalyticsProvider>
      <Navbar onOpenWaitlist={() => setWaitlistOpen(true)} />
      <main>
        <HeroSection onOpenWaitlist={() => setWaitlistOpen(true)} />
        <StatsBar />
        <HowItWorks />
        <FeaturesGrid onOpenWaitlist={() => setWaitlistOpen(true)} />
        <CTASection onOpenWaitlist={() => setWaitlistOpen(true)} />
      </main>
      <Footer />
      <WaitlistModal isOpen={waitlistOpen} onClose={() => setWaitlistOpen(false)} />
    </AnalyticsProvider>
  );
}
