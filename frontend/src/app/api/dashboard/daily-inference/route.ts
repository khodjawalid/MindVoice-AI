import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const date = searchParams.get("date");

    if (!date) {
      return NextResponse.json(
        { detail: "Date parameter is required" },
        { status: 400 }
      );
    }

    const backendResponse = await fetch(
      `${BACKEND_URL}/wellness/daily-inference/${date}`,
      {
        method: "GET",
        cache: "no-store",
      }
    );

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({}));
      return NextResponse.json(
        { detail: errorData.detail || "Failed to fetch daily inference" },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Daily inference fetch error:", error);
    return NextResponse.json(
      { detail: "Failed to fetch daily inference data" },
      { status: 500 }
    );
  }
}
