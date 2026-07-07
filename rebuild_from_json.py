"""
Reconstrói .apkg / .tsv a partir de um JSON já gerado pelo card_agent
(sem chamar o modelo de novo). Útil após editar os templates.

Uso:  .venv\\Scripts\\python.exe rebuild_from_json.py --json output/javascriptbasico.json
"""
import argparse
import json
from pathlib import Path

import genanki
import anki_models
import card_agent  # reutiliza write_tsv / slugify

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
    cards = data.get("cards", [])

    by_type = {}
    for c in cards:
        by_type.setdefault(c["type"], []).append(c["fields"])

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    slug = card_agent.slugify(deck_name)
    formats = {f.strip() for f in args.formats.split(",") if f.strip()}
    tags = ["gerado-ollama", slug]

    if "csv" in formats:
        for t, rows in by_type.items():
            card_agent.write_tsv(out / f"{slug}__{t}.tsv",
                                 anki_models.MODEL_NAMES[t], deck_name, tags, rows)

    if "apkg" in formats:
        models = anki_models.build_models()
        deck = genanki.Deck(anki_models.DECK_DEFAULT + (abs(hash(slug)) % 100000), deck_name)
        for t, rows in by_type.items():
            for fields in rows:
                deck.add_note(genanki.Note(model=models[t], fields=fields, tags=tags))
        genanki.Package(deck).write_to_file(str(out / f"{slug}.apkg"))

    total = sum(len(v) for v in by_type.values())
    print(f"OK -> {slug}  ({total} cards, templates atualizados)")


if __name__ == "__main__":
    main()
