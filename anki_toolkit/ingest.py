"""
Ingestão de documentos (PDF -> markdown limpo, pronto para virar cards).

Três rotas, com seleção automática:
  digital -> PDF com texto embutido: docling direto (rápido, sem OCR)
  scanned -> PDF escaneado/longo: docling + OCR em lotes de páginas (GPU se
             houver; os lotes evitam o std::bad_alloc do backend C++ em
             documentos longos — diagnóstico herdado de ~/scripts/ocr_ext.py)
  ollama  -> fallback sem docling/GPU: renderiza cada página (pymupdf) e pede
             transcrição a um modelo multimodal do Ollama

As dependências pesadas (docling, torch, pypdf, pymupdf) são importadas de
forma preguiçosa DENTRO das funções: importar este módulo não exige nada além
do core. Instale com:  pip install -r requirements-ingest.txt
"""
import base64
from datetime import datetime
from pathlib import Path

from . import llm
from .outputs import slugify

BASE = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY = BASE / "library"

# Detecção de rota: média mínima de caracteres de texto embutido por página
# para considerar o PDF "digital" (abaixo disso, tratamos como escaneado)
MIN_CHARS_PER_PAGE = 200
SAMPLE_PAGES = 8

BATCH_SIZE = 8          # páginas por lote na rota scanned
OLLAMA_OCR_MODEL = "gemma4:12b"  # multimodal local; troque por um :cloud se quiser

OCR_PAGE_PROMPT = (
    "Você está lendo UMA página escaneada de um documento em português.\n"
    "TAREFA: transcreva o conteúdo desta página em markdown limpo.\n"
    "REGRAS:\n"
    "- Retorne SOMENTE o markdown, sem comentários nem introduções\n"
    "- Use títulos (#, ##) quando a página tiver cabeçalhos evidentes\n"
    "- Corrija erros óbvios de digitalização (letras trocadas, palavras coladas)\n"
    "- Preserve números, unidades, fórmulas e termos técnicos\n"
    "- Palavras ilegíveis: mantenha como estão, não invente"
)


class IngestError(RuntimeError):
    """Falha de ingestão (dependência ausente, PDF ilegível...)."""


# ----------------------------------------------------------------------------- lógica pura
def decide_route(page_texts):
    """Decide digital/scanned a partir do texto embutido de páginas amostradas."""
    texts = [t or "" for t in page_texts]
    if not texts:
        return "scanned"
    avg = sum(len(t.strip()) for t in texts) / len(texts)
    return "digital" if avg >= MIN_CHARS_PER_PAGE else "scanned"


def make_frontmatter(title, source, pages, route):
    """Frontmatter YAML dos .md ingeridos (metadados de origem)."""
    return (
        "---\n"
        f"title: \"{title}\"\n"
        f"source: \"{source}\"\n"
        f"pages: {pages}\n"
        f"route: {route}\n"
        f"ingested: {datetime.now().isoformat(timespec='seconds')}\n"
        "tipo: material\n"
        "---\n\n"
    )


def split_sections(md_text, limit=12000):
    """Divide markdown em pedaços de até `limit` chars, cortando em títulos.

    Seções maiores que o limite são divididas por parágrafos. Usado pelo
    card_agent para gerar cards de materiais grandes em múltiplas chamadas.
    """
    text = (md_text or "").strip()
    if len(text) <= limit:
        return [text] if text else []

    # quebra preferencial: linhas de título markdown
    sections, current = [], []
    for line in text.split("\n"):
        if line.lstrip().startswith("#") and current:
            sections.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current))

    # agrupa seções consecutivas até o limite; estoura -> corta por parágrafos
    chunks, buf = [], ""
    for sec in sections:
        while len(sec) > limit:  # seção sozinha maior que o limite
            if buf:
                chunks.append(buf)
                buf = ""
            # preferência de corte: parágrafo > linha > espaço > corte seco
            cut = sec.rfind("\n\n", 0, limit)
            if cut < limit // 4:
                cut = sec.rfind("\n", 0, limit)
            if cut < limit // 4:
                cut = sec.rfind(" ", 0, limit)
            if cut < limit // 4:
                cut = limit
            chunks.append(sec[:cut].strip())
            sec = sec[cut:].strip()
        if buf and len(buf) + len(sec) + 1 > limit:
            chunks.append(buf)
            buf = sec
        else:
            buf = (buf + "\n" + sec) if buf else sec
    if buf:
        chunks.append(buf)
    return [c for c in (c.strip() for c in chunks) if c]


