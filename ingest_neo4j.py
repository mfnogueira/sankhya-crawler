"""Ingestão da documentação Sankhya no Neo4j como base de conhecimento."""

import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

from parser import load_all_documents

load_dotenv()

# ── Configuração Neo4j ───────────────────────────────────────────────
NEO4J_URI = os.environ.get("NEO4J_URI", "")
NEO4J_USER = os.environ.get("NEO4J_USER", "")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")


# ── Ingestão Neo4j ──────────────────────────────────────────────────


def create_constraints_and_indexes(driver):
    print("Criando constraints e indexes...")
    queries = [
        "CREATE CONSTRAINT doc_slug IF NOT EXISTS FOR (d:Document) REQUIRE d.slug IS UNIQUE",
        "CREATE CONSTRAINT cat_name IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT sec_id IF NOT EXISTS FOR (s:Section) REQUIRE s.id IS UNIQUE",
        "CREATE INDEX doc_title IF NOT EXISTS FOR (d:Document) ON (d.title)",
    ]
    for q in queries:
        driver.execute_query(q, database_=NEO4J_DATABASE)


def clear_database(driver):
    print("Limpando dados existentes...")
    driver.execute_query(
        "MATCH (n) DETACH DELETE n",
        database_=NEO4J_DATABASE,
    )


def ingest_categories(driver, categories: list[str]):
    print(f"Ingerindo {len(categories)} categorias...")
    driver.execute_query(
        "UNWIND $categories AS name MERGE (:Category {name: name})",
        categories=categories,
        database_=NEO4J_DATABASE,
    )


def ingest_documents(driver, documents: list[dict]):
    print(f"Ingerindo {len(documents)} documentos...")
    docs_data = [
        {
            "slug": d["slug"],
            "title": d["title"],
            "url": d["url"],
            "content_preview": d["content_preview"],
            "category": d["category"],
        }
        for d in documents
    ]
    driver.execute_query(
        """
        UNWIND $docs AS doc
        CREATE (d:Document {
            slug: doc.slug,
            title: doc.title,
            url: doc.url,
            content_preview: doc.content_preview
        })
        WITH d, doc
        MATCH (c:Category {name: doc.category})
        CREATE (d)-[:IN_CATEGORY]->(c)
        """,
        docs=docs_data,
        database_=NEO4J_DATABASE,
    )


def ingest_sections(driver, documents: list[dict]):
    all_sections = [s for d in documents for s in d["sections"]]
    print(f"Ingerindo {len(all_sections)} seções...")
    driver.execute_query(
        """
        UNWIND $sections AS sec
        MATCH (d:Document {slug: sec.doc_slug})
        CREATE (s:Section {
            id: sec.id,
            title: sec.title,
            content: sec.content,
            level: sec.level,
            order: sec.order
        })
        CREATE (d)-[:HAS_SECTION]->(s)
        """,
        sections=all_sections,
        database_=NEO4J_DATABASE,
    )

    # Criar cadeia NEXT entre seções de cada documento
    print("Criando relações NEXT entre seções...")
    slugs = [d["slug"] for d in documents if len(d["sections"]) > 1]
    for slug in slugs:
        driver.execute_query(
            """
            MATCH (d:Document {slug: $slug})-[:HAS_SECTION]->(s:Section)
            WITH s ORDER BY s.order
            WITH collect(s) AS sections
            FOREACH (i IN range(0, size(sections)-2) |
                FOREACH (s1 IN [sections[i]] |
                    FOREACH (s2 IN [sections[i+1]] |
                        CREATE (s1)-[:NEXT]->(s2)
                    )
                )
            )
            """,
            slug=slug,
            database_=NEO4J_DATABASE,
        )


def ingest_cross_references(driver, documents: list[dict]):
    known_slugs = {d["slug"] for d in documents}
    links = []
    for d in documents:
        for ref in d["links"]:
            if ref in known_slugs:
                links.append({"from_slug": d["slug"], "to_slug": ref})

    print(f"Criando {len(links)} referências cruzadas...")
    if links:
        driver.execute_query(
            """
            UNWIND $links AS link
            MATCH (from:Document {slug: link.from_slug})
            MATCH (to:Document {slug: link.to_slug})
            MERGE (from)-[:LINKS_TO]->(to)
            """,
            links=links,
            database_=NEO4J_DATABASE,
        )


# ── Main ─────────────────────────────────────────────────────────────


def main():
    if not NEO4J_PASSWORD:
        print("Defina NEO4J_PASSWORD no arquivo .env")
        return

    documents = load_all_documents()
    if not documents:
        print("Nenhum documento encontrado em output/")
        return

    categories = sorted(set(d["category"] for d in documents))
    total_sections = sum(len(d["sections"]) for d in documents)

    print(f"Parseados {len(documents)} documentos, {len(categories)} categorias, {total_sections} seções\n")

    print(f"Conectando ao Neo4j ({NEO4J_URI})...")
    with GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
        driver.verify_connectivity()
        print("Conectado!\n")

        clear_database(driver)
        create_constraints_and_indexes(driver)
        ingest_categories(driver, categories)
        ingest_documents(driver, documents)
        ingest_sections(driver, documents)
        ingest_cross_references(driver, documents)

        records, _, _ = driver.execute_query(
            """
            MATCH (d:Document) WITH count(d) AS docs
            MATCH (s:Section) WITH docs, count(s) AS secs
            MATCH (c:Category) WITH docs, secs, count(c) AS cats
            RETURN docs, secs, cats
            """,
            database_=NEO4J_DATABASE,
        )
        r = records[0]
        print(f"\nIngestão concluída!")
        print(f"  Categorias: {r['cats']}")
        print(f"  Documentos: {r['docs']}")
        print(f"  Seções:     {r['secs']}")


if __name__ == "__main__":
    main()
