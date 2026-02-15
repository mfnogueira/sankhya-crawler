"""Descobre todas as URLs do menu lateral do Sankhya Developer e grava em urls.txt."""

import re
from pathlib import Path

from docling.document_converter import DocumentConverter

BASE_URL = "https://developer.sankhya.com.br"
SEED_URL = f"{BASE_URL}/docs/conhecendo-o-portal"
URLS_FILE = Path("urls.txt")


def main():
    print(f"Acessando {SEED_URL} para extrair menu lateral...")
    converter = DocumentConverter()
    result = converter.convert(SEED_URL)
    raw_md = result.document.export_to_markdown()

    # Extrai somente o menu lateral (do início até "Powered by")
    menu_match = re.match(r"^(.*?Powered by)", raw_md, flags=re.DOTALL)
    if not menu_match:
        print("Não foi possível identificar o menu lateral.")
        return

    menu = menu_match.group(1)

    # Extrai todos os links /docs/... do menu (ignora links externos)
    slugs = re.findall(r"\(/docs/([^)]+)\)", menu)
    urls = list(dict.fromkeys(f"{BASE_URL}/docs/{slug}" for slug in slugs))

    # Preserva URLs manuais já existentes no arquivo
    existing = set()
    if URLS_FILE.exists():
        existing = {line.strip() for line in URLS_FILE.read_text().splitlines() if line.strip()}

    new_urls = [u for u in urls if u not in existing]

    with open(URLS_FILE, "a", encoding="utf-8") as f:
        for url in new_urls:
            f.write(url + "\n")

    print(f"\n{len(urls)} URLs encontradas no menu lateral.")
    print(f"{len(new_urls)} novas adicionadas ao {URLS_FILE}.")
    print(f"{len(existing)} já existiam.")
    print(f"\nTotal no {URLS_FILE}: {len(existing) + len(new_urls)}")


if __name__ == "__main__":
    main()
