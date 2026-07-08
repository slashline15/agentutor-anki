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

from anki_toolkit import bridge, llm, outputs, tts, vault
from anki_toolkit.ingest import split_sections
from anki_toolkit.llm import DEFAULT_HOST, DEFAULT_MODEL
from anki_toolkit.models import VOCAB_AUDIO_FIELD

CHUNK_LIMIT = 12000  # chars por chamada; acima disso o material é dividido

VOCAB_INSTRUCTION = """
IMPORTANTE — MODO VOCABULÁRIO COM ÁUDIO: o aluno quer aprender vocabulário de
inglês. PREFIRA o type "vocab" para a maioria dos cards:
{"type":"vocab","term":"palavra ou frase EM INGLÊS","ipa":"/transcrição fonética/","meaning":"significado em português","example":"frase de exemplo natural EM INGLÊS usando o termo","extra":"dica opcional"}
Regras do vocab: term e example sempre em inglês; meaning em português; ipa no
formato /.../ (pode omitir se não souber); um termo por card."""
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
    ap.add_argument("--push", action="store_true",
                    help="Adiciona direto no Anki aberto via AnkiConnect "
                         "(se o Anki estiver fechado, cai para .apkg).")
    ap.add_argument("--vault", action="store_true",
                    help="Grava uma nota de estudo do baralho no vault do "
                         "Obsidian (caminho em config.json; autodetectado).")
    ap.add_argument("--audio", action="store_true",
                    help="Modo vocabulário: gera cards 'vocab' com MP3 de voz "
                         "nativa (edge-tts). Falha de áudio nunca impede o card.")
    ap.add_argument("--voice", default=tts.DEFAULT_VOICE,
                    help=f"Voz do TTS (padrão {tts.DEFAULT_VOICE}; "
                         "ex.: en-GB-RyanNeural).")
    ap.add_argument("--tts", default=tts.DEFAULT_ENGINE, dest="tts_engine",
                    choices=["edge", "piper"],
                    help="Motor de TTS (edge=online padrão, piper=offline).")
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

    # material maior que o limite: divide por seções e gera em várias chamadas
    chunks = split_sections(content, limit=CHUNK_LIMIT)
    if not chunks:
        sys.exit("[erro] Conteúdo vazio.")
    per_chunk = max(2, -(-args.num // len(chunks)))  # ceil(num/chunks)

    if len(chunks) == 1:
        print(f"[1/4] Gerando ~{args.num} cards com '{args.model}'...")
    else:
        print(f"[1/4] Material grande: {len(chunks)} blocos, "
              f"~{per_chunk} cards por bloco com '{args.model}'...")

    template = USER_TEMPLATE + (VOCAB_INSTRUCTION if args.audio else "")
    cards, deck_sugerido = [], None
    for i, chunk in enumerate(chunks, 1):
        user = (template
                .replace("__N__", str(per_chunk if len(chunks) > 1 else args.num))
                .replace("__LANG__", args.lang)
                .replace("__CONTENT__", chunk))
        try:
            raw = llm.call_ollama(args.host, args.model, SYSTEM_PROMPT, user,
                                  args.timeout)
            data = llm.extract_json(raw)
        except (llm.OllamaError, ValueError) as e:
            if len(chunks) == 1:
                sys.exit(f"[erro] {e}")
            print(f"        bloco {i}/{len(chunks)} falhou: {e} (pulando)")
            continue
        deck_sugerido = deck_sugerido or data.get("deck")
        novos = data.get("cards", [])
        cards.extend(novos)
        if len(chunks) > 1:
            print(f"        bloco {i}/{len(chunks)}: {len(novos)} cards")

    deck_name = args.deck or deck_sugerido or default_deck or "Ollama Cards"
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

    # TTS: preenche o campo Áudio dos cards vocab (falha vira aviso, nunca erro)
    media_paths = []
    if args.audio and "vocab" in by_type:
        media_dir = out / "media"
        ok = 0
        for fields in by_type["vocab"]:
            texto = tts.vocab_tts_text(fields[0].replace("<br>", " "),
                                       fields[3].replace("<br>", " "))
            try:
                path, name = tts.synthesize(texto, media_dir,
                                            voice=args.voice,
                                            engine=args.tts_engine)
                fields[VOCAB_AUDIO_FIELD] = f"[sound:{name}]"
                media_paths.append(path)
                ok += 1
            except tts.TTSError as e:
                print(f"[tts] sem áudio para '{fields[0][:40]}': {e}")
        print(f"[tts] {ok}/{len(by_type['vocab'])} áudios gerados "
              f"({args.voice}, {args.tts_engine}).")

    if args.push:
        try:
            for p in media_paths:  # áudio entra na media da coleção primeiro
                bridge.store_media_file(p)
            res = bridge.push_cards(deck_name, tags, by_type)
            print(f"[push] {res['added']} adicionados ao Anki, "
                  f"{res['skipped']} pulados (duplicados/erro).")
        except bridge.AnkiConnectError as e:
            print(f"[push] {e}")
            print("[push] Caindo para .apkg — importe manualmente depois.")
            formats.add("apkg")

    if "json" in formats:
        outputs.write_json(out / f"{slug}.json", deck_name, args.model, kept)

    if "csv" in formats:
        outputs.write_tsvs(out, slug, deck_name, tags, by_type)

    if "apkg" in formats:
        outputs.write_apkg(out / f"{slug}.apkg", deck_name, tags, by_type,
                           media_files=media_paths)

    if args.vault:
        try:
            source_stem = Path(args.file).stem if args.file else None
            note = vault.write_deck_note(deck_name, args.model, tags, kept,
                                         source_stem=source_stem)
            print(f"[vault] nota de estudo: {note}")
        except vault.VaultError as e:  # nunca derruba a geração
            print(f"[vault] {e}")

    print(f"[3/4] Baralho: '{deck_name}'  (tags: {', '.join(tags)})")
    print(f"[4/4] Arquivos em: {out}")
    for f in sorted(out.glob(f"{slug}*")):
        print(f"        - {f.name}")


if __name__ == "__main__":
    main()
