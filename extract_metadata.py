"""Extração de metadados estruturais e semânticos via GPT-4o-mini."""

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from parser import load_all_documents

load_dotenv()

METADATA_DIR = Path("metadata")
METADATA_DIR.mkdir(exist_ok=True)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

EXTRACTION_PROMPT = """Analise o documento técnico da documentação Sankhya Developer abaixo e extraia metadados estruturados em JSON.

DOCUMENTO:
Título: {title}
Categoria: {category}
URL: {url}

Conteúdo:
{content}

---

Retorne APENAS um JSON válido (sem markdown, sem ```json```) com a seguinte estrutura:

{{
  "estruturais": {{
    "sistema": "Sankhya-Om",
    "modulo": "<módulo principal: Personalizações | Add-on Studio | SDK Sankhya | Relatórios | Frameworks | Portal do Desenvolvedor | Certificação | Geral>",
    "tipo_acao": "<tipo de ação descrita: Rotina no Banco de Dados | Botão de Ação | Listener | Callback | Service | Job | Configuração | Tutorial | Conceitual | Referência>",
    "tecnologias": ["<tecnologias mencionadas: Oracle, SQLServer, Java, JavaScript, HTML, CSS, etc.>"],
    "linguagem": "<linguagem principal: SQL / PL-SQL | Java | JavaScript | SankhyaJS | Misto | N/A>",
    "tipo_conteudo": "<Tutorial Técnico | Guia de Configuração | Referência API | Conceitual | FAQ | Boas Práticas>",
    "nivel": "<Iniciante | Intermediario | Avançado>",
    "tema_principal": "<tema em 2-3 palavras>",
    "usa_funcoes_act": <true se usa funções ACT_*, false caso contrário>
  }},
  "semanticos": {{
    "funcoes_utilizadas": ["<funções ACT_*, métodos Jape, funções Sankhya mencionadas>"],
    "conceitos": ["<conceitos-chave: P_IDSESSAO, SessionHandle, EntityFacade, NativeSql, DynamicVO, etc.>"],
    "tabelas_exemplo": ["<tabelas mencionadas: TGFCAB, AD_*, TSIEMP, etc.>"],
    "apis_referenciadas": ["<APIs/serviços: ServiceContext, JapeWrapper, DWFDataProvider, etc.>"],
    "classes_java": ["<classes Java mencionadas: JapeSession, EntityFacade, DynamicVO, etc.>"]
  }}
}}

Regras:
- Use arrays vazios [] quando não houver itens para um campo
- Extraia APENAS informações explicitamente presentes no texto
- Não invente dados que não estão no documento
- Para "tecnologias", inclua apenas as que são realmente mencionadas
- Para "funcoes_utilizadas", inclua funções ACT_*, métodos de API Sankhya, e helpers mencionados"""


def extract_metadata_for_doc(doc: dict) -> dict:
    """Extrai metadados de um documento usando GPT-4o-mini."""
    content = "\n\n".join(
        f"## {s['title']}\n{s['content']}" for s in doc["sections"]
    )
    # Limitar conteúdo para não estourar contexto
    if len(content) > 12000:
        content = content[:12000] + "\n\n[... conteúdo truncado ...]"

    prompt = EXTRACTION_PROMPT.format(
        title=doc["title"],
        category=doc["category"],
        url=doc["url"],
        content=content,
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.0,
        max_tokens=1024,
        messages=[
            {
                "role": "system",
                "content": "Você é um classificador de documentação técnica. Retorne apenas JSON válido.",
            },
            {"role": "user", "content": prompt},
        ],
    )

    raw = response.choices[0].message.content.strip()
    # Limpar possíveis delimitadores markdown
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip()

    return json.loads(raw)


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("Defina OPENAI_API_KEY no arquivo .env")
        return

    documents = load_all_documents()
    if not documents:
        print("Nenhum documento encontrado em output/")
        return

    print(f"Extraindo metadados de {len(documents)} documentos via GPT-4o-mini...\n")

    success = 0
    skipped = 0
    errors = 0

    for i, doc in enumerate(documents, 1):
        slug = doc["slug"]
        output_path = METADATA_DIR / f"{slug}.json"

        # Pular se já extraído
        if output_path.exists():
            print(f"  [{i}/{len(documents)}] {slug} — já extraído, pulando")
            skipped += 1
            continue

        try:
            print(f"  [{i}/{len(documents)}] {slug}...", end=" ", flush=True)
            metadata = extract_metadata_for_doc(doc)

            output_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print("OK")
            success += 1

            # Rate limiting: ~20 req/min para tier gratuito
            time.sleep(0.5)

        except json.JSONDecodeError as e:
            print(f"ERRO (JSON inválido): {e}")
            errors += 1
        except Exception as e:
            print(f"ERRO: {e}")
            errors += 1
            time.sleep(2)  # Backoff em caso de erro

    print(f"\nConcluído! Sucesso: {success}, Pulados: {skipped}, Erros: {errors}")
    print(f"Metadados salvos em: {METADATA_DIR}/")


if __name__ == "__main__":
    main()
