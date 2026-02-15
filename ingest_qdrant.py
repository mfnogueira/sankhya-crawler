"""Ingestão vetorial da documentação Sankhya no Qdrant."""

import os
import uuid

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from parser import load_all_documents

load_dotenv()

# ── Configuração ─────────────────────────────────────────────────────
QDRANT_URL = os.environ.get("QDRANT_URL", "")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "")
COLLECTION_NAME = "sankhya_docs"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
VECTOR_SIZE = 384  # dimensão do all-MiniLM-L6-v2
BATCH_SIZE = 64


def main():
    if not QDRANT_URL or not QDRANT_API_KEY:
        print("Defina QDRANT_URL e QDRANT_API_KEY no arquivo .env")
        return

    documents = load_all_documents()
    if not documents:
        print("Nenhum documento encontrado em output/")
        return

    # Preparar seções para vetorização
    sections = []
    for doc in documents:
        for section in doc["sections"]:
            sections.append(
                {
                    "id": section["id"],
                    "text": f"{doc['title']} - {section['title']}\n\n{section['content']}",
                    "metadata": {
                        "doc_slug": doc["slug"],
                        "doc_title": doc["title"],
                        "doc_url": doc["url"],
                        "section_title": section["title"],
                        "section_order": section["order"],
                        "category": doc["category"],
                    },
                }
            )

    print(f"Parseados {len(documents)} documentos, {len(sections)} seções\n")

    # Carregar modelo de embeddings
    print(f"Carregando modelo de embeddings ({EMBEDDING_MODEL})...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    # Gerar embeddings
    print(f"Gerando embeddings para {len(sections)} seções...")
    texts = [s["text"] for s in sections]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=BATCH_SIZE)

    # Conectar ao Qdrant
    print(f"\nConectando ao Qdrant ({QDRANT_URL})...")
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    # Recriar collection (clean & reload)
    if client.collection_exists(COLLECTION_NAME):
        print(f"Removendo collection existente '{COLLECTION_NAME}'...")
        client.delete_collection(COLLECTION_NAME)

    print(f"Criando collection '{COLLECTION_NAME}'...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )

    # Preparar pontos
    points = []
    for i, section in enumerate(sections):
        points.append(
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, section["id"])),
                vector=embeddings[i].tolist(),
                payload={
                    "section_id": section["id"],
                    "text": section["text"],
                    **section["metadata"],
                },
            )
        )

    # Upload em batches
    print(f"Enviando {len(points)} pontos ao Qdrant...")
    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i : i + BATCH_SIZE]
        client.upsert(collection_name=COLLECTION_NAME, points=batch)
        print(f"  Batch {i // BATCH_SIZE + 1}/{(len(points) - 1) // BATCH_SIZE + 1} enviado")

    # Verificar
    info = client.get_collection(COLLECTION_NAME)
    print(f"\nIngestão concluída!")
    print(f"  Collection: {COLLECTION_NAME}")
    print(f"  Pontos:     {info.points_count}")
    print(f"  Dimensão:   {VECTOR_SIZE}")
    print(f"  Distância:  cosine")


if __name__ == "__main__":
    main()
