# Sankhya Docs RAG

Assistente inteligente da documentação [Sankhya Developer](https://developer.sankhya.com.br/docs/conhecendo-o-portal), utilizando RAG (Retrieval-Augmented Generation) para responder perguntas com base exclusivamente no conteúdo oficial.

## Arquitetura

```
Coleta (Docling) → Vetorização (Qdrant) → API REST (Express + GPT-4o-mini) → Chat UI
                 → Grafo (Neo4j) [em desenvolvimento]
```

### Pipeline

1. **Coleta** — `crawl_sankhya.py` baixa as páginas da documentação Sankhya via [Docling](https://github.com/DS4SD/docling), exporta como Markdown com imagens referenciadas
2. **Descoberta** — `discover_urls.py` extrai automaticamente todas as URLs do menu lateral do portal
3. **Vetorização** — `ingest_qdrant.py` divide o conteúdo em seções (H2), gera embeddings com `all-MiniLM-L6-v2` e armazena no Qdrant
4. **Grafo** — `ingest_neo4j.py` ingere documentos, seções, categorias e referências cruzadas no Neo4j (etapa em desenvolvimento para exploração via grafos)
5. **API + Chat** — API REST Node.js com busca vetorial, guardrails de tópico e interface de chat

## Estrutura do projeto

```
├── crawl_sankhya.py       # Coleta de páginas via Docling
├── discover_urls.py       # Descoberta automática de URLs do menu lateral
├── parser.py              # Parsing compartilhado de Markdown
├── ingest_qdrant.py       # Ingestão vetorial no Qdrant
├── ingest_neo4j.py        # Ingestão em grafo no Neo4j
├── urls.txt               # Lista de URLs a coletar
├── output/                # Markdown + imagens coletados
├── .env                   # Credenciais (não versionado)
├── .env.example           # Exemplo de configuração
└── api/                   # API REST + Chat UI
    ├── src/
    │   ├── index.js           # Express + Swagger
    │   ├── routes/ask.js      # POST /api/ask
    │   ├── services/
    │   │   ├── qdrant.js      # Busca vetorial
    │   │   ├── openai.js      # GPT-4o-mini
    │   │   └── cache.js       # Cache em memória (TTL 1h)
    │   └── guardrails/
    │       └── topic.js       # Classificação on/off-topic
    ├── public/index.html      # Interface de chat
    └── swagger.json           # Documentação da API
```

## Requisitos

- Python 3.12+ com [uv](https://github.com/astral-sh/uv)
- Node.js 18+
- Conta no [Qdrant Cloud](https://cloud.qdrant.io/)
- Conta na [OpenAI](https://platform.openai.com/)
- (Opcional) Conta no [Neo4j Aura](https://neo4j.com/cloud/aura/)

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

### 3. Ingestão no Qdrant

```bash
uv pip install qdrant-client sentence-transformers
uv run ingest_qdrant.py
```

### 4. Ingestão no Neo4j (opcional)

```bash
uv pip install neo4j
uv run ingest_neo4j.py
```

### 5. API + Chat

```bash
cd api && npm install && npm start
```

- Chat UI: http://localhost:3000
- Swagger: http://localhost:3000/api-docs

## Guardrails

O assistente possui duas camadas de proteção para garantir respostas fiéis à documentação:

- **Classificação pré-query** — GPT-4o-mini verifica se a pergunta é sobre Sankhya antes de processar. Perguntas fora do tema são rejeitadas
- **System prompt rígido** — O modelo é instruído a responder APENAS com base no contexto recuperado do Qdrant, citando as fontes

## Cache

Respostas são cacheadas em memória (TTL de 1 hora) usando hash MD5 da pergunta normalizada. Perguntas repetidas não consomem tokens.
