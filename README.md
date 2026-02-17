# Sankhya Docs RAG

Assistente inteligente da documentação [Sankhya Developer](https://developer.sankhya.com.br/docs/conhecendo-o-portal), utilizando RAG (Retrieval-Augmented Generation) para responder perguntas com base exclusivamente no conteúdo oficial.

## Arquitetura

```
Coleta (Docling)
  → Extração de Metadados (GPT-4o-mini)
  → Embedding Service (bge-m3 dense + sparse)
  → Ingestão Vetorial (Qdrant)
  → API REST (Express + GPT-4o-mini + Re-ranking)
  → Chat UI
```

### Pipeline

1. **Coleta** — `crawl_sankhya.py` baixa as páginas da documentação Sankhya via [Docling](https://github.com/DS4SD/docling), exporta como Markdown
2. **Descoberta** — `discover_urls.py` extrai automaticamente todas as URLs do menu lateral do portal
3. **Extração de Metadados** — `extract_metadata.py` classifica cada documento via GPT-4o-mini, extraindo metadados estruturais (módulo, tipo de ação, tecnologias, nível) e semânticos (funções, conceitos, tabelas, classes Java). Os metadados são salvos em `metadata/` e reutilizados na ingestão como payload filtrado no Qdrant
4. **Ingestão Vetorial** — `ingest_qdrant.py` divide o conteúdo em seções (H2), gera embeddings **dense + sparse** com `bge-m3` e armazena no Qdrant com payload enriquecido pelos metadados
5. **Embedding Service** — Microserviço FastAPI (`embedding_service/`) que serve os modelos `bge-m3` (embeddings) e `bge-reranker-v2-m3` (re-ranking) em tempo de query
6. **API + Chat** — API REST Node.js com busca híbrida (dense + sparse + RRF fusion), re-ranking via cross-encoder, guardrails de tópico e interface de chat

### Por que bge-m3 com dense + sparse?

A documentação Sankhya é altamente técnica, contendo nomes de classes Java (`EntityFacade`, `JapeSession`), funções específicas (`ACT_*`), nomes de tabelas (`TGFCAB`, `AD_*`), e termos do domínio que modelos puramente semânticos podem diluir.

- **Dense vectors (1024d)** capturam a semântica geral — "como criar um botão de ação" encontra documentos sobre `action_button` mesmo sem match lexical exato
- **Sparse vectors (BM25-like)** preservam matches exatos de termos técnicos — uma busca por `TGFCAB` ou `JapeWrapper` encontra exatamente os documentos que mencionam esses termos
- **RRF Fusion** combina os dois rankings, garantindo que resultados relevantes por ambos os critérios apareçam no topo
- **Cross-encoder re-ranking** (`bge-reranker-v2-m3`) refina os top-20 candidatos para os top-5 mais relevantes, melhorando a precisão do contexto enviado ao LLM

Essa abordagem híbrida é especialmente eficaz para documentação técnica onde tanto a intenção semântica quanto os termos exatos importam.

## Estrutura do projeto

```
├── crawl_sankhya.py          # Coleta de páginas via Docling
├── discover_urls.py          # Descoberta automática de URLs do menu lateral
├── parser.py                 # Parsing compartilhado de Markdown + carregamento de metadados
├── extract_metadata.py       # Extração de metadados via GPT-4o-mini
├── ingest_qdrant.py          # Ingestão vetorial no Qdrant (bge-m3 dense + sparse)
├── urls.txt                  # Lista de URLs a coletar
├── output/                   # Markdown coletados
├── metadata/                 # Metadados extraídos (JSON por documento)
├── .env                      # Credenciais (não versionado)
├── .env.example              # Exemplo de configuração
├── embedding_service/        # Microserviço Python (FastAPI)
│   ├── main.py               # Endpoints /embed, /embed/batch, /rerank, /health
│   └── models.py             # Schemas Pydantic
└── api/                      # API REST + Chat UI (Node.js)
    ├── src/
    │   ├── index.js              # Express + Swagger
    │   ├── routes/ask.js         # POST /api/ask (pipeline RAG completo)
    │   ├── services/
    │   │   ├── qdrant.js         # Busca híbrida (dense + sparse + RRF)
    │   │   ├── reranker.js       # Re-ranking via cross-encoder
    │   │   ├── openai.js         # Geração de resposta (GPT-4o-mini)
    │   │   └── cache.js          # Cache em memória (TTL 1h)
    │   └── guardrails/
    │       └── topic.js          # Classificação on/off-topic
    ├── public/index.html         # Interface de chat
    └── swagger.json              # Documentação da API
```

## Requisitos

- Python 3.12+ com [uv](https://github.com/astral-sh/uv)
- Node.js 18+
- Conta no [Qdrant Cloud](https://cloud.qdrant.io/)
- Conta na [OpenAI](https://platform.openai.com/)
- GPU recomendada para o embedding service (funciona em CPU, mas mais lento)

## Setup

### 1. Configuração

```bash
cp .env.example .env
# Preencha as credenciais no .env
```

### 2. Coleta da documentação

```bash
uv run discover_urls.py    # Descobre todas as URLs do portal
uv run crawl_sankhya.py    # Baixa o conteúdo (pula páginas já coletadas)
```

### 3. Extração de metadados

```bash
uv run extract_metadata.py
```

Classifica cada documento e salva metadados em `metadata/`. O script pula documentos já processados, então pode ser interrompido e retomado sem custo adicional de tokens.

### 4. Ingestão no Qdrant

```bash
uv run ingest_qdrant.py
```

Gera embeddings dense + sparse com bge-m3 e envia ao Qdrant com payload enriquecido pelos metadados (módulo, tecnologias, nível, etc.), criando índices para filtros.

### 5. Embedding Service

**Local (desenvolvimento):**

```bash
cd embedding_service
uv run --with fastapi --with "uvicorn[standard]" --with FlagEmbedding --with pydantic --with torch uvicorn main:app --host 0.0.0.0 --port 8000
```

**Docker (produção/Render):**

```bash
docker build -t sankhya-embedding ./embedding_service
docker run -p 8000:8000 sankhya-embedding
```

Carrega os modelos bge-m3 e bge-reranker-v2-m3 na inicialização. Aguarde o log "bge-reranker-v2-m3 carregado" antes de iniciar a API.

### 6. API + Chat

```bash
cd api && npm install && npm run dev
```

- Chat UI: http://localhost:3000
- Swagger: http://localhost:3000/api-docs
- Health check: http://localhost:3000/api/health

## Pipeline de query (fluxo completo)

1. Usuário envia pergunta via `POST /api/ask`
2. **Cache** — verifica se já respondeu essa pergunta (TTL 1h)
3. **Guardrail** — GPT-4o-mini classifica se é sobre Sankhya (rejeita off-topic)
4. **Embedding** — embedding service gera vetores dense + sparse da pergunta
5. **Busca híbrida** — Qdrant faz prefetch dense (top-40) + sparse (top-40), funde via RRF (top-20)
6. **Re-ranking** — cross-encoder bge-reranker-v2-m3 reordena top-20 → top-5
7. **Geração** — GPT-4o-mini gera resposta baseada apenas no contexto recuperado
8. **Cache** — salva resultado para reuso

## Guardrails

- **Classificação pre-query** — GPT-4o-mini verifica se a pergunta é sobre Sankhya antes de processar. Perguntas fora do tema são rejeitadas
- **System prompt restritivo** — O modelo responde APENAS com base no contexto recuperado do Qdrant, citando as fontes

## Cache

Respostas cacheadas em memória (TTL de 1 hora) usando hash MD5 da pergunta normalizada. Perguntas repetidas não consomem tokens.

## Deploy no Render

### Embedding Service (Web Service com Docker)

1. Criar novo **Web Service** no Render
2. Conectar o repositório
3. Configurar **Root Directory:** `embedding_service`
4. **Environment:** Docker
5. **Instance Type:** mínimo 4GB RAM (os modelos consomem ~3-4GB)
6. Deploy

### API Node.js (Web Service)

1. Criar novo **Web Service** no Render
2. Conectar o repositório
3. Configurar **Root Directory:** `api`
4. **Build Command:** `npm install`
5. **Start Command:** `node src/index.js`
6. **Environment Variables:**
   - `QDRANT_URL` — URL do Qdrant Cloud
   - `QDRANT_API_KEY` — API key do Qdrant
   - `OPENAI_API_KEY` — API key da OpenAI
   - `EMBEDDING_SERVICE_URL` — URL interna do embedding service no Render
