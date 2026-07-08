"""
Definição central dos note types (genanki) usados por build_apkg.py,
card_agent.py e rebuild_from_json.py. IDs fixos: reimportar atualiza os
templates sem duplicar notas na coleção. NUNCA alterar os IDs.

6 note types:
  code_cloze  -> Python — Terminal (Cloze)     campos: Front, Back
  code_write  -> Python — Digite o Código       campos: Pergunta, Codigo, Notas
  code_output -> Python — Digite a Saída        campos: Codigo, Saida, Notas
  qa          -> Geral — Básico (Q&A)           campos: Frente, Verso, Extra
  cloze       -> Geral — Cloze                  campos: Texto, Extra
  vocab       -> Inglês — Vocabulário           campos: Termo, IPA, Significado,
                                                 Exemplo, Áudio, Notas
                 (2 cartões: Reconhecimento termo→significado e
                  Produção significado→termo, ambos com áudio TTS)
"""
from pathlib import Path
import genanki

# Raiz do projeto (pasta acima de anki_toolkit/), onde ficam os templates HTML
BASE = Path(__file__).resolve().parents[1]

def _read(*parts: str) -> str:
    return BASE.joinpath(*parts).read_text(encoding="utf-8")

# IDs fixos -------------------------------------------------------------------
ID_CODE_CLOZE = 1980530001
ID_CODE_WRITE = 1980530002
ID_CODE_OUT   = 1980530003
ID_QA         = 1980530004
ID_CLOZE      = 1980530005
ID_VOCAB      = 1980530006
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

VOCAB_CSS = GENERAL_CSS + """
.vocab-term{font-size:30px;font-weight:700;letter-spacing:.3px;}
.vocab-ipa{color:#888;font-size:17px;margin-top:2px;font-family:'Segoe UI',Arial,sans-serif;}
.vocab-meaning{font-size:22px;font-weight:600;}
.vocab-example{font-style:italic;color:#444;margin-top:10px;font-size:17px;}
.vocab-hint{color:#999;font-size:13px;margin-top:14px;}
.nightMode .vocab-example{color:#b8bec8;}
.nightMode .vocab-ipa{color:#8a919c;}
"""

# Reconhecimento: vê/ouve o termo -> lembra o significado
VOCAB_REC_FRONT = ('<div class="vocab-term">{{Termo}}</div>'
                   '<div>{{Áudio}}</div>'
                   '<div class="vocab-hint">Qual o significado?</div>')
VOCAB_REC_BACK = ('{{FrontSide}}<hr id="answer">'
                  '<div class="vocab-meaning">{{Significado}}</div>'
                  '{{#IPA}}<div class="vocab-ipa">{{IPA}}</div>{{/IPA}}'
                  '{{#Exemplo}}<div class="vocab-example">{{Exemplo}}</div>{{/Exemplo}}'
                  '{{#Notas}}<div class="extra">{{Notas}}</div>{{/Notas}}')

# Produção: vê o significado -> lembra (e fala) o termo
VOCAB_PROD_FRONT = ('<div class="vocab-meaning">{{Significado}}</div>'
                    '<div class="vocab-hint">Diga a palavra em inglês</div>')
VOCAB_PROD_BACK = ('{{FrontSide}}<hr id="answer">'
                   '<div class="vocab-term">{{Termo}}</div>'
                   '{{#IPA}}<div class="vocab-ipa">{{IPA}}</div>{{/IPA}}'
                   '<div>{{Áudio}}</div>'
                   '{{#Exemplo}}<div class="vocab-example">{{Exemplo}}</div>{{/Exemplo}}'
                   '{{#Notas}}<div class="extra">{{Notas}}</div>{{/Notas}}')

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

    vocab = genanki.Model(
        ID_VOCAB, "Inglês — Vocabulário",
        fields=[{"name": "Termo"}, {"name": "IPA"}, {"name": "Significado"},
                {"name": "Exemplo"}, {"name": "Áudio"}, {"name": "Notas"}],
        templates=[
            {"name": "Reconhecimento",
             "qfmt": VOCAB_REC_FRONT, "afmt": VOCAB_REC_BACK},
            {"name": "Producao",
             "qfmt": VOCAB_PROD_FRONT, "afmt": VOCAB_PROD_BACK},
        ],
        css=VOCAB_CSS)

    return {"code_cloze": code_cloze, "code_write": code_write,
            "code_output": code_output, "qa": qa, "cloze": cloze,
            "vocab": vocab}


# Ordem dos campos por tipo (usado pelo agente para montar notas/CSV) ----------
FIELDS = {
    "code_cloze":  ["Front", "Back"],
    "code_write":  ["Pergunta", "Codigo", "Notas"],
    "code_output": ["Codigo", "Saida", "Notas"],
    "qa":          ["Frente", "Verso", "Extra"],
    "cloze":       ["Texto", "Extra"],
    "vocab":       ["Termo", "IPA", "Significado", "Exemplo", "Áudio", "Notas"],
}
MODEL_NAMES = {
    "code_cloze":  "Python — Terminal (Cloze)",
    "code_write":  "Python — Digite o Código",
    "code_output": "Python — Digite a Saída",
    "qa":          "Geral — Básico (Q&A)",
    "cloze":       "Geral — Cloze",
    "vocab":       "Inglês — Vocabulário",
}

# Índice do campo Áudio do vocab (preenchido pelo passo de TTS do card_agent)
VOCAB_AUDIO_FIELD = FIELDS["vocab"].index("Áudio")
