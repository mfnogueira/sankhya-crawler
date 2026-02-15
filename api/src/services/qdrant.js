import { QdrantClient } from "@qdrant/js-client-rest";
import { pipeline } from "@xenova/transformers";

const COLLECTION_NAME = "sankhya_docs";
const TOP_K = 5;

const qdrant = new QdrantClient({
  url: process.env.QDRANT_URL,
  apiKey: process.env.QDRANT_API_KEY,
});

// Singleton do modelo de embeddings (carrega uma vez)
let embedder = null;

async function getEmbedder() {
  if (!embedder) {
    console.log("Carregando modelo de embeddings (all-MiniLM-L6-v2)...");
    embedder = await pipeline("feature-extraction", "Xenova/all-MiniLM-L6-v2");
    console.log("Modelo de embeddings carregado.");
  }
  return embedder;
}

async function embedQuery(text) {
  const model = await getEmbedder();
  const output = await model(text, { pooling: "mean", normalize: true });
  return Array.from(output.data);
}

export async function searchSections(question) {
  const vector = await embedQuery(question);

  const results = await qdrant.search(COLLECTION_NAME, {
    vector,
    limit: TOP_K,
    with_payload: true,
  });

  return results.map((r) => ({
    score: r.score,
    text: r.payload.text,
    doc_title: r.payload.doc_title,
    doc_url: r.payload.doc_url,
    section_title: r.payload.section_title,
    category: r.payload.category,
  }));
}

export async function checkHealth() {
  const info = await qdrant.getCollection(COLLECTION_NAME);
  return {
    status: info.status,
    points: info.points_count,
    collection: COLLECTION_NAME,
  };
}

// Pré-carrega o modelo ao importar
getEmbedder().catch(console.error);
