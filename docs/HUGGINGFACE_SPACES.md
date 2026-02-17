# Deploy do Embedding Service no Hugging Face Spaces

Este guia explica como fazer o deploy do microserviço de embeddings (`embedding_service/`) no [Hugging Face Spaces](https://huggingface.co/spaces) usando Docker. O HF Spaces oferece um tier gratuito com 16GB de RAM, suficiente para carregar os modelos `bge-m3` (~2.5GB) e `bge-reranker-v2-m3` (~1.5GB).

## Por que Hugging Face Spaces?

| Plataforma | RAM gratuita | Suporte Docker | Custo |
|---|---|---|---|
| Render (free) | 512 MB | Sim | Gratuito (insuficiente) |
| Railway | 512 MB | Sim | Gratuito (insuficiente) |
| **HF Spaces (CPU Basic)** | **16 GB** | **Sim** | **Gratuito** |
| HF Spaces (GPU T4) | 16 GB + GPU | Sim | ~$0.60/h |

> Os modelos bge-m3 + bge-reranker-v2-m3 consomem ~3.5GB de RAM em CPU. O tier gratuito do HF Spaces (16GB) é suficiente.

## Pré-requisitos

- Conta no [Hugging Face](https://huggingface.co/)
- Git instalado
- Git LFS instalado: `sudo apt install git-lfs` / `brew install git-lfs`

## Passo a passo

### 1. Criar o Space

1. Acesse [huggingface.co/new-space](https://huggingface.co/new-space)
2. Preencha:
   - **Space name:** `sankhya-embedding` (ou o nome de sua preferência)
   - **License:** MIT (ou outra de sua escolha)
   - **SDK:** selecione **Docker**
   - **Visibility:** Public (tier gratuito requer Space público)
3. Clique em **Create Space**

### 2. Clonar o Space

Após criar, o HF fornece uma URL de clone. Substitua `seu-usuario` pelo seu username:

```bash
git clone https://huggingface.co/spaces/seu-usuario/sankhya-embedding
cd sankhya-embedding
```

### 3. Copiar os arquivos do embedding service

A partir da raiz do projeto `sankhya-crawler`:

```bash
cp embedding_service/main.py sankhya-embedding/
cp embedding_service/models.py sankhya-embedding/
cp embedding_service/Dockerfile sankhya-embedding/
```

### 4. Verificar o Dockerfile

O HF Spaces **exige a porta 7860**. Certifique-se de que o `Dockerfile` usa essa porta:

```dockerfile
EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
```

O `Dockerfile` já está configurado corretamente para o HF Spaces.

### 5. Push para o Space

```bash
cd sankhya-embedding
git add .
git commit -m "feat: embedding service com bge-m3 e bge-reranker-v2-m3"
git push
```

> Se for solicitado login, use seu **username** do HF e um **token de acesso** (não a senha). Gere o token em: Settings → Access Tokens → New Token. Permissão necessária: **Write** (para fazer push para repositórios/Spaces).

### 6. Acompanhar o build

1. Acesse a página do seu Space: `https://huggingface.co/spaces/seu-usuario/sankhya-embedding`
2. Clique na aba **Logs**
3. Aguarde o build completar — o download e pré-carregamento dos modelos ocorre durante o build, o que pode levar **15-30 minutos** na primeira vez

O Space estará pronto quando os logs mostrarem:
```
bge-m3 carregado
bge-reranker-v2-m3 carregado
INFO: Application startup complete.
```

### 7. Testar o serviço

Substitua `seu-usuario` pela sua conta:

```bash
# Health check
curl https://seu-usuario-sankhya-embedding.hf.space/health

# Resposta esperada:
# {"status":"ok","models":{"bge-m3":true,"bge-reranker-v2-m3":true}}

# Teste de embedding
curl -X POST https://seu-usuario-sankhya-embedding.hf.space/embed \
  -H "Content-Type: application/json" \
  -d '{"text":"como criar um addon Sankhya?","return_sparse":true}'
```

## Configurar a API para usar o Space

Após o deploy, configure a URL do Space como `EMBEDDING_SERVICE_URL`:

### Desenvolvimento local (`.env`)

```env
EMBEDDING_SERVICE_URL=https://seu-usuario-sankhya-embedding.hf.space
```

### Vercel (produção)

1. Acesse: Vercel Dashboard → Project → Settings → **Environment Variables**
2. Adicione:
   - **Key:** `EMBEDDING_SERVICE_URL`
   - **Value:** `https://seu-usuario-sankhya-embedding.hf.space`
   - **Environments:** Production, Preview, Development
3. Salve e faça **Redeploy** para aplicar

## Comportamento do tier gratuito

- **Hibernação:** Spaces gratuitos entram em hibernação após **48 horas** sem requisições
- **Cold start:** Ao acordar do hibernate, o serviço demora **30-90 segundos** para ficar disponível (os modelos precisam ser recarregados em memória)
- **Solução:** A API já tem fallback no reranker (timeout de 60s + retorna ordem original em caso de erro). Para evitar hibernação, considere fazer uma requisição de health check periódica (ex: com um cron job ou UptimeRobot)

## Endpoints disponíveis

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/health` | Status do serviço e dos modelos |
| `POST` | `/embed` | Gera embedding dense + sparse de um texto |
| `POST` | `/embed/batch` | Gera embeddings em lote |
| `POST` | `/rerank` | Re-ranking de documentos com cross-encoder |

### Exemplo: `/embed`

**Request:**
```json
{
  "text": "como usar o JapeWrapper?",
  "return_sparse": true
}
```

**Response:**
```json
{
  "dense": [0.023, -0.041, ...],
  "sparse": {
    "indices": [42, 156, 891],
    "values": [0.31, 0.28, 0.19]
  }
}
```

### Exemplo: `/rerank`

**Request:**
```json
{
  "query": "como criar um addon?",
  "documents": ["texto do doc 1", "texto do doc 2"],
  "top_k": 5
}
```

**Response:**
```json
{
  "results": [
    {"index": 1, "score": 0.94},
    {"index": 0, "score": 0.71}
  ]
}
```

## Atualizar o Space

Para atualizar o código do serviço (ex: após modificar `main.py`):

```bash
cd sankhya-crawler
cp embedding_service/main.py ../sankhya-embedding/
cd ../sankhya-embedding
git add . && git commit -m "update: ..." && git push
```

O HF Spaces fará o rebuild automaticamente após o push.
