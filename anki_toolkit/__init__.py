"""
anki_toolkit — núcleo compartilhado do gerador de flashcards.

Módulos:
  models  -> note types genanki (IDs fixos — nunca alterar)
  llm     -> cliente Ollama (chat JSON) e extração tolerante de JSON
  outputs -> conversão de cards, TSV, APKG e JSON intermediário (schema 1)

Os scripts da raiz (card_agent.py, build_apkg.py, rebuild_from_json.py) são
invólucros finos sobre este pacote; a interface de linha de comando não muda.
"""

SCHEMA_VERSION = 1
