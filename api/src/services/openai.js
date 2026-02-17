import OpenAI from "openai";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const SYSTEM_PROMPT = `Você é um assistente técnico da documentação Sankhya Developer.

REGRAS OBRIGATÓRIAS:
- Responda APENAS com base no contexto fornecido abaixo entre as tags <contexto> e </contexto>
- Se o contexto não contém informação suficiente para responder, diga explicitamente: "Não encontrei essa informação na documentação disponível."
- NUNCA invente informações ou use conhecimento externo ao contexto fornecido
- Cite o nome da seção/documento de onde veio a informação
- Responda sempre em português brasileiro
- Formate a resposta em Markdown quando apropriado (code blocks, listas, etc.)`;

export async function askWithContext(question, contextSections) {
  const contextText = contextSections
    .map((s) => `### ${s.doc_title} — ${s.section_title}\n${s.text}`)
    .join("\n\n---\n\n");

  const response = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    temperature: 0.1,
    max_tokens: 2048,
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      {
        role: "user",
        content: `<contexto>\n${contextText}\n</contexto>\n\nPergunta: ${question}`,
      },
    ],
  });

  return response.choices[0].message.content;
}

export async function streamWithContext(question, contextSections) {
  const contextText = contextSections
    .map((s) => `### ${s.doc_title} — ${s.section_title}\n${s.text}`)
    .join("\n\n---\n\n");

  return openai.chat.completions.create({
    model: "gpt-4o-mini",
    temperature: 0.1,
    max_tokens: 2048,
    stream: true,
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      {
        role: "user",
        content: `<contexto>\n${contextText}\n</contexto>\n\nPergunta: ${question}`,
      },
    ],
  });
}

export { openai };
