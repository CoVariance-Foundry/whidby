import { NextResponse } from 'next/server';
import { getSupabase } from '@/lib/supabase';
import { tagContactFromSurvey } from '@/lib/activecampaign';

export async function POST(request: Request) {
  try {
    const { email, contactId, businessSize, sitesManaged, useCases } = await request.json();

    if (!email || !businessSize || !sitesManaged || !Array.isArray(useCases)) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    // Store in Supabase
    const { error } = await getSupabase().from('onboarding_responses').insert({
      email: email.toLowerCase().trim(),
      business_size: businessSize,
      sites_managed: sitesManaged,
      use_cases: useCases,
    });

    if (error) {
      console.error('Onboarding insert error:', error);
      return NextResponse.json({ error: 'Failed to store response' }, { status: 500 });
    }

    // Tag contact in ActiveCampaign (non-blocking)
    if (contactId) {
      try {
        await tagContactFromSurvey(contactId, { businessSize, sitesManaged, useCases });
      } catch (acError) {
        console.error('ActiveCampaign tagging error:', acError);
      }
    }

    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }
}
