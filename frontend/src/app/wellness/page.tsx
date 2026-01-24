import { TagReviewList } from "@/components/TagReviewList";

async function getTags() {
  try {
    const res = await fetch("http://localhost:8000/wellness/tags", {
      cache: "no-store",
    });
    if (!res.ok) return { data: [], count: 0 };
    return await res.json();
  } catch {
    return { data: [], count: 0 };
  }
}

export default async function WellnessPage() {
  const tags = await getTags();

  return (
    <main className="p-8 space-y-8">
      <h1 className="text-2xl font-bold">Wellness Tags</h1>
      <p className="text-muted-foreground">{tags.count} tags found</p>
      <TagReviewList data={tags.data} />
    </main>
  );
}
