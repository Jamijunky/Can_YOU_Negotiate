import { AccessToken, RoomServiceClient } from "livekit-server-sdk";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { LIVEKIT_EMPTY_TIMEOUT_SECONDS, ROOM_NAME_RANDOM_MAX } from "@/lib/constants";

const tokenRequestSchema = z.object({
  room: z
    .string()
    .max(128)
    .regex(/^[a-zA-Z0-9_-]+$/, "Room name must be alphanumeric with hyphens/underscores")
    .optional(),
  username: z
    .string()
    .max(64)
    .regex(/^[a-zA-Z0-9_-]+$/, "Username must be alphanumeric with hyphens/underscores")
    .optional(),
  metadata: z.string().max(8192).optional(),
});

const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT_WINDOW_MS = 60_000;
const RATE_LIMIT_MAX = 30;

function checkRateLimit(ip: string): boolean {
  const now = Date.now();
  const entry = rateLimitMap.get(ip);
  if (!entry || now > entry.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    return true;
  }
  if (entry.count >= RATE_LIMIT_MAX) return false;
  entry.count++;
  return true;
}

export async function GET(req: NextRequest) {
  const ip = req.headers.get("x-forwarded-for") || req.headers.get("x-real-ip") || "unknown";
  if (!checkRateLimit(ip)) {
    return NextResponse.json({ error: "Rate limit exceeded. Please try again later." }, { status: 429 });
  }

  const rawRoom = req.nextUrl.searchParams.get("room");
  const rawUsername = req.nextUrl.searchParams.get("username");
  const rawMetadata = req.nextUrl.searchParams.get("metadata");

  const parsed = tokenRequestSchema.safeParse({
    room: rawRoom || undefined,
    username: rawUsername || undefined,
    metadata: rawMetadata || undefined,
  });

  if (!parsed.success) {
    return NextResponse.json(
      { error: "Invalid request parameters." },
      { status: 400 }
    );
  }

  const room = parsed.data.room || `negotiation-room-${Math.floor(Math.random() * ROOM_NAME_RANDOM_MAX)}`;
  const participantName = parsed.data.username || `Negotiator-${Math.floor(Math.random() * 1000)}`;
  const metadata = parsed.data.metadata || "";

  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;

  if (!apiKey || !apiSecret) {
    return NextResponse.json(
      { error: "Server configuration error." },
      { status: 500 }
    );
  }

  if (metadata) {
    const livekitHost = process.env.NEXT_PUBLIC_LIVEKIT_URL!.replace("wss://", "https://");
    const roomService = new RoomServiceClient(livekitHost, apiKey, apiSecret);
    try {
      await roomService.createRoom({
        name: room,
        metadata: metadata,
        emptyTimeout: LIVEKIT_EMPTY_TIMEOUT_SECONDS,
      });
    } catch {
      try {
        await roomService.updateRoomMetadata(room, metadata);
      } catch (e2: unknown) {
        const msg = e2 instanceof Error ? e2.message : "unknown error";
        console.warn("Failed to update room metadata:", msg);
      }
    }
  }

  const at = new AccessToken(apiKey, apiSecret, {
    identity: participantName,
    metadata: metadata || undefined,
  });

  at.addGrant({ roomJoin: true, room: room });

  return NextResponse.json({ token: await at.toJwt() });
}
