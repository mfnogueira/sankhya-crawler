import { Router } from "express";
import { isOnTopic } from "../guardrails/topic.js";
import { getFromCache, setInCache } from "../services/cache.js";
import { askWithContext } from "../services/openai.js";
import { searchSections } from "../services/qdrant.js";

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

    // 3. Busca vetorial no Qdrant
    const sections = await searchSections(trimmed);

    if (!sections.length) {
      return res.json({
        answer:
          "Não encontrei informações relevantes na documentação sobre esse tema.",
        sources: [],
        cached: false,
      });
    }

    // 4. Gerar resposta com GPT-4o-mini
    const answer = await askWithContext(trimmed, sections);

    // Montar sources únicos
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
      }));

    const result = { answer, sources, cached: false };

    // 5. Salvar no cache
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
