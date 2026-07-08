"""
Cliente Ollama (endpoint /api/chat) e extração tolerante de JSON.

Diferente dos scripts antigos, este módulo NÃO chama sys.exit: erros viram
exceções (OllamaError / ValueError) e quem decide encerrar é o script de CLI.
"""
import json
import time
import urllib.error
import urllib.request

DEFAULT_MODEL = "gpt-oss:120b-cloud"
DEFAULT_HOST = "http://localhost:11434"

RETRIES = 3       # o gateway dos modelos :cloud devolve 502 esporádico
RETRY_WAIT = 10   # segundos entre tentativas


class OllamaError(RuntimeError):
    """Falha de comunicação com o servidor Ollama."""


def call_ollama(host, model, system, user, timeout, temperature=0.4, fmt="json",
                images=None):
    """Chama /api/chat; retorna o texto da resposta.

    fmt="json" força resposta JSON (uso do card_agent); fmt=None deixa o
    modelo responder texto/código livre. system=None omite o prompt de
    sistema. images = lista de PNGs em base64 para modelos multimodais
    (usado pela rota ollama da ingestão de PDFs).
    """
    user_msg = {"role": "user", "content": user}
    if images:
        user_msg["images"] = list(images)
    messages = [{"role": "system", "content": system}] if system else []
    messages.append(user_msg)
    body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": temperature},
    }
    if fmt:
        body["format"] = fmt
    data = json.dumps(body).encode("utf-8")
    last_err = None
    for attempt in range(1, RETRIES + 1):
        req = urllib.request.Request(
            host.rstrip("/") + "/api/chat", data=data,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                resp = json.loads(r.read().decode("utf-8"))
            return resp.get("message", {}).get("content", "")
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code < 500 or attempt == RETRIES:  # 4xx não adianta repetir
                break
            time.sleep(RETRY_WAIT)
        except urllib.error.URLError as e:
            last_err = e
            break  # servidor fora do ar: repetir não resolve
    raise OllamaError(
        f"Não consegui falar com o Ollama em {host}: {last_err}\n"
        f"Verifique se o servidor está ativo (ollama serve) e o modelo existe."
    ) from last_err


def extract_json(text):
    """Extrai o primeiro objeto JSON do texto; tolera lixo em volta.

    Levanta ValueError se não houver JSON válido.
    """
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e != -1 and e > s:
        try:
            return json.loads(text[s:e + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError(
        "O modelo não retornou JSON válido. Início da resposta:\n" + text[:600])
