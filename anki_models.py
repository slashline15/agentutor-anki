"""
Compatibilidade: o conteúdo real vive em anki_toolkit/models.py.
Este módulo só re-exporta os mesmos nomes para não quebrar imports antigos.
"""
from anki_toolkit.models import (  # noqa: F401
    BASE,
    CLOZE_BACK,
    CLOZE_FRONT,
    CODE_CSS,
    DECK_DEFAULT,
    FIELDS,
    GENERAL_CSS,
    ID_CLOZE,
    ID_CODE_CLOZE,
    ID_CODE_OUT,
    ID_CODE_WRITE,
    ID_QA,
    MODEL_NAMES,
    QA_BACK,
    QA_FRONT,
    build_models,
)
