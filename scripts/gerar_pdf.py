from __future__ import annotations

import html
import json
import subprocess
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "MEE120-Diurno-cronograma.pdf"
NODE = Path(
    r"C:\Users\Gabriel\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\node\bin\node.exe"
)

MESES = {8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez"}


def carregar_conteudos() -> dict:
    codigo = (
        "global.window={}; require('./conteudos.js'); "
        "process.stdout.write(JSON.stringify(window.conteudosAulas));"
    )
    resultado = subprocess.run(
        [str(NODE), "-e", codigo],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(resultado.stdout)


def data_curta(data_iso: str) -> str:
    data = datetime.strptime(data_iso, "%Y-%m-%d")
    return f"{data.day:02d}/{MESES[data.month]}"


def titulo(conteudo: dict) -> str:
    valor = conteudo.get("titulo") or conteudo.get("nome") or "Conteúdo"
    return " + ".join(valor) if isinstance(valor, list) else valor


def detalhes(conteudo: dict) -> str:
    itens = conteudo.get("itens") or []
    if not itens:
        return html.escape(conteudo.get("conteudo", ""))

    linhas = []
    for item in itens:
        capitulo = html.escape(item.get("capitulo", ""))
        pagina = html.escape(item.get("pagina", ""))
        assunto = html.escape(item.get("conteudo", ""))
        prefixo = f"<b>{capitulo}</b> - " if capitulo else ""
        sufixo = f" (p. {pagina})" if pagina and pagina != "[EXP]" else ""
        marcador = " <b>[Experimento]</b>" if capitulo == "[EXP]" else ""
        linhas.append(prefixo + assunto + sufixo + marcador)
    return "<br/>".join(linhas)


def montar_agenda(conteudos: dict) -> tuple[list, list]:
    laboratorio = []
    teoria = []

    for data_iso, conteudo in conteudos.items():
        dia_semana = datetime.strptime(data_iso, "%Y-%m-%d").weekday()
        if dia_semana == 1:
            laboratorio.append((data_iso, conteudo))
        elif dia_semana == 3:
            teoria.append((data_iso, conteudo))

    return sorted(laboratorio), sorted(teoria)


def gerar_pdf() -> None:
    conteudos = carregar_conteudos()
    laboratorio, teoria = montar_agenda(conteudos)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    estilos = getSampleStyleSheet()
    azul = colors.HexColor("#1F4E79")
    azul_claro = colors.HexColor("#DCE6F1")
    cinza = colors.HexColor("#F4F6F8")

    estilos.add(ParagraphStyle(
        name="CapaTitulo",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=27,
        leading=32,
        textColor=azul,
        alignment=TA_CENTER,
        spaceAfter=8 * mm,
    ))
    estilos.add(ParagraphStyle(
        name="Secao",
        parent=estilos["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=azul,
        spaceAfter=3 * mm,
    ))
    estilos.add(ParagraphStyle(
        name="Celula",
        parent=estilos["BodyText"],
        fontSize=7.8,
        leading=9.5,
    ))
    estilos.add(ParagraphStyle(
        name="CelulaTitulo",
        parent=estilos["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=9.5,
        textColor=colors.HexColor("#163A5B"),
    ))
    estilos.add(ParagraphStyle(
        name="Cabecalho",
        parent=estilos["CelulaTitulo"],
        textColor=colors.white,
    ))

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=landscape(A4),
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="MEE120-Diurno - Cronograma 2026",
        author="MEE120",
    )

    historia = [
        Spacer(1, 28 * mm),
        Paragraph("MEE120-Diurno", estilos["CapaTitulo"]),
        Paragraph("Cronograma estático - 2º semestre de 2026", estilos["Heading2"]),
        Spacer(1, 15 * mm),
    ]

    resumo = [
        [Paragraph("Atividade", estilos["Cabecalho"]), Paragraph("Quando", estilos["Cabecalho"])],
        ["Laboratório", "Terças-feiras"],
        ["Teoria", "Quintas-feiras"],
        ["Avaliações", "P1: 22/set a 3/out | P2: 19/nov e 21/nov a 1/dez | P3: 7 a 15/dez"],
    ]
    tabela_resumo = Table(resumo, colWidths=[70 * mm, 135 * mm])
    tabela_resumo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), azul),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), cinza),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C6D1")),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    historia.extend([tabela_resumo, PageBreak()])

    def tabela_agenda(nome: str, subtitulo: str, agenda: list) -> list:
        elementos = [
            Paragraph(nome, estilos["Secao"]),
            Paragraph(subtitulo, estilos["BodyText"]),
            Spacer(1, 2 * mm),
        ]
        linhas = [[
            Paragraph("Data", estilos["Cabecalho"]),
            Paragraph("Tema", estilos["Cabecalho"]),
            Paragraph("Conteúdos, capítulos e páginas", estilos["Cabecalho"]),
        ]]
        for data_iso, conteudo in agenda:
            linhas.append([
                Paragraph(data_curta(data_iso), estilos["CelulaTitulo"]),
                Paragraph(html.escape(titulo(conteudo)), estilos["CelulaTitulo"]),
                Paragraph(detalhes(conteudo), estilos["Celula"]),
            ])

        tabela = Table(linhas, colWidths=[20 * mm, 58 * mm, 175 * mm], repeatRows=1)
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), azul),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, azul_claro]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C6D1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elementos.append(tabela)
        return elementos

    historia.extend(tabela_agenda("Teoria", "Aulas às quintas-feiras.", teoria))
    historia.append(PageBreak())
    historia.extend(tabela_agenda("Laboratório", "Aulas às terças-feiras.", laboratorio))

    def rodape(canvas, documento):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#66727A"))
        canvas.drawString(14 * mm, 8 * mm, "MEE120-Diurno - 2º semestre de 2026")
        canvas.drawRightString(landscape(A4)[0] - 14 * mm, 8 * mm, f"Página {documento.page}")
        canvas.restoreState()

    doc.build(historia, onFirstPage=rodape, onLaterPages=rodape)
    print(OUTPUT)


if __name__ == "__main__":
    gerar_pdf()
