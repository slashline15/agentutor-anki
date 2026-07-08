"""
Integração com o Obsidian por sistema de arquivos — um vault é só uma pasta
de .md, então escrever arquivos lá É a integração (sem plugin, sem API, nada
que quebre com atualização do Obsidian).

O caminho do vault fica em config.json na raiz do projeto. Na primeira vez,
é autodetectado no registro do Obsidian (%APPDATA%/obsidian/obsidian.json):
vale o vault aberto; empate, o de uso mais recente.

Estrutura criada dentro do vault (subpasta configurável, padrão "Estudos"):
  Estudos/Materiais/  .md ingeridos de PDFs (ingest.py --vault)
  Estudos/Baralhos/   uma nota por baralho gerado (card_agent.py --vault)
  Estudos/Revisões/   reservado para os relatórios do tutor (Fase 6)
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE / "config.json"
DEFAULT_SUBDIR = "Estudos"


class VaultError(RuntimeError):
    """Vault não configurado/encontrado. NÃO derruba o fluxo principal."""


# ----------------------------------------------------------------------------- puras
def parse_vault_registry(text):
    """JSON do registro do Obsidian -> [(path, ts, aberto)], abertos primeiro,
    depois por uso mais recente."""
    try:
        data = json.loads(text or "{}")
    except json.JSONDecodeError:
        return []
    vaults = []
    for v in (data.get("vaults") or {}).values():
        path = v.get("path")
        if path:
            vaults.append((path, int(v.get("ts", 0)), bool(v.get("open"))))
    vaults.sort(key=lambda x: (not x[2], -x[1]))
    return vaults


def safe_filename(name):
    """Nome de deck -> nome de arquivo seguro no Windows e no Obsidian."""
    s = re.sub(r'[\\/:*?"<>|#^\[\]]+', "-", str(name or "").strip())
    s = re.sub(r"\s+", " ", s).strip(" -.")
    return s or "sem-nome"


def html_to_md(s):
    """Campos dos cards guardam quebras como <br>; volta para \n na nota."""
    return str(s or "").replace("<br>", "\n").strip()


def _render_card(i, tipo, fields):
    f = [html_to_md(x) for x in fields] + ["", "", ""]
    lines = [f"### {i}. `{tipo}`", ""]
    if tipo == "qa":
        lines += [f"**P:** {f[0]}", "", f"**R:** {f[1]}"]
        extra = f[2]
    elif tipo == "cloze":
        lines += [f[0]]
        extra = f[1]
    elif tipo == "code_write":
        lines += [f"**Enunciado:** {f[0]}", "", "```", f[1], "```"]
        extra = f[2]
    elif tipo == "code_output":
        lines += ["```", f[0], "```", "", f"**Saída:** `{f[1]}`"]
        extra = f[2]
    elif tipo == "code_cloze":
        lines += ["```", f[0], "```"]
        extra = f[1]
    else:  # tipo futuro: mostra os campos crus, não quebra
        lines += [x for x in f if x]
        extra = ""
    if extra:
        lines += ["", f"> {extra}"]
    return "\n".join(lines)


def render_deck_note(deck_name, model, tags, cards, source_stem=None, now=None):
    """Nota de estudo (markdown) de um baralho gerado. `cards` no formato do
    JSON do projeto: [{"type": t, "fields": [...]}]."""
    now = now or datetime.now().isoformat(timespec="seconds")
    tags_yaml = ", ".join(str(t) for t in tags)
    head = [
        "---",
        "tipo: baralho",
        f"deck: \"{deck_name}\"",
        f"modelo: \"{model}\"",
        f"tags: [{tags_yaml}]",
        f"cards: {len(cards)}",
        f"gerado: {now}",
        "---",
        "",
        f"# {deck_name}",
        "",
    ]
    if source_stem:
        head += [f"Fonte: [[{source_stem}]]", ""]
    head += [f"## Cards ({len(cards)})", ""]
    body = "\n\n".join(
        _render_card(i, c.get("type", "?"), c.get("fields", []))
        for i, c in enumerate(cards, 1))
    return "\n".join(head) + body + "\n"


# ----------------------------------------------------------------------------- config e IO
def load_config(path=CONFIG_PATH):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(cfg, path=CONFIG_PATH):
    Path(path).write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def registry_path():
    return Path(os.environ.get("APPDATA", "")) / "obsidian" / "obsidian.json"


def get_vault_root(config_path=CONFIG_PATH, auto_save=True):
    """Vault do config.json; sem config, autodetecta no registro do Obsidian
    (e salva a escolha para as próximas execuções)."""
    cfg = load_config(config_path)
    if cfg.get("vault"):
        root = Path(cfg["vault"])
        if not root.exists():
            raise VaultError(
                f"O vault configurado não existe: {root}. Ajuste config.json.")
        return root

    reg = registry_path()
    if not reg.exists():
        raise VaultError(
            "Obsidian não encontrado e config.json sem 'vault'. Crie "
            'config.json na raiz com {"vault": "C:\\\\caminho\\\\do\\\\vault"}.')
    candidates = [
        (p, ts, op) for p, ts, op in
        parse_vault_registry(reg.read_text(encoding="utf-8"))
        if Path(p).exists()]
    if not candidates:
        raise VaultError("Nenhum vault válido no registro do Obsidian.")
    root = Path(candidates[0][0])
    if auto_save:
        cfg["vault"] = str(root)
        cfg.setdefault("vault_subdir", DEFAULT_SUBDIR)
        save_config(cfg, config_path)
    return root


def _study_dir(kind, config_path=CONFIG_PATH):
    root = get_vault_root(config_path)
    sub = load_config(config_path).get("vault_subdir", DEFAULT_SUBDIR)
    d = root / sub / kind
    d.mkdir(parents=True, exist_ok=True)
    return d


def materials_dir(config_path=CONFIG_PATH):
    """Pasta de materiais ingeridos (destino do ingest.py --vault)."""
    return _study_dir("Materiais", config_path)


def write_deck_note(deck_name, model, tags, cards, source_stem=None,
                    config_path=CONFIG_PATH):
    """Grava a nota de estudo do baralho no vault. Retorna o Path."""
    path = _study_dir("Baralhos", config_path) / f"{safe_filename(deck_name)}.md"
    path.write_text(
        render_deck_note(deck_name, model, tags, cards, source_stem),
        encoding="utf-8")
    return path
