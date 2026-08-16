#!/usr/bin/env python3
"""Gera as medidas DAX que devolvem HTML para o visual HTML Content (lite)."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

TMDL = Path("powerbi/sm_lh_nautical.SemanticModel/definition/tables/_Medidas.tmdl")

AZUL, LARANJA, ROXO = "#2D9CDB", "#D9772A", "#8B7AE8"
TEXTO, SUAVE, FRACO = "#E8EEF4", "#93A5B8", "#6F8299"
TRILHO, BORDA = "#16233A", "#1E2E42"
FONTE = "Segoe UI,-apple-system,Roboto,sans-serif"

Q = '""'          # aspa dupla dentro de string DAX


def s(texto: str) -> str:
    """Envelopa em literal DAX, escapando aspas."""
    return '"' + texto.replace('"', Q) + '"'


def guid(semente: str) -> str:
    h = hashlib.sha1(f"lh_nautical::{semente}".encode()).hexdigest()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def bloco(nome: str, corpo: list[str], doc: list[str]) -> str:
    linhas = [("\t/// " + d).rstrip() for d in doc]
    linhas.append(f"\tmeasure '{nome}' =")
    linhas += ["\t\t\t" + c for c in corpo]
    linhas += ["\t\tdisplayFolder: 0 HTML", f"\t\tlineageTag: {guid('med:' + nome)}", ""]
    return "\r\n".join(linhas) + "\r\n"


# ─────────────────────────────────────────────────────────── faixa de KPIs ──
CAIXA = (f"flex:1;min-width:0;background:#12203366;border:1px solid {BORDA};"
         "border-radius:14px;padding:14px 16px;")
ROTULO = (f"font-size:10px;letter-spacing:.10em;text-transform:uppercase;"
          f"color:{SUAVE};font-weight:600;white-space:nowrap;")
NOTA = f"font-size:11px;color:{FRACO};margin-top:8px;white-space:nowrap;"


def num(cor: str) -> str:
    return (f"font-size:30px;line-height:1.1;font-weight:200;color:{cor};"
            "margin-top:10px;white-space:nowrap;")


def cartao(rotulo: str, valor: str, nota: str, cor: str = TEXTO,
           barra: str | None = None) -> list[str]:
    saida = [
        f'& {s(f"<div style={chr(34)}{CAIXA}{chr(34)}>")}',
        f'& {s(f"<div style={chr(34)}{ROTULO}{chr(34)}>{rotulo}</div>")}',
        f'& {s(f"<div style={chr(34)}{num(cor)}{chr(34)}>")} & {valor} & {s("</div>")}',
    ]
    if barra:
        t = f"height:3px;background:{TRILHO};border-radius:2px;margin-top:12px;overflow:hidden;"
        f = f"height:3px;border-radius:2px;background:linear-gradient(90deg,{AZUL},{ROXO});width:"
        saida.append(
            f'& {s(f"<div style={chr(34)}{t}{chr(34)}><div style={chr(34)}{f}")}'
            f' & {barra} & {s(f"%{chr(34)}></div></div>")}'
        )
    saida += [
        f'& {s(f"<div style={chr(34)}{NOTA}{chr(34)}>")} & {nota} & {s("</div>")}',
        f'& {s("</div>")}',
    ]
    return saida


faixa = [
    "VAR _Bruta     = [Receita Bruta]",
    "VAR _Efetivada = [Receita Efetivada]",
    "VAR _Pct       = DIVIDE(_Efetivada, _Bruta)",
    "RETURN",
    f'    {s(f"<div style={chr(34)}display:flex;gap:10px;font-family:{FONTE};{chr(34)}>")}',
]
faixa += cartao("Receita Bruta", 'FORMAT(_Bruta / 1000000, "R$ #,##0") & " Mi"',
                s("GMV — todos os status"))
faixa += cartao("Receita Efetivada", 'FORMAT(_Efetivada / 1000000, "R$ #,##0") & " Mi"',
                'FORMAT(_Pct, "0.0%") & " do GMV virou receita"', AZUL,
                barra='FORMAT(_Pct * 100, "0")')
faixa += cartao("Pedidos", 'FORMAT([Nº Pedidos], "#,##0")', s("2020 a 2026"))
faixa += cartao("Ticket Médio", 'FORMAT([Ticket Médio], "R$ #,##0.00")',
                s("a resposta da Questão 1"))
faixa += cartao("Margem Líquida", 'FORMAT([% Margem Líquida], "0.00%")',
                s("já líquida de desconto"), LARANJA)
faixa.append(f'& {s("</div>")}')

DOC_FAIXA = [
    'FAIXA DE KPIs — para o visual "HTML Content (lite)".',
    "",
    "Os cinco indicadores da capa num bloco HTML: número em peso 200,",
    "rótulo em versalete espaçado, barra de proporção na receita efetivada e",
    "uma linha de contexto por indicador, que o cartão nativo não comporta.",
    "",
    "REAGE AOS FILTROS como qualquer medida: trocar o status no segmentador",
    "reescreve os cinco números e a largura da barra.",
    "",
    "CSS INLINE POR OBRIGAÇÃO, não por gosto — o visual roda num iframe com",
    "apenas `allow-scripts`, que bloqueia toda tag <script> externa. Nenhum",
    "CDN carrega ali: nem Tailwind, nem fonte do Google.",
]


# ────────────────────────────────────────────────────────────────── ranking ──
LINHA = f"display:flex;align-items:center;gap:10px;padding:7px 2px;border-bottom:1px solid {BORDA};"
POS = f"width:18px;font-size:11px;color:{FRACO};text-align:right;flex:none;"
NOME = (f"width:148px;font-size:12px;color:{TEXTO};overflow:hidden;"
        "text-overflow:ellipsis;white-space:nowrap;flex:none;")
TRI = f"flex:1;height:8px;background:{TRILHO};border-radius:4px;overflow:hidden;min-width:30px;"
RODAPE = f"font-size:11px;color:{FRACO};margin-top:10px;"
VAL = f"width:78px;text-align:right;font-size:12px;color:{SUAVE};flex:none;"


def ranking(tabela: str, coluna: str, med: str, fmt: str, n: int,
            cor: str, rodape: str) -> list[str]:
    topn = f"TOPN({n}, VALUES({tabela}[{coluna}]), {med}, DESC)"
    barra = (f"height:8px;border-radius:4px;"
             f"background:linear-gradient(90deg,{cor},{cor}66);width:")
    return [
        f"VAR _Top = {topn}",
        f"VAR _Max = MAXX(_Top, {med})",
        "VAR _Corpo =",
        "    CONCATENATEX(",
        "        _Top,",
        f"        VAR _V = {med}",
        f"        VAR _P = RANKX(_Top, {med},, DESC)",
        "        VAR _L = DIVIDE(_V, _Max) * 100",
        "        RETURN",
        f"            {s(f'<div style={chr(34)}{LINHA}{chr(34)}>')}",
        f"          & {s(f'<div style={chr(34)}{POS}{chr(34)}>')} & _P & {s('</div>')}",
        f"          & {s(f'<div style={chr(34)}{NOME}{chr(34)}>')}"
        f" & {tabela}[{coluna}] & {s('</div>')}",
        f"          & {s(f'<div style={chr(34)}{TRI}{chr(34)}><div style={chr(34)}{barra}')}"
        f" & FORMAT(_L, \"0.0\") & {s(f'%{chr(34)}></div></div>')}",
        f"          & {s(f'<div style={chr(34)}{VAL}{chr(34)}>')}"
        f" & FORMAT(_V, {s(fmt)}) & {s('</div>')}",
        f"          & {s('</div>')},",
        f"        \"\", {med}, DESC",
        "    )",
        "RETURN",
        f'    {s(f"<div style={chr(34)}font-family:{FONTE};{chr(34)}>")} & _Corpo'
        f' & {s(f"<div style={chr(34)}{RODAPE}{chr(34)}>{rodape}</div></div>")}',
    ]


blocos = [
    bloco("HTML — Faixa de KPIs", faixa, DOC_FAIXA),
    bloco(
        "HTML — Top Produtos por Margem",
        ranking("dim_produto", "produto", "[% Margem Líquida]", "0.00%", 10, LARANJA,
                "Percentual sobre a receita de itens, líquido do desconto rateado."),
        ["TOP 10 PRODUTOS POR MARGEM — visual HTML.",
         "",
         "A barra é proporcional ao MAIOR DA LISTA, não a 100%: as margens vão",
         "de 37% a 53%, e num eixo de 0 a 100 nada se distinguiria. O valor",
         "absoluto vai no rótulo, então a escala relativa não engana ninguém."],
    ),
    bloco(
        "HTML — Top Similares Q7",
        ranking("fct_similaridade_produto", "produto", "[Similaridade de Cosseno]",
                "0.0000", 10, AZUL,
                "Cosseno sobre a matriz cliente x produto. O 1o ganha do 2o por 0,0003."),
        ["RANKING DA QUESTÃO 7 — visual HTML.",
         "",
         "Quatro casas decimais de propósito: o 1º lugar ganha do 2º por",
         "0,0003, e arredondar para duas casas empataria os três primeiros —",
         "que é exatamente o argumento da resposta."],
    ),
]

with open(TMDL, encoding="utf-8", newline="") as fh:
    texto = fh.read()
# IDEMPOTENTE: remove os blocos já gravados antes de inserir. Sem isto, rodar o
# script duas vezes deixa duas cópias de cada medida — e o TMDL aceita, porque
# a segunda simplesmente sobrescreve a primeira na hora de carregar.
for _nome in ("HTML — Faixa de KPIs", "HTML — Top Produtos por Margem",
              "HTML — Top Similares Q7"):
    texto = re.sub(
        r"\t///[^\r\n]*(?:\r\n\t///[^\r\n]*)*\r\n\tmeasure '" + re.escape(_nome)
        + r"' =(?:\r\n(?!\t///|\tmeasure |\tcolumn |\tpartition )[^\r\n]*)*\r\n\r\n",
        "", texto)

ancora = "\t/// As 207 unidades efetivamente vendidas"
assert texto.count(ancora) == 1, "âncora não encontrada"
with open(TMDL, "w", encoding="utf-8", newline="") as fh:
    fh.write(texto.replace(ancora, "".join(blocos) + ancora))
print(f"{len(blocos)} medidas HTML gravadas")
