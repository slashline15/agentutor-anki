"""
build_templates.py — injeta templates/tokenizer.js (fonte única) nos HTML dos
note types de terminal. Fim da duplicação: edite templates/tokenizer.js e rode

    .venv\\Scripts\\python.exe build_templates.py

Os HTML gerados continuam commitados: quem só copia e cola no Anki não roda nada.
Na primeira execução substitui o <script> antigo; depois, atualiza apenas o
trecho entre os marcadores TOKENIZER:BEGIN/END.
"""
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
TOKENIZER = BASE / "templates" / "tokenizer.js"

MARK_BEGIN = ("// ==== TOKENIZER:BEGIN — gerado de templates/tokenizer.js; "
              "edite lá e rode build_templates.py ====")
MARK_END = "// ==== TOKENIZER:END ===="

# arquivo -> chamada específica (fora dos marcadores, preservada entre builds)
CALLS = {
    "1-terminal-cloze/front.html": "TermHl.run({cloze:true, focus:true});",
    "1-terminal-cloze/back.html":  "TermHl.run({cloze:true});",
    "2-digite-codigo/back.html":   "TermHl.run({});",
    "3-digite-saida/front.html":   "TermHl.run({focus:true});",
    "3-digite-saida/back.html":    "TermHl.run({});",
}
# (2-digite-codigo/front.html não realça código; mantém só o script de foco)


def build_block(js, call):
    return ("<script>\n" + MARK_BEGIN + "\n" + js.strip() + "\n" + MARK_END
            + "\n" + call + "\n</script>")


def inject(path, js, call):
    text = path.read_text(encoding="utf-8")
    block = build_block(js, call)
    if MARK_BEGIN.split("—")[0] in text:  # já tem marcadores: troca o miolo
        new = re.sub(r"<script>\s*\n// ==== TOKENIZER:BEGIN[\s\S]*?</script>",
                     lambda _: block, text, count=1)
        action = "atualizado"
    else:  # primeira vez: substitui o ÚLTIMO <script>...</script> do arquivo
        i = text.rfind("<script>")
        j = text.rfind("</script>")
        if i == -1 or j == -1:
            sys.exit(f"[erro] {path}: nenhum <script> para substituir.")
        new = text[:i] + block + text[j + len("</script>"):]
        action = "migrado"
    if not new.rstrip().endswith(">"):
        new = new.rstrip() + "\n"
    path.write_text(new.rstrip() + "\n", encoding="utf-8")
    return action


def main():
    js = TOKENIZER.read_text(encoding="utf-8")
    for rel, call in CALLS.items():
        action = inject(BASE / rel, js, call)
        print(f"{action}: {rel}")
    print("OK — templates regenerados a partir de templates/tokenizer.js")

    if "--push" in sys.argv:  # atualiza os note types na coleção do Anki aberto
        from anki_toolkit import bridge
        try:
            existing = set(bridge.invoke("modelNames"))
            from anki_toolkit import models as _m
            for key in ("code_cloze", "code_write", "code_output"):
                if _m.MODEL_NAMES[key] in existing:
                    print(f"[push] atualizado no Anki: {bridge.update_model(key)}")
        except bridge.AnkiConnectError as e:
            print(f"[push] {e}")


if __name__ == "__main__":
    main()
