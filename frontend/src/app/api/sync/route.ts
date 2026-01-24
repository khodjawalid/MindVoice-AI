import { NextResponse } from "next/server";

export async function POST() {
  try {
    // Step 1: Sync from S3 and process AVRO files
    const syncRes = await fetch("http://localhost:8000/sync/empatica", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
      cache: "no-store",
    });

    if (!syncRes.ok) {
      return NextResponse.json(
        { status: "error", error: "Failed to sync" },
        { status: syncRes.status }
      );
    }

    const syncData = await syncRes.json();

    // Step 2: Migrate processed data to Supabase
    const migrateRes = await fetch(
      `http://localhost:8000/sync/migrate/${syncData.date}`,
      {
        method: "POST",
        cache: "no-store",
      }
    );

    let migrateData = null;
    if (migrateRes.ok) {
      migrateData = await migrateRes.json();
    }

    return NextResponse.json({
      ...syncData,
      migration: migrateData,
    });
  } catch {
    return NextResponse.json(
      { status: "error", error: "Backend unavailable" },
      { status: 503 }
    );
  }
}
