import { NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { email, utm_source, utm_medium, utm_campaign, referrer } = body;

    if (!email || typeof email !== 'string' || !email.includes('@')) {
      return NextResponse.json({ error: 'Valid email is required' }, { status: 400 });
    }

    const { error } = await supabase.from('waitlist_signups').insert({
      email: email.toLowerCase().trim(),
      utm_source: utm_source || null,
      utm_medium: utm_medium || null,
      utm_campaign: utm_campaign || null,
      referrer: referrer || null,
    });

    if (error) {
      if (error.code === '23505') {
        return NextResponse.json({ success: true, message: 'Already on waitlist' });
      }
      console.error('Supabase insert error:', error);
      return NextResponse.json({ error: 'Failed to join waitlist' }, { status: 500 });
    }

    return NextResponse.json({ success: true, message: 'Added to waitlist' });
  } catch {
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }
}
