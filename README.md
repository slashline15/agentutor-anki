# Templates Anki — Python (terminal + digitar e comparar)

Três note types com tema de terminal escuro (One Dark), realce de sintaxe Python
robusto e comparação de digitação **nativa** do Anki.

```
anki-python-templates/
├─ styling-comum.css        ← cole na aba "Styling" dos 3 note types
├─ 1-terminal-cloze/        ← seu template antigo, corrigido (Cloze)
├─ 2-digite-codigo/         ← NOVO: digite o código e compare (Basic)
└─ 3-digite-saida/          ← NOVO: digite a saída (output) e compare (Basic)
```

## O que foi corrigido no template original

| Problema antigo | Correção |
|---|---|
| `DOMContentLoaded` não dispara no Anki → realce/linhas não rodavam | Script roda imediatamente (com fallback) |
| Regex `{{c1::...}}` nunca casava (Anki já virou HTML) | Realce via `TreeWalker` preservando os `.cloze` |
| Realce sobre `innerHTML` destacava dentro de strings/tags | Tokenizador linear que escapa HTML e nunca entra em string/comentário |
| Diff custom redundante e frágil | Usa a comparação **nativa** `{{type:}}` do Anki (`.typeGood/.typeBad/.typeMissed`) |
| Auto-fechamento de `()` atrapalhava a comparação exata | Removido |
| Numeração com fundo azul alternado | Gutter discreto |

## Como instalar (vale para os 3)

1. Anki → **Ferramentas → Gerenciar tipos de nota → Adicionar**.
   - Template 1: baseie em **Cloze**.
   - Templates 2 e 3: baseie em **Básico (digite a resposta)**.
2. Selecione o note type → **Cartões…**.
3. Cole **Front Template** ← `front.html`, **Back Template** ← `back.html`,
   **Styling** ← `styling-comum.css`.

### Campos de cada note type
- **1) Terminal Cloze** → `Front` (código com `{{c1::...}}`), `Back` (explicação, opcional).
- **2) Digite o Código** → `Pergunta`, `Codigo` (resposta), `Notas` (opcional).
- **3) Digite a Saída** → `Codigo` (mostrado), `Saida` (resposta), `Notas` (opcional).

> Em 2 e 3, renomeie os campos do "Básico" exatamente para esses nomes,
> ou ajuste os `{{...}}` nos templates.

## Sobre o `{{type:...}}` (digitar e comparar)
A comparação é **literal**, caractere a caractere — ótima para respostas curtas e
exatas (uma linha, um nome, um output). Para blocos grandes de código fica chato
(qualquer espaço diferente acusa erro). Por isso o **template 1 (cloze)** é o ideal
para trechos longos, e os **2/3** para respostas pontuais.

**Dica:** no campo da resposta, use **uma linha**. Se precisar de várias, ative
em *Opções do tipo de nota* a comparação ignorando quebras, ou prefira o cloze.
