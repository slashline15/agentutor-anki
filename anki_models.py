"""
Definição central dos note types (genanki) usados pelo build_apkg.py e pelo
card_agent.py. IDs fixos: reimportar atualiza os templates sem duplicar.

5 note types:
  code_cloze  -> Python — Terminal (Cloze)     campos: Front, Back
  code_write  -> Python — Digite o Código       campos: Pergunta, Codigo, Notas
  code_output -> Python — Digite a Saída        campos: Codigo, Saida, Notas
  qa          -> Geral — Básico (Q&A)           campos: Frente, Verso, Extra
  cloze       -> Geral — Cloze                  campos: Texto, Extra
"""
from pathlib import Path
import genanki

BASE = Path(__file__).resolve().parent

def _read(*parts: str) -> str:
    return BASE.joinpath(*parts).read_text(encoding="utf-8")

# IDs fixos -------------------------------------------------------------------
ID_CODE_CLOZE = 1980530001
ID_CODE_WRITE = 1980530002
ID_CODE_OUT   = 1980530003
ID_QA         = 1980530004
ID_CLOZE      = 1980530005
DECK_DEFAULT  = 1980530100

CODE_CSS = _read("styling-comum.css")

GENERAL_CSS = """
.card{font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;font-size:18px;
  line-height:1.55;color:#222;background:#fafafa;text-align:center;padding:18px;}
.qa-front{font-weight:600;}
#answer{margin:16px auto;border:none;border-top:2px solid #ddd;max-width:560px;}
.qa-back,.cloze-card{max-width:660px;margin:0 auto;}
.extra{margin:14px auto 0;max-width:660px;font-size:15px;color:#555;background:#fff;
  border-left:3px solid #4584b6;padding:8px 12px;text-align:left;border-radius:4px;}
.extra code,.qa-back code,.cloze-card code{background:#eef1f5;padding:1px 5px;
  border-radius:4px;font-family:Consolas,monospace;font-size:.92em;}
.cloze,.cloze b{font-weight:bold;color:#4584b6;}
.nightMode.card{background:#16181d;color:#e6e6e6;}
.nightMode .extra{background:#23272e;color:#cfd3da;}
.nightMode #answer{border-top-color:#333;}
.nightMode .cloze,.nightMode .cloze b{color:#61afef;}
.nightMode .extra code,.nightMode .qa-back code,.nightMode .cloze-card code{
  background:#1c2027;color:#e6e6e6;}
"""

QA_FRONT = '<div class="qa-front">{{Frente}}</div>'
QA_BACK = ('{{FrontSide}}<hr id="answer"><div class="qa-back">{{Verso}}</div>'
           '{{#Extra}}<div class="extra">{{Extra}}</div>{{/Extra}}')

CLOZE_FRONT = '<div class="cloze-card">{{cloze:Texto}}</div>'
CLOZE_BACK = ('<div class="cloze-card">{{cloze:Texto}}</div>'
              '{{#Extra}}<div class="extra">{{Extra}}</div>{{/Extra}}')


def build_models() -> dict:
    code_cloze = genanki.Model(
        ID_CODE_CLOZE, "Python — Terminal (Cloze)",
        fields=[{"name": "Front"}, {"name": "Back"}],
        templates=[{"name": "Cloze",
                    "qfmt": _read("1-terminal-cloze", "front.html"),
                    "afmt": _read("1-terminal-cloze", "back.html")}],
        css=CODE_CSS, model_type=genanki.Model.CLOZE)

    code_write = genanki.Model(
        ID_CODE_WRITE, "Python — Digite o Código",
        fields=[{"name": "Pergunta"}, {"name": "Codigo"}, {"name": "Notas"}],
        templates=[{"name": "Digite o Codigo",
                    "qfmt": _read("2-digite-codigo", "front.html"),
                    "afmt": _read("2-digite-codigo", "back.html")}],
        css=CODE_CSS)

    code_output = genanki.Model(
        ID_CODE_OUT, "Python — Digite a Saída",
        fields=[{"name": "Codigo"}, {"name": "Saida"}, {"name": "Notas"}],
        templates=[{"name": "Digite a Saida",
                    "qfmt": _read("3-digite-saida", "front.html"),
                    "afmt": _read("3-digite-saida", "back.html")}],
        css=CODE_CSS)

    qa = genanki.Model(
        ID_QA, "Geral — Básico (Q&A)",
        fields=[{"name": "Frente"}, {"name": "Verso"}, {"name": "Extra"}],
        templates=[{"name": "QA", "qfmt": QA_FRONT, "afmt": QA_BACK}],
        css=GENERAL_CSS)

    cloze = genanki.Model(
        ID_CLOZE, "Geral — Cloze",
        fields=[{"name": "Texto"}, {"name": "Extra"}],
        templates=[{"name": "Cloze", "qfmt": CLOZE_FRONT, "afmt": CLOZE_BACK}],
        css=GENERAL_CSS, model_type=genanki.Model.CLOZE)

    return {"code_cloze": code_cloze, "code_write": code_write,
            "code_output": code_output, "qa": qa, "cloze": cloze}


# Ordem dos campos por tipo (usado pelo agente para montar notas/CSV) ----------
FIELDS = {
    "code_cloze":  ["Front", "Back"],
    "code_write":  ["Pergunta", "Codigo", "Notas"],
    "code_output": ["Codigo", "Saida", "Notas"],
    "qa":          ["Frente", "Verso", "Extra"],
    "cloze":       ["Texto", "Extra"],
}
MODEL_NAMES = {
    "code_cloze":  "Python — Terminal (Cloze)",
    "code_write":  "Python — Digite o Código",
    "code_output": "Python — Digite a Saída",
    "qa":          "Geral — Básico (Q&A)",
    "cloze":       "Geral — Cloze",
}
