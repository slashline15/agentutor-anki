"""
ingest.py — converte PDF em markdown limpo, pronto para virar cards.

Rotas (seleção automática por padrão):
  digital  PDF com texto embutido (docling, rápido)
  scanned  PDF escaneado (docling + OCR em lotes; GPU se houver)
  ollama   fallback via modelo multimodal do Ollama (sem docling)

Uso:
  .venv\\Scripts\\python.exe ingest.py apostila.pdf
  .venv\\Scripts\\python.exe ingest.py apostila.pdf --route scanned --out library
  # depois:  card_agent.py --file library/apostila.md --push
"""
import argparse
import sys

from anki_toolkit import ingest as ing
from anki_toolkit import vault


def main():
    ap = argparse.ArgumentParser(description="PDF -> markdown para flashcards.")
    ap.add_argument("pdf", help="Arquivo PDF de entrada.")
    ap.add_argument("--out", default=str(ing.DEFAULT_LIBRARY),
                    help="Pasta de saída (padrão: library/).")
    ap.add_argument("--route", default="auto",
                    choices=["auto", "digital", "scanned", "ollama"],
                    help="Rota de conversão (padrão: auto).")
    ap.add_argument("--batch", type=int, default=ing.BATCH_SIZE,
                    help=f"Páginas por lote na rota scanned (padrão {ing.BATCH_SIZE}).")
    ap.add_argument("--model", default=ing.OLLAMA_OCR_MODEL,
                    help="Modelo multimodal da rota ollama.")
    ap.add_argument("--vault", action="store_true",
                    help="Grava o markdown em Estudos/Materiais/ do vault do "
                         "Obsidian em vez de library/.")
    args = ap.parse_args()

    kwargs = {}
    if args.route == "scanned":
        kwargs["batch_size"] = args.batch
    if args.route == "ollama":
        kwargs["model"] = args.model

    out_dir = args.out
    if args.vault:
        try:
            out_dir = vault.materials_dir()
        except vault.VaultError as e:
            sys.exit(f"[erro] {e}")

    try:
        out = ing.ingest(args.pdf, out_dir=out_dir, route=args.route, **kwargs)
    except ing.IngestError as e:
        sys.exit(f"[erro] {e}")

    print(f"OK -> {out}")
    print(f"Próximo passo:  card_agent.py --file \"{out}\" --push")


if __name__ == "__main__":
    main()
