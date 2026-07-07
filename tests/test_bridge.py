from anki_toolkit import bridge
from anki_toolkit.models import MODEL_NAMES, FIELDS
import urllib.error


def test_invoke_retorna_result_quando_sem_erro(monkeypatch):
    def fake_post(url, payload, timeout):
        return {"result": "ok", "error": None}

    monkeypatch.setattr(bridge, "_post", fake_post)
    assert bridge.invoke("ping") == "ok"


def test_invoke_levanta_erro_quando_resposta_contem_error(monkeypatch):
    def fake_post(url, payload, timeout):
        return {"result": None, "error": "algum erro"}

    monkeypatch.setattr(bridge, "_post", fake_post)

    try:
        bridge.invoke("qualquer")
    except bridge.AnkiConnectError as e:
        assert "qualquer" in str(e)
        assert "algum erro" in str(e)
        return

    raise AssertionError("Esperava AnkiConnectError")


def test_invoke_levanta_erro_quando_post_falha_com_url_error(monkeypatch):
    def fake_post(url, payload, timeout):
        raise urllib.error.URLError("recusado")

    monkeypatch.setattr(bridge, "_post", fake_post)

    try:
        bridge.invoke("ping", url="http://localhost:8765")
    except bridge.AnkiConnectError as e:
        assert "http://localhost:8765" in str(e)
        return

    raise AssertionError("Esperava AnkiConnectError")


def test_is_available_true_quando_version_responde(monkeypatch):
    def fake_post(url, payload, timeout):
        return {"result": 6, "error": None}

    monkeypatch.setattr(bridge, "_post", fake_post)
    assert bridge.is_available() is True


def test_is_available_false_quando_post_levanta_url_error(monkeypatch):
    def fake_post(url, payload, timeout):
        raise urllib.error.URLError("recusado")

    monkeypatch.setattr(bridge, "_post", fake_post)
    assert bridge.is_available() is False


def test_to_notes_gera_notas_corretamente():
    by_type = {
        "qa": [["Pergunta", "Resposta", "Extra"]],
        "cloze": [["{{c1::texto}}", "Extra"]],
    }
    notes = bridge._to_notes("MeuDeck", ["tag1"], by_type)

    assert len(notes) == 2

    nota_qa = notes[0]
    assert nota_qa["deckName"] == "MeuDeck"
    assert nota_qa["modelName"] == MODEL_NAMES["qa"]
    assert nota_qa["fields"] == dict(zip(FIELDS["qa"], by_type["qa"][0]))
    assert nota_qa["tags"] == ["tag1"]
    assert nota_qa["options"] == {"allowDuplicate": False}

    nota_cloze = notes[1]
    assert nota_cloze["deckName"] == "MeuDeck"
    assert nota_cloze["modelName"] == MODEL_NAMES["cloze"]
    assert nota_cloze["fields"] == dict(zip(FIELDS["cloze"], by_type["cloze"][0]))
    assert nota_cloze["tags"] == ["tag1"]
    assert nota_cloze["options"] == {"allowDuplicate": False}


def test_push_cards_caminho_feliz(monkeypatch):
    chamadas = []

    def fake_post(url, payload, timeout):
        chamadas.append(payload)
        action = payload["action"]

        if action == "modelNames":
            return {"result": list(MODEL_NAMES.values()), "error": None}
        if action == "createDeck":
            return {"result": 1, "error": None}
        if action == "canAddNotes":
            return {"result": [True, False, True], "error": None}
        if action == "addNotes":
            return {"result": [111, 222], "error": None}

        return {"result": None, "error": None}

    monkeypatch.setattr(bridge, "_post", fake_post)

    by_type = {
        "qa": [["P1", "R1", ""], ["P2", "R2", ""]],
        "cloze": [["{{c1::x}}", ""]],
    }

    resultado = bridge.push_cards("DeckTeste", ["tag"], by_type)

    assert resultado == {"added": 2, "skipped": 1, "total": 3}

    acoes = [c["action"] for c in chamadas]
    assert "createDeck" in acoes
    assert "canAddNotes" in acoes
    assert "addNotes" in acoes

    create_deck_call = next(c for c in chamadas if c["action"] == "createDeck")
    assert create_deck_call["params"]["deck"] == "DeckTeste"

    add_notes_call = next(c for c in chamadas if c["action"] == "addNotes")
    assert len(add_notes_call["params"]["notes"]) == 2


def test_push_cards_todas_duplicadas_e_resultado_normal(monkeypatch):
    # duplicata total NÃO é erro: retorna zeros e não cai para .apkg
    chamadas = []

    def fake_post(url, payload, timeout):
        chamadas.append(payload)
        action = payload["action"]

        if action == "modelNames":
            return {"result": list(MODEL_NAMES.values()), "error": None}
        if action == "createDeck":
            return {"result": 1, "error": None}
        if action == "canAddNotes":
            return {"result": [False, False, False], "error": None}

        return {"result": None, "error": None}

    monkeypatch.setattr(bridge, "_post", fake_post)

    by_type = {
        "qa": [["P1", "R1", ""], ["P2", "R2", ""], ["P3", "R3", ""]],
    }

    resultado = bridge.push_cards("DeckTeste", ["tag"], by_type)
    assert resultado == {"added": 0, "skipped": 3, "total": 3}
    # addNotes nunca deve ser chamado quando não há nada adicionável
    assert "addNotes" not in [c["action"] for c in chamadas]


def test_push_cards_note_type_ausente_levanta_erro(monkeypatch):
    # coleção sem os note types do projeto: erro claro ANTES de criar o deck
    chamadas = []

    def fake_post(url, payload, timeout):
        chamadas.append(payload)
        if payload["action"] == "modelNames":
            return {"result": ["Basic", "Cloze"], "error": None}
        return {"result": None, "error": None}

    monkeypatch.setattr(bridge, "_post", fake_post)

    by_type = {"qa": [["P1", "R1", ""]]}

    try:
        bridge.push_cards("DeckTeste", ["tag"], by_type)
    except bridge.AnkiConnectError as e:
        assert "ausentes" in str(e).lower()
        assert MODEL_NAMES["qa"] in str(e)
        assert [c["action"] for c in chamadas] == ["modelNames"]
        return

    raise AssertionError("Esperava AnkiConnectError")


def test_push_cards_by_type_vazio_retorna_zeros_sem_chamadas(monkeypatch):
    chamadas = []

    def fake_post(url, payload, timeout):
        chamadas.append(payload)
        return {"result": None, "error": None}

    monkeypatch.setattr(bridge, "_post", fake_post)

    resultado = bridge.push_cards("DeckTeste", ["tag"], {})
    assert resultado == {"added": 0, "skipped": 0, "total": 0}
    assert chamadas == []


def test_push_cards_add_notes_com_falha_conta_como_pulado(monkeypatch):
    chamadas = []

    def fake_post(url, payload, timeout):
        chamadas.append(payload)
        action = payload["action"]

        if action == "modelNames":
            return {"result": list(MODEL_NAMES.values()), "error": None}
        if action == "createDeck":
            return {"result": 1, "error": None}
        if action == "canAddNotes":
            return {"result": [True, True], "error": None}
        if action == "addNotes":
            return {"result": [111, None], "error": None}

        return {"result": None, "error": None}

    monkeypatch.setattr(bridge, "_post", fake_post)

    by_type = {
        "qa": [["P1", "R1", ""], ["P2", "R2", ""]],
    }

    resultado = bridge.push_cards("DeckTeste", ["tag"], by_type)
    assert resultado == {"added": 1, "skipped": 1, "total": 2}
