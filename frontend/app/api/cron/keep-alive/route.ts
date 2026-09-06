import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const res = await fetch('https://can-you-negotiate-agent.onrender.com', {
      method: 'GET',
      headers: {
        'User-Agent': 'Vercel-Cron',
      }
    });
    return NextResponse.json({ status: 'ok', target_status: res.status });
  } catch (error: any) {
    return NextResponse.json({ status: 'error', message: error.message }, { status: 500 });
  }
}
