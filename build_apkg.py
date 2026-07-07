"""
Gera 'python-templates.apkg' com os note types e alguns cards de exemplo.
Usa as definições centrais de anki_models.py (mesmos IDs do agente).

Uso:  .venv\\Scripts\\python.exe build_apkg.py
"""
from pathlib import Path
import genanki
import anki_models

BASE = Path(__file__).resolve().parent
models = anki_models.build_models()
deck = genanki.Deck(anki_models.DECK_DEFAULT, "Python (Templates)")

# Terminal (Cloze) ------------------------------------------------------------
for front, back in [
    ("def soma(a, b):\n    return {{c1::a + b}}",
     "Retorna a soma de <code>a</code> e <code>b</code>."),
    ("for i in {{c1::range(5)}}:\n    print(i)",
     "<code>range(5)</code> gera os números de 0 a 4."),
    ("nums = [1, 2, 3]\ntotal = {{c1::sum(nums)}}  # 6",
     "<code>sum()</code> soma os itens de um iterável."),
]:
    deck.add_note(genanki.Note(model=models["code_cloze"],
                               fields=[front.replace("\n", "<br>"), back]))

# Digite o Código -------------------------------------------------------------
for pergunta, codigo, notas in [
    ("Crie uma lista com os quadrados de 0 a 4 usando list comprehension.",
     "[x**2 for x in range(5)]", "Resultado: <code>[0, 1, 4, 9, 16]</code>."),
    ("Abra o arquivo 'dados.txt' em modo leitura, atribuindo a variável f.",
     "f = open('dados.txt', 'r')", "Prefira <code>with open(...) as f:</code> na prática."),
]:
    deck.add_note(genanki.Note(model=models["code_write"],
                               fields=[pergunta, codigo.replace("\n", "<br>"), notas]))

# Digite a Saída --------------------------------------------------------------
for codigo, saida, notas in [
    ("print(2 ** 10)", "1024", "<code>**</code> é o operador de potência."),
    ("print('ab' * 3)", "ababab", "Multiplicar string repete o conteúdo."),
    ("print(len('python'))", "6", "<code>len()</code> conta os caracteres."),
]:
    deck.add_note(genanki.Note(model=models["code_output"],
                               fields=[codigo.replace("\n", "<br>"), saida, notas]))

# Geral — Básico (Q&A) --------------------------------------------------------
deck.add_note(genanki.Note(model=models["qa"], fields=[
    "Qual estrutura de dados Python é imutável e ordenada?",
    "A tupla (<code>tuple</code>).",
    "Listas são mutáveis; tuplas não podem ser alteradas após criadas."]))

# Geral — Cloze ---------------------------------------------------------------
deck.add_note(genanki.Note(model=models["cloze"], fields=[
    "Em Python, o método {{c1::.append()}} adiciona um item ao {{c2::final}} de uma lista.",
    ""]))

out_path = BASE / "python-templates.apkg"
genanki.Package(deck).write_to_file(str(out_path))
print(f"OK -> {out_path}  ({len(deck.notes)} cards)")
