import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const date = searchParams.get("date");

    if (!date) {
      // Return list of available dates
      const res = await fetch(`${BACKEND_URL}/dashboard/dates`, {
        cache: "no-store",
      });
      if (!res.ok) {
        return Response.json({ dates: [] }, { status: res.status });
      }
      return Response.json(await res.json());
    }

    // Get dashboard data for a specific date
    const res = await fetch(
      `${BACKEND_URL}/dashboard/data/${date}?run_inference_if_missing=true`,
      { cache: "no-store" }
    );

    if (!res.ok) {
      return Response.json(
        { error: "Failed to fetch dashboard data" },
        { status: res.status }
      );
    }
    return Response.json(await res.json());
  } catch (error) {
    console.error("Dashboard API error:", error);
    return Response.json({ error: "Backend unavailable" }, { status: 503 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const { date, force = false } = await request.json();

    if (!date) {
      return Response.json({ error: "date is required" }, { status: 400 });
    }

    // Trigger inference for the date
    const res = await fetch(
      `${BACKEND_URL}/dashboard/infer/${date}?force=${force}`,
      {
        method: "POST",
        cache: "no-store",
      }
    );

    if (!res.ok) {
      const error = await res.json();
      return Response.json(error, { status: res.status });
    }
    return Response.json(await res.json());
  } catch (error) {
    console.error("Dashboard inference error:", error);
    return Response.json({ error: "Backend unavailable" }, { status: 503 });
  }
}
