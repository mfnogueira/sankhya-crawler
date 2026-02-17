const EMBEDDING_SERVICE_URL =
  process.env.EMBEDDING_SERVICE_URL || "http://localhost:8000";

const RERANK_TOP_K = 5;

export async function rerankSections(question, sections) {
  if (!sections.length) return [];

  const documents = sections.map((s) => s.text);

  const res = await fetch(`${EMBEDDING_SERVICE_URL}/rerank`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: question,
      documents,
      top_k: RERANK_TOP_K,
    }),
    signal: AbortSignal.timeout(60_000),
  });

  if (!res.ok) {
    console.error(`Reranker error: ${res.status}, falling back to original order`);
    return sections.slice(0, RERANK_TOP_K);
  }

  const { results } = await res.json();

  return results.map((r) => ({
    ...sections[r.index],
    rerank_score: r.score,
  }));
}
