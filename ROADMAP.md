# ROADMAP — Anki Toolkit / Tutor pessoal de estudo

> **STATUS: TODAS AS 6 FASES CONCLUÍDAS (2026-07-07 → 2026-07-08).**
> Fase 0 `619e8db` · Fase 1 `4268376` · Fase 2 `640b119` · Fase 3 `c1dea9b`
> · Fase 4 `1114f80` · Fase 5 `aabda9e` · Fase 6 (tutor) no commit final.
> O documento abaixo é o plano original, mantido como referência de decisões.

> Plano revisado em 2026-07-07. Objetivo macro: transformar o gerador de cards num
> **tutor pessoal** que ingere material (PDFs, anotações), cria cards bem formulados,
> adiciona sozinho ao Anki, guarda tudo no Obsidian e acompanha a evolução do aluno.
>
> Base já pronta: 5 note types com IDs fixos, `card_agent.py` (Ollama local/cloud),
> saídas `.apkg`/TSV/JSON, `rebuild_from_json.py`, extrator de PDFs em `~/scripts/`
> (docling + OCR via Ollama, será incorporado na Fase 2).

---

## Princípios de arquitetura (o que garante que cada fase é independente)

1. **Contrato central = o JSON de cards.** Todo produtor (agente, tutor) e todo
   consumidor (apkg, TSV, AnkiConnect, Obsidian) fala esse formato. Ele ganha um campo
   `"schema": 1` e só evolui de forma retrocompatível (campos novos são opcionais).
2. **Markdown = formato universal de conteúdo.** PDF vira `.md`; o Obsidian lê e escreve
   `.md`; o `card_agent --file` já consome `.md`. Nenhuma fase precisa conhecer a outra —
   todas se encontram em arquivos markdown e no JSON de cards.
3. **Toda funcionalidade nova entra como módulo + flag de CLI, desligada por padrão.**
   O comportamento atual dos comandos nunca muda sem o usuário pedir (`--push`, `--vault`,
   `--tts`...). Parar o projeto no fim de qualquer fase deixa um sistema completo e usável.
4. **Todo caminho novo tem fallback para o caminho antigo.** Anki fechado → `.apkg`;
   sem GPU → docling em CPU ou OCR via Ollama; sem internet → TTS local. Nada quebra
   por dependência externa indisponível.
5. **Dependências pesadas são opcionais.** O core continua só com `genanki`. Docling/torch
   (ingestão) e edge-tts (áudio) entram como extras instaláveis à parte — quem não usa
   a fase, não instala nada dela.
6. **Cada fase termina com critério de pronto verificável** (comando que dá para rodar
   e ver funcionando) e testes automatizados do contrato que ela introduz.

## Visão do fluxo final

```
PDF / apostila ──[ingest]──► Markdown ──────┐
anotações do Obsidian ──────────────────────┤
tópico digitado ────────────────────────────┴──[card_agent]──► JSON de cards
                                                                    │
                             ┌──────────────────────────────────────┤
                             ▼                                      ▼
                   nota de estudo no vault                AnkiConnect ──► Anki aberto
                   (Obsidian: material,                        │
                    baralhos, revisões)                        └► .apkg (fallback)
                             ▲
                             │
            relatório de fraquezas ◄──[tutor]◄── histórico de revisões (revlog)
```

---

## Fase 0 — Fundação: pacote, testes e correções (esforço: pequeno)

**Meta:** preparar o terreno para crescer sem virar bola de neve. É a fase que compra
a independência de todas as outras.

- Reorganizar em pacote `anki_toolkit/` com módulos: `models` (os note types de hoje),
  `llm` (cliente Ollama), `outputs` (apkg/TSV/JSON). Os comandos atuais
  (`card_agent.py`, `build_apkg.py`, `rebuild_from_json.py`) viram invólucros finos —
  **a linha de comando não muda em nada** para o usuário.
- Adicionar `pytest` com testes de contrato: validação de cards (`card_to_fields`),
  geração de `.apkg` e TSV a partir de um JSON fixo de exemplo (sem chamar LLM).
