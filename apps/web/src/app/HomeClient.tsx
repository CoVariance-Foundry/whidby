'use client';

import { useState } from 'react';
import { Navbar } from '@/components/Navbar';
import { HeroSection } from '@/components/HeroSection';
import { StatsBar } from '@/components/StatsBar';
import { HowItWorks } from '@/components/HowItWorks';
import { FeaturesGrid } from '@/components/FeaturesGrid';
import { PricingSection } from '@/components/PricingSection';
import { AboutSection } from '@/components/AboutSection';
import { CTASection } from '@/components/CTASection';
import { Footer } from '@/components/Footer';
import { WaitlistModal } from '@/components/WaitlistModal';
import { AnalyticsProvider } from '@/components/AnalyticsProvider';

export default function HomeClient({ showPricing }: { showPricing: boolean }) {
  const [waitlistOpen, setWaitlistOpen] = useState(false);
  const [waitlistSource, setWaitlistSource] = useState('');

  const openWaitlist = (source: string) => {
    setWaitlistSource(source);
    setWaitlistOpen(true);
  };

  return (
    <AnalyticsProvider>
      <Navbar onOpenWaitlist={openWaitlist} showPricing={showPricing} />
      <main>
        <HeroSection onOpenWaitlist={openWaitlist} />
        <StatsBar />
        <HowItWorks />
        <FeaturesGrid onOpenWaitlist={openWaitlist} />
        {showPricing && <PricingSection onOpenWaitlist={openWaitlist} />}
        <AboutSection />
        <CTASection onOpenWaitlist={openWaitlist} />
      </main>
      <Footer />
      <WaitlistModal isOpen={waitlistOpen} onClose={() => setWaitlistOpen(false)} source={waitlistSource} />
    </AnalyticsProvider>
  );
}
