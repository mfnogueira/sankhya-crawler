"""Parsing compartilhado de markdown da documentação Sankhya."""

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

URLS_FILE = Path("urls.txt")
OUTPUT_DIR = Path("output")
METADATA_DIR = Path("metadata")
BASE_URL = "https://developer.sankhya.com.br/docs"

# ── Mapeamento slug → categoria (extraído do menu lateral) ──────────
CATEGORY_MAP: dict[str, str] = {
    # Sankhya Developer
    "conhecendo-o-portal": "Sankhya Developer",
    "como-contribuir": "Sankhya Developer",
    "comunidade": "Sankhya Developer",
    # Portal do Desenvolvedor
    "portal-do-desenvolvedor": "Portal do Desenvolvedor",
    "como-obter-acesso-como-desenvolvedor-externo": "Portal do Desenvolvedor",
    "criar-uma-solucao-de-uso-exclusivo-do-cliente": "Portal do Desenvolvedor",
    "versoes-de-um-add-on": "Portal do Desenvolvedor",
    "minhas-solucoes": "Portal do Desenvolvedor",
    "marketplace": "Portal do Desenvolvedor",
    "como-cadastrar-uma-solucao-no-marketplace-via-portal-do-desenvolvedor": "Portal do Desenvolvedor",
    "cliente-sankhya-como-obter-acesso-ao-portal-do-desenvolvedor": "Portal do Desenvolvedor",
    # Certificação
    "certificação-sankhya-developer": "Certificação Sankhya Developer",
    "certified-associate-sankhya-developer-java-web": "Certificação Sankhya Developer",
    "associate-front-end": "Certificação Sankhya Developer",
    "associate-framework-dicionário-de-dados": "Certificação Sankhya Developer",
    "specialist-extensões": "Certificação Sankhya Developer",
    "specialist-relatorios-formatados": "Certificação Sankhya Developer",
    "specialist-dashboards": "Certificação Sankhya Developer",
    "specialist-plataforma-de-personalizacoes": "Certificação Sankhya Developer",
    # Tech Academy
    "tech-academy-sankhya": "Tech Academy",
    # ADDON STUDIO
    "add-on-studio": "ADDON STUDIO",
    "configuracao-inicial": "ADDON STUDIO",
    "01_ambiente": "ADDON STUDIO",
    "03_conf_addonstudio": "ADDON STUDIO",
    "04_deploy_testes_locais": "ADDON STUDIO",
    "03_estrutura-do-projeto": "ADDON STUDIO",
    "01_dicionario-de-dados": "ADDON STUDIO",
    "02_autoddl": "ADDON STUDIO",
    "03_dynamicform": "ADDON STUDIO",
    "04_tabela_hierarquica": "ADDON STUDIO",
    "05_filtros": "ADDON STUDIO",
    "06_menu": "ADDON STUDIO",
    "07_telas": "ADDON STUDIO",
    "02_scripts": "ADDON STUDIO",
    "03_parameter": "ADDON STUDIO",
    "04_dashboard": "ADDON STUDIO",
    "05_action_button": "ADDON STUDIO",
    "06_business_rules": "ADDON STUDIO",
    "07_listeners": "ADDON STUDIO",
    "08_callback": "ADDON STUDIO",
    "09_service": "ADDON STUDIO",
    "jobs-agendados-com-job": "ADDON STUDIO",
    # SDK Sankhya
    "introducao-sdk-sankhya": "SDK Sankhya",
    "conceitos-fundamentais": "SDK Sankhya",
    "iniciando": "SDK Sankhya",
    "services-controllers": "SDK Sankhya",
    "job": "SDK Sankhya",
    "bean-validation": "SDK Sankhya",
    "injecao-de-dependencias": "SDK Sankhya",
    "controle-transacional": "SDK Sankhya",
    "mapeamento-relacional": "SDK Sankhya",
    "repositorio-dados": "SDK Sankhya",
    "️-mapeamento-de-objetos-com-mapstruct": "SDK Sankhya",
    "️-adaptadores-de-tipos": "SDK Sankhya",
    "serviço-de-logs-remotos": "SDK Sankhya",
    "11_controller_advice": "SDK Sankhya",
    "migrando-extensões-que-usam-o-dwf-para-o-add-on-studio": "ADDON STUDIO",
    "guia-de-boas-praticas": "ADDON STUDIO",
    "faq": "ADDON STUDIO",
    # Personalização e Customização
    "tipos_de_personalizacao": "Personalização e Customização",
    "módulo-java-para-regras-da-central": "Personalização e Customização",
    "botoes-de-acao": "Personalização e Customização",
    "rotina-lançador": "Personalização e Customização",
    "rotina-banco-de-dados": "Personalização e Customização",
    "scripts": "Personalização e Customização",
    "rotina-java": "Personalização e Customização",
    "transação-manual-para-ações": "Personalização e Customização",
    "botões-de-ação-na-fap": "Personalização e Customização",
    "operacoes-comerciais": "Personalização e Customização",
    # Relatórios Formatados / iReport
    "instalacao-e-configuracao-ireport": "Relatórios Formatados",
    "plugin-ireport": "Relatórios Formatados",
    "boas-praticas-ireport": "Relatórios Formatados",
    "propriedades-de-parametros-do-ireport": "Relatórios Formatados",
    "funções-utilitárias-em-relatórios-ireport-1": "Relatórios Formatados",
    "qr-code-no-ireport": "Relatórios Formatados",
    "eventos-de-click-no-ireport": "Relatórios Formatados",
    # Frameworks, APIs e Ferramentas
    "dicionário-de-dados": "Frameworks, APIs e Ferramentas",
    "recursos-avançados": "Frameworks, APIs e Ferramentas",
    "jape": "Frameworks, APIs e Ferramentas",
    "sankhya-js": "Frameworks, APIs e Ferramentas",
    "generator-sankhya": "Frameworks, APIs e Ferramentas",
    "sankhyautil": "Frameworks, APIs e Ferramentas",
    "debug-de-aplicações-java-remotamente": "Frameworks, APIs e Ferramentas",
    "configuração-java_opts": "Frameworks, APIs e Ferramentas",
}


