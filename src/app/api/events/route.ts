import { NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

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

    const { error } = await supabase.from('analytics_events').insert({
      event_name,
      event_data: event_data || {},
      page_url: page_url || null,
      referrer: referrer || null,
      utm_source: utm_source || null,
      utm_medium: utm_medium || null,
      utm_campaign: utm_campaign || null,
      utm_term: utm_term || null,
      utm_content: utm_content || null,
      session_id: session_id || null,
      user_agent: user_agent || null,
      screen_width: screen_width || null,
    });

    if (error) {
      console.error('Supabase insert error:', error);
      return NextResponse.json({ error: 'Failed to store event' }, { status: 500 });
    }

    return NextResponse.json({ success: true });
  } catch {
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }
}
