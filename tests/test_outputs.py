from anki_toolkit import outputs
from anki_toolkit.models import DECK_DEFAULT, MODEL_NAMES


def test_nl2br_converte_quebras_de_linha():
    assert outputs.nl2br("a\nb") == "a<br>b"
    assert outputs.nl2br("a\r\nb") == "a<br>b"
    assert outputs.nl2br("a\nb\nc") == "a<br>b<br>c"


def test_nl2br_none_e_vazio_viram_string_vazia():
    assert outputs.nl2br(None) == ""
    assert outputs.nl2br("") == ""


def test_slugify_minusculas_espacos_e_underscores_viram_hifen():
    assert outputs.slugify("List Comprehensions em Python!") == "list-comprehensions-em-python"
    assert outputs.slugify("A_B C") == "a-b-c"


def test_slugify_string_vazia_vira_cards():
    assert outputs.slugify("") == "cards"


def test_has_cloze_detecta_cloze_valido():
    assert outputs.has_cloze("{{c1::texto}}") is True
    assert outputs.has_cloze("{{c2::outro}}") is True


def test_has_cloze_false_para_texto_sem_cloze_ou_none():
    assert outputs.has_cloze("texto normal") is False
    assert outputs.has_cloze(None) is False


def test_card_to_fields_qa_valido():
    resultado = outputs.card_to_fields({"type": "qa", "front": "Pergunta", "back": "Resposta"})
    assert resultado == ("qa", ["Pergunta", "Resposta", ""])


def test_card_to_fields_qa_invalido_sem_back():
    assert outputs.card_to_fields({"type": "qa", "front": "Pergunta", "back": ""}) is None


def test_card_to_fields_cloze_valido():
    resultado = outputs.card_to_fields({"type": "cloze", "text": "{{c1::texto}}"})
    assert resultado == ("cloze", ["{{c1::texto}}", ""])


def test_card_to_fields_cloze_invalido_sem_cloze():
    assert outputs.card_to_fields({"type": "cloze", "text": "texto normal"}) is None


def test_card_to_fields_code_output_valido():
    resultado = outputs.card_to_fields({"type": "code_output", "code": "print(1)", "answer": "0"})
    assert resultado == ("code_output", ["print(1)", "0", ""])


def test_card_to_fields_code_output_invalido_sem_answer():
    assert outputs.card_to_fields({"type": "code_output", "code": "print(1)", "answer": ""}) is None


def test_card_to_fields_code_write_valido():
    resultado = outputs.card_to_fields({"type": "code_write", "front": "Escreva", "answer": "codigo"})
    assert resultado == ("code_write", ["Escreva", "codigo", ""])


def test_card_to_fields_code_write_invalido_sem_answer():
    assert outputs.card_to_fields({"type": "code_write", "front": "Escreva", "answer": ""}) is None


def test_card_to_fields_code_cloze_valido():
    resultado = outputs.card_to_fields({"type": "code_cloze", "code": "{{c1::codigo}}"})
    assert resultado == ("code_cloze", ["{{c1::codigo}}", ""])


def test_card_to_fields_code_cloze_invalido_sem_cloze():
    assert outputs.card_to_fields({"type": "code_cloze", "code": "codigo normal"}) is None


def test_card_to_fields_tipo_desconhecido_retorna_none():
    assert outputs.card_to_fields({"type": "inexistente", "front": "x", "back": "y"}) is None


def test_deck_id_deterministico():
    assert outputs.deck_id("slug") == outputs.deck_id("slug")


def test_deck_id_diferente_para_slugs_diferentes():
    assert outputs.deck_id("slug-a") != outputs.deck_id("slug-b")


def test_deck_id_dentro_do_intervalo_padrao():
    did = outputs.deck_id("qualquer-slug")
    assert DECK_DEFAULT <= did < DECK_DEFAULT + 100000


def test_group_by_type_preserva_ordem():
    cards = [
        {"type": "qa", "fields": ["f1", "b1", ""]},
        {"type": "cloze", "fields": ["c1", ""]},
        {"type": "qa", "fields": ["f2", "b2", ""]},
    ]
    agrupado = outputs.group_by_type(cards)
    assert agrupado == {
        "qa": [["f1", "b1", ""], ["f2", "b2", ""]],
        "cloze": [["c1", ""]],
    }


def test_write_tsv_cabecalhos_e_formatacao(tmp_path):
    caminho = tmp_path / "saida.tsv"
    outputs.write_tsv(
        caminho,
        model_name="Modelo Basico",
        deck="Meu Deck",
        tags=["tag1", "tag2"],
        rows=[["a\tb", "linha\nquebra"], ["normal", "ok"]],
    )
    conteudo = caminho.read_text(encoding="utf-8")
    linhas = conteudo.splitlines()
    assert linhas[0] == "#separator:tab"
    assert linhas[1] == "#html:true"
    assert linhas[2] == "#notetype:Modelo Basico"
    assert linhas[3] == "#deck:Meu Deck"
    assert linhas[4] == "#tags:tag1 tag2"
    assert linhas[5] == "a    b\tlinha<br>quebra"
    assert linhas[6] == "normal\tok"
    assert conteudo.endswith("\n")


def test_write_tsvs_cria_arquivo_por_tipo(tmp_path):
    by_type = {
        "qa": [["f", "b", ""]],
        "cloze": [["{{c1::x}}", ""]],
    }
    caminhos = outputs.write_tsvs(
        out_dir=tmp_path,
        slug="meu-deck",
        deck_name="Meu Deck",
        tags=["tag"],
        by_type=by_type,
    )
    assert len(caminhos) == 2
    nomes = sorted(p.name for p in caminhos)
    assert nomes == ["meu-deck__cloze.tsv", "meu-deck__qa.tsv"]
    for p in caminhos:
        assert p.exists()
        assert MODEL_NAMES[p.name.split("__")[1].replace(".tsv", "")] in p.read_text(encoding="utf-8")
