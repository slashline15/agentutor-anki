"""
ollama_worker.py — despacha uma tarefa de código para um modelo Ollama e salva
a resposta em arquivo. Peça de orquestração: o Claude (ou você) define a
especificação num arquivo de prompt; o modelo cloud faz o trabalho pesado.

Uso:
  python tools/ollama_worker.py --model kimi-k2.7-code:cloud \
      --prompt-file spec.txt --out tests/test_x.py [--system-file sys.txt]

A resposta é limpa de cercas markdown (```...```) antes de salvar.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from anki_toolkit.llm import DEFAULT_HOST, OllamaError, call_ollama  # noqa: E402

RETRIES = 4  # o gateway cloud do Ollama devolve 502 esporádico sob paralelismo
RETRY_WAIT = 20  # segundos entre tentativas

DEFAULT_SYSTEM = (
    "Você é um engenheiro de software sênior. Responda SOMENTE com o conteúdo "
    "do arquivo pedido — sem explicações antes ou depois, sem cerca markdown."
)


def strip_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        first_nl = t.find("\n")
        if first_nl != -1:
            t = t[first_nl + 1:]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--system-file", help="Prompt de sistema (padrão embutido).")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--temperature", type=float, default=0.2)
    args = ap.parse_args()

    system = (Path(args.system_file).read_text(encoding="utf-8")
              if args.system_file else DEFAULT_SYSTEM)
    user = Path(args.prompt_file).read_text(encoding="utf-8")

    t0 = time.time()
    print(f"[worker] {args.model} <- {args.prompt_file}", flush=True)
    raw = ""
    for attempt in range(1, RETRIES + 1):
        try:
            raw = call_ollama(args.host, args.model, system, user,
                              args.timeout, temperature=args.temperature, fmt=None)
            if raw.strip():
                break
            print(f"[worker] tentativa {attempt}: resposta vazia.", flush=True)
        except OllamaError as e:
            print(f"[worker] tentativa {attempt}: {e}", flush=True)
        if attempt < RETRIES:
            time.sleep(RETRY_WAIT * attempt)
    if not raw.strip():
        sys.exit(f"[worker] {args.model}: sem resposta após {RETRIES} tentativas.")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(strip_fences(raw), encoding="utf-8")
    print(f"[worker] {args.model} -> {out}  "
          f"({len(raw)} chars, {time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
