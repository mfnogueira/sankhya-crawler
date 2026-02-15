import { openai } from "../services/openai.js";

const CLASSIFIER_PROMPT = `Você é um classificador. Determine se a pergunta abaixo é sobre desenvolvimento no ERP Sankhya (frameworks, APIs, Jape, SankhyaJS, Add-ons, Add-on Studio, SDK Sankhya, iReport, dicionário de dados, personalização, botões de ação, relatórios, ou qualquer tema técnico relacionado ao Sankhya).

Responda APENAS "sim" ou "não".`;

export async function isOnTopic(question) {
  const response = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    temperature: 0,
    max_tokens: 5,
    messages: [
      { role: "system", content: CLASSIFIER_PROMPT },
      { role: "user", content: question },
    ],
  });

  const answer = response.choices[0].message.content.trim().toLowerCase();
  return answer.startsWith("sim");
}
