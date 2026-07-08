"""
Síntese de voz para os cards de vocabulário (Fase 4).

Motores:
  edge  -> edge-tts (padrão): vozes neurais da Microsoft, grátis, sem chave,
           precisa de internet. Voz padrão en-US-AriaNeural (troque com --voice).
  piper -> 100% offline (pacote piper-tts + modelo de voz .onnx baixado à
           parte). Alternativa para quando não há internet.

Regra do projeto: áudio NUNCA derruba a geração de cards — quem chama trata
TTSError e segue sem áudio, avisando.

O nome do arquivo é determinístico por (texto, voz): gerar o mesmo card duas
vezes reusa o mesmo mp3 na media do Anki em vez de duplicar.
"""
import asyncio
import zlib
from pathlib import Path

DEFAULT_VOICE = "en-US-AriaNeural"
DEFAULT_ENGINE = "edge"


class TTSError(RuntimeError):
    """Falha de síntese (sem internet, motor ausente...)."""


def media_filename(text, voice=DEFAULT_VOICE):
    """Nome determinístico do mp3 na media do Anki."""
    key = f"{voice}|{text}".encode("utf-8")
    return f"anki-vocab-{zlib.crc32(key):08x}.mp3"


def _synth_edge(text, out_path, voice):
    # usa o repositório de certificados do WINDOWS (truststore) antes de
    # importar o edge_tts: com antivírus/proxy interceptando TLS, o certifi
    # puro rejeita a conexão com speech.platform.bing.com
    try:
        import truststore
        truststore.inject_into_ssl()
    except ImportError:
        pass
    try:
        import edge_tts
    except ImportError as e:
        raise TTSError("edge-tts não instalado (pip install edge-tts).") from e

    async def _run():
        await edge_tts.Communicate(text, voice).save(str(out_path))

    try:
        asyncio.run(_run())
    except Exception as e:  # rede fora, voz inexistente...
        raise TTSError(f"edge-tts falhou ({voice}): {e}") from e


def _synth_piper(text, out_path, voice):
    try:
        from piper import PiperVoice  # noqa: F401
    except ImportError as e:
        raise TTSError(
            "piper-tts não instalado (pip install piper-tts + modelo .onnx). "
            "Sem internet e sem piper, os cards saem sem áudio.") from e
    # voice aqui é o caminho do modelo .onnx
    import wave

    from piper import PiperVoice
    model = PiperVoice.load(voice)
    with wave.open(str(out_path), "wb") as w:
        model.synthesize(text, w)


def synthesize(text, out_dir, voice=DEFAULT_VOICE, engine=DEFAULT_ENGINE):
    """Gera o áudio de `text` em out_dir; retorna (Path, nome do arquivo).

    Se o arquivo já existe (mesmo texto+voz), não sintetiza de novo.
    """
    text = " ".join(str(text or "").split())
    if not text:
        raise TTSError("Texto vazio.")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = media_filename(text, voice)
    path = out_dir / name
    if path.exists() and path.stat().st_size > 0:
        return path, name

    if engine == "edge":
        _synth_edge(text, path, voice)
    elif engine == "piper":
        _synth_piper(text, path, voice)
    else:
        raise TTSError(f"Motor de TTS desconhecido: {engine}")

    if not path.exists() or path.stat().st_size == 0:
        raise TTSError(f"{engine} não produziu áudio para: {text[:60]}")
    return path, name


def vocab_tts_text(term, example=""):
    """O que narrar num card de vocabulário: o termo e, se houver, a frase."""
    term = str(term or "").strip()
    example = str(example or "").strip()
    return f"{term}. {example}" if example else term
