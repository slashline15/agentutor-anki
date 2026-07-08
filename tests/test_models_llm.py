import zipfile

import genanki
import pytest

from anki_toolkit import models, llm, outputs


def test_ids_contrato():
    # IDs fixos devem permanecer inalterados
    assert models.ID_CODE_CLOZE == 1980530001
    assert models.ID_CODE_WRITE == 1980530002
    assert models.ID_CODE_OUT == 1980530003
    assert models.ID_QA == 1980530004
    assert models.ID_CLOZE == 1980530005
    assert models.ID_VOCAB == 1980530006
    assert models.DECK_DEFAULT == 1980530100

    # os IDs dos modelos retornados por build_models() devem coincidir
    built = models.build_models()
    assert built["code_cloze"].model_id == models.ID_CODE_CLOZE
    assert built["code_write"].model_id == models.ID_CODE_WRITE
    assert built["code_output"].model_id == models.ID_CODE_OUT
    assert built["qa"].model_id == models.ID_QA
    assert built["cloze"].model_id == models.ID_CLOZE
    assert built["vocab"].model_id == models.ID_VOCAB


def test_build_models_chaves_e_contratos():
    built = models.build_models()
    esperado = {"code_cloze", "code_write", "code_output", "qa", "cloze",
                "vocab"}
    assert set(built.keys()) == esperado
    # as mesmas chaves devem existir em FIELDS e MODEL_NAMES
    assert set(models.FIELDS.keys()) == esperado
    assert set(models.MODEL_NAMES.keys()) == esperado


def test_vocab_dois_cartoes_e_campo_audio():
    # o vocab tem 2 templates (reconhecimento + produção) e o índice do campo
    # Áudio usado pelo passo de TTS precisa apontar para o campo certo
    built = models.build_models()
    assert len(built["vocab"].templates) == 2
    assert models.FIELDS["vocab"][models.VOCAB_AUDIO_FIELD] == "Áudio"


def test_modelos_nomes_e_campos():
    built = models.build_models()
    for key, model in built.items():
        # nome do modelo
        assert model.name == models.MODEL_NAMES[key]
        # lista de nomes de campos
        campos_modelo = [f["name"] for f in model.fields]
        assert campos_modelo == models.FIELDS[key]


def test_modelos_cloze_tipo():
    built = models.build_models()
    assert built["code_cloze"].model_type == genanki.Model.CLOZE
    assert built["cloze"].model_type == genanki.Model.CLOZE


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ('{"a": 1, "b": "x"}', {"a": 1, "b": "x"}),
        ('texto antes {"c": true} texto depois', {"c": True}),
        ('  \n\t {"lista": [1,2,3]}  ', {"lista": [1, 2, 3]}),
    ],
)
def test_extract_json_valido(texto, esperado):
    assert llm.extract_json(texto) == esperado


@pytest.mark.parametrize("texto", ["sem json aqui", "", None])
def test_extract_json_erro(texto):
    with pytest.raises(ValueError):
        llm.extract_json(texto)


def test_write_apkg_gera_arquivo_valido(tmp_path):
    # um card de cada tipo, campos na ordem de models.FIELDS
    # (clozes precisam de {{c1::...}} para o genanki gerar os cartões)
    by_type = {
        "qa": [["Pergunta?", "Resposta.", ""]],
        "cloze": [["Um {{c1::fato}} em contexto.", ""]],
        "code_cloze": [["for i in {{c1::range(5)}}:<br>    print(i)", ""]],
        "code_write": [["Enunciado", "print(1)", ""]],
        "code_output": [["print(2+2)", "4", ""]],
    }
    apkg_path = tmp_path / "teste.apkg"
    outputs.write_apkg(apkg_path, "Teste Deck", ["tag-teste"], by_type)

    assert apkg_path.is_file()
    assert apkg_path.stat().st_size > 0
    assert zipfile.is_zipfile(apkg_path)

    with zipfile.ZipFile(apkg_path) as zf:
        membros = zf.namelist()
        assert any(m.startswith("collection.") for m in membros)
