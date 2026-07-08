from anki_toolkit.ingest import decide_route, make_frontmatter, split_sections, MIN_CHARS_PER_PAGE


def test_decide_route_lista_vazia_retorna_scanned():
    assert decide_route([]) == "scanned"


def test_decide_route_textos_longos_retorna_digital():
    textos = ["x" * 500 for _ in range(3)]
    assert decide_route(textos) == "digital"


def test_decide_route_textos_curtos_retorna_scanned():
    textos = ["curto", "", "pequeno"]
    assert decide_route(textos) == "scanned"


def test_decide_route_media_com_texto_longo_e_vazios_retorna_digital():
    textos = ["x" * 2000, "", "", ""]
    assert decide_route(textos) == "digital"


def test_decide_route_tolerancia_a_none():
    textos = [None, "algum texto", None]
    assert decide_route(textos) == "scanned"


def test_decide_route_limite_exato():
    textos = ["x" * MIN_CHARS_PER_PAGE]
    assert decide_route(textos) == "digital"


def test_make_frontmatter_formato_basico():
    fm = make_frontmatter("Meu Título", "/caminho/doc.pdf", 42, "digital")
    assert fm.startswith("---\n")
    assert "\n---\n\n" in fm
    assert fm.endswith("---\n\n")
    assert 'title: "Meu Título"' in fm
    assert 'source: "/caminho/doc.pdf"' in fm
    assert "pages: 42" in fm
    assert "route: digital" in fm
    assert "tipo: material" in fm
    assert "ingested:" in fm


def test_split_sections_texto_vazio_retorna_vazio():
    assert split_sections("") == []
    assert split_sections(None) == []


def test_split_sections_texto_menor_que_limite_retorna_inalterado():
    texto = "Texto curto sem divisão."
    assert split_sections(texto, limit=100) == [texto]


def test_split_sections_divide_por_titulos_respeitando_limite():
    texto = "# A\n" + "a " * 30 + "\n## B\n" + "b " * 30 + "\n## C\n" + "c " * 30
    pedacos = split_sections(texto, limit=100)
    assert all(len(p) <= 100 for p in pedacos)
    assert all(p.strip() for p in pedacos)
    assert any("# A" in p for p in pedacos)
    assert any("## B" in p for p in pedacos)
    assert any("## C" in p for p in pedacos)


def test_split_sections_linha_unica_gigante_corta_seco():
    texto = "x" * 350
    pedacos = split_sections(texto, limit=100)
    assert all(len(p) <= 100 for p in pedacos)
    assert "".join(pedacos) == texto
    assert all(p.strip() for p in pedacos)


def test_split_sections_gigante_com_paragrafos_corta_nos_paragrafos():
    paragrafos = [" ".join([f"palavra{i}" for i in range(10)]) for _ in range(10)]
    texto = "\n\n".join(paragrafos)
    pedacos = split_sections(texto, limit=100)
    assert all(len(p) <= 100 for p in pedacos)
    assert all(p.strip() for p in pedacos)
    juncao = " ".join(pedacos)
    for palavra in {p for par in paragrafos for p in par.split()}:
        assert palavra in juncao


def test_split_sections_preserva_todas_as_palavras():
    palavras = ["alfa", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"]
    texto = " ".join(palavras)
    pedacos = split_sections(texto, limit=20)
    juncao = " ".join(pedacos)
    for palavra in palavras:
        assert palavra in juncao


def test_split_sections_titulos_e_paragrafos_respeitam_limite():
    linhas = [
        "# Introdução",
        "Este é um parágrafo introdutório com várias palavras.",
        "",
        "## Seção 1",
        "Outro parágrafo com conteúdo suficiente para testar.",
        "",
        "## Seção 2",
        "Mais texto para garantir a divisão correta dos pedaços.",
    ]
    texto = "\n".join(linhas)
    pedacos = split_sections(texto, limit=80)
    assert all(len(p) <= 80 for p in pedacos)
    assert all(p.strip() for p in pedacos)
    assert any("# Introdução" in p for p in pedacos)
    assert any("## Seção 1" in p for p in pedacos)
    assert any("## Seção 2" in p for p in pedacos)
