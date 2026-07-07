"""
card_agent.py — Gera flashcards de Anki com modelos Ollama (local ou cloud),
aplicando boas técnicas de memorização (princípios de Woźniak + recordação ativa).

Saídas: .apkg pronto, CSV/TSV por note type e um JSON intermediário (schema 1).
A lógica compartilhada vive no pacote anki_toolkit/ (llm, outputs, models).

Exemplos:
  # a partir de um tópico
  python card_agent.py --topic "List comprehensions em Python" -n 12

  # a partir de um arquivo de material (txt/md)
  python card_agent.py --file material.md -n 20 --deck "Estudos::Redes"

  # escolhendo o modelo (local ou cloud)
  python card_agent.py --topic "Mitose" --model gemma4:12b
  python card_agent.py --topic "Mitose" --model gpt-oss:120b-cloud
"""
import argparse
import sys
from pathlib import Path

from anki_toolkit import llm, outputs
from anki_toolkit.llm import DEFAULT_HOST, DEFAULT_MODEL
# Re-exports de compatibilidade (rebuild_from_json antigo importava daqui)
from anki_toolkit.outputs import slugify, write_tsv  # noqa: F401

BASE = Path(__file__).resolve().parent

SYSTEM_PROMPT = """Você é um especialista em criar flashcards para Anki otimizados para \
memorização de longo prazo (repetição espaçada). Você domina e APLICA os princípios de \
Piotr Woźniak ("20 regras de formulação do conhecimento") e a recordação ativa.

Regras que você SEMPRE segue:
1. Informação mínima: cada card testa UMA única ideia. Quebre temas complexos em vários cards atômicos.
2. Recordação ativa: a frente deve forçar o aluno a LEMBRAR algo, nunca apenas reconhecer. Evite perguntas de sim/não.
3. Evite listas e enumerações longas. Se inevitável, use clozes separados (um por item).
4. Respostas curtas, precisas e SEM ambiguidade — a frente deve ter uma única resposta correta.
5. Nunca entregue a resposta na própria pergunta.
6. Adicione contexto mínimo para remover ambiguidade (ex.: "Em Python, ...").
7. Use cloze para fixar fatos dentro de um contexto/definição.
8. Para programação, prefira: prever a saída, escrever o código, ou cloze de sintaxe.
9. Prefira exemplos concretos a definições abstratas.
10. No campo "extra", dê uma explicação breve do PORQUÊ (opcional, mas útil).

Você responde SOMENTE com JSON válido — sem markdown, sem comentários, sem texto fora do JSON."""

USER_TEMPLATE = """Crie __N__ flashcards sobre o conteúdo abaixo. Idioma dos cards: __LANG__.

CONTEÚDO:
\"\"\"
__CONTENT__
\"\"\"

Para cada card escolha o melhor "type":
- "qa": pergunta/resposta de conhecimento geral. Campos: front, back, extra(opcional).
- "cloze": fato em contexto. Campo: text (use lacunas no formato {{c1::resposta}}, {{c2::...}}). extra(opcional).
- "code_output": mostrar código e perguntar a saída. Campos: code, answer (a saída EXATA), extra(opcional).
- "code_write": pedir para escrever um trecho de código. Campos: front (enunciado), answer (o código), extra(opcional).
- "code_cloze": código com lacuna de sintaxe. Campo: code (com {{c1::trecho}}), extra(opcional).

Use os tipos de código (code_*) SOMENTE quando o conteúdo for sobre programação.
Nas respostas de código, use \\n para quebras de linha. Mantenha a saída ("answer" de code_output) idêntica ao que o Python imprimiria.

Responda EXATAMENTE neste formato JSON (sem nada além do JSON):
{
  "deck": "<nome curto do baralho>",
  "cards": [
    {"type":"qa","front":"...","back":"...","extra":"..."},
    {"type":"cloze","text":"... {{c1::...}} ...","extra":"..."},
    {"type":"code_output","code":"print(2 + 2)","answer":"4","extra":"..."},
    {"type":"code_write","front":"...","answer":"...","extra":"..."},
    {"type":"code_cloze","code":"for i in {{c1::range(5)}}:\\n    print(i)","extra":"..."}
  ]
}"""


def main():
    ap = argparse.ArgumentParser(description="Gera flashcards de Anki via Ollama.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--topic", help="Tópico/assunto em texto livre.")
    src.add_argument("--file", help="Arquivo de material (txt/md) como fonte.")
    ap.add_argument("-n", "--num", type=int, default=15, help="Nº alvo de cards (padrão 15).")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"Modelo Ollama (padrão {DEFAULT_MODEL}).")
    ap.add_argument("--host", default=DEFAULT_HOST, help="URL do Ollama.")
    ap.add_argument("--deck", help="Nome do baralho (padrão: sugerido pelo modelo).")
    ap.add_argument("--out", default=str(BASE / "output"), help="Pasta de saída.")
    ap.add_argument("--formats", default="apkg,csv", help="apkg,csv,json (separados por vírgula).")
    ap.add_argument("--lang", default="português", help="Idioma dos cards.")
    ap.add_argument("--timeout", type=int, default=900, help="Timeout da chamada (s).")
    args = ap.parse_args()

    if args.file:
        content = Path(args.file).read_text(encoding="utf-8")
        default_deck = Path(args.file).stem
    else:
        content = args.topic
        default_deck = args.topic
    content = content.strip()
    if not content:
        sys.exit("[erro] Conteúdo vazio.")

    user = (USER_TEMPLATE
            .replace("__N__", str(args.num))
            .replace("__LANG__", args.lang)
            .replace("__CONTENT__", content[:12000]))

    print(f"[1/4] Gerando ~{args.num} cards com '{args.model}'...")
    try:
        raw = llm.call_ollama(args.host, args.model, SYSTEM_PROMPT, user, args.timeout)
        data = llm.extract_json(raw)
    except (llm.OllamaError, ValueError) as e:
        sys.exit(f"[erro] {e}")

    deck_name = args.deck or data.get("deck") or default_deck or "Ollama Cards"
    cards = data.get("cards", [])
    if not cards:
        sys.exit("[erro] O modelo não retornou nenhum card.")

    # converter e agrupar por tipo
    by_type, skipped, kept = {}, 0, []
    for c in cards:
        conv = outputs.card_to_fields(c)
        if conv is None:
            skipped += 1
            continue
        t, fields = conv
        by_type.setdefault(t, []).append(fields)
        kept.append({"type": t, "fields": fields})

    if not kept:
        sys.exit("[erro] Nenhum card válido após validação.")

    print(f"[2/4] {len(kept)} cards válidos ({skipped} descartados). "
          f"Tipos: {', '.join(f'{k}={len(v)}' for k, v in by_type.items())}")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    slug = outputs.slugify(deck_name)
    formats = {f.strip() for f in args.formats.split(",") if f.strip()}
    tags = ["gerado-ollama", slug]

    if "json" in formats:
        outputs.write_json(out / f"{slug}.json", deck_name, args.model, kept)

    if "csv" in formats:
        outputs.write_tsvs(out, slug, deck_name, tags, by_type)

    if "apkg" in formats:
        outputs.write_apkg(out / f"{slug}.apkg", deck_name, tags, by_type)

    print(f"[3/4] Baralho: '{deck_name}'  (tags: {', '.join(tags)})")
    print(f"[4/4] Arquivos em: {out}")
    for f in sorted(out.glob(f"{slug}*")):
        print(f"        - {f.name}")


if __name__ == "__main__":
    main()
