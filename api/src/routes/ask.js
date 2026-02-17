import { Router } from "express";
import { isOnTopic } from "../guardrails/topic.js";
import { getFromCache, setInCache } from "../services/cache.js";
import { streamWithContext } from "../services/openai.js";
import { searchSections } from "../services/qdrant.js";
import { rerankSections } from "../services/reranker.js";

const router = Router();

function sendSSE(res, event) {
  res.write(`data: ${JSON.stringify(event)}\n\n`);
}

router.post("/", async (req, res) => {
  const { question } = req.body;

  if (!question || typeof question !== "string" || !question.trim()) {
    return res.status(400).json({
      error: "invalid_request",
      message: "O campo 'question' é obrigatório.",
    });
  }

  const trimmed = question.trim();

  // 1. Guardrail: classificação de tópico (antes de iniciar SSE)
  let onTopic;
  try {
    onTopic = await isOnTopic(trimmed);
  } catch (err) {
    console.error("Erro no guardrail:", err);
    return res.status(500).json({
      error: "internal_error",
      message: "Erro interno ao processar sua pergunta.",
    });
  }

  if (!onTopic) {
    return res.status(400).json({
      error: "off_topic",
      message:
        "Só posso responder perguntas sobre a documentação Sankhya Developer. Tente perguntar sobre Jape, SankhyaJS, Add-ons, SDK, dicionário de dados, etc.",
    });
  }

  // A partir daqui: resposta via SSE
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();

  try {
    // 2. Cache check
    const cached = getFromCache(trimmed);
    if (cached) {
      for (const token of cached.answer.split("")) {
        sendSSE(res, { type: "token", content: token });
      }
      sendSSE(res, { type: "sources", sources: cached.sources, cached: true });
      sendSSE(res, { type: "done" });
      return res.end();
    }

    // 3. Busca híbrida no Qdrant (dense + sparse + RRF, top-20)
    const candidates = await searchSections(trimmed);

    if (!candidates.length) {
      sendSSE(res, {
        type: "token",
        content: "Não encontrei informações relevantes na documentação sobre esse tema.",
      });
      sendSSE(res, { type: "sources", sources: [], cached: false });
      sendSSE(res, { type: "done" });
      return res.end();
    }

    // 4. Re-ranking com cross-encoder (top-20 → top-5)
    const sections = await rerankSections(trimmed, candidates);

    // 5. Montar sources únicos
    const seen = new Set();
    const sources = sections
      .filter((s) => {
        const key = s.doc_url;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .map((s) => ({
        title: `${s.doc_title} — ${s.section_title}`,
        url: s.doc_url,
        category: s.category,
        modulo: s.modulo,
        tipo_conteudo: s.tipo_conteudo,
        nivel: s.nivel,
        tecnologias: s.tecnologias,
      }));

    // 6. Gerar resposta com GPT-4o-mini em streaming
    const stream = await streamWithContext(trimmed, sections);
    let fullAnswer = "";

    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content;
      if (content) {
        fullAnswer += content;
        sendSSE(res, { type: "token", content });
      }
    }

    // 7. Salvar no cache e encerrar stream
    setInCache(trimmed, { answer: fullAnswer, sources });
    sendSSE(res, { type: "sources", sources, cached: false });
    sendSSE(res, { type: "done" });
    res.end();
  } catch (err) {
    console.error("Erro ao processar pergunta:", err);
    if (!res.headersSent) {
      return res.status(500).json({
        error: "internal_error",
        message: "Erro interno ao processar sua pergunta.",
      });
    }
    sendSSE(res, { type: "error", message: "Erro interno ao processar sua pergunta." });
    res.end();
  }
});

export default router;
