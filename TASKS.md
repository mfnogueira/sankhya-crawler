# Tasks — Debug Vercel Deploy

## Status atual
Aguardando redeploy do Vercel após remoção do `api/vercel.json` duplicado.

---

## Bugs corrigidos (já commitados)

- [x] `results.map is not a function` — `qdrant.js:68`
  - Causa: `qdrant.query()` retorna `{ points: [...] }`, não array direto
  - Fix: `results.map(...)` → `results.points.map(...)`
  - Commit: `cb871aa`

- [x] `api/vercel.json` duplicado causando build do código antigo
  - Causa: Vercel usava `api/vercel.json` como base, ignorando fixes no `qdrant.js`
  - Fix: deletado `api/vercel.json` — apenas o da raiz permanece
  - Commit: `3658c04`

---

## Pendente

- [ ] **Confirmar que o fix funcionou no Vercel**
  - Aguardar deploy do commit `3658c04`
  - Testar: `curl -X POST .../api/ask -d '{"question":"o que e o Jape?"}'`
  - Esperado: JSON com `answer` e `sources`, sem `error`

- [ ] **Remover campo `debug` do response de erro**
  - Arquivo: `api/src/routes/ask.js` linha 87
  - Remover: `debug: err.message,`
  - Commit e push após confirmar que o deploy funciona

---

## Contexto da infraestrutura

| Componente | Plataforma | URL |
|---|---|---|
| Embedding Service | Hugging Face Spaces | `https://mfnogueira-sankhya-embedding.hf.space` |
| API Node.js | Vercel | `https://sankhya-crawler-git-main-mfnogueiras-projects.vercel.app` |
| Vector DB | Qdrant Cloud | `us-west-1` (458 pontos indexados) |
| LLM | OpenAI | `gpt-4o-mini` |

## Variáveis de ambiente (Vercel)

| Variável | Status |
|---|---|
| `QDRANT_URL` | ✅ configurada |
| `QDRANT_API_KEY` | ✅ configurada |
| `OPENAI_API_KEY` | ✅ configurada |
| `EMBEDDING_SERVICE_URL` | ✅ configurada → HF Space |

## Como testar localmente

```bash
# Health check
curl http://localhost:3000/api/health

# Pergunta
curl -s -X POST http://localhost:3000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"o que e o Jape?"}'
```

## Como testar no Vercel

```bash
# Health check
curl https://sankhya-crawler-git-main-mfnogueiras-projects.vercel.app/api/health

# Pergunta
curl -s -X POST \
  "https://sankhya-crawler-git-main-mfnogueiras-projects.vercel.app/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"o que e o Jape?"}'
```
