FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    "transformers<5" \
    FlagEmbedding \
    pydantic

COPY main.py models.py ./

# Pré-download dos modelos no build (evita download no startup)
RUN python -c "from FlagEmbedding import BGEM3FlagModel, FlagReranker; BGEM3FlagModel('BAAI/bge-m3'); FlagReranker('BAAI/bge-reranker-v2-m3')"

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
