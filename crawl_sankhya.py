import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from docling.document_converter import DocumentConverter
from docling_core.types.doc import ImageRefMode

URLS_FILE = Path("urls.txt")
OUTPUT_DIR = Path("output")


def clean_content(md: str) -> str:
    # Remove menu lateral do início (até "Powered by")
    md = re.sub(r"^.*?Powered by\s*", "", md, count=1, flags=re.DOTALL)
    # Remove rodapé (Próxima/Anterior página, Ask AI, etc.)
    md = re.sub(r"\n(Próxima página|Página anterior|Ask AI).*$", "", md, flags=re.DOTALL)
    return md.strip()


def url_to_slug(url: str) -> str:
    last_segment = urlparse(url).path.rstrip("/").split("/")[-1]
    return unquote(last_segment)


def main():
    if not URLS_FILE.exists():
        print(f"Arquivo {URLS_FILE} não encontrado. Crie-o com uma URL por linha.")
        return

    urls = [line.strip() for line in URLS_FILE.read_text().splitlines() if line.strip()]
    if not urls:
        print(f"Nenhuma URL encontrada em {URLS_FILE}.")
        return

    OUTPUT_DIR.mkdir(exist_ok=True)

    pending = []
    for url in urls:
        slug = url_to_slug(url)
        md_file = OUTPUT_DIR / f"{slug}.md"
        if md_file.exists():
            print(f"Já coletado, pulando: {md_file.name}")
        else:
            pending.append((url, slug, md_file))

    if not pending:
        print("\nTodas as URLs já foram coletadas. Nada a fazer.")
        return

    converter = DocumentConverter()

    for url, slug, md_file in pending:
        print(f"Processando: {url}")
        result = converter.convert(url)

        images_dir = OUTPUT_DIR / slug / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # Exporta markdown com imagens referenciadas como PNGs
        result.document.save_as_markdown(
            filename=md_file,
            artifacts_dir=images_dir,
            image_mode=ImageRefMode.REFERENCED,
        )

        # Limpa o conteúdo (remove menu lateral e rodapé)
        raw = md_file.read_text(encoding="utf-8")
        cleaned = clean_content(raw)
        md_file.write_text(cleaned, encoding="utf-8")

        # Remove pasta de imagens se ficou vazia
        if not any(images_dir.iterdir()):
            images_dir.rmdir()
            slug_dir = OUTPUT_DIR / slug
            if not any(slug_dir.iterdir()):
                slug_dir.rmdir()

        print(f"  Salvo em {md_file} ({len(cleaned)} caracteres)")

    print(f"\nConcluído! {len(pending)} nova(s) página(s) coletada(s), {len(urls) - len(pending)} já existente(s).")


if __name__ == "__main__":
    main()
