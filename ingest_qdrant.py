"""Ingestão vetorial da documentação Sankhya no Qdrant (bge-m3 dense + sparse)."""

import os
import uuid

from dotenv import load_dotenv
from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PayloadSchemaType,
    PointStruct,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from parser import load_all_documents

load_dotenv()

# ── Configuração ─────────────────────────────────────────────────────
QDRANT_URL = os.environ.get("QDRANT_URL", "")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "")
COLLECTION_NAME = "sankhya_docs"
DENSE_SIZE = 1024  # dimensão do bge-m3
BATCH_SIZE = 32


def flatten_metadata(doc_metadata: dict) -> dict:
    """Achata metadados estruturais e semânticos para o payload do Qdrant."""
    payload = {}
    estruturais = doc_metadata.get("estruturais", {})
    semanticos = doc_metadata.get("semanticos", {})

    # Estruturais
    for key in (
        "sistema", "modulo", "tipo_acao", "tecnologias", "linguagem",
        "tipo_conteudo", "nivel", "tema_principal", "usa_funcoes_act",
    ):
        if key in estruturais:
            payload[key] = estruturais[key]

    # Semânticos
    for key in (
        "funcoes_utilizadas", "conceitos", "tabelas_exemplo",
        "apis_referenciadas", "classes_java",
    ):
        if key in semanticos:
            payload[key] = semanticos[key]

    return payload


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
        meta_payload = flatten_metadata(doc.get("metadata", {}))
        for section in doc["sections"]:
            sections.append(
                {
                    "id": section["id"],
                    "text": f"{doc['title']} - {section['title']}\n\n{section['content']}",
                    "payload": {
                        "section_id": section["id"],
                        "doc_slug": doc["slug"],
                        "doc_title": doc["title"],
                        "doc_url": doc["url"],
                        "section_title": section["title"],
                        "section_order": section["order"],
                        "category": doc["category"],
                        **meta_payload,
                    },
                }
            )

    print(f"Parseados {len(documents)} documentos, {len(sections)} seções\n")

    # Carregar modelo bge-m3
    print("Carregando modelo bge-m3...")
    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)

    # Gerar embeddings (dense + sparse)
    print(f"Gerando embeddings dense + sparse para {len(sections)} seções...")
    texts = [s["text"] for s in sections]
    output = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,
    )

    dense_embeddings = output["dense_vecs"]
    sparse_embeddings = output["lexical_weights"]

    # Conectar ao Qdrant
    print(f"\nConectando ao Qdrant ({QDRANT_URL})...")
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    # Recriar collection com named vectors (dense + sparse)
    if client.collection_exists(COLLECTION_NAME):
        print(f"Removendo collection existente '{COLLECTION_NAME}'...")
        client.delete_collection(COLLECTION_NAME)

    print(f"Criando collection '{COLLECTION_NAME}' (dense 1024d + sparse)...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "dense": VectorParams(size=DENSE_SIZE, distance=Distance.COSINE),
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams(),
        },
    )

    # Criar índices de payload para filtros
    print("Criando índices de payload para filtros...")
    for field, schema_type in [
        ("category", PayloadSchemaType.KEYWORD),
        ("modulo", PayloadSchemaType.KEYWORD),
        ("tipo_conteudo", PayloadSchemaType.KEYWORD),
        ("nivel", PayloadSchemaType.KEYWORD),
        ("linguagem", PayloadSchemaType.KEYWORD),
        ("tecnologias", PayloadSchemaType.KEYWORD),
        ("funcoes_utilizadas", PayloadSchemaType.KEYWORD),
        ("tabelas_exemplo", PayloadSchemaType.KEYWORD),
    ]:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field,
            field_schema=schema_type,
        )

    # Preparar e enviar pontos
    print(f"Enviando {len(sections)} pontos ao Qdrant...")
    points = []
    for i, section in enumerate(sections):
        # Converter sparse weights para formato Qdrant
        token_weights = sparse_embeddings[i]
        sparse_indices = list(token_weights.keys())
        sparse_values = list(token_weights.values())

        point = PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, section["id"])),
            vector={
                "dense": dense_embeddings[i].tolist(),
                "sparse": SparseVector(
                    indices=sparse_indices,
                    values=sparse_values,
                ),
            },
            payload={
                "text": section["text"],
                **section["payload"],
            },
        )
        points.append(point)

        # Upload em batches
        if len(points) >= BATCH_SIZE or i == len(sections) - 1:
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(sections) - 1) // BATCH_SIZE + 1
            client.upsert(collection_name=COLLECTION_NAME, points=points)
            print(f"  Batch {batch_num}/{total_batches} enviado ({len(points)} pontos)")
            points = []

    # Verificar
    info = client.get_collection(COLLECTION_NAME)
    print(f"\nIngestão concluída!")
    print(f"  Collection:     {COLLECTION_NAME}")
    print(f"  Pontos:         {info.points_count}")
    print(f"  Dense dim:      {DENSE_SIZE}")
    print(f"  Sparse:         habilitado")
    print(f"  Distância:      cosine")


if __name__ == "__main__":
    main()
