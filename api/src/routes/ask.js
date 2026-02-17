import { Router } from "express";
import { isOnTopic } from "../guardrails/topic.js";
import { getFromCache, setInCache } from "../services/cache.js";
import { askWithContext } from "../services/openai.js";
import { searchSections } from "../services/qdrant.js";
import { rerankSections } from "../services/reranker.js";

const router = Router();

router.post("/", async (req, res) => {
  const { question } = req.body;

  if (!question || typeof question !== "string" || !question.trim()) {
    return res.status(400).json({
      error: "invalid_request",
      message: "O campo 'question' é obrigatório.",
    });
  }

  const trimmed = question.trim();

  try {
    // 1. Cache check
    const cached = getFromCache(trimmed);
    if (cached) {
      return res.json({ ...cached, cached: true });
    }

    // 2. Guardrail: classificação de tópico
    const onTopic = await isOnTopic(trimmed);
    if (!onTopic) {
      return res.status(400).json({
        error: "off_topic",
        message:
          "Só posso responder perguntas sobre a documentação Sankhya Developer. Tente perguntar sobre Jape, SankhyaJS, Add-ons, SDK, dicionário de dados, etc.",
      });
    }

    // 3. Busca híbrida no Qdrant (dense + sparse + RRF, top-20)
    const candidates = await searchSections(trimmed);

    if (!candidates.length) {
      return res.json({
        answer:
          "Não encontrei informações relevantes na documentação sobre esse tema.",
        sources: [],
        cached: false,
      });
    }

    // 4. Re-ranking com cross-encoder (top-20 → top-5)
    const sections = await rerankSections(trimmed, candidates);

    // 5. Gerar resposta com GPT-4o-mini
    const answer = await askWithContext(trimmed, sections);

    // Montar sources únicos com metadados enriquecidos
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

    const result = { answer, sources, cached: false };

    // 6. Salvar no cache
    setInCache(trimmed, { answer, sources });

    return res.json(result);
  } catch (err) {
    console.error("Erro ao processar pergunta:", err);
    return res.status(500).json({
      error: "internal_error",
      message: "Erro interno ao processar sua pergunta.",
    });
  }
});

export default router;
