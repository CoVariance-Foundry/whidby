import { NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function POST(request: Request) {
  try {
    const { email, utm_source, utm_medium, utm_campaign, referrer } = await request.json();

    if (!email || typeof email !== 'string' || !email.includes('@')) {
      return NextResponse.json({ error: 'Valid email is required' }, { status: 400 });
    }

    const { error } = await supabase.from('waitlist_signups').insert({
      email: email.toLowerCase().trim(),
      utm_source,
      utm_medium,
      utm_campaign,
      referrer,
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
