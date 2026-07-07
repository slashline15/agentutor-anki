# ROADMAP — Anki Toolkit / Agente de estudo

> Documento de planejamento para a **próxima sessão**. Rodar `/plan` a partir daqui.
> Estado atual (base já pronta): 5 note types, `card_agent.py` (Ollama local/cloud),
> realce multilinguagem Python+JS, saídas `.apkg`/TSV/JSON, `rebuild_from_json.py`.

Objetivo macro: transformar o gerador de cards num **tutor pessoal** que cria, narra,
adiciona automaticamente e acompanha a evolução do aluno.

---

## Fase 1 — Cards de inglês com áudio (TTS de voz nativa)

**Meta:** dado um termo ou assunto, gerar cards de vocabulário/frases com pronúncia e
**MP3 narrado por voz nativa**, embutido no card.

- **Novo note type** `Inglês — Vocabulário`:
  campos `Termo`, `IPA`, `Significado`, `Exemplo` (frase), `Áudio` (`[sound:...]`), `Notas`.
  Frente: termo/frase + botão de áudio; verso: significado + exemplo + IPA.
- **TTS — opções avaliadas:**
  - ✅ **edge-tts** (recomendado): online grátis, sem chave, vozes neurais nativas
    (`en-US-AriaNeural`, `en-GB-RyanNeural`...). `pip install edge-tts`. Ótima qualidade.
  - **Piper TTS**: 100% offline/local, leve (CPU), boa qualidade — fallback sem internet.
  - **pyttsx3/SAPI** (Windows): local, mas voz robótica — só último recurso.
  - Decisão: edge-tts como padrão, `--tts piper` como alternativa offline.
- **Integração:** gerar 1 MP3 por card, salvar e passar como `media_files` no `genanki.Package`
  (no `.apkg`) **ou** `storeMediaFile` via AnkiConnect (ver Fase 3).
- **Pontos a decidir:** sotaque padrão (US/UK), velocidade, gerar áudio do termo e/ou da frase.
- **Técnicas:** card de produção (ver palavra → falar/lembrar) + reconhecimento (ouvir → significado).

## Fase 2 — Mais linguagens no realce (Bash / PowerShell / outras)

**Meta:** realce correto para shell além de Python/JS.

- Adicionar conjuntos de keywords: **Bash** (`if/then/fi/for/do/done/case/esac/echo/export/...`,
  variáveis `$VAR`, `${...}`) e **PowerShell** (`param/function/foreach`, cmdlets `Verbo-Substantivo`,
  `$var`, `-eq/-ne/...`).
- **Problema:** juntar tudo num único conjunto gera colisões (ex.: `echo`, `set`, `do`).
  Solução proposta: **realce por linguagem** — o card carrega `data-lang` no bloco de código
  e o tokenizer escolhe o dicionário certo. O agente já sabe a linguagem e marca o campo.
- **Dívida técnica a resolver junto:** o tokenizer está **duplicado em 5 arquivos**.
  Avaliar mover o JS para um único `_tokenizer.js` na pasta `media` da coleção e referenciar
  com `<script src="_tokenizer.js">` (Anki carrega arquivos `_*` da media) — elimina a duplicação.

## Fase 3 — Automação na área de trabalho (criar + adicionar sozinho)

**Meta:** pedir um card/baralho rapidamente e ele já cria **e adiciona ao Anki** sem passos manuais.

- **AnkiConnect** (addon, API HTTP em `localhost:8765`): adicionar notas direto no Anki aberto
  (`addNotes`), enviar áudio (`storeMediaFile`), criar decks (`createDeck`). Substitui o
  "gerar .apkg + importar". Manter `.apkg` como fallback quando o Anki estiver fechado.
- **Disparo rápido (Windows):**
  - Atalho na área de trabalho + `prompt` (PowerShell `InputBox`) pedindo o tópico → roda o agente.
  - **Hotkey global** (AutoHotkey) para abrir o prompt de qualquer lugar.
  - Opcional: app de bandeja (system tray) leve.
- **Fluxo alvo:** `Win+atalho → digita tópico → agente gera → AnkiConnect adiciona → notificação`.
- **Pré-requisito:** instalar e detectar AnkiConnect; tratar Anki fechado (fallback `.apkg`).

## Fase 4 — GRAND FINALE: agente com acesso ao progresso de aprendizado

**Meta:** o agente lê o histórico de estudo, foca nos pontos fracos, tira dúvidas e adapta.

- **Fonte de dados:** coleção do Anki (SQLite `collection.anki2`: tabelas `cards`, `revlog`, `notes`).
  Ler preferencialmente via **AnkiConnect** (`findCards`, `cardsInfo`, `getReviews`) para evitar
  lock do banco com o Anki aberto.
- **Funcionalidades:**
  - **Diagnóstico de fraquezas:** cards com mais `lapses`/menor `factor`, decks com baixa retenção
    (query tipo `prop:lapses>3`). Relatório por tema/tag.
  - **Geração adaptativa:** criar cards extras reforçando exatamente os temas onde erra mais.
  - **Tutor/dúvidas:** chat sobre um card específico — explicar, dar mais exemplos, reformular.
  - **Acompanhamento:** evolução ao longo do tempo (revisões, acertos), metas e sugestões.
- **Arquitetura:** considerar migrar para **AnkiConnect-first**; agente vira serviço local que
  conversa com Anki + Ollama. Tudo local possível (privacidade).
- **Pontos a decidir:** modelo padrão (cloud p/ qualidade vs local p/ privacidade do histórico),
  formato dos relatórios, frequência de análise.

---

## Ordem sugerida de execução
1. Fase 3 (AnkiConnect) primeiro — destrava automação e é base para Fases 1 e 4.
2. Fase 1 (inglês + TTS) — alto valor imediato.
3. Fase 2 (bash/PS + refatorar tokenizer) — incremental.
4. Fase 4 (tutor adaptativo) — depende de AnkiConnect e de histórico acumulado.

## Decisões em aberto para a próxima sessão
- [ ] edge-tts (online, melhor voz) vs Piper (offline) como padrão?
- [ ] Sotaque inglês padrão: US ou UK?
- [ ] AnkiConnect-first ou manter `.apkg` como caminho principal?
- [ ] Hotkey global (AutoHotkey) ou só atalho com InputBox?
- [ ] Modelo padrão para a Fase 4 (cloud vs local, por causa do histórico pessoal).

## Dependências novas previstas
`edge-tts` (ou `piper-tts`), AnkiConnect (addon Anki), opcional AutoHotkey.