- Introduzir `"schema": 1` no JSON gerado (leitura continua aceitando JSONs antigos).
- **Corrigir bug latente:** o ID do deck usa `hash(slug)`, que muda a cada execução do
  Python (hash de string é aleatório por processo). Trocar por hash determinístico
  (`zlib.crc32`) — o mesmo baralho passa a ter sempre o mesmo ID.

**Pronto quando:** `pytest` passa; `rebuild_from_json.py` gera saída idêntica à de hoje;
rodar duas vezes gera o mesmo ID de deck.

## Fase 1 — AnkiConnect: adicionar cards sozinho (esforço: médio)

**Meta:** eliminar o passo manual "abrir Anki → importar .apkg". Pedir cards e eles
aparecerem na coleção.

- Novo módulo `bridge`: detecta o AnkiConnect (addon, API HTTP em `localhost:8765`),
  cria decks (`createDeck`), adiciona notas (`addNotes`) usando os nomes de note type
  e campos que já existem na coleção, envia mídia (`storeMediaFile` — pré-requisito da
  Fase 4).
- Nova flag `card_agent.py --push`: tenta AnkiConnect; **se o Anki estiver fechado ou
  o addon ausente, cai automaticamente para gerar `.apkg`** e avisa. O fallback é
  permanente, não provisório.
- Duplicatas: consultar `canAddNotes` antes e pular os repetidos (relatando quantos).
- Disparo rápido no Windows: atalho na área de trabalho rodando um `.ps1` com caixa de
  texto (InputBox) para digitar o tópico → gera → adiciona → notificação. Hotkey global
  via AutoHotkey fica como opcional futuro, só se o atalho não bastar.

**Pronto quando:** com o Anki aberto, `--push` adiciona direto; com o Anki fechado, o
mesmo comando produz `.apkg` sem erro. Duplicata não entra duas vezes.

**Independência:** quem nunca usar `--push` não percebe diferença nenhuma.

## Fase 2 — Ingestão de PDFs (esforço: médio; reaproveita `~/scripts/`)

**Meta:** `python ingest.py apostila.pdf` → markdown limpo pronto para virar cards
(e para entrar no vault do Obsidian na Fase 3).

- Incorporar os scripts já desenvolvidos como módulo `ingest`, com três rotas e
  seleção automática:
  1. **PDF digital** (texto embutido): docling direto (base no `ocr_doc.py`).
  2. **PDF escaneado / documento longo**: docling com GPU e conversão em lotes de
     páginas (base no `ocr_ext.py`, que já resolve o estouro de RAM do backend).
  3. **Fallback sem GPU / qualidade ruim**: OCR + correção via modelo multimodal do
     Ollama, com retomada por página (base no `ocr_restore.py`).
- Saída: um `.md` por documento em `library/` (ou direto no vault, Fase 3), com
  frontmatter de metadados (arquivo de origem, nº de páginas, data, rota usada).
- Dependências (docling, torch, pypdf...) entram como extra opcional
  (`requirements-ingest.txt`), sem pesar o core.
- Integração imediata e sem código novo: `card_agent.py --file library/apostila.md`.
- Materiais grandes: o agente hoje corta em 12k caracteres; adicionar divisão por
  seções do markdown (títulos) com geração em múltiplas chamadas quando o material
  passar do limite.

**Pronto quando:** um PDF digital e um escaneado viram `.md` legível com um comando, e
esse `.md` gera um baralho válido.

**Independência:** é um pré-processador puro. Nada no gerador muda; quem não tem PDFs
nunca instala docling.

## Fase 3 — Obsidian: o vault como memória do estudo (esforço: médio)

**Meta:** tudo que o sistema produz (material extraído, baralhos gerados, futuros
relatórios) vira nota no Obsidian, pesquisável e editável.

- **Decisão técnica: integração por sistema de arquivos.** Um vault do Obsidian é só
  uma pasta de `.md` — escrever arquivos lá é integração completa, sem plugin, sem API,
  sem risco de quebrar com atualização do Obsidian.
- Novo módulo `vault` + `config.json` na raiz com o caminho do vault (com autodetecção
  dos vaults registrados em `%APPDATA%\obsidian\obsidian.json` para sugerir o caminho).
