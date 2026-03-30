import { NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function POST(request: Request) {
  try {
    const { email, utm_source, utm_medium, utm_campaign, referrer, portfolio_size, signup_source } = await request.json();

    if (!email || typeof email !== 'string' || !email.includes('@')) {
      return NextResponse.json({ error: 'Valid email is required' }, { status: 400 });
    }

    const selected_tier = signup_source?.startsWith('pricing_')
      ? signup_source.replace('pricing_', '')
      : null;

    const { error } = await supabase.from('waitlist_signups').insert({
      email: email.toLowerCase().trim(),
      utm_source,
      utm_medium,
      utm_campaign,
      referrer,
      portfolio_size: portfolio_size || null,
      signup_source: signup_source || null,
      selected_tier,
    });

    if (error) {
      if (error.code === '23505') {
        return NextResponse.json({ error: 'already_signed_up' }, { status: 409 });
      }
      console.error('Waitlist insert error:', error);
      return NextResponse.json({ error: 'Failed to sign up' }, { status: 500 });
    }

    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }
}
