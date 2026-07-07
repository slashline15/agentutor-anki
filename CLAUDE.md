# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é este projeto

Toolkit de flashcards Anki com duas partes:
1. **Templates HTML/CSS** de note types com tema de terminal (One Dark) e realce de sintaxe Python em JS puro (pastas `1-terminal-cloze/`, `2-digite-codigo/`, `3-digite-saida/` + `styling-comum.css`).
2. **Gerador de cards via LLM** (`card_agent.py`) que usa Ollama (local ou cloud) para criar baralhos a partir de um tópico ou arquivo de material.

Documentação existente: `README.md` (templates), `AGENTE.md` (uso do card_agent), `ROADMAP.md` (planejamento das próximas fases — ler antes de iniciar trabalho novo).

## Comandos

Dependência do core: só `genanki`; dev: `pytest` (`requirements-dev.txt`). Usar o Python do venv:

```powershell
# Testes (rodar após qualquer mudança em anki_toolkit/ ou nos scripts)
.\.venv\Scripts\python.exe -m pytest tests/ -v

# Gerar o .apkg de exemplo com os 5 note types (após editar templates/CSS)
.\.venv\Scripts\python.exe build_apkg.py

# Gerar cards via Ollama (requer servidor em localhost:11434)
.\.venv\Scripts\python.exe card_agent.py --topic "List comprehensions" -n 12
.\.venv\Scripts\python.exe card_agent.py --file material.md -n 25 --deck "Estudos::Redes"

# Reconstruir .apkg/.tsv de um JSON já gerado, SEM chamar o modelo de novo
# (é assim que se testa mudança de template com cards reais)
.\.venv\Scripts\python.exe rebuild_from_json.py --json output/<slug>.json

# Orquestração: delegar tarefa de código a um modelo Ollama cloud
# (o usuário tem saldo ilimitado no Ollama; preferir isso a gastar tokens
#  Anthropic em geração longa de código bem especificado — Claude escreve a
#  spec num arquivo, o modelo executa, Claude revisa e integra)
.\.venv\Scripts\python.exe tools\ollama_worker.py --model kimi-k2.7-code:cloud --prompt-file spec.txt --out resultado.py
```

Modelos cloud bons para código: `kimi-k2.7-code:cloud`, `gpt-oss:120b-cloud`, `gemma4:31b-cloud` (até 3 em paralelo; o worker tem retry porque o gateway cloud dá 502 esporádico).

Saídas vão para `output/`: `<slug>.apkg`, `<slug>__<tipo>.tsv` (um por note type, com cabeçalho `#notetype/#deck/#tags`) e `<slug>.json` (cards crus, editáveis).

## Arquitetura

**O pacote `anki_toolkit/` é a fonte única de verdade**; os scripts da raiz são invólucros finos de CLI:
- `anki_toolkit/models.py` — os 5 note types genanki (IDs fixos). `anki_models.py` na raiz é só um shim de compatibilidade que re-exporta daqui.
- `anki_toolkit/llm.py` — cliente Ollama (`call_ollama`, com `fmt=None` para texto livre) e `extract_json`. Levanta exceções (`OllamaError`/`ValueError`); quem chama `sys.exit` é o script de CLI.
- `anki_toolkit/outputs.py` — conversão (`card_to_fields`), TSV, APKG e o JSON intermediário com `"schema": 1` (contrato central do projeto; evoluir só com campos opcionais). `deck_id()` usa crc32 (determinístico — nunca voltar para `hash()`, que é salgado por processo).

Note types definidos em `anki_toolkit/models.py`:

| chave | Note type no Anki | campos |
|---|---|---|
| `code_cloze` | Python — Terminal (Cloze) | Front, Back |
| `code_write` | Python — Digite o Código | Pergunta, Codigo, Notas |
| `code_output` | Python — Digite a Saída | Codigo, Saida, Notas |
| `qa` | Geral — Básico (Q&A) | Frente, Verso, Extra |
| `cloze` | Geral — Cloze | Texto, Extra |

- **Os IDs de modelo (198053000x) e do deck são fixos e NUNCA devem mudar** — é o que permite reimportar um `.apkg` atualizando os templates sem duplicar notas na coleção do usuário.
- Os note types `code_*` carregam os HTML das pastas de template + `styling-comum.css`; os `qa`/`cloze` usam templates/CSS inline no próprio `anki_models.py`.
- `FIELDS` e `MODEL_NAMES` (no fim de `anki_models.py`) mapeiam tipo → ordem de campos e nome do note type; qualquer note type novo precisa entrar nos três lugares (`build_models`, `FIELDS`, `MODEL_NAMES`).

**Fluxo do `card_agent.py`:** prompt (princípios de Woźniak) → `POST /api/chat` do Ollama via `urllib` puro (sem SDK) com `format: json` → `extract_json` (tolerante a texto em volta) → `card_to_fields` valida e converte cada card (descarta inválidos, ex.: cloze sem `{{c1::}}`) → agrupa por tipo → emite apkg/tsv/json. Quebras de linha viram `<br>` (`nl2br`) porque os campos do Anki são HTML. O ID do deck gerado é `DECK_DEFAULT + hash(slug) % 100000`.

**Templates HTML:** cada `front.html`/`back.html` embute seu próprio JS de realce (tokenizador linear que escapa HTML e preserva os spans `.cloze` via TreeWalker; não usa `DOMContentLoaded` porque o Anki não dispara esse evento). A comparação de digitação usa o `{{type:...}}` nativo do Anki — não reimplementar diff.

## Armadilhas conhecidas

- **O tokenizador JS está duplicado nos arquivos HTML dos templates.** Alteração no realce precisa ser replicada em todas as cópias (refatoração para `_tokenizer.js` na media do Anki está prevista no ROADMAP, Fase 2).
- Nomes de campos e de note types precisam bater exatamente com os da coleção Anki do usuário — renomear quebra a importação por TSV (`#notetype:`) e a atualização por `.apkg`.
- Modelos Ollama pequenos (3B–9B) erram sintaxe de cloze com frequência; o descarte silencioso em `card_to_fields` é intencional.
