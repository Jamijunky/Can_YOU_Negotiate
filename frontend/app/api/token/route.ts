import { AccessToken, RoomServiceClient } from 'livekit-server-sdk';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  const room = req.nextUrl.searchParams.get('room') || `negotiation-room-${Math.floor(Math.random() * 10000)}`;
  const participantName = req.nextUrl.searchParams.get('username') || `Negotiator-${Math.floor(Math.random() * 1000)}`;
  const metadata = req.nextUrl.searchParams.get('metadata') || '';

  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;

  if (!apiKey || !apiSecret) {
    return NextResponse.json(
      { error: 'LiveKit API key and secret are required' },
      { status: 500 }
    );
  }

  // Proactively ping Render agent to wake it up if idle
  fetch('https://can-you-negotiate-agent.onrender.com', {
    signal: AbortSignal.timeout(2000),
  }).catch(() => {});

  if (metadata) {
    const roomService = new RoomServiceClient(
      process.env.NEXT_PUBLIC_LIVEKIT_URL!.replace('wss://', 'https://'),
      apiKey,
      apiSecret
    );
    // Fire room creation in background without blocking token delivery
    roomService.createRoom({
      name: room,
      metadata: metadata,
      emptyTimeout: 10 * 60,
    }).catch((e) => {
      console.warn('Non-blocking room creation notice:', e.message);
    });
  }

  const at = new AccessToken(apiKey, apiSecret, {
    identity: participantName,
    metadata: metadata || undefined,
  });

  at.addGrant({ roomJoin: true, room: room });

  return NextResponse.json({ token: await at.toJwt() });
}