- Estrutura no vault (subpasta `Estudos/`, configurável):
  - `Estudos/Materiais/` — os `.md` extraídos dos PDFs (Fase 2 passa a poder gravar aqui).
  - `Estudos/Baralhos/<deck>.md` — uma **nota de estudo por baralho gerado**: frontmatter
    (deck, data, modelo usado, tags), resumo do tema e os cards em formato legível,
    com link `[[material]]` para a fonte. Serve de índice humano do que já virou card.
  - `Estudos/Revisões/` — reservado para os relatórios do tutor (Fase 6).
- Direção inversa (já funciona hoje, documentar o fluxo): qualquer anotação sua no vault
  vira baralho com `card_agent.py --file <nota do vault>`.
- Nova flag `--vault` no `card_agent.py` e no `ingest.py`, desligada por padrão.

**Pronto quando:** gerar um baralho com `--vault` cria a nota de estudo no Obsidian com
links funcionando; um PDF ingerido aparece em `Materiais/`.

**Independência:** sem `config.json` ou sem a flag, nada é escrito fora de `output/`.

## Fase 4 — Inglês com áudio nativo (TTS) (esforço: médio)

**Meta:** cards de vocabulário/frases com MP3 de voz neural nativa embutido.

- Novo note type `Inglês — Vocabulário` (ID fixo novo, `1980530006`), campos:
  `Termo`, `IPA`, `Significado`, `Exemplo`, `Áudio` (`[sound:...]`), `Notas`.
  Dois cartões no mesmo note type: **produção** (significado → lembrar o termo) e
  **reconhecimento** (ouvir/ler o termo → significado).
- **Decisões técnicas:** `edge-tts` como padrão (grátis, sem chave, vozes neurais);
  voz padrão `en-US-AriaNeural` com flag `--voice` (quem prefere UK troca por flag);
  `--tts piper` como alternativa 100% offline. Sem internet e sem piper → card é gerado
  sem áudio, com aviso (nunca falha por causa do áudio).
- Novo tipo `"vocab"` no JSON do agente (campo novo opcional — schema retrocompatível).
- Mídia: `media_files` no pacote genanki (`.apkg`) ou `storeMediaFile` quando `--push`
  (por isso a Fase 1 vem antes).
- Uso: `card_agent.py --topic "phrasal verbs de trabalho" --lang inglês --audio`.

**Pronto quando:** um baralho de vocabulário toca o áudio dentro do Anki, tanto via
`.apkg` quanto via `--push`.

**Independência:** sem `--audio`, nada de TTS acontece; os 5 note types atuais não mudam.

## Fase 5 — Realce multilinguagem + fim da duplicação do tokenizer (esforço: pequeno/médio)

**Meta:** realce correto para Bash e PowerShell além de Python/JS, sem manter 5 cópias
do mesmo JS.

- **Decisão técnica: gerar os templates em build-time, não em runtime.** Um único
  `templates/tokenizer.js` fonte + `build_templates.py` que injeta o script nos
  `front.html`/`back.html` das três pastas. É mais robusto que referenciar
  `_tokenizer.js` na media do Anki (não depende de arquivo externo na coleção do
  usuário; o card continua autossuficiente). Os HTML gerados continuam commitados —
  quem só copia e cola no Anki não precisa rodar nada.
- Realce por linguagem: o bloco de código carrega `data-lang` (o agente já sabe a
  linguagem e preenche); o tokenizer escolhe o dicionário (Python, JS, Bash, PowerShell).
  Sem `data-lang`, mantém o comportamento atual (Python) — cards antigos não mudam.
- Dicionários novos: Bash (`if/then/fi/done/echo/export`, `$VAR`, `${...}`) e
  PowerShell (`param/function/foreach`, cmdlets `Verbo-Substantivo`, `$var`, `-eq/-ne`).

**Pronto quando:** `build_templates.py` regenera os 6 HTML idênticos em estrutura;
um card Bash e um PowerShell aparecem com realce correto; cards antigos inalterados.

