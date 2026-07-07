# card_agent — gerador de flashcards com Ollama

Gera flashcards de Anki a partir de um **tópico** ou de um **arquivo de material**,
usando modelos Ollama (locais ou cloud), já aplicando boas técnicas de memorização
(informação mínima, recordação ativa, cloze, princípios de Woźniak).

## Saídas (pasta `output/`)
- **`<deck>.apkg`** — importa direto no Anki (já com os note types certos).
- **`<deck>__<tipo>.tsv`** — um por note type, com cabeçalho `#notetype/#deck/#tags`
  (importação direta, sem mapear campos). Bom para revisar antes no editor.
- **`<deck>.json`** — cards crus, para revisar/editar em massa.

## Uso
```powershell
cd "C:\Users\Danilo Gohan\anki-python-templates"
.\.venv\Scripts\python.exe card_agent.py --topic "List comprehensions em Python" -n 12
```

A partir de um material (apostila, anotações):
```powershell
.\.venv\Scripts\python.exe card_agent.py --file material.md -n 25 --deck "Estudos::Redes"
```

## Opções
| Flag | Padrão | Descrição |
|---|---|---|
| `--topic` / `--file` | — | Fonte (um dos dois, obrigatório) |
| `-n, --num` | 15 | Nº alvo de cards |
| `--model` | `gpt-oss:120b-cloud` | Modelo Ollama (ver `ollama list`) |
| `--deck` | sugerido pelo modelo | Nome do baralho (use `::` para subdecks) |
| `--formats` | `apkg,csv` | `apkg`, `csv`, `json` (vírgula) |
| `--lang` | `português` | Idioma dos cards |
| `--host` | `http://localhost:11434` | URL do Ollama |
| `--timeout` | 900 | Timeout da chamada (s) |

## Modelos (no seu PC)
- **Cloud (melhor qualidade):** `gpt-oss:120b-cloud`, `qwen3.5:397b-cloud`, `deepseek-v4-pro:cloud`
  — usam sua `OLLAMA_API_KEY`.
- **Local (privado, sem custo):** `gemma4:12b`, `qwen3.5:9b`, `llama3.2:3b`.

> Modelos pequenos (3B–9B) às vezes erram a sintaxe de cloze (`{{c1::...}}`) ou a
> contagem. Para resultado fino, prefira um modelo cloud ou revise o `.json` antes
> de importar.

## Tipos de card gerados
| type | Note type | Quando |
|---|---|---|
| `qa` | Geral — Básico (Q&A) | fatos/conceitos |
| `cloze` | Geral — Cloze | fato em contexto |
| `code_output` | Python — Digite a Saída | prever saída de código |
| `code_write` | Python — Digite o Código | escrever código |
| `code_cloze` | Python — Terminal (Cloze) | lacuna de sintaxe |

O agente escolhe o tipo automaticamente; os tipos `code_*` só aparecem quando o
conteúdo é de programação.
