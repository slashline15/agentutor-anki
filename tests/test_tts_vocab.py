from anki_toolkit import tts
from anki_toolkit import outputs


def test_media_filename_eh_deterministico():
    """Mesmo (texto, voz) deve gerar o mesmo nome em duas chamadas."""
    nome1 = tts.media_filename("hello", "en-US-AriaNeural")
    nome2 = tts.media_filename("hello", "en-US-AriaNeural")
    assert nome1 == nome2


def test_media_filename_textos_diferentes_diferentes_nomes():
    """Textos diferentes devem produzir nomes de arquivo diferentes."""
    nome_a = tts.media_filename("hello", "en-US-AriaNeural")
    nome_b = tts.media_filename("world", "en-US-AriaNeural")
    assert nome_a != nome_b


def test_media_filename_vozes_diferentes_diferentes_nomes():
    """Vozes diferentes devem produzir nomes de arquivo diferentes."""
    nome_a = tts.media_filename("hello", "en-US-AriaNeural")
    nome_b = tts.media_filename("hello", "en-GB-RyanNeural")
    assert nome_a != nome_b


def test_media_filename_formato_correto():
    """O nome deve começar com 'anki-vocab-' e terminar com '.mp3'."""
    nome = tts.media_filename("hello", "en-US-AriaNeural")
    assert nome.startswith("anki-vocab-")
    assert nome.endswith(".mp3")


def test_vocab_tts_text_com_termo_e_exemplo():
    """Termo e exemplo devem ser unidos por ponto e espaço."""
    assert tts.vocab_tts_text("run", "I run daily.") == "run. I run daily."


def test_vocab_tts_text_somente_termo():
    """Apenas termo não deve adicionar ponto extra."""
    assert tts.vocab_tts_text("run") == "run"


def test_vocab_tts_text_tolerancia_a_none_e_espacos():
    """None e espaços excessivos devem ser tratados sem erro."""
    assert tts.vocab_tts_text(None, None) == ""
    assert tts.vocab_tts_text("  run  ", "  I run daily.  ") == "run. I run daily."


def test_card_to_fields_vocab_completo():
    """Card vocab completo gera todos os campos, com áudio vazio."""
    card = {
        "type": "vocab",
        "term": "to run",
        "ipa": "/rʌn/",
        "meaning": "correr",
        "example": "I run daily.",
        "extra": "dica",
    }
    resultado = outputs.card_to_fields(card)
    assert resultado == (
        "vocab",
        ["to run", "/rʌn/", "correr", "I run daily.", "", "dica"],
    )


def test_card_to_fields_vocab_sem_term_retorna_none():
    """Card vocab sem termo é inválido."""
    card = {
        "type": "vocab",
        "meaning": "correr",
    }
    assert outputs.card_to_fields(card) is None


def test_card_to_fields_vocab_sem_meaning_retorna_none():
    """Card vocab sem significado é inválido."""
    card = {
        "type": "vocab",
        "term": "to run",
    }
    assert outputs.card_to_fields(card) is None


def test_card_to_fields_vocab_campos_opcionais_ausentes():
    """IPA, exemplo e extra ausentes viram campos vazios nas posições certas."""
    card = {
        "type": "vocab",
        "term": "to run",
        "meaning": "correr",
    }
    resultado = outputs.card_to_fields(card)
    assert resultado == (
        "vocab",
        ["to run", "", "correr", "", "", ""],
    )


def test_card_to_fields_vocab_quebras_de_linha_em_meaning():
    """Quebras de linha no significado devem virar <br>."""
    card = {
        "type": "vocab",
        "term": "to run",
        "meaning": "correr\nrapidamente",
    }
    resultado = outputs.card_to_fields(card)
    assert resultado == (
        "vocab",
        ["to run", "", "correr<br>rapidamente", "", "", ""],
    )