**Independência:** puramente interna aos templates; nenhum script Python muda.

## Fase 6 — GRAND FINALE: tutor com acesso ao progresso (esforço: grande)

**Meta:** o agente lê seu histórico de revisões, encontra os pontos fracos, gera reforço
e registra a evolução no Obsidian.

- **Decisão técnica: ler o histórico só via AnkiConnect** (`findCards`, `cardsInfo`,
  `getReviews`) — nunca abrir o SQLite `collection.anki2` direto (evita corromper/travar
  a coleção com o Anki aberto). Por isso depende da Fase 1.
- **Decisão técnica: modelo local por padrão nesta fase** (o histórico de estudo é dado
  pessoal; cloud só com flag explícita `--model *-cloud`).
- Funcionalidades, em ordem de entrega (cada uma já é útil sozinha):
  1. `tutor.py relatorio` — diagnóstico de fraquezas: cards com mais lapsos/menor ease
     (`prop:lapses>3`), retenção por deck/tag. Sai no terminal e, com `--vault`, vira
     nota datada em `Estudos/Revisões/`.
  2. `tutor.py reforcar --deck X` — geração adaptativa: pega os temas dos cards que você
     mais erra e gera cards novos reformulados (ângulo diferente, exemplo concreto).
  3. `tutor.py explicar <busca>` — chat sobre um card específico: explicar, dar exemplos,
     reformular (usa o conteúdo do card como contexto).
  4. Acompanhamento: o relatório periódico no vault forma a linha do tempo da evolução.

**Pronto quando:** o relatório aponta os mesmos cards problemáticos que o navegador do
Anki mostra com `prop:lapses>3`; um comando gera baralho de reforço só dos temas fracos.

**Independência:** módulo somente-leitura sobre a coleção + gerador que reusa todo o
pipeline existente. Se nunca rodar, nada muda.

---

## Ordem de execução e dependências

```
Fase 0 (fundação)
  └─► Fase 1 (AnkiConnect) ──► Fase 4 (TTS, usa storeMediaFile)
  └─► Fase 2 (PDFs) ─────┐    └─► Fase 6 (tutor, usa leitura via AnkiConnect)
  └─► Fase 3 (Obsidian) ◄┘         (relatórios do tutor usam a Fase 3)
Fase 5 (realce/tokenizer): independente, encaixa em qualquer momento.
```

Sugestão de sequência: **0 → 1 → 2 → 3 → 4 → 5 → 6** (a 5 pode adiantar se surgir
necessidade de cards de shell antes).

## Decisões tomadas (antes "em aberto" no roadmap antigo)

| Questão | Decisão | Motivo |
|---|---|---|
| edge-tts vs Piper | edge-tts padrão, `--tts piper` offline | Melhor voz, zero custo; fallback local garantido |
| Sotaque padrão | `en-US-AriaNeural`, trocável por `--voice` | Preferência pessoal vira flag, não decisão fixa |
| AnkiConnect vs `.apkg` | AnkiConnect-first com fallback `.apkg` **permanente** | Automação sem perder robustez com Anki fechado |
| Hotkey global vs atalho | Atalho + InputBox primeiro; AutoHotkey só se fizer falta | Menor dependência externa, mesmo resultado |
| Modelo do tutor | Local por padrão, cloud com flag explícita | Histórico de estudo é dado pessoal |
| Obsidian: plugin vs arquivos | Sistema de arquivos puro | Vault é pasta de `.md`; zero dependência frágil |
| Tokenizer compartilhado | Build-time (`build_templates.py`), não `_tokenizer.js` na media | Card autossuficiente, sem dependência da coleção |

## Dependências novas por fase (todas opcionais ao core)

- **Fase 0:** `pytest` (dev)
- **Fase 1:** addon AnkiConnect (código 2055492159) no Anki
- **Fase 2:** `docling`, `pypdf` (+ `torch` p/ GPU) — `requirements-ingest.txt`
- **Fase 3:** — (só filesystem)
- **Fase 4:** `edge-tts` (opcional `piper-tts`)
- **Fase 6:** — (reusa AnkiConnect e Ollama)
