"""
tutor.py — tutor pessoal: lê seu histórico no Anki (via AnkiConnect),
diagnostica fraquezas, gera cards de reforço e explica cards.

Uso (Anki precisa estar aberto):
  .venv\\Scripts\\python.exe tutor.py relatorio [--min-lapses 3] [--deck X] [--vault]
  .venv\\Scripts\\python.exe tutor.py reforcar --deck "Estudos::X" [-n 8] [--push]
  .venv\\Scripts\\python.exe tutor.py explicar "busca do anki"

Privacidade: o modelo padrão é LOCAL (histórico de estudo é dado pessoal);
use --model gpt-oss:120b-cloud etc. só se quiser qualidade cloud.
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

from anki_toolkit import bridge, llm, outputs, tutor, vault
from anki_toolkit.llm import DEFAULT_HOST

BASE = Path(__file__).resolve().parent

REINFORCE_SYSTEM = """Você é um tutor que cria flashcards de REFORÇO para Anki.
O aluno errou repetidamente os cards abaixo. Crie cards NOVOS sobre os MESMOS
conceitos, mas reformulados: outro ângulo, exemplo concreto diferente, ou
quebrando a ideia em passos menores. Nunca copie a pergunta original.
Responda SOMENTE com JSON válido."""

REINFORCE_TEMPLATE = """Crie __N__ flashcards de reforço em __LANG__ a partir dos cards
que o aluno mais erra (abaixo). Um conceito por card; respostas curtas e sem
ambiguidade; prefira exemplos concretos.

CARDS COM ERRO FREQUENTE:
__CONTENT__

Tipos permitidos (mesmo formato do JSON): "qa" (front/back/extra),
"cloze" (text com {{c1::...}}/extra), "code_output" (code/answer/lang/extra),
"code_write" (front/answer/lang/extra), "code_cloze" (code com {{c1::...}}/lang/extra).

