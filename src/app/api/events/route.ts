import { NextResponse } from 'next/server';
import { getSupabase } from '@/lib/supabase';

export async function POST(request: Request) {
  try {
    const body = await request.json();

    const {
      event_name,
      event_data,
      page_url,
      referrer,
      utm_source,
      utm_medium,
      utm_campaign,
      utm_term,
      utm_content,
      session_id,
      user_agent,
      screen_width,
    } = body;

    if (!event_name || typeof event_name !== 'string') {
      return NextResponse.json({ error: 'event_name is required' }, { status: 400 });
    }

    const supabase = getSupabase();
    const { error } = await supabase.from('analytics_events').insert({
      event_name,
      event_data: event_data || {},
      page_url,
      referrer,
      utm_source,
      utm_medium,
      utm_campaign,
      utm_term,
      utm_content,
      session_id,
      user_agent,
      screen_width,
    });

    if (error) {
      console.error('Analytics insert error:', error);
      return NextResponse.json({ error: 'Failed to store event' }, { status: 500 });
    }

    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }
}
