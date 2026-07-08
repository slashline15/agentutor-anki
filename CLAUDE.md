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

# --push: adiciona direto no Anki aberto via AnkiConnect (fallback .apkg se fechado)
.\.venv\Scripts\python.exe card_agent.py --topic "..." --push

# Reconstruir .apkg/.tsv de um JSON já gerado, SEM chamar o modelo de novo
# (é assim que se testa mudança de template com cards reais)
.\.venv\Scripts\python.exe rebuild_from_json.py --json output/<slug>.json

# Templates: fonte única do realce é templates/tokenizer.js; após editar:
.\.venv\Scripts\python.exe build_templates.py          # regenera os HTML
.\.venv\Scripts\python.exe build_templates.py --push   # atualiza no Anki aberto
node --test tests/                                     # testes do tokenizer

# Tutor (Anki aberto; modelo LOCAL por padrão — histórico é dado pessoal)
.\.venv\Scripts\python.exe tutor.py relatorio --vault
.\.venv\Scripts\python.exe tutor.py reforcar --deck "X" --push
.\.venv\Scripts\python.exe tutor.py explicar "busca do anki"

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
- `anki_toolkit/bridge.py` — AnkiConnect (addon 2055492159, HTTP em `localhost:8765`, só responde com o Anki aberto). `push_cards()` checa note types (`modelNames`), pula duplicatas (`canAddNotes`) — duplicata total é resultado normal, NÃO erro (erro dispararia o fallback .apkg no CLI e o usuário importaria duplicado). `_post` é separado de propósito para os testes fazerem monkeypatch. `tools/novo_baralho.ps1` + atalho na área de trabalho usam o `--push`.
- `anki_toolkit/ingest.py` — PDF → markdown (`library/`, ignorada pelo git). Rotas: `digital` (docling com `do_ocr=False` — OBRIGATÓRIO, o pipeline padrão tenta baixar modelos RapidOCR e falha), `scanned` (docling + EasyOCR em lotes de páginas; lotes evitam `std::bad_alloc` do backend em PDFs longos; GPU via torch CUDA), `ollama` (multimodal, fallback). Imports pesados são preguiçosos DENTRO das funções — importar o módulo não pode exigir docling/torch. `split_sections()` (pura) divide material grande para o card_agent gerar em várias chamadas.
- `anki_toolkit/tts.py` — áudio dos cards vocab (`card_agent --audio`): edge-tts padrão (`--voice`), piper offline. Nome do mp3 é determinístico por (texto, voz) — regerar não duplica media. **Nesta máquina há interceptação TLS (antivírus/proxy): o `_synth_edge` injeta `truststore` ANTES de importar edge_tts, senão SSL falha** — não remover. Falha de TTS vira aviso, nunca erro. O bridge cria note types ausentes na coleção via `createModel` (`ensure_models`) — não existe mais o passo "importe o .apkg primeiro".
- `anki_toolkit/vault.py` — Obsidian via sistema de arquivos (sem plugin). Caminho do vault em `config.json` (ignorado pelo git; autodetectado do registro `%APPDATA%\obsidian\obsidian.json` na primeira execução com `--vault` — prioriza o vault com `"open": true`). Estrutura: `Estudos/Materiais|Baralhos|Revisões`. `VaultError` no card_agent é avisado e NUNCA derruba a geração. Funções de render/parse são puras (testáveis sem IO); as de IO aceitam `config_path=` para os testes.
- `anki_toolkit/tutor.py` + `tutor.py` — tutor: lê fraquezas (lapses/ease) SÓ via AnkiConnect (nunca abrir o SQLite `collection.anki2` direto), gera reforço em `<deck>::Reforço` e explica cards. Modelo padrão LOCAL (`gemma4:12b`) por privacidade do histórico — não trocar o default para cloud.
- **Templates HTML são GERADOS**: o realce vive em `templates/tokenizer.js` (fonte única) e `build_templates.py` injeta entre os marcadores `TOKENIZER:BEGIN/END` dos 5 HTML. Nunca editar o bloco injetado à mão. O modo padrão do tokenizer deve permanecer byte-idêntico ao antigo (teste em `tests/tokenizer.test.js` compara com uma cópia literal do algoritmo original). Linguagem por card: `<span data-lang="bash|powershell" hidden>` inserido por `outputs.lang_marker` SEMPRE num campo exibido, nunca no alvo de `{{type:}}`.
- O gateway dos modelos Ollama `:cloud` devolve **HTTP 502 em episódios de minutos**; `llm.call_ollama` tem retry (3x/10s) para 5xx — se um 502 persistir, é episódio: usar um modelo local (ex.: `gemma4:12b`) ou aguardar; não é bug do código.

Note types definidos em `anki_toolkit/models.py`:

| chave | Note type no Anki | campos |
|---|---|---|
| `code_cloze` | Python — Terminal (Cloze) | Front, Back |
| `code_write` | Python — Digite o Código | Pergunta, Codigo, Notas |
| `code_output` | Python — Digite a Saída | Codigo, Saida, Notas |
| `qa` | Geral — Básico (Q&A) | Frente, Verso, Extra |
| `cloze` | Geral — Cloze | Texto, Extra |
| `vocab` | Inglês — Vocabulário | Termo, IPA, Significado, Exemplo, Áudio, Notas (2 cartões: Reconhecimento + Produção) |

- **Os IDs de modelo (198053000x) e do deck são fixos e NUNCA devem mudar** — é o que permite reimportar um `.apkg` atualizando os templates sem duplicar notas na coleção do usuário.
- Os note types `code_*` carregam os HTML das pastas de template + `styling-comum.css`; os `qa`/`cloze` usam templates/CSS inline no próprio `anki_models.py`.
- `FIELDS` e `MODEL_NAMES` (no fim de `anki_models.py`) mapeiam tipo → ordem de campos e nome do note type; qualquer note type novo precisa entrar nos três lugares (`build_models`, `FIELDS`, `MODEL_NAMES`).

**Fluxo do `card_agent.py`:** prompt (princípios de Woźniak) → `POST /api/chat` do Ollama via `urllib` puro (sem SDK) com `format: json` → `extract_json` (tolerante a texto em volta) → `card_to_fields` valida e converte cada card (descarta inválidos, ex.: cloze sem `{{c1::}}`) → agrupa por tipo → emite apkg/tsv/json. Quebras de linha viram `<br>` (`nl2br`) porque os campos do Anki são HTML. O ID do deck gerado é `DECK_DEFAULT + hash(slug) % 100000`.

**Templates HTML:** cada `front.html`/`back.html` embute seu próprio JS de realce (tokenizador linear que escapa HTML e preserva os spans `.cloze` via TreeWalker; não usa `DOMContentLoaded` porque o Anki não dispara esse evento). A comparação de digitação usa o `{{type:...}}` nativo do Anki — não reimplementar diff.

## Armadilhas conhecidas

- **O tokenizador JS está duplicado nos arquivos HTML dos templates.** Alteração no realce precisa ser replicada em todas as cópias (refatoração para `_tokenizer.js` na media do Anki está prevista no ROADMAP, Fase 2).
- Nomes de campos e de note types precisam bater exatamente com os da coleção Anki do usuário — renomear quebra a importação por TSV (`#notetype:`) e a atualização por `.apkg`.
- Modelos Ollama pequenos (3B–9B) erram sintaxe de cloze com frequência; o descarte silencioso em `card_to_fields` é intencional.
