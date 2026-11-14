#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Converte os documentos Markdown de docs/ em .docx (Word), incluindo tabelas e imagens.

Uso (a partir da pasta docs/):
    ../backend/.venv/bin/python gerar_docx.py
Requer python-docx (instalado pelo backend/requirements.txt).

Suporta o subconjunto de Markdown usado nos documentos: títulos (#, ##, ###),
parágrafos com **negrito**, *itálico* e `código`, listas (- e 1.), tabelas,
imagens ![legenda](caminho), blocos de código ``` e separadores ---.
Blocos <details> (fontes Mermaid) são omitidos.
"""
import os
import re
import sys

from docx import Document
from docx.enum.section import WD_ORIENT  # noqa: F401
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

AQUI = os.path.dirname(os.path.abspath(__file__))
DOCUMENTOS = ["01_documento_requisitos.md", "02_modelagem.md", "03_protocolo.md", "04_relatorio_tecnico.md",
              "05_plano_verificacao_testes.md"]

FONTE = "Calibri"
FONTE_CODIGO = "Consolas"
AZUL = RGBColor(0x1F, 0x4E, 0x8C)
CINZA = RGBColor(0x52, 0x51, 0x4E)
LARGURA_UTIL = Cm(16)  # A4 com margens de 2,5 cm

INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*|\[[^\]]+\]\([^)]+\))")


def configurar_estilos(doc):
    secao = doc.sections[0]
    secao.page_height, secao.page_width = Cm(29.7), Cm(21.0)
    for margem in ("left_margin", "right_margin"):
        setattr(secao, margem, Cm(2.5))
    secao.top_margin = secao.bottom_margin = Cm(2.2)

    normal = doc.styles["Normal"]
    normal.font.name = FONTE
    normal.font.size = Pt(11)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONTE)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    for nome, tamanho, antes, depois in (("Title", 22, 0, 6), ("Heading 1", 16, 18, 8),
                                        ("Heading 2", 13, 14, 6), ("Heading 3", 11.5, 10, 4)):
        estilo = doc.styles[nome]
        estilo.font.name = FONTE
        estilo.font.size = Pt(tamanho)
        estilo.font.bold = True
        estilo.font.color.rgb = AZUL
        estilo.element.rPr.rFonts.set(qn("w:eastAsia"), FONTE)
        estilo.element.rPr.rFonts.set(qn("w:ascii"), FONTE)
        estilo.element.rPr.rFonts.set(qn("w:hAnsi"), FONTE)
        estilo.paragraph_format.space_before = Pt(antes)
        estilo.paragraph_format.space_after = Pt(depois)
        estilo.paragraph_format.keep_with_next = True


def adicionar_inline(paragrafo, texto, tamanho=None, negrito=False):
    texto = texto.replace("\\|", "|")
    for parte in INLINE.split(texto):
        if not parte:
            continue
        if parte.startswith("**") and parte.endswith("**"):
            run = paragrafo.add_run(parte[2:-2])
            run.bold = True
        elif parte.startswith("`") and parte.endswith("`"):
            run = paragrafo.add_run(parte[1:-1])
            run.font.name = FONTE_CODIGO
            run.font.color.rgb = RGBColor(0x8A, 0x2B, 0x0E)
        elif parte.startswith("[") and "](" in parte:
            run = paragrafo.add_run(parte[1:parte.index("](")])
            run.underline = True
        elif parte.startswith("*") and parte.endswith("*") and len(parte) > 2:
            run = paragrafo.add_run(parte[1:-1])
            run.italic = True
        else:
            run = paragrafo.add_run(parte)
        if negrito:
            run.bold = True
        if tamanho:
            run.font.size = Pt(tamanho)


def sombrear(celula, cor_hex):
    tc_pr = celula._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), cor_hex)
    tc_pr.append(shd)


def adicionar_tabela(doc, linhas):
    celulas = [[c.strip() for c in re.split(r"(?<!\\)\|", l.strip().strip("|"))] for l in linhas]
    cabecalho, corpo = celulas[0], [c for c in celulas[2:]]
    n = len(cabecalho)
    tabela = doc.add_table(rows=1 + len(corpo), cols=n)
    tabela.style = "Table Grid"
    tabela.alignment = WD_TABLE_ALIGNMENT.CENTER
    tamanho = 9 if n >= 6 else 9.5
    for j, texto in enumerate(cabecalho):
        cel = tabela.rows[0].cells[j]
        sombrear(cel, "DCE6F2")
        p = cel.paragraphs[0]
        adicionar_inline(p, texto, tamanho, negrito=True)
    for i, linha in enumerate(corpo, start=1):
        for j in range(n):
            texto = linha[j] if j < len(linha) else ""
            p = tabela.rows[i].cells[j].paragraphs[0]
            adicionar_inline(p, texto, tamanho)
    # repete o cabeçalho em quebras de página
    tr_pr = tabela.rows[0]._tr.get_or_add_trPr()
    repetir = OxmlElement("w:tblHeader")
    repetir.set(qn("w:val"), "true")
    tr_pr.append(repetir)
    for linha in tabela.rows:
        for cel in linha.cells:
            for p in cel.paragraphs:
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.line_spacing = 1.0
    doc.add_paragraph()


def adicionar_imagem(doc, legenda, caminho, base):
    arquivo = os.path.normpath(os.path.join(base, caminho))
    if not os.path.exists(arquivo):
        doc.add_paragraph(f"[imagem não encontrada: {caminho}]")
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(arquivo, width=LARGURA_UTIL)
    leg = doc.add_paragraph()
    leg.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = leg.add_run(f"Figura — {legenda}")
    run.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = CINZA


def adicionar_codigo(doc, linhas):
    for linha in linhas:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.left_indent = Cm(0.5)
        run = p.add_run(linha if linha else " ")
        run.font.name = FONTE_CODIGO
        run.font.size = Pt(8.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def converter(md_path, docx_path):
    base = os.path.dirname(md_path)
    with open(md_path, encoding="utf-8") as f:
        linhas = f.read().splitlines()

    doc = Document()
    configurar_estilos(doc)
    i, primeiro_titulo = 0, True
    while i < len(linhas):
        linha = linhas[i]
        s = linha.strip()

        if s.startswith("<details"):
            while i < len(linhas) and "</details>" not in linhas[i]:
                i += 1
            i += 1
            continue
        if s.startswith("```"):
            bloco = []
            i += 1
            while i < len(linhas) and not linhas[i].strip().startswith("```"):
                bloco.append(linhas[i])
                i += 1
            adicionar_codigo(doc, bloco)
            i += 1
            continue
        if s.startswith("|"):
            bloco = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                bloco.append(linhas[i])
                i += 1
            adicionar_tabela(doc, bloco)
            continue
        if not s or s == "---":
            i += 1
            continue

        m = re.match(r"^(#{1,3})\s+(.*)$", s)
        if m:
            nivel, texto = len(m.group(1)), m.group(2)
            if primeiro_titulo and nivel == 1:
                p = doc.add_paragraph(style="Title")
                adicionar_inline(p, texto)
                primeiro_titulo = False
            else:
                p = doc.add_paragraph(style=f"Heading {nivel}")
                adicionar_inline(p, texto)
            i += 1
            continue

        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", s)
        if m:
            adicionar_imagem(doc, m.group(1), m.group(2), base)
            i += 1
            continue

        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", linha)
        if m:
            recuo = len(m.group(1)) // 2
            estilo = "List Number" if m.group(2)[0].isdigit() else "List Bullet"
            if recuo:
                estilo += " 2"
            p = doc.add_paragraph(style=estilo)
            p.paragraph_format.space_after = Pt(2)
            adicionar_inline(p, m.group(3))
            i += 1
            continue

        # parágrafo comum: junta linhas consecutivas
        partes = [s]
        i += 1
        while i < len(linhas):
            prox = linhas[i].strip()
            if (not prox or prox.startswith(("#", "|", "```", "<details", "![")) or prox == "---"
                    or re.match(r"^([-*]|\d+\.)\s", prox)):
                break
            partes.append(prox)
            i += 1
        p = doc.add_paragraph()
        for k, parte in enumerate(partes):
            adicionar_inline(p, parte)
            if k < len(partes) - 1:
                p.add_run().add_break()

    doc.save(docx_path)
    print(f"[OK] {docx_path}")


def main(argv):
    nomes = argv or DOCUMENTOS
    for nome in nomes:
        caminho = os.path.join(AQUI, nome)
        converter(caminho, os.path.splitext(caminho)[0] + ".docx")


if __name__ == "__main__":
    main(sys.argv[1:])