def url_to_slug(url: str) -> str:
    last_segment = urlparse(url).path.rstrip("/").split("/")[-1]
    return unquote(last_segment)


def build_slug_url_map() -> dict[str, str]:
    """Constrói mapeamento slug → URL completa a partir do urls.txt."""
    mapping = {}
    if URLS_FILE.exists():
        for line in URLS_FILE.read_text().splitlines():
            url = line.strip()
            if url:
                mapping[url_to_slug(url)] = url
    return mapping


def clean_section_content(text: str) -> str:
    """Remove artefatos de imagem e normaliza headings malformados."""
    text = re.sub(r"\n\d{2,4}\n\n<!-- image -->", "", text)
    text = re.sub(r"<!-- image -->", "", text)
    text = re.sub(r"^(#{2,})\s+#{2,}\s+", r"\1 ", text, flags=re.MULTILINE)
    text = re.sub(r"\n*Updated \d+ \w+ ago\s*$", "", text)
    return text.strip()


def extract_cross_references(content: str) -> list[str]:
    """Extrai slugs de links internos no conteúdo markdown."""
    refs = set()
    for slug in re.findall(r"\(doc:([^)]+)\)", content):
        refs.add(slug)
    for slug in re.findall(
        r"\(https://developer\.sankhya\.com\.br/docs/([^)#\s]+)\)", content
    ):
        refs.add(unquote(slug))
    for slug in re.findall(r"\(/docs/([^)#\s]+)\)", content):
        refs.add(unquote(slug))
    return list(refs)


def parse_markdown(filepath: Path, slug: str, url: str) -> dict:
    """Parseia um arquivo markdown e retorna estrutura para ingestão."""
    content = filepath.read_text(encoding="utf-8")

    title_match = re.match(r"^#\s+(.+)", content)
    title = title_match.group(1).strip() if title_match else slug

    sections = []
    current_title = "Introdução"
    current_lines: list[str] = []
    order = 0

    for line in content.split("\n"):
        h2_match = re.match(r"^##\s+(\S.+)", line)
        if h2_match:
            section_content = clean_section_content("\n".join(current_lines))
            if section_content:
                sections.append(
                    {
                        "id": f"{slug}___{order}",
                        "title": current_title,
                        "content": section_content,
                        "level": 2,
                        "order": order,
                        "doc_slug": slug,
                    }
                )
                order += 1
            current_title = h2_match.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    section_content = clean_section_content("\n".join(current_lines))
    if section_content:
        sections.append(
            {
                "id": f"{slug}___{order}",
                "title": current_title,
                "content": section_content,
                "level": 2,
                "order": order,
                "doc_slug": slug,
            }
        )

    links = extract_cross_references(content)
    links = [ref for ref in links if ref != slug]

    preview = content[:300].replace("\n", " ").strip()
    category = CATEGORY_MAP.get(slug, "Outros")

    return {
        "slug": slug,
        "title": title,
        "url": url,
        "content_preview": preview,
        "category": category,
        "sections": sections,
        "links": links,
    }


def load_metadata(slug: str) -> dict:
    """Carrega metadados extraídos para um documento (ou retorna dict vazio)."""
    meta_path = METADATA_DIR / f"{slug}.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return {}


def load_all_documents() -> list[dict]:
    """Carrega e parseia todos os documentos markdown."""
    slug_url_map = build_slug_url_map()
    md_files = sorted(OUTPUT_DIR.glob("*.md"))
    documents = []
    for filepath in md_files:
        slug = filepath.stem
        url = slug_url_map.get(slug, f"{BASE_URL}/{slug}")
        doc = parse_markdown(filepath, slug, url)
        doc["metadata"] = load_metadata(slug)
        documents.append(doc)
    return documents