# ----------------------------------------------------------------------------- rotas
def detect_route(pdf_path):
    """Amostra páginas com pypdf e decide digital/scanned."""
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise IngestError(
            "Dependências de ingestão ausentes. Rode: "
            "pip install -r requirements-ingest.txt") from e
    reader = PdfReader(str(pdf_path))
    n = len(reader.pages)
    step = max(1, n // SAMPLE_PAGES)
    texts = []
    for i in list(range(0, n, step))[:SAMPLE_PAGES]:
        try:
            texts.append(reader.pages[i].extract_text() or "")
        except Exception:
            texts.append("")
    return decide_route(texts), n


def convert_digital(pdf_path):
    """PDF com texto embutido -> markdown via docling, com OCR DESLIGADO
    (é o que distingue esta rota: usa só o texto que o PDF já tem)."""
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except ImportError as e:
        raise IngestError(
            "docling não instalado. Rode: pip install -r requirements-ingest.txt") from e
    opts = PdfPipelineOptions()
    opts.do_ocr = False
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    result = converter.convert(source=str(pdf_path))
    return result.document.export_to_markdown()


def convert_scanned(pdf_path, batch_size=BATCH_SIZE, progress=print):
    """PDF escaneado -> markdown via docling + OCR, em lotes de páginas.

    GPU (CUDA) se o torch enxergar; os lotes liberam a RAM do backend entre
    conversões (sem eles, documentos longos estouram com std::bad_alloc).
    """
    try:
        import gc

        import torch
        from pypdf import PdfReader

        from docling.datamodel.accelerator_options import (
            AcceleratorDevice, AcceleratorOptions)
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            EasyOcrOptions, PdfPipelineOptions, TableFormerMode)
        from docling.datamodel.settings import settings
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except ImportError as e:
        raise IngestError(
            "docling/torch não instalados. Rode: "
            "pip install -r requirements-ingest.txt") from e

    use_cuda = torch.cuda.is_available()
    device = AcceleratorDevice.CUDA if use_cuda else AcceleratorDevice.CPU
    progress(f"[ingest] OCR em {'GPU (CUDA)' if use_cuda else 'CPU (lento)'}")

    opts = PdfPipelineOptions()
    opts.accelerator_options = AcceleratorOptions(device=device, num_threads=8)
    opts.do_ocr = True
    opts.ocr_options = EasyOcrOptions(lang=["pt", "en"], use_gpu=use_cuda)
    opts.do_table_structure = True
    opts.table_structure_options.mode = TableFormerMode.ACCURATE
    opts.generate_page_images = False
    opts.generate_picture_images = False

    settings.perf.page_batch_size = 4
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})

    total = len(PdfReader(str(pdf_path)).pages)
    parts = []
    for start in range(1, total + 1, batch_size):
        end = min(start + batch_size - 1, total)
        try:
            result = converter.convert(str(pdf_path), page_range=(start, end))
            parts.append(result.document.export_to_markdown())
            progress(f"[ingest] páginas {start}-{end}/{total} OK")
        except Exception as e:
            progress(f"[ingest] falha nas páginas {start}-{end}: {e} (pulando)")
        finally:
            result = None
            gc.collect()
            if use_cuda:
                torch.cuda.empty_cache()
    if not parts:
        raise IngestError("Nenhuma página pôde ser convertida.")
    return "\n\n".join(parts)


def convert_ollama(pdf_path, model=OLLAMA_OCR_MODEL, host=llm.DEFAULT_HOST,
                   progress=print, timeout=300):
    """Fallback sem docling: renderiza páginas (pymupdf) e transcreve com um
    modelo multimodal do Ollama."""
    try:
        import fitz  # pymupdf
    except ImportError as e:
        raise IngestError(
            "pymupdf não instalado. Rode: pip install -r requirements-ingest.txt") from e

    doc = fitz.open(str(pdf_path))
    parts = []
    for i, page in enumerate(doc, start=1):
        png = page.get_pixmap(dpi=150).tobytes("png")
        img_b64 = base64.b64encode(png).decode("ascii")
        try:
            text = llm.call_ollama(host, model, None, OCR_PAGE_PROMPT,
                                   timeout, temperature=0.1, fmt=None,
                                   images=[img_b64])
            parts.append(text.strip())
            progress(f"[ingest] página {i}/{len(doc)} OK ({model})")
        except llm.OllamaError as e:
            progress(f"[ingest] página {i}: {e} (pulando)")
    doc.close()
    if not parts:
        raise IngestError("Nenhuma página pôde ser transcrita via Ollama.")
    return "\n\n".join(parts)


# ----------------------------------------------------------------------------- entrada única
def ingest(pdf_path, out_dir=None, route="auto", progress=print, **route_kwargs):
    """Converte 1 PDF em <out_dir>/<slug>.md com frontmatter. Retorna o Path."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise IngestError(f"Arquivo não encontrado: {pdf_path}")

    pages = None
    if route == "auto":
        route, pages = detect_route(pdf_path)
        progress(f"[ingest] rota automática: {route} ({pages} páginas)")

    if route == "digital":
        md = convert_digital(pdf_path)
    elif route == "scanned":
        md = convert_scanned(pdf_path, progress=progress, **route_kwargs)
    elif route == "ollama":
        md = convert_ollama(pdf_path, progress=progress, **route_kwargs)
    else:
        raise IngestError(f"Rota desconhecida: {route}")

    if pages is None:
        try:
            from pypdf import PdfReader
            pages = len(PdfReader(str(pdf_path)).pages)
        except Exception:
            pages = 0

    out_dir = Path(out_dir) if out_dir else DEFAULT_LIBRARY
    out_dir.mkdir(parents=True, exist_ok=True)
    title = pdf_path.stem.replace("-", " ").replace("_", " ").strip()
    out_path = out_dir / f"{slugify(pdf_path.stem)}.md"
    out_path.write_text(
        make_frontmatter(title, pdf_path.name, pages, route) + md.strip() + "\n",
        encoding="utf-8")
    return out_path
