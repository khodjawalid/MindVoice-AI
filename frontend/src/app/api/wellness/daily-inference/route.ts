import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const date = searchParams.get("date");

    if (!date) {
      return NextResponse.json(
        { error: "date parameter is required" },
        { status: 400 }
      );
    }

    const response = await fetch(
      `${BACKEND_URL}/wellness/daily-inference/${date}`,
      { cache: "no-store" }
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to fetch daily inference" },
        { status: response.status }
      );
    }

    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Daily inference GET error:", error);
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const date = searchParams.get("date");

    if (!date) {
      return NextResponse.json(
        { error: "date parameter is required" },
        { status: 400 }
      );
    }

    // Forward the form data to the backend
    const formData = await request.formData();

    const response = await fetch(
      `${BACKEND_URL}/wellness/daily-inference/${date}`,
      {
        method: "POST",
        body: formData,
      }
    );

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { error: errorData.detail || "Inference failed" },
        { status: response.status }
      );
    }

    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Daily inference POST error:", error);
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    );
  }
}
