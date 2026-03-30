'use client';

import { useState } from 'react';
import { AnalyticsProvider } from '@/components/AnalyticsProvider';
import { Navbar } from '@/components/Navbar';
import { HeroSection } from '@/components/HeroSection';
import { StatsBar } from '@/components/StatsBar';
import { HowItWorks } from '@/components/HowItWorks';
import { FeaturesGrid } from '@/components/FeaturesGrid';
import { CTASection } from '@/components/CTASection';
import { Footer } from '@/components/Footer';
import { WaitlistModal } from '@/components/WaitlistModal';

export default function Home() {
  const [waitlistOpen, setWaitlistOpen] = useState(false);
  const [waitlistSource, setWaitlistSource] = useState('navbar');

  function openWaitlist(source: string = 'navbar') {
    setWaitlistSource(source);
    setWaitlistOpen(true);
  }

  return (
    <AnalyticsProvider>
      <Navbar onWaitlistOpen={() => openWaitlist('navbar')} />
      <main>
        <HeroSection onWaitlistOpen={() => openWaitlist('hero')} />
        <StatsBar />
        <HowItWorks />
        <FeaturesGrid onWaitlistOpen={() => openWaitlist('features_grid')} />
        <CTASection onWaitlistOpen={() => openWaitlist('cta_section')} />
      </main>
      <Footer />
      <WaitlistModal
        isOpen={waitlistOpen}
        onClose={() => setWaitlistOpen(false)}
        source={waitlistSource}
      />
    </AnalyticsProvider>
  );
}
