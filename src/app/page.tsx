'use client';

import { useState } from 'react';
import { Navbar } from '@/components/Navbar';
import { HeroSection } from '@/components/HeroSection';
import { StatsBar } from '@/components/StatsBar';
import { HowItWorks } from '@/components/HowItWorks';
import { FeaturesGrid } from '@/components/FeaturesGrid';
import { PricingSection } from '@/components/PricingSection';
import { CTASection } from '@/components/CTASection';
import { Footer } from '@/components/Footer';
import { WaitlistModal } from '@/components/WaitlistModal';
import { AnalyticsProvider } from '@/components/AnalyticsProvider';

export default function Home() {
  const [waitlistOpen, setWaitlistOpen] = useState(false);
  const [waitlistSource, setWaitlistSource] = useState('');

  const openWaitlist = (source: string) => {
    setWaitlistSource(source);
    setWaitlistOpen(true);
  };

  return (
    <AnalyticsProvider>
      <Navbar onOpenWaitlist={openWaitlist} />
      <main>
        <HeroSection onOpenWaitlist={openWaitlist} />
        <StatsBar />
        <HowItWorks />
        <FeaturesGrid onOpenWaitlist={openWaitlist} />
        <PricingSection onOpenWaitlist={openWaitlist} />
        <CTASection onOpenWaitlist={openWaitlist} />
      </main>
      <Footer />
      <WaitlistModal isOpen={waitlistOpen} onClose={() => setWaitlistOpen(false)} source={waitlistSource} />
    </AnalyticsProvider>
  );
}
