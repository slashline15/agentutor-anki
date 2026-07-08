from anki_toolkit import tutor


def test_strip_html_remove_tags():
    assert tutor.strip_html("<b>x</b>") == "x"


def test_strip_html_br_vira_espaco():
    assert tutor.strip_html("a<br>b") == "a b"
    assert tutor.strip_html("a<br/>b") == "a b"
    assert tutor.strip_html("a<BR>b") == "a b"


def test_strip_html_remove_blocos_style_e_script():
    assert tutor.strip_html("x<style>.a{}</style>y") == "x y"
    assert tutor.strip_html("x<script>alert(1)</script>y") == "x y"


def test_strip_html_decodifica_entidades():
    assert tutor.strip_html("&lt;&gt;&amp;&quot;&nbsp;") == '<>&"'  # strip final


def test_strip_html_colapsa_espacos():
    assert tutor.strip_html("  a   b\tc\n") == "a b c"


def test_strip_html_none_retorna_vazio():
    assert tutor.strip_html(None) == ""


def test_simplify_card_mapeia_campos():
    info = {
        "deckName": "Deck::Sub",
        "modelName": "Básico",
        "question": "<b>Q</b>",
        "answer": "<i>A</i>",
        "lapses": 5,
        "factor": 2100,
        "reps": 10,
        "interval": 3,
    }
    assert tutor.simplify_card(info) == {
        "deck": "Deck::Sub",
        "model": "Básico",
        "question": "Q",
        "answer": "A",
        "lapses": 5,
        "ease": 2100,
        "reps": 10,
        "interval": 3,
    }


def test_simplify_card_trunca_em_200_caracteres():
    info = {"question": "x" * 250, "answer": "y" * 250}
    card = tutor.simplify_card(info)
    assert len(card["question"]) == 200
    assert len(card["answer"]) == 200


def test_simplify_card_valores_ausentes_viram_zero():
    info = {}
    card = tutor.simplify_card(info)
    assert card["lapses"] == 0
    assert card["ease"] == 0
    assert card["reps"] == 0
    assert card["interval"] == 0


def test_rank_weak_ordena_por_lapses_descrescente():
    cards = [
        {"lapses": 1, "ease": 2500},
        {"lapses": 5, "ease": 2500},
        {"lapses": 3, "ease": 2500},
    ]
    result = tutor.rank_weak(cards)
    assert [c["lapses"] for c in result] == [5, 3, 1]


def test_rank_weak_empate_por_ease_crescente():
    cards = [
        {"lapses": 2, "ease": 2500},
        {"lapses": 2, "ease": 1300},
        {"lapses": 2, "ease": 2000},
    ]
    result = tutor.rank_weak(cards)
    assert [c["ease"] for c in result] == [1300, 2000, 2500]


def test_rank_weak_respeita_top_n():
    cards = [{"lapses": i, "ease": 1000} for i in range(1, 30)]
    result = tutor.rank_weak(cards, top=5)
    assert len(result) == 5


def test_aggregate_by_deck_soma_lapses_e_conta_cards():
    cards = [
        {"deck": "A", "lapses": 2, "ease": 2000},
        {"deck": "A", "lapses": 3, "ease": 2500},
        {"deck": "B", "lapses": 5, "ease": 1300},
    ]
    result = tutor.aggregate_by_deck(cards)
    assert {d["deck"]: (d["cards"], d["lapses"]) for d in result} == {
        "A": (2, 5),
        "B": (1, 5),
    }


def test_aggregate_by_deck_ease_medio_eh_media_inteira():
    cards = [
        {"deck": "A", "lapses": 1, "ease": 2100},
        {"deck": "A", "lapses": 1, "ease": 2200},
    ]
    result = tutor.aggregate_by_deck(cards)
    assert result[0]["ease_medio"] == 2150


def test_aggregate_by_deck_ordenado_por_lapses_descrescente():
    cards = [
        {"deck": "A", "lapses": 1, "ease": 1000},
        {"deck": "B", "lapses": 5, "ease": 1000},
        {"deck": "C", "lapses": 3, "ease": 1000},
    ]
    result = tutor.aggregate_by_deck(cards)
    assert [d["deck"] for d in result] == ["B", "C", "A"]


def test_render_report_vazio_contem_nenhum_card():
    report = tutor.render_report([], [], 3, "2024-01-01T10:00:00")
    assert "Nenhum card" in report


def test_render_report_vazio_contem_frontmatter():
    report = tutor.render_report([], [], 3, "2024-01-01T10:00:00")
    assert "tipo: revisao" in report
    assert "gerado: 2024-01-01T10:00:00" in report
    assert "criterio: lapses >= 3" in report


def test_render_report_com_cards_contem_tabela_de_decks():
    weak = [
        {"deck": "A", "lapses": 5, "ease": 1300, "question": "q1", "answer": "a1"},
        {"deck": "A", "lapses": 3, "ease": 2000, "question": "q2", "answer": "a2"},
    ]
    by_deck = tutor.aggregate_by_deck(weak)
    report = tutor.render_report(weak, by_deck, 3, "2024-01-01T10:00:00")
    assert "| Deck |" in report
    assert "| A |" in report


def test_render_report_com_cards_contem_titulos_e_pergunta_resposta():
    weak = [
        {"deck": "A", "lapses": 5, "ease": 1300, "question": "q1", "answer": "a1"},
    ]
    by_deck = tutor.aggregate_by_deck(weak)
    report = tutor.render_report(weak, by_deck, 3, "2024-01-01T10:00:00")
    assert "### 1." in report
    assert "**P:** q1" in report
    assert "**R:** a1" in report


def test_render_report_com_cards_contem_dica_reforcar():
    weak = [
        {"deck": "A", "lapses": 5, "ease": 1300, "question": "q1", "answer": "a1"},
    ]
    by_deck = tutor.aggregate_by_deck(weak)
    report = tutor.render_report(weak, by_deck, 3, "2024-01-01T10:00:00")
    assert "tutor.py reforcar" in report


def test_weak_to_material_contem_pergunta_resposta_e_errado():
    weak = [
        {"deck": "A", "lapses": 5, "ease": 1300, "question": "q1", "answer": "a1"},
    ]
    material = tutor.weak_to_material(weak)
    assert "Pergunta:" in material
    assert "Resposta:" in material
    assert "(errado 5x)" in material
    assert "q1" in material
    assert "a1" in material
