import { QdrantClient } from "@qdrant/js-client-rest";

const COLLECTION_NAME = "sankhya_docs";
const PREFETCH_LIMIT = 20;
const FUSION_LIMIT = 10;
const EMBEDDING_SERVICE_URL =
  process.env.EMBEDDING_SERVICE_URL || "http://localhost:8000";

const qdrant = new QdrantClient({
  url: process.env.QDRANT_URL,
  apiKey: process.env.QDRANT_API_KEY,
});

async function getEmbedding(text) {
  const res = await fetch(`${EMBEDDING_SERVICE_URL}/embed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, return_sparse: true }),
    signal: AbortSignal.timeout(30_000),
  });

  if (!res.ok) {
    throw new Error(`Embedding service error: ${res.status}`);
  }

  return res.json();
}

export async function searchSections(question, filters = {}) {
  const { dense, sparse } = await getEmbedding(question);

  // Construir filtro Qdrant a partir dos metadados
  const mustConditions = [];
  for (const [field, value] of Object.entries(filters)) {
    if (value) {
      mustConditions.push({
        key: field,
        match: { value },
      });
    }
  }
  const filter = mustConditions.length > 0 ? { must: mustConditions } : undefined;

  // Busca híbrida com prefetch (dense + sparse) + RRF fusion
  const results = await qdrant.query(COLLECTION_NAME, {
    prefetch: [
      {
        query: dense,
        using: "dense",
        limit: PREFETCH_LIMIT,
        ...(filter && { filter }),
      },
      {
        query: {
          indices: sparse.indices,
          values: sparse.values,
        },
        using: "sparse",
        limit: PREFETCH_LIMIT,
        ...(filter && { filter }),
      },
    ],
    query: { fusion: "rrf" },
    limit: FUSION_LIMIT,
    with_payload: true,
  });

  return results.points.map((r) => ({
    score: r.score,
    text: r.payload.text,
    doc_title: r.payload.doc_title,
    doc_url: r.payload.doc_url,
    section_title: r.payload.section_title,
    category: r.payload.category,
    // Metadados enriquecidos
    modulo: r.payload.modulo,
    tipo_conteudo: r.payload.tipo_conteudo,
    nivel: r.payload.nivel,
    tecnologias: r.payload.tecnologias,
    linguagem: r.payload.linguagem,
  }));
}

export async function checkHealth() {
  const [collectionInfo, embeddingHealth] = await Promise.all([
    qdrant.getCollection(COLLECTION_NAME),
    fetch(`${EMBEDDING_SERVICE_URL}/health`)
      .then((r) => r.json())
      .catch(() => ({ status: "unavailable" })),
  ]);

  return {
    status: collectionInfo.status,
    points: collectionInfo.points_count,
    collection: COLLECTION_NAME,
    embedding_service: embeddingHealth,
  };
}
