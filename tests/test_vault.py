from pathlib import Path
import json

import pytest

from anki_toolkit import vault


def test_parse_vault_registry_aberto_primeiro_depois_ts_decrescente():
    texto = json.dumps({
        "vaults": {
            "v1": {"path": "/vault/fechada1", "ts": 200, "open": False},
            "v2": {"path": "/vault/aberta", "ts": 100, "open": True},
            "v3": {"path": "/vault/fechada2", "ts": 300, "open": False},
        }
    })
    resultado = vault.parse_vault_registry(texto)
    assert [r[0] for r in resultado] == [
        "/vault/aberta",
        "/vault/fechada2",
        "/vault/fechada1",
    ]


def test_parse_vault_registry_json_invalido_retorna_vazio():
    assert vault.parse_vault_registry("não é json") == []


def test_parse_vault_registry_sem_chave_vaults_retorna_vazio():
    assert vault.parse_vault_registry('{"outro": []}') == []


def test_parse_vault_registry_vault_sem_path_e_ignorado():
    texto = json.dumps({
        "vaults": {
            "v1": {"ts": 100, "open": True},
            "v2": {"path": "/vault/com-path", "ts": 200, "open": False},
        }
    })
    resultado = vault.parse_vault_registry(texto)
    assert len(resultado) == 1
    assert resultado[0][0] == "/vault/com-path"


def test_safe_filename_remove_dois_pontos():
    assert ":" not in vault.safe_filename("Testes::AnkiConnect")


def test_safe_filename_remove_caracteres_proibidos():
    proibidos = r'\ / : * ? " < > | # ^ [ ]'.split()
    nome = "".join(proibidos)
    resultado = vault.safe_filename(nome)
    for c in proibidos:
        assert c not in resultado


def test_safe_filename_colapsa_espacos_e_vazio_ou_none():
    assert vault.safe_filename("  a   b  c  ") == "a b c"
    assert vault.safe_filename("") == "sem-nome"
    assert vault.safe_filename(None) == "sem-nome"


def test_html_to_md_converte_br_para_quebra():
    assert vault.html_to_md("a<br>b") == "a\nb"


def test_html_to_md_none_retorna_vazio():
    assert vault.html_to_md(None) == ""


def test_render_deck_note_contem_frontmatter_esperado():
    nota = vault.render_deck_note(
        deck_name="Meu::Baralho",
        model="Básico",
        tags=["tag1", "tag2"],
        cards=[{"type": "qa", "fields": ["P", "R"]}],
        now="2026-01-01T00:00:00",
    )
    assert "tipo: baralho" in nota
    assert 'deck: "Meu::Baralho"' in nota
    assert 'modelo: "Básico"' in nota
    assert "cards: 1" in nota
    assert "gerado: 2026-01-01T00:00:00" in nota


def test_render_deck_note_com_source_stem_contem_link():
    nota = vault.render_deck_note(
        deck_name="Baralho",
        model="Modelo",
        tags=[],
        cards=[],
        source_stem="apostila",
        now="2026-01-01T00:00:00",
    )
    assert "[[apostila]]" in nota


def test_render_deck_note_sem_source_stem_nao_contem_link():
    nota = vault.render_deck_note(
        deck_name="Baralho",
        model="Modelo",
        tags=[],
        cards=[],
        now="2026-01-01T00:00:00",
    )
    assert "[[" not in nota


def test_render_deck_note_todos_os_tipos_de_card():
    cards = [
        {"type": "qa", "fields": ["Pergunta<br>com quebra", "Resposta"]},
        {"type": "cloze", "fields": ["Texto {{c1::cloze}}", "extra"]},
        {"type": "code_write", "fields": ["Escreva X", "def x(): pass", "dica"]},
        {"type": "code_output", "fields": ["print(1)", "1", "obs"]},
        {"type": "code_cloze", "fields": ["{{c1::code}}", "nota"]},
        {"type": "desconhecido", "fields": ["campo1", "campo2"]},
    ]
    nota = vault.render_deck_note(
        deck_name="Baralho",
        model="Modelo",
        tags=[],
        cards=cards,
        now="2026-01-01T00:00:00",
    )
    assert "Pergunta\ncom quebra" in nota
    assert "Texto {{c1::cloze}}" in nota
    assert "Escreva X" in nota
    assert "```" in nota and "def x(): pass" in nota
    assert "**Saída:** `1`" in nota
    assert "campo1" in nota and "campo2" in nota


def test_load_config_arquivo_inexistente_retorna_vazio(tmp_path):
    assert vault.load_config(tmp_path / "inexistente.json") == {}


def test_save_e_load_config_roundtrip(tmp_path):
    caminho = tmp_path / "config.json"
    dados = {"vault": "C:\\vault", "vault_subdir": "Estudos"}
    vault.save_config(dados, caminho)
    assert vault.load_config(caminho) == dados


def test_load_config_json_corrompido_retorna_vazio(tmp_path):
    caminho = tmp_path / "config.json"
    caminho.write_text("{invalido", encoding="utf-8")
    assert vault.load_config(caminho) == {}


def test_get_vault_root_retorna_diretorio_configurado(tmp_path):
    vault_dir = tmp_path / "meu_vault"
    vault_dir.mkdir()
    cfg = tmp_path / "config.json"
    vault.save_config({"vault": str(vault_dir)}, cfg)
    assert vault.get_vault_root(cfg) == vault_dir


def test_get_vault_root_diretorio_inexistente_levanta_vault_error(tmp_path):
    cfg = tmp_path / "config.json"
    vault.save_config({"vault": str(tmp_path / "nao_existe")}, cfg)
    with pytest.raises(vault.VaultError):
        vault.get_vault_root(cfg)


def test_write_deck_note_cria_arquivo_correto(tmp_path):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    cfg = tmp_path / "config.json"
    vault.save_config({"vault": str(vault_dir)}, cfg)

    cards = [{"type": "qa", "fields": ["Pergunta", "Resposta"]}]
    caminho = vault.write_deck_note(
        deck_name="A::B",
        model="Modelo",
        tags=["tag"],
        cards=cards,
        source_stem="apostila",
        config_path=cfg,
    )

    assert caminho.exists()
    assert caminho.name == "A-B.md"
    assert caminho.parent.name == "Baralhos"
    assert caminho.parent.parent.name == "Estudos"

    conteudo = caminho.read_text(encoding="utf-8")
    assert "A::B" in conteudo
    assert "[[apostila]]" in conteudo
    assert "Pergunta" in conteudo
    assert "Resposta" in conteudo
