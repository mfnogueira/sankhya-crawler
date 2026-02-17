"""FastAPI embedding service com bge-m3 (dense + sparse) e bge-reranker-v2-m3."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from FlagEmbedding import BGEM3FlagModel, FlagReranker

from models import (
    EmbedBatchRequest,
    EmbedBatchResponse,
    EmbedRequest,
    EmbedResponse,
    HealthResponse,
    RerankRequest,
    RerankResponse,
    RerankResult,
    SparseVector,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Singletons dos modelos
embed_model: BGEM3FlagModel | None = None
rerank_model: FlagReranker | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carrega modelos na inicialização."""
    global embed_model, rerank_model

    logger.info("Carregando bge-m3...")
    embed_model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
    logger.info("bge-m3 carregado.")

    logger.info("Carregando bge-reranker-v2-m3...")
    rerank_model = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)
    logger.info("bge-reranker-v2-m3 carregado.")

    yield

    embed_model = None
    rerank_model = None


app = FastAPI(
    title="Sankhya Embedding Service",
    description="Dense + Sparse embeddings (bge-m3) e Re-ranking (bge-reranker-v2-m3)",
    version="1.0.0",
    lifespan=lifespan,
)


def _encode_single(text: str, return_sparse: bool) -> EmbedResponse:
    output = embed_model.encode(
        [text],
        return_dense=True,
        return_sparse=return_sparse,
        return_colbert_vecs=False,
    )
    dense = output["dense_vecs"][0].tolist()

    sparse = None
    if return_sparse:
        weights = output["lexical_weights"][0]
        sparse = SparseVector(
            indices=list(weights.keys()),
            values=list(weights.values()),
        )

    return EmbedResponse(dense=dense, sparse=sparse)


@app.post("/embed", response_model=EmbedResponse)
async def embed(req: EmbedRequest):
    """Gera embedding dense (+ sparse opcional) para um texto."""
    return _encode_single(req.text, req.return_sparse)


@app.post("/embed/batch", response_model=EmbedBatchResponse)
async def embed_batch(req: EmbedBatchRequest):
    """Gera embeddings dense (+ sparse opcional) para múltiplos textos."""
    output = embed_model.encode(
        req.texts,
        return_dense=True,
        return_sparse=req.return_sparse,
        return_colbert_vecs=False,
    )

    embeddings = []
    for i in range(len(req.texts)):
        dense = output["dense_vecs"][i].tolist()
        sparse = None
        if req.return_sparse:
            weights = output["lexical_weights"][i]
            sparse = SparseVector(
                indices=list(weights.keys()),
                values=list(weights.values()),
            )
        embeddings.append(EmbedResponse(dense=dense, sparse=sparse))

    return EmbedBatchResponse(embeddings=embeddings)


@app.post("/rerank", response_model=RerankResponse)
async def rerank(req: RerankRequest):
    """Re-rankeia documentos candidatos em relação à query."""
    pairs = [[req.query, doc] for doc in req.documents]
    scores = rerank_model.compute_score(pairs, normalize=True)

    # compute_score retorna float para par único, lista para múltiplos
    if isinstance(scores, float):
        scores = [scores]

    results = [
        RerankResult(index=i, score=score, text=req.documents[i])
        for i, score in enumerate(scores)
    ]
    results.sort(key=lambda r: r.score, reverse=True)
    results = results[: req.top_k]

    return RerankResponse(results=results)


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check com status dos modelos."""
    return HealthResponse(
        status="ok",
        models={
            "bge-m3": embed_model is not None,
            "bge-reranker-v2-m3": rerank_model is not None,
        },
    )
