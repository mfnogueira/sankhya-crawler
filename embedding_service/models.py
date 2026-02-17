"""Schemas Pydantic para o embedding service."""

from pydantic import BaseModel


class EmbedRequest(BaseModel):
    text: str
    return_sparse: bool = True


class EmbedBatchRequest(BaseModel):
    texts: list[str]
    return_sparse: bool = True


class SparseVector(BaseModel):
    indices: list[int]
    values: list[float]


class EmbedResponse(BaseModel):
    dense: list[float]
    sparse: SparseVector | None = None


class EmbedBatchResponse(BaseModel):
    embeddings: list[EmbedResponse]


class RerankRequest(BaseModel):
    query: str
    documents: list[str]
    top_k: int = 5


class RerankResult(BaseModel):
    index: int
    score: float
    text: str


class RerankResponse(BaseModel):
    results: list[RerankResult]


class HealthResponse(BaseModel):
    status: str
    models: dict[str, bool]
