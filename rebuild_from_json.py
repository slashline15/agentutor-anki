"""
Reconstrói .apkg / .tsv a partir de um JSON já gerado pelo card_agent
(sem chamar o modelo de novo). Útil após editar os templates.

Uso:  .venv\\Scripts\\python.exe rebuild_from_json.py --json output/javascriptbasico.json
"""
import argparse
import json
from pathlib import Path

from anki_toolkit import outputs

BASE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True, help="JSON gerado pelo card_agent.")
    ap.add_argument("--out", default=str(BASE / "output"))
    ap.add_argument("--deck", help="Sobrescreve o nome do baralho.")
    ap.add_argument("--formats", default="apkg,csv")
    args = ap.parse_args()

    data = json.loads(Path(args.json).read_text(encoding="utf-8"))
    deck_name = args.deck or data.get("deck") or "Cards"
    by_type = outputs.group_by_type(data.get("cards", []))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    slug = outputs.slugify(deck_name)
    formats = {f.strip() for f in args.formats.split(",") if f.strip()}
    tags = ["gerado-ollama", slug]

    if "csv" in formats:
        outputs.write_tsvs(out, slug, deck_name, tags, by_type)

    if "apkg" in formats:
        outputs.write_apkg(out / f"{slug}.apkg", deck_name, tags, by_type)

    total = sum(len(v) for v in by_type.values())
    print(f"OK -> {slug}  ({total} cards, templates atualizados)")


if __name__ == "__main__":
    main()
