"""
Tutor (Fase 6): lê o histórico de estudo, encontra os pontos fracos, gera
reforço e explica cards.

Decisões do projeto:
- Leitura SÓ via AnkiConnect (findCards/cardsInfo) — nunca abrir o SQLite
  collection.anki2 direto (risco de corromper/travar com o Anki aberto).
- O histórico de estudo é dado pessoal: o modelo PADRÃO do tutor é LOCAL
  (DEFAULT_TUTOR_MODEL); cloud só com --model explícito.

Sinais de fraqueza (por card): lapses (nº de vezes que errou depois de
aprendido) e ease/factor (quanto menor, mais difícil o Anki considera).
"""
import re

from . import bridge
from .llm import DEFAULT_HOST

DEFAULT_TUTOR_MODEL = "gemma4:12b"   # local: privacidade do histórico
DEFAULT_MIN_LAPSES = 3


# ----------------------------------------------------------------------------- puras
def strip_html(s):
    """HTML de um campo/card -> texto simples de uma linha (sem tags de áudio)."""
    s = re.sub(r"<style[\s\S]*?</style>", " ", str(s or ""))
    s = re.sub(r"<script[\s\S]*?</script>", " ", s)
    s = re.sub(r"\[anki:play:[^\]]*\]|\[sound:[^\]]*\]", " ", s)
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = (s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
          .replace("&quot;", '"').replace("&nbsp;", " "))
    return re.sub(r"\s+", " ", s).strip()


def simplify_card(info):
    """cardsInfo -> dict enxuto usado pelo relatório e pelo reforço."""
    return {
        "deck": info.get("deckName", "?"),
        "model": info.get("modelName", "?"),
        "question": strip_html(info.get("question", ""))[:200],
        "answer": strip_html(info.get("answer", ""))[:200],
        "lapses": int(info.get("lapses", 0) or 0),
        "ease": int(info.get("factor", 0) or 0),  # 2500 = padrão; <2000 difícil
        "reps": int(info.get("reps", 0) or 0),
        "interval": int(info.get("interval", 0) or 0),
    }


def rank_weak(cards, top=20):
    """Ordena por 'fraqueza': mais lapsos primeiro; empate, menor ease."""
    return sorted(cards, key=lambda c: (-c["lapses"], c["ease"]))[:top]


def aggregate_by_deck(cards):
    """[{deck, lapses, ease, ...}] -> ranking de decks problemáticos."""
    by = {}
    for c in cards:
        d = by.setdefault(c["deck"], {"deck": c["deck"], "cards": 0,
                                      "lapses": 0, "ease_sum": 0})
        d["cards"] += 1
        d["lapses"] += c["lapses"]
        d["ease_sum"] += c["ease"]
    out = []
    for d in by.values():
        d["ease_medio"] = d["ease_sum"] // max(1, d["cards"])
        del d["ease_sum"]
        out.append(d)
    return sorted(out, key=lambda x: (-x["lapses"], x["ease_medio"]))


def render_report(weak, by_deck, min_lapses, now):
    """Relatório de fraquezas em markdown (terminal e Estudos/Revisões/)."""
    lines = [
        "---", "tipo: revisao", f"gerado: {now}",
        f"criterio: lapses >= {min_lapses}", f"cards_fracos: {len(weak)}",
        "---", "", f"# Diagnóstico de fraquezas — {now[:10]}", "",
    ]
    if not weak:
        lines += ["Nenhum card com lapsos suficientes — bom sinal. "
                  "Diminua `--min-lapses` para investigar mais fundo.", ""]
        return "\n".join(lines)

    lines += ["## Decks problemáticos", "",
              "| Deck | Cards fracos | Lapsos | Ease médio |",
              "|---|---|---|---|"]
    for d in by_deck:
        lines.append(f"| {d['deck']} | {d['cards']} | {d['lapses']} "
                     f"| {d['ease_medio']} |")
    lines += ["", "## Cards que você mais erra", ""]
    for i, c in enumerate(weak, 1):
        lines += [f"### {i}. [{c['deck']}] {c['lapses']} lapsos, ease {c['ease']}",
                  "", f"**P:** {c['question']}", "", f"**R:** {c['answer']}", ""]
    lines += ["> Gere reforço com: `tutor.py reforcar --deck \"<deck>\"`", ""]
    return "\n".join(lines)


def weak_to_material(weak):
    """Cards fracos -> texto de material para o gerador de reforço."""
    partes = []
    for c in weak:
        partes.append(f"- Pergunta: {c['question']}\n  Resposta: {c['answer']}"
                      f"\n  (errado {c['lapses']}x)")
    return "\n".join(partes)


# ----------------------------------------------------------------------------- leitura via AnkiConnect
def fetch_weak(min_lapses=DEFAULT_MIN_LAPSES, deck=None, top=20,
               url=bridge.DEFAULT_URL):
    """Cards com lapses >= min_lapses (opcionalmente de um deck)."""
    query = f"prop:lapses>={min_lapses}"
    if deck:
        query += f' deck:"{deck}"'
    ids = bridge.invoke("findCards", {"query": query}, url=url)
    if not ids:
        return []
    infos = bridge.invoke("cardsInfo", {"cards": ids[:500]}, url=url)
    return rank_weak([simplify_card(i) for i in infos], top=top)


def find_card(search, url=bridge.DEFAULT_URL):
    """Primeiro card que casa com a busca (sintaxe de busca do Anki)."""
    ids = bridge.invoke("findCards", {"query": search}, url=url)
    if not ids:
        return None
    info = bridge.invoke("cardsInfo", {"cards": ids[:1]}, url=url)
    return simplify_card(info[0]) if info else None
