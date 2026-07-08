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

## Adicionar direto no Anki (`--push`)

Com o Anki **aberto** (e o addon AnkiConnect instalado), a flag `--push` adiciona
os cards direto na coleção — sem gerar/importar `.apkg`:

```powershell
.\.venv\Scripts\python.exe card_agent.py --topic "Verbos irregulares" -n 10 --push
```

- Anki aberto → cards entram na hora; duplicatas são puladas automaticamente.
- Anki fechado → cai para o fluxo antigo (gera `.apkg` em `output/`) e avisa.

**Atalho "Novo baralho Anki"** (área de trabalho): clique → digite o **tópico**
numa caixa de texto → o agente gera e adiciona sozinho → popup com o resultado.

## De PDF para baralho (`ingest.py`)

Converte PDF em markdown limpo (pasta `library/`), pronto para virar cards:

```powershell
.\.venv\Scripts\python.exe ingest.py apostila.pdf
.\.venv\Scripts\python.exe card_agent.py --file library\apostila.md --push
```

| Tipo de PDF | Rota (automática) | Observações |
|---|---|---|
| Texto embutido | `digital` — extração direta, sem OCR | Rápida |
| Escaneado | `scanned` — docling + EasyOCR em lotes | Usa GPU se houver; pode demorar |
| Qualquer um | `--route ollama` — modelo multimodal local | Fallback sem docling/torch |

Dependências (opcionais, só para quem usa PDFs):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ingest.txt
```

Para OCR na GPU, instale o torch CUDA antes (comando no comentário do próprio
`requirements-ingest.txt`).

**Materiais grandes:** o `card_agent` divide o conteúdo por seções e faz várias
chamadas ao modelo automaticamente — nada muda no comando.

## Notas no Obsidian (--vault)

- A flag `--vault` está presente em **card_agent.py** e **ingest.py**.  
  Sem ela, nada é escrito no Obsidian.

### card_agent.py … `--vault`

- Além de criar o baralho no Anki, grava uma **nota de estudo** no vault em:  

  ```
  Estudos/Baralhos/<deck>.md
  ```

- O arquivo contém:
  - **frontmatter** com: `deck`, `modelo`, `tags`, `nº de cards`, `data`.
  - Link `[[material]]` quando o baralho foi gerado a partir de um arquivo.
  - Todos os cards em formato legível, funcionando como índice do que já virou card.

### ingest.py `apostila.pdf --vault`

- Extrai o conteúdo da apostila e grava o markdown resultante em:  

  ```
  Estudos/Materiais/
  ```

  dentro do vault, ao invés de `library/`.

### Configuração do caminho do vault

- O caminho do vault é definido em **config.json** na raiz do projeto, na chave `"vault"`.
- Na **primeira execução** com `--vault`, o script detecta automaticamente o vault aberto no Obsidian e salva o caminho em `config.json`.
- Para mudar o vault, edite o valor de `"vault"` em `config.json`.
- A subpasta padrão `"Estudos"` também é configurável via a chave `"vault_subdir"` em `config.json`.

### Fluxo completo de exemplo

```powershell
# 1. Ingestão da apostila para o vault
.\.venv\Scripts\python.exe ingest.py apostila.pdf --vault

# 2. Geração de cards a partir do arquivo no vault e envio ao Anki
#    (o ingest imprime o caminho completo do .md — use-o aqui)
.\.venv\Scripts\python.exe card_agent.py --file "<caminho-do-vault>studosMateriaispostila.md" --push --vault
```

Esse fluxo cria a nota de estudo em `Estudos/Baralhos/<deck>.md` e mantém o material original em `Estudos/Materiais/`.

## Inglês com áudio nativo (--audio)

- `card_agent.py --topic "..." --audio` entra em modo vocabulário: gera cards do note type **Inglês — Vocabulário** (campos **Termo, IPA, Significado, Exemplo, Áudio, Notas**), com MP3 de voz neural nativa embutido (motor *edge‑tts*, grátis, precisa de internet).  
- Cada nota gera **DOIS** cartões no Anki:  
  1. **Reconhecimento** – mostra/ouve o termo em inglês e pede o significado.  
  2. **Produção** – mostra o significado e pede que o usuário fale ou lembre o termo em inglês.  
- `--voice` troca a voz utilizada (padrão `en-US-AriaNeural`; exemplo de voz britânica: `en-GB-RyanNeural`).  
- `--tts piper` usa motor **100 % offline** (requer `pip install piper-tts` e um modelo de voz compatível).  
- Se o áudio falhar (por falta de internet ou erro no TTS), os cards são criados **mesmo assim**, apenas sem o som – o processo nunca trava.  
- Compatível com `--push`: o áudio já é inserido na mídia do Anki durante o upload.  
- Compatível com exportação `.apkg`: o MP3 é incluído dentro do pacote.  
- O note type novo é criado automaticamente na coleção no primeiro `--push`.  

**Exemplo de uso (PowerShell):**

```powershell
.\.venv\Scripts\python.exe card_agent.py --topic "phrasal verbs de trabalho" -n 10 --audio --push
```
