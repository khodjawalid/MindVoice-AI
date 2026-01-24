import { NextResponse } from "next/server";

export async function POST() {
  try {
    const res = await fetch("http://localhost:8000/sync/empatica", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
      cache: "no-store",
    });

    if (!res.ok) {
      return NextResponse.json(
        { status: "error", error: "Failed to sync" },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { status: "error", error: "Backend unavailable" },
      { status: 503 }
    );
  }
}