Responda EXATAMENTE neste formato JSON:
{"deck": "<sugestão>", "cards": [ ... ]}"""

EXPLAIN_SYSTEM = """Você é um tutor paciente. Explique o conteúdo do flashcard do aluno
em português claro: por que a resposta é essa, um exemplo concreto diferente do
card, e um macete para não errar de novo. Seja direto (máx. ~15 linhas)."""


def cmd_relatorio(args):
    weak = tutor.fetch_weak(min_lapses=args.min_lapses, deck=args.deck,
                            top=args.top)
    by_deck = tutor.aggregate_by_deck(weak)
    now = datetime.now().isoformat(timespec="seconds")
    report = tutor.render_report(weak, by_deck, args.min_lapses, now)
    print(report)
    if args.vault:
        try:
            d = vault._study_dir("Revisões")
            path = d / f"revisao-{now[:10]}.md"
            path.write_text(report, encoding="utf-8")
            print(f"[vault] relatório salvo: {path}")
        except vault.VaultError as e:
            print(f"[vault] {e}")


def cmd_reforcar(args):
    weak = tutor.fetch_weak(min_lapses=args.min_lapses, deck=args.deck,
                            top=args.top)
    if not weak:
        sys.exit(f"[tutor] nenhum card com lapses >= {args.min_lapses}"
                 f"{' no deck ' + args.deck if args.deck else ''}. "
                 "Tente --min-lapses menor.")
    material = tutor.weak_to_material(weak)
    print(f"[1/3] {len(weak)} cards fracos; gerando ~{args.num} de reforço "
          f"com '{args.model}' (local)..." if ":cloud" not in args.model else
          f"[1/3] {len(weak)} cards fracos; gerando com '{args.model}'...")

    user = (REINFORCE_TEMPLATE.replace("__N__", str(args.num))
            .replace("__LANG__", "português").replace("__CONTENT__", material))
    try:
        raw = llm.call_ollama(args.host, args.model, REINFORCE_SYSTEM, user,
                              args.timeout)
        data = llm.extract_json(raw)
    except (llm.OllamaError, ValueError) as e:
        sys.exit(f"[erro] {e}")

    by_type, kept = {}, []
    for c in data.get("cards", []):
        conv = outputs.card_to_fields(c)
        if conv:
            t, fields = conv
            by_type.setdefault(t, []).append(fields)
            kept.append({"type": t, "fields": fields})
    if not kept:
        sys.exit("[erro] nenhum card de reforço válido.")

    deck_name = (args.deck + "::Reforço") if args.deck else "Reforço"
    slug = outputs.slugify(deck_name)
    tags = ["tutor-reforco", slug]
    print(f"[2/3] {len(kept)} cards de reforço -> '{deck_name}'")

    out = BASE / "output"
    out.mkdir(exist_ok=True)
    outputs.write_json(out / f"{slug}.json", deck_name, args.model, kept)
    if args.push:
        try:
            res = bridge.push_cards(deck_name, tags, by_type)
            print(f"[3/3] {res['added']} adicionados ao Anki, "
                  f"{res['skipped']} pulados.")
            return
        except bridge.AnkiConnectError as e:
            print(f"[push] {e} — gerando .apkg.")
    outputs.write_apkg(out / f"{slug}.apkg", deck_name, tags, by_type)
    print(f"[3/3] .apkg em {out / (slug + '.apkg')}")


def cmd_explicar(args):
    card = tutor.find_card(args.busca)
    if not card:
        sys.exit(f"[tutor] nenhum card encontrado para: {args.busca}")
    print(f"[card] ({card['deck']}) P: {card['question']}\n"
          f"       R: {card['answer']}\n")
    user = (f"Card do deck '{card['deck']}'.\n"
            f"Pergunta: {card['question']}\nResposta: {card['answer']}\n"
            f"(o aluno já errou este card {card['lapses']}x)\n\nExplique.")
    try:
        texto = llm.call_ollama(args.host, args.model, EXPLAIN_SYSTEM, user,
                                args.timeout, fmt=None)
    except llm.OllamaError as e:
        sys.exit(f"[erro] {e}")
    print(texto.strip())


def main():
    ap = argparse.ArgumentParser(description="Tutor pessoal sobre o Anki.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--model", default=tutor.DEFAULT_TUTOR_MODEL,
                       help=f"Modelo Ollama (padrão LOCAL: "
                            f"{tutor.DEFAULT_TUTOR_MODEL}).")
        p.add_argument("--host", default=DEFAULT_HOST)
        p.add_argument("--timeout", type=int, default=600)
        p.add_argument("--min-lapses", type=int, default=tutor.DEFAULT_MIN_LAPSES,
                       help="Mínimo de lapsos para considerar fraco (padrão 3).")
        p.add_argument("--deck", help="Restringe a um deck.")
        p.add_argument("--top", type=int, default=20,
                       help="Máx. de cards fracos considerados (padrão 20).")

    p1 = sub.add_parser("relatorio", help="Diagnóstico de fraquezas.")
    common(p1)
    p1.add_argument("--vault", action="store_true",
                    help="Salva o relatório em Estudos/Revisões/ do Obsidian.")
    p1.set_defaults(fn=cmd_relatorio)

    p2 = sub.add_parser("reforcar", help="Gera cards novos dos temas fracos.")
    common(p2)
    p2.add_argument("-n", "--num", type=int, default=8)
    p2.add_argument("--push", action="store_true",
                    help="Adiciona direto no Anki (senão gera .apkg).")
    p2.set_defaults(fn=cmd_reforcar)

    p3 = sub.add_parser("explicar", help="Explica um card (busca do Anki).")
    common(p3)
    p3.add_argument("busca", help='Busca do Anki, ex.: "deck:X aderência".')
    p3.set_defaults(fn=cmd_explicar)

    args = ap.parse_args()
    try:
        args.fn(args)
    except bridge.AnkiConnectError as e:
        sys.exit(f"[erro] {e}")


if __name__ == "__main__":
    main()
