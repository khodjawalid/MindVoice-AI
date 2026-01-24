import { HeartRateChartWrapper } from "@/components/HeartRateChartWrapper";

async function getMetrics() {
  try {
    const res = await fetch("http://localhost:8000/metrics", {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export default async function MetricsPage() {
  const json = await getMetrics();

  return (
    <main className="p-8 space-y-8">
      <h1 className="text-2xl font-bold">Metrics</h1>

      <HeartRateChartWrapper data={json?.data || []} />

      {json && (
        <pre className="text-xs bg-muted p-4 rounded">
          {JSON.stringify(json, null, 2)}
        </pre>
      )}
    </main>
  );
}
