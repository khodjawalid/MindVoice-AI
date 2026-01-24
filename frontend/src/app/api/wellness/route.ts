import { NextRequest } from "next/server";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const date = searchParams.get("date");

    // Build backend URL with optional date parameter
    const backendUrl = date
      ? `http://localhost:8000/wellness/tags?date=${date}`
      : "http://localhost:8000/wellness/tags";

    const res = await fetch(backendUrl, {
      cache: "no-store",
    });

    if (!res.ok) {
      return Response.json({ data: [], count: 0 }, { status: res.status });
    }
    return Response.json(await res.json());
  } catch {
    return Response.json(
      { error: "Backend unavailable" },
      { status: 503 }
    );
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const { reviewId, ...data } = await request.json();

    if (!reviewId) {
      return Response.json(
        { error: "reviewId is required" },
        { status: 400 }
      );
    }

    const res = await fetch(`http://localhost:8000/wellness/tags/${reviewId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (!res.ok) {
      const error = await res.json();
      return Response.json(error, { status: res.status });
    }

    return Response.json(await res.json());
  } catch {
    return Response.json(
      { error: "Backend unavailable" },
      { status: 503 }
    );
  }
}
