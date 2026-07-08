"""
Ponte com o AnkiConnect (addon 2055492159): adiciona cards direto na coleção
do Anki aberto, sem passar por .apkg.

Regras do projeto:
- Falha de comunicação vira AnkiConnectError; quem decide cair para .apkg é o
  script de CLI (fallback permanente, não provisório).
- Duplicatas são detectadas com canAddNotes e puladas (nunca inseridas 2x).
- Note types ausentes na coleção são CRIADOS automaticamente via createModel
  (a partir das mesmas definições genanki de models.py) — o primeiro --push
  funciona numa coleção zerada, sem importar .apkg antes.
"""
import base64
import json
import urllib.error
import urllib.request

import genanki

from . import models as _models

DEFAULT_URL = "http://localhost:8765"
API_VERSION = 6


class AnkiConnectError(RuntimeError):
    """AnkiConnect inacessível ou ação recusada pelo Anki."""


def _post(url, payload, timeout):
    """Transporte HTTP puro (separado para facilitar teste com monkeypatch)."""
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def invoke(action, params=None, url=DEFAULT_URL, timeout=30):
    """Chama uma ação do AnkiConnect e retorna o campo result."""
    payload = {"action": action, "version": API_VERSION, "params": params or {}}
    try:
        resp = _post(url, payload, timeout)
    except (urllib.error.URLError, OSError) as e:
        raise AnkiConnectError(
            f"AnkiConnect inacessível em {url} (o Anki está aberto com o "
            f"addon 2055492159 instalado?): {e}") from e
    if resp.get("error"):
        raise AnkiConnectError(f"AnkiConnect recusou '{action}': {resp['error']}")
    return resp.get("result")


def is_available(url=DEFAULT_URL, timeout=3):
    """True se o Anki está aberto com o AnkiConnect respondendo."""
    try:
        invoke("version", url=url, timeout=timeout)
        return True
    except AnkiConnectError:
        return False


def _to_notes(deck_name, tags, by_type):
    """Converte o by_type do projeto em notas no formato do AnkiConnect."""
    notes = []
    for t, rows in by_type.items():
        model_name = _models.MODEL_NAMES[t]
        field_names = _models.FIELDS[t]
        for row in rows:
            notes.append({
                "deckName": deck_name,
                "modelName": model_name,
                "fields": dict(zip(field_names, row)),
                "tags": list(tags),
                "options": {"allowDuplicate": False},
            })
    return notes


def store_media(filename, data_b64, url=DEFAULT_URL):
    """Grava um arquivo na media da coleção (base64). Usado pela fase de TTS."""
    return invoke("storeMediaFile", {"filename": filename, "data": data_b64},
                  url=url)


def store_media_file(path, url=DEFAULT_URL):
    """Grava um arquivo local na media da coleção. Retorna o nome usado."""
    from pathlib import Path
    p = Path(path)
    data_b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    store_media(p.name, data_b64, url=url)
    return p.name


def _model_payload(key):
    """Definição genanki -> params do createModel do AnkiConnect."""
    m = _models.build_models()[key]
    return {
        "modelName": m.name,
        "inOrderFields": [f["name"] for f in m.fields],
        "css": m.css,
        "isCloze": m.model_type == genanki.Model.CLOZE,
        "cardTemplates": [
            {"Name": t["name"], "Front": t["qfmt"], "Back": t["afmt"]}
            for t in m.templates],
    }


def ensure_models(types, url=DEFAULT_URL):
    """Cria na coleção os note types de `types` que ainda não existem.

    Retorna a lista de nomes criados (vazia se todos já existiam).
    """
    existing = set(invoke("modelNames", url=url))
    created = []
    for t in sorted(set(types)):
        name = _models.MODEL_NAMES[t]
        if name not in existing:
            invoke("createModel", _model_payload(t), url=url)
            created.append(name)
    return created


def push_cards(deck_name, tags, by_type, url=DEFAULT_URL):
    """Cria o deck (se preciso) e adiciona as notas; pula duplicatas.

    Retorna {"added": n, "skipped": m, "total": t}. Levanta AnkiConnectError
    se o Anki estiver inacessível ou se nenhuma nota puder ser adicionada
    (ex.: note types ausentes na coleção).
    """
    notes = _to_notes(deck_name, tags, by_type)
    if not notes:
        return {"added": 0, "skipped": 0, "total": 0}

    # note types ausentes são criados na hora (coleção zerada funciona)
    ensure_models(by_type.keys(), url=url)

    invoke("createDeck", {"deck": deck_name}, url=url)

    addable = invoke("canAddNotes", {"notes": notes}, url=url)
    to_add = [n for n, ok in zip(notes, addable) if ok]
    skipped = len(notes) - len(to_add)

    if not to_add:  # todas duplicadas: resultado normal, nada a fazer
        return {"added": 0, "skipped": skipped, "total": len(notes)}

    ids = invoke("addNotes", {"notes": to_add}, url=url)
    added = sum(1 for i in ids if i)
    failed = len(to_add) - added
    return {"added": added, "skipped": skipped + failed, "total": len(notes)}
