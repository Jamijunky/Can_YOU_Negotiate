import { NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/constants";

export const maxDuration = 30;

export async function GET() {
  try {
    const res = await fetch(BACKEND_URL, {
      method: "GET",
      headers: { "User-Agent": "Vercel-Cron" },
    });
    return NextResponse.json({ status: "ok", target_status: res.status });
  } catch {
    return NextResponse.json(
      { status: "error", message: "Failed to reach backend." },
      { status: 500 }
    );
  }
}
