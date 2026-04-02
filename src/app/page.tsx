import { getFlag } from '@/lib/flags';
import HomeClient from './HomeClient';

export default async function Home() {
  const showPricing = await getFlag('show_pricing', true);

  return <HomeClient showPricing={showPricing} />;
}
