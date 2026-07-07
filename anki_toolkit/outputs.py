"""
Conversão de cards e escrita das saídas: TSV, APKG e JSON intermediário.

Contrato central do projeto: o "JSON de cards" (ver make_json_payload), com
"schema": 1. Produtores e consumidores novos devem falar este formato; campos
novos só entram como opcionais (retrocompatível).
"""
import json
import re
import zlib
from datetime import datetime

import genanki

from . import SCHEMA_VERSION
from . import models as _models


# ----------------------------------------------------------------------------- helpers
def nl2br(s):
    return str(s or "").replace("\r\n", "\n").replace("\n", "<br>")


def slugify(s):
    s = re.sub(r"[^\w\s-]", "", str(s).lower(), flags=re.UNICODE).strip()
    return re.sub(r"[\s_-]+", "-", s) or "cards"


def has_cloze(s):
    return bool(re.search(r"\{\{c\d+::", str(s or "")))


def deck_id(slug):
    """ID de deck determinístico por slug (crc32, não o hash() salgado do
    Python — o mesmo baralho tem sempre o mesmo ID entre execuções)."""
    return _models.DECK_DEFAULT + (zlib.crc32(slug.encode("utf-8")) % 100000)


# ----------------------------------------------------------------------------- conversão
def card_to_fields(card):
    """Converte 1 card do JSON nos campos do note type. Retorna (tipo, [campos]) ou None."""
    t = card.get("type", "qa")
    ex = nl2br(card.get("extra", ""))
    if t == "qa":
        front, back = card.get("front", ""), card.get("back", "")
        if not front or not back:
            return None
        return "qa", [nl2br(front), nl2br(back), ex]
    if t == "cloze":
        text = card.get("text", "")
        if not has_cloze(text):
            return None
        return "cloze", [nl2br(text), ex]
    if t == "code_output":
        code, ans = card.get("code", ""), card.get("answer", "")
        if not code or ans == "":
            return None
        return "code_output", [nl2br(code), nl2br(ans), ex]
    if t == "code_write":
        front, ans = card.get("front", ""), card.get("answer", "")
        if not front or not ans:
            return None
        return "code_write", [nl2br(front), nl2br(ans), ex]
    if t == "code_cloze":
        code = card.get("code", "")
        if not has_cloze(code):
            return None
        return "code_cloze", [nl2br(code), ex]
    return None


def group_by_type(cards):
    """Agrupa cards já convertidos ({"type": t, "fields": [...]}) por tipo."""
    by_type = {}
    for c in cards:
        by_type.setdefault(c["type"], []).append(c["fields"])
    return by_type


# ----------------------------------------------------------------------------- escrita
def write_tsv(path, model_name, deck, tags, rows):
    def san(x):
        return str(x).replace("\t", "    ").replace("\r", "").replace("\n", "<br>")
    lines = [
        "#separator:tab", "#html:true",
        f"#notetype:{model_name}", f"#deck:{deck}",
        f"#tags:{' '.join(tags)}",
    ]
    for r in rows:
        lines.append("\t".join(san(c) for c in r))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_tsvs(out_dir, slug, deck_name, tags, by_type):
    """Um TSV por note type presente em by_type. Retorna os caminhos escritos."""
    paths = []
    for t, rows in by_type.items():
        p = out_dir / f"{slug}__{t}.tsv"
        write_tsv(p, _models.MODEL_NAMES[t], deck_name, tags, rows)
        paths.append(p)
    return paths


def build_deck(deck_name, tags, by_type):
    """Monta um genanki.Deck com todas as notas (ID determinístico por slug)."""
    built = _models.build_models()
    deck = genanki.Deck(deck_id(slugify(deck_name)), deck_name)
    for t, rows in by_type.items():
        for fields in rows:
            deck.add_note(genanki.Note(model=built[t], fields=fields, tags=tags))
    return deck


def write_apkg(path, deck_name, tags, by_type, media_files=None):
    deck = build_deck(deck_name, tags, by_type)
    pkg = genanki.Package(deck)
    if media_files:
        pkg.media_files = list(media_files)
    pkg.write_to_file(str(path))
    return path


def make_json_payload(deck_name, model, cards):
    """JSON intermediário (contrato do projeto). cards = [{"type","fields"}]."""
    return {
        "schema": SCHEMA_VERSION,
        "deck": deck_name,
        "model": model,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "cards": cards,
    }


def write_json(path, deck_name, model, cards):
    path.write_text(
        json.dumps(make_json_payload(deck_name, model, cards),
                   ensure_ascii=False, indent=2),
        encoding="utf-8")
    return path
