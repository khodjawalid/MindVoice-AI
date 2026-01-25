import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ tagId: string }> }
) {
  try {
    const { tagId } = await params;

    // Get form data from request
    const formData = await request.formData();

    // Forward to backend
    const backendResponse = await fetch(
      `${BACKEND_URL}/wellness/tags/${tagId}/inference`,
      {
        method: "POST",
        body: formData,
      }
    );

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({}));
      return NextResponse.json(
        { detail: errorData.detail || "Inference failed" },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Inference proxy error:", error);
    return NextResponse.json(
      { detail: "Failed to process video inference" },
      { status: 500 }
    );
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ tagId: string }> }
) {
  try {
    const { tagId } = await params;

    // Forward to backend
    const backendResponse = await fetch(
      `${BACKEND_URL}/wellness/tags/${tagId}/inference`,
      {
        method: "GET",
      }
    );

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({}));
      return NextResponse.json(
        { detail: errorData.detail || "Failed to get inference" },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Inference fetch error:", error);
    return NextResponse.json(
      { detail: "Failed to fetch inference data" },
      { status: 500 }
    );
  }
}
