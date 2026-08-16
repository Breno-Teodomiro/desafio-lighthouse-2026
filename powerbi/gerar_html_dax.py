#!/usr/bin/env python3
"""
Gera os componentes HTML do dashboard: medidas DAX + visuais PBIR.

    python3 powerbi/gerar_html_dax.py

Tudo o que é HTML no relatório sai daqui — a medida que emite o markup e o
`visual.json` que a consome. Os dois no mesmo arquivo porque não fazem sentido
separados: um visual sem a medida renderiza vazio, e uma medida sem o visual é
texto que ninguém lê.

POR QUE UM GERADOR, E NÃO DAX ESCRITO À MÃO
-------------------------------------------
Em DAX, aspa dupla dentro de string se escapa dobrando (""). Um HTML com
dezenas de atributos vira um campo minado onde um `"` a mais quebra a medida, e
o erro do Desktop não aponta a coluna. Aqui o escape acontece uma vez, em `s()`.

OS TRÊS TIPOS, E QUANDO CADA UM SERVE
-------------------------------------
· FAIXA   — cartões de indicador lado a lado. Forma BLOCO.
· RANKING — lista com barra proporcional, uma ou duas séries. Forma LINHA.
· SÉRIE   — linha do tempo em SVG, com área em gradiente. Forma BLOCO.

FORMA BLOCO × FORMA LINHA — a diferença decide a interatividade
--------------------------------------------------------------
· BLOCO: a medida devolve o componente inteiro. O visual recebe UMA linha, e um
  dataset de uma linha tem um ponto de seleção só — o componente todo. Não há
  o que clicar, e para uma faixa de KPIs ou uma série de 75 meses está certo.

· LINHA: a medida devolve UMA linha da lista, e a coluna de granularidade entra
  no papel `sampling`. O visual cria um selectionId por linha e o clique
  CROSS-FILTRA a página. A regra está em `src/view-model.ts` do visual:

      const hasGranularity   = columns.some((c) => c.roles?.sampling);
      const hasCrossFiltering = hasGranularity && settings.crossFilter.enabled;

  Sem campo em `sampling`, a opção de cross-filter nem aparece no painel.

O TOP N SEM FILTRO DE VISUAL
----------------------------
A medida de linha devolve BLANK() fora do corte. O Power BI descarta a linha
cujas medidas são todas vazias, então a lista se limita sozinha — sem
`filterConfig`, que não tem uma única ocorrência nos projetos PBIR desta
máquina.

SVG É PERMITIDO, <script> NÃO
-----------------------------
A edição certificada sanitiza o HTML contra uma allowlist que inclui `svg`,
`path`, `polyline`, `polygon`, `lineargradient` e `text` (ver
`visual-constants.ts` do visual), mas bloqueia toda tag `<script>` e todo
carregamento externo. Por isso as séries são SVG inline, e por isso não há
Tailwind: nenhum CDN carrega dentro do iframe.

Autor: Breno Teodomiro · Desafio Técnico Lighthouse 2026 (Indicium)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path

RAIZ = Path("powerbi")
TMDL = RAIZ / "sm_lh_nautical.SemanticModel/definition/tables/_Medidas.tmdl"
PAGES = RAIZ / "rel_lh_nautical.Report/definition/pages"
GUID = "htmlContent443BE3AD55E043BF878BED274D3A6865"

AZUL, LARANJA, ROXO = "#2D9CDB", "#D9772A", "#8B7AE8"
TEXTO, SUAVE, FRACO = "#E8EEF4", "#93A5B8", "#6F8299"
TRILHO, BORDA, CARTAO = "#16233A", "#1E2E42", "#0E1826"
FONTE = "Segoe UI,-apple-system,Roboto,sans-serif"

Q = '""'
A = chr(34)


def s(t: str) -> str:
    """Literal DAX, com a aspa dupla escapada por duplicação."""
    return '"' + t.replace('"', Q) + '"'


def guid(semente: str) -> str:
    h = hashlib.sha1(f"lh_nautical::{semente}".encode()).hexdigest()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def id_curto(semente: str) -> str:
    return hashlib.sha1(f"lh_nautical::{semente}".encode()).hexdigest()[:20]


def bloco_tmdl(nome: str, corpo: list[str], doc: list[str]) -> str:
    linhas = [("\t/// " + d).rstrip() for d in doc]
    linhas.append(f"\tmeasure '{nome}' =")
    linhas += ["\t\t\t" + c for c in corpo]
    linhas += ["\t\tdisplayFolder: 0 HTML",
               f"\t\tlineageTag: {guid('med:' + nome)}", ""]
    return "\r\n".join(linhas) + "\r\n"


# ══════════════════════════════════════════════════════ tipo FAIXA (bloco) ══
CAIXA = (f"flex:1;min-width:0;background:#12203366;border:1px solid {BORDA};"
         "border-radius:14px;padding:14px 16px;")
ROTULO = ("font-size:10px;letter-spacing:.10em;text-transform:uppercase;"
          f"color:{SUAVE};font-weight:600;white-space:nowrap;")
NOTA = f"font-size:11px;color:{FRACO};margin-top:8px;white-space:nowrap;"


def _num(cor: str, tam: int) -> str:
    return (f"font-size:{tam}px;line-height:1.1;font-weight:200;color:{cor};"
            "margin-top:10px;white-space:nowrap;")


def faixa(itens: list[tuple], tam: int = 30, coluna: bool = False) -> list[str]:
    """`itens` = [(rótulo, expr valor, expr nota, cor, expr barra|None)]."""
    direcao = "column" if coluna else "row"
    # Sem recuo na primeira linha: no TMDL ela define a indentação base do
    # bloco de expressão, e as seguintes começam com "&" sem recuo. Recuar só
    # a primeira deixa todas as outras abaixo dela — e o parser recusa o
    # arquivo inteiro com "Invalid indentation".
    saida = [f'{s(f"<div style={A}display:flex;flex-direction:{direcao};"
                  f"gap:10px;font-family:{FONTE};{A}>")}']
    for rotulo, valor, nota, cor, barra in itens:
        saida += [
            f'& {s(f"<div style={A}{CAIXA}{A}>")}',
            f'& {s(f"<div style={A}{ROTULO}{A}>{rotulo}</div>")}',
            f'& {s(f"<div style={A}{_num(cor, tam)}{A}>")} & {valor} & {s("</div>")}',
        ]
        if barra:
            t = (f"height:3px;background:{TRILHO};border-radius:2px;"
                 "margin-top:12px;overflow:hidden;")
            f = (f"height:3px;border-radius:2px;"
                 f"background:linear-gradient(90deg,{AZUL},{ROXO});width:")
            saida.append(f'& {s(f"<div style={A}{t}{A}><div style={A}{f}")}'
                         f' & {barra} & {s(f"%{A}></div></div>")}')
        saida += [
            f'& {s(f"<div style={A}{NOTA}{A}>")} & {nota} & {s("</div>")}',
            f'& {s("</div>")}',
        ]
    saida.append(f'& {s("</div>")}')
    return saida


# ═════════════════════════════════════════════════════ tipo RANKING (linha) ══
LINHA = ("display:flex;align-items:center;gap:9px;padding:2px 2px;"
         f"font-family:{FONTE};")
ESPACO_ENTRE_BARRAS = "margin-top:3px;"
POS = f"width:18px;font-size:11px;color:{FRACO};text-align:right;flex:none;"


def _nome(larg: int) -> str:
    return (f"width:{larg}px;font-size:12px;color:{TEXTO};overflow:hidden;"
            "text-overflow:ellipsis;white-space:nowrap;flex:none;")


def _val(larg: int) -> str:
    return (f"width:{larg}px;text-align:right;font-size:12px;color:{SUAVE};"
            "flex:none;line-height:1.35;")


def _tri(alt: int, extra: str = "") -> str:
    return (f"flex:1;height:{alt}px;background:{TRILHO};"
            f"border-radius:{alt // 2}px;overflow:hidden;min-width:26px;{extra}")


def _barra(cor: str, alt: int) -> str:
    return (f"height:{alt}px;border-radius:{alt // 2}px;"
            f"background:linear-gradient(90deg,{cor},{cor}66);width:")


def ranking(tabela: str, coluna: str, med: str, fmt: str, n: int, cor: str,
            larg_nome: int = 150, ordem: str = "valor", larg_val: int = 78,
            med2: str | None = None, fmt2: str | None = None,
            cor2: str = LARANJA) -> list[str]:
    """Uma linha da lista. A coluna vai no papel `sampling` do visual.

    `ordem="natural"` mantém a ordem da própria coluna (dias da semana, anos) e
    dispensa o número de posição; `ordem="valor"` ranqueia e numera.
    """
    escopo = f"ALLSELECTED({tabela}[{coluna}])"
    corpo = [f"VAR _V   = {med}"]
    if med2:
        corpo.append(f"VAR _V2  = {med2}")
    corpo.append(f"VAR _Max = MAXX(TOPN({n}, {escopo}, {med}, DESC), {med})")
    if med2:
        corpo.append(f"VAR _Max2 = MAXX(TOPN({n}, {escopo}, {med2}, DESC), {med2})")
    if ordem == "natural":
        corpo.append("VAR _Dentro = NOT ISBLANK(_V)")
    else:
        corpo += [f"VAR _Pos = RANKX({escopo}, {med},, DESC)",
                  f"VAR _Dentro = _Pos <= {n}"]
    corpo += ["RETURN", "    IF(", "        _Dentro,",
              f"        {s(f'<div style={A}{LINHA}{A}>')}"]
    if ordem != "natural":
        corpo.append(f"      & {s(f'<div style={A}{POS}{A}>')} & _Pos & {s('</div>')}")
    corpo += [
        f"      & {s(f'<div style={A}{_nome(larg_nome)}{A}>')}",
        f"      & SELECTEDVALUE({tabela}[{coluna}]) & {s('</div>')}",
    ]
    if med2:
        # duas séries empilhadas: a comparação é entre as DUAS da mesma linha,
        # não entre linhas, então elas dividem o mesmo eixo horizontal
        corpo += [
            f"      & {s(f'<div style={A}flex:1;min-width:40px;{A}>')}",
            f"      & {s(f'<div style={A}{_tri(7)}{A}><div style={A}{_barra(cor, 7)}')}",
            '      & FORMAT(DIVIDE(_V, _Max) * 100, "0.0")',
            f"      & {s(f'%{A}></div></div>')}",
            f"      & {s(f'<div style={A}{_tri(7, ESPACO_ENTRE_BARRAS)}{A}>'
                        f'<div style={A}{_barra(cor2, 7)}')}",
            '      & FORMAT(DIVIDE(_V2, _Max2) * 100, "0.0")',
            f"      & {s(f'%{A}></div></div></div>')}",
            f"      & {s(f'<div style={A}{_val(larg_val)}{A}>')} & FORMAT(_V, {s(fmt)})",
            f"      & {s(f'<br><span style={A}color:{cor2};{A}>')}"
            f" & FORMAT(_V2, {s(fmt2 or fmt)}) & {s('</span></div>')}",
        ]
    else:
        corpo += [
            f"      & {s(f'<div style={A}{_tri(8)}{A}><div style={A}{_barra(cor, 8)}')}",
            '      & FORMAT(DIVIDE(_V, _Max) * 100, "0.0")',
            f"      & {s(f'%{A}></div></div>')}",
            f"      & {s(f'<div style={A}{_val(larg_val)}{A}>')}"
            f" & FORMAT(_V, {s(fmt)}) & {s('</div>')}",
        ]
    corpo += [f"      & {s('</div>')}", "    )"]
    return corpo


# ═══════════════════════════════════════════════════════ tipo SÉRIE (bloco) ══
def serie(tabela: str, coluna: str, series: list[tuple[str, str]],
          altura: int = 96, base_zero: bool = True) -> list[str]:
    """Linha do tempo em SVG. `series` = [(expressão da medida, cor)].

    O eixo X é o índice do período e o `preserveAspectRatio=none` estica o
    desenho para a largura do visual — 84 meses cabem sem barra de rolagem,
    que era o defeito do gráfico nativo nestes lugares.
    """
    corpo = [
        f"VAR _Base = ALLSELECTED({tabela}[{coluna}])",
        "VAR _T =",
        "    ADDCOLUMNS(",
        "        _Base,",
        # Índice do mês a partir do próprio rótulo "AAAA-MM". RANKX sobre
        # texto não deu ordem estável e a série saiu embaralhada — os pontos
        # do polyline vinham fora de sequência.
        f'        "@i", VALUE(LEFT({tabela}[{coluna}], 4)) * 12'
        f' + VALUE(MID({tabela}[{coluna}], 6, 2)),',
    ]
    for k, (med, _) in enumerate(series, 1):
        corpo.append(f'        "@v{k}", {med},')
    corpo[-1] = corpo[-1].rstrip(",")
    corpo += [
        "    )",
        "VAR _Ini = MINX(_T, [@i])",
        "VAR _N   = MAXX(_T, [@i]) - _Ini",
    ]
    # o teto é o MAIOR VALOR de qualquer série, não a soma delas — somar
    # comprimia o desenho à metade da altura quando havia duas linhas
    teto = "MAXX(_T, [@v1])"
    for k in range(2, len(series) + 1):
        teto = f"MAX({teto}, MAXX(_T, [@v{k}]))"
    if base_zero:
        corpo += [f"VAR _Max = {teto}", "VAR _Min = 0"]
    else:
        # Série de variação estreita (margem de 40% a 42%): num eixo que
        # começa em zero ela vira uma reta. Aqui o eixo é o próprio intervalo
        # dos dados, com 12% de folga — e sem área preenchida, que sugeriria
        # uma base em zero que não existe.
        piso = "MINX(_T, [@v1])"
        for k in range(2, len(series) + 1):
            piso = f"MIN({piso}, MINX(_T, [@v{k}]))"
        corpo += [f"VAR _Teto = {teto}", f"VAR _Piso = {piso}",
                  "VAR _Folga = (_Teto - _Piso) * 0.12",
                  "VAR _Max = _Teto + _Folga", "VAR _Min = _Piso - _Folga"]
    for k in range(1, len(series) + 1):
        corpo += [
            f"VAR _P{k} =",
            "    CONCATENATEX(",
            f"        FILTER(_T, NOT ISBLANK([@v{k}])),",
            f'        FORMAT([@i] - _Ini, "0") & "," & '
            f'FORMAT({altura} - DIVIDE([@v{k}] - _Min, _Max - _Min) * {altura - 6}, "0.00"),',
            '        " ", [@i], ASC',
            "    )",
        ]
    grad = (f"<defs><lineargradient id={A}lhg{A} x1={A}0{A} y1={A}0{A} "
            f"x2={A}0{A} y2={A}1{A}>"
            f"<stop offset={A}0%{A} stop-color={A}{series[0][1]}{A} "
            f"stop-opacity={A}.45{A}></stop>"
            f"<stop offset={A}100%{A} stop-color={A}{series[0][1]}{A} "
            f"stop-opacity={A}0{A}></stop></lineargradient></defs>")
    corpo += [
        "RETURN",
        f'    {s(f"<div style={A}font-family:{FONTE};{A}>")}',
        f'  & {s(f"<svg viewBox={A}0 0 ")} & _N & {s(f" {altura}{A} "
                                                     f"preserveAspectRatio={A}none{A} "
                                                     f"style={A}width:100%;"
                                                     f"height:{altura}px;display:block;{A}>")}',
        f"  & {s(grad)}",
    ]
    if base_zero:
        corpo.append(
            f'  & {s(f"<polygon fill={A}url(#lhg){A} points={A}0,{altura} ")}'
            f' & _P1 & {s(" ")} & _N & {s(f",{altura}{A}></polygon>")}')
    for k, (_, cor) in enumerate(series, 1):
        corpo.append(
            f'  & {s(f"<polyline fill={A}none{A} stroke={A}{cor}{A} "
                     f"stroke-width={A}1.6{A} vector-effect={A}non-scaling-stroke{A} "
                     f"stroke-linejoin={A}round{A} stroke-linecap={A}round{A} "
                     f"points={A}")}'
            f" & _P{k} & {s(f'{A}></polyline>')}"
        )
    corpo.append(f'  & {s("</svg></div>")}')
    return corpo


# ═════════════════════════════════════════════════════════════ componentes ══
DOC_CROSS = [
    "",
    "FORMA LINHA — devolve UMA linha, e a coluna de granularidade entra no",
    "papel `sampling` do visual. É isso que dá cross-filter: o visual cria um",
    "selectionId por linha, e clicar filtra a página como um gráfico nativo.",
]
DOC_BLOCO = [
    "",
    "FORMA BLOCO — devolve o componente inteiro, então o visual recebe uma",
    "linha só e não emite filtro. Recebe filtro normalmente.",
]

# Medida pela qual cada lista é ordenada NA TELA. As de ordem natural — dias
# da semana e anos — ficam de fora de propósito: ali a sequência correta é a
# da própria coluna, e o `sortByColumn` do modelo já resolve.
ORDENACAO: dict[str, str] = {
    "HTML — Linha de Status": "Receita Bruta",
    "HTML — Linha de Canal": "Nº Pedidos",
    "HTML — Linha de Categoria": "Margem Líquida R$",
    "HTML — Linha de Categoria Dupla": "Receita de Itens",
    "HTML — Linha de Produto": "% Margem Líquida",
    "HTML — Linha de Cliente": "Ticket Médio",
    "HTML — Linha de Cliente Dupla": "Ticket Médio",
    "HTML — Linha de Categoria Itens": "Itens Vendidos",
    "HTML — Linha de Similar": "Similaridade de Cosseno",
    "HTML — Linha de Cesta": "Pedidos em Comum",
}


COMPONENTES: list[tuple] = []


def add(nome, corpo, doc, pagina, titulo, caixa, gran, substitui):
    COMPONENTES.append((nome, corpo, doc, pagina, titulo, caixa, gran, substitui))


P1, P2 = "9b59c383596f4321410c", "8b9a1639803b1ec67486"
P3, P4 = "7063cddba223efdc191f", "f6abdb8b3f2b10695db3"
P5 = "64e0f916489ae8f4673f"

# ── capa ────────────────────────────────────────────────────────────────────
add("HTML — Faixa de KPIs",
    ["VAR _Bruta     = [Receita Bruta]",
     "VAR _Efetivada = [Receita Efetivada]",
     "VAR _Pct       = DIVIDE(_Efetivada, _Bruta)",
     "RETURN"] +
    faixa([
        ("Receita Bruta", 'FORMAT(_Bruta / 1000000, "R$ #,##0") & " Mi"',
         s("GMV — todos os status"), TEXTO, None),
        ("Receita Efetivada", 'FORMAT(_Efetivada / 1000000, "R$ #,##0") & " Mi"',
         'FORMAT(_Pct, "0.0%") & " do GMV virou receita"', AZUL,
         'FORMAT(_Pct * 100, "0")'),
        ("Pedidos", 'FORMAT([Nº Pedidos], "#,##0")', s("2020 a 2026"), TEXTO, None),
        ("Ticket Médio", 'FORMAT([Ticket Médio], "R$ #,##0.00")',
         s("a resposta da Questão 1"), TEXTO, None),
        ("Margem Líquida", 'FORMAT([% Margem Líquida], "0.00%")',
         s("já líquida de desconto"), LARANJA, None),
    ]),
    ["OS CINCO INDICADORES DA CAPA."] + DOC_BLOCO,
    P1, None, (32, 162, 1216, 100), None, ["14bbe354ad1b1c4d5f5f"])

add("HTML — Série de Receita",
    serie("dim_data", "ano_mes",
          [("[Receita Bruta]", AZUL), ("[Receita Efetivada]", LARANJA)], 96),
    ["RECEITA MENSAL, BRUTA E EFETIVADA, em SVG.",
     "",
     "A distância entre as duas linhas é o dinheiro que nunca virou receita —",
     "R$ 207,1 milhões no período inteiro."] + DOC_BLOCO,
    P1, "A receita cresce todo ano — e a faixa entre as linhas é o que se perde",
    (32, 272, 780, 250), None, ["08a8b95020955a6cfff2"])

add("HTML — Linha de Status",
    ranking("dim_status_pedido", "status_exibicao", "[Receita Bruta]",
            'R$ #,##0,, " Mi"', 4, AZUL, 104),
    ["RECEITA POR STATUS DO PEDIDO."] + DOC_CROSS,
    P1, "Um em cada sete reais nunca virou receita",
    (826, 272, 422, 250), ("dim_status_pedido", "status_exibicao"),
    ["7f9c74f6ab90cdb128b1"])

add("HTML — Linha de Canal",
    ranking("dim_canal", "canal_exibicao", "[Nº Pedidos]", "#,##0", 2, ROXO, 92),
    ["PEDIDOS POR CANAL."] + DOC_CROSS,
    P1, "E-commerce responde por 70% dos pedidos",
    (32, 534, 592, 158), ("dim_canal", "canal_exibicao"), ["649f66a46725abff8ec5"])

add("HTML — Linha de Categoria",
    ranking("dim_produto", "categoria", "[Margem Líquida R$]",
            'R$ #,##0,, " Mi"', 5, LARANJA, 120),
    ["AS CINCO MAIORES CATEGORIAS POR MARGEM LÍQUIDA."] + DOC_CROSS,
    P1, "Margem líquida por categoria — as cinco maiores",
    (656, 534, 592, 158), ("dim_produto", "categoria"), ["74da21ed1ccad7ce7954"])

# ── vendas e margem ─────────────────────────────────────────────────────────
add("HTML — Faixa de Margem",
    faixa([
        ("Receita de Itens",
         'FORMAT([Receita de Itens] / 1000000, "R$ #,##0") & " Mi"',
         s("grão de item — 147.320 linhas"), TEXTO, None),
        ("Margem Bruta",
         'FORMAT([Margem Bruta R$] / 1000000, "R$ #,##0") & " Mi"',
         'FORMAT([% Margem Bruta], "0.00%") & " da receita"', TEXTO, None),
        ("Desconto",
         'FORMAT(([Margem Bruta R$] - [Margem Líquida R$]) / 1000000, "R$ #,##0") & " Mi"',
         s("rateado por linha de item"), LARANJA, None),
        ("Margem Líquida",
         'FORMAT([Margem Líquida R$] / 1000000, "R$ #,##0") & " Mi"',
         s("depois do desconto"), TEXTO, None),
        ("% Margem Líquida", 'FORMAT([% Margem Líquida], "0.00%")',
         s("estável em todo o período"), AZUL, None),
    ]),
    ["INDICADORES DE MARGEM.",
     "",
     "O terceiro cartão troca o `% Margem Bruta` do desenho antigo pelo",
     "DESCONTO em reais — a diferença entre as duas margens, que é o número",
     "que ninguém olha e explica o resto da página."] + DOC_BLOCO,
    P2, None, (32, 96, 1216, 100), None,
    ["86bd2d1a878bb01a28de", "0942fb2b8c2ed856679b", "97e04d009a559ffb2420",
     "dc474a897e08e28f7760", "2da145560069913d032f"])

add("HTML — Linha de Categoria Dupla",
    ranking("dim_produto", "categoria", "[Receita de Itens]", 'R$ #,##0,, " Mi"',
            14, AZUL, 116, larg_val=68, med2="[Margem Líquida R$]",
            fmt2='R$ #,##0,, " Mi"', cor2=LARANJA),
    ["RECEITA E MARGEM POR CATEGORIA, as duas barras empilhadas.",
     "",
     "Empilhadas e não lado a lado porque a comparação é entre as DUAS de uma",
     "mesma categoria, não entre categorias — e é a proporção constante entre",
     "elas que sustenta o título da página."] + DOC_CROSS,
    P2, "Margem homogênea (37,8% a 41,5%): o lucro repete o ranking de receita",
    (32, 206, 608, 290), ("dim_produto", "categoria"), ["f41f5fed1beae784b907"])

add("HTML — Linha de Produto",
    ranking("dim_produto", "produto", "[% Margem Líquida]", "0.00%", 10, LARANJA,
            168),
    ["TOP 10 PRODUTOS POR MARGEM.",
     "",
     "A barra é proporcional ao MAIOR DA LISTA, não a 100%: as margens vão de",
     "37% a 53%, e num eixo de 0 a 100 nada se distinguiria. O valor absoluto",
     "vai no rótulo, então a escala relativa não engana."] + DOC_CROSS,
    P2, "Produtos por margem — clique para filtrar a página",
    (654, 206, 594, 290), ("dim_produto", "produto"), ["60017aa09e90e8383d05"])

add("HTML — Série de Margem",
    serie("dim_data", "ano_mes", [("[% Margem Líquida]", AZUL)], 96,
          base_zero=False),
    ["MARGEM PERCENTUAL MÊS A MÊS, em SVG."] + DOC_BLOCO,
    P2, "A margem percentual é estável no tempo — o crescimento vem de volume",
    (32, 510, 1216, 182), None, ["adf3da49728681a7a490"])

# ── clientes (Q4) ───────────────────────────────────────────────────────────
add("HTML — Faixa de Clientes",
    faixa([
        ("Clientes", 'FORMAT([Clientes], "#,##0")', s("todos compraram"),
         TEXTO, None),
        ("Ticket Médio", 'FORMAT([Ticket Médio], "R$ #,##0.00")',
         s("o critério do ranking"), AZUL, None),
        ("Pedidos", 'FORMAT([Nº Pedidos], "#,##0")', s("2020 a 2026"), TEXTO, None),
        ("Itens Vendidos", 'FORMAT([Itens Vendidos], "#,##0")',
         s("soma das quantidades"), TEXTO, None),
        ("Taxa de Devolução", 'FORMAT([Taxa de Devolução], "0.00%")',
         s("sobre itens vendidos"), LARANJA, None),
    ]),
    ["INDICADORES DE CLIENTE."] + DOC_BLOCO,
    P3, None, (32, 148, 1216, 100), None,
    ["e34e09e690469ad21b9c", "1d210e226b7df23b2a3a", "b3f419d540761592d5a0",
     "653d7ceea4149af060b9", "83615857b1d1e882acac"])

add("HTML — Linha de Cliente",
    ranking("dim_cliente", "cliente", "[Ticket Médio]", "R$ #,##0", 10, ROXO, 168),
    ["TOP 10 CLIENTES POR TICKET MÉDIO — o ranking literal da Questão 4."]
    + DOC_CROSS,
    P3, "Os 10 de maior ticket — clique para filtrar a página",
    (32, 258, 640, 250), ("dim_cliente", "cliente"), ["20e60e4241e69b7591bc"])

add("HTML — Linha de Cliente Dupla",
    ranking("dim_cliente", "cliente", "[Ticket Médio]", "R$ #,##0", 10, AZUL, 96,
            larg_val=62, med2="[Receita Bruta]", fmt2='R$ #,##0.00,, " Mi"',
            cor2=LARANJA),
    ["TICKET × FATURAMENTO, no mesmo cliente.",
     "",
     "As duas barras raramente acompanham uma à outra, e é esse descompasso",
     "que mostra que ticket alto não é o mesmo que cliente valioso."] + DOC_CROSS,
    P3, "Ticket alto não é cliente valioso",
    (960, 258, 288, 250), ("dim_cliente", "cliente"), ["6b83e06018435b48c816"])

add("HTML — Linha de Categoria Itens",
    ranking("dim_produto", "categoria", "[Itens Vendidos]", "#,##0", 8, AZUL, 88,
            larg_val=62),
    ["CATEGORIAS POR ITENS VENDIDOS."] + DOC_CROSS,
    P3, "Hélices lidera o grupo",
    (686, 258, 260, 250), ("dim_produto", "categoria"), ["8dd4bd284e6dfc2a6573"])

# ── sazonalidade (Q5) ───────────────────────────────────────────────────────
add("HTML — Faixa de Sazonalidade",
    faixa([
        ("Média Correta", 'FORMAT([Média de Venda por Dia POS], "R$ #,##0")',
         s("divide pelo calendário inteiro"), AZUL, None),
        ("Média Ingênua",
         'FORMAT([Média por Dia (só dias com venda)], "R$ #,##0")',
         s("só dias com venda — o erro"), LARANJA, None),
        ("Dias sem Venda", 'FORMAT([Dias sem Venda], "#,##0")',
         s("de 2.557 dias de calendário"), TEXTO, None),
        ("Inflação da Média",
         'FORMAT([Inflação da Média (erro do estagiário)], "0.00%")',
         s("e não é uniforme entre os dias"), LARANJA, None),
    ]),
    ["OS QUATRO NÚMEROS DA QUESTÃO 5."] + DOC_BLOCO,
    P4, None, (32, 92, 1216, 100), None,
    ["a670e3e2e2618ebe11dd", "2949bb6144eed05d9756", "35a9445dd117e7f4ab98",
     "13ba3e8a52365c5d7239"])

add("HTML — Linha de Dia",
    ranking("dim_data", "dia_semana", "[Média de Venda por Dia POS]",
            "R$ #,##0", 7, AZUL, 116, ordem="natural", larg_val=72,
            med2="[Média por Dia (só dias com venda)]", fmt2="R$ #,##0",
            cor2=LARANJA),
    ["AS DUAS MÉDIAS, DIA A DIA — o visual mais importante do painel.",
     "",
     "Ordem natural da semana, não por valor: o leitor procura o dia, não a",
     "posição. A barra de cima é a média correta e a de baixo a ingênua; onde",
     "a laranja se estica mais, o erro é maior — e ele é maior justamente na",
     "quinta-feira, que é o que inverte o ranking."] + DOC_CROSS,
    P4, "As duas médias lado a lado: a correta (azul) põe a quinta em último",
    (32, 202, 760, 300), ("dim_data", "dia_semana"), ["95999cbea26ffa863dcb"])

add("HTML — Linha de Dia Vazio",
    ranking("dim_data", "dia_semana", "[Dias sem Venda]", "#,##0", 7, LARANJA,
            116, ordem="natural", larg_val=44),
    ["DIAS SEM VENDA POR DIA DA SEMANA.",
     "",
     "20 na quinta contra 7 na segunda — a desigualdade que faz a média",
     "ingênua inflar mais um dia que outro e trocar o pior dia da semana."]
    + DOC_CROSS,
    P4, "20 dias vazios na quinta contra 7 na segunda",
    (806, 202, 442, 300), ("dim_data", "dia_semana"), ["d0401fb0db54c66a2b47"])

add("HTML — Linha de Ano",
    ranking("dim_data", "ano", "[Dias sem Venda]", "#,##0", 8, ROXO, 52,
            ordem="natural", larg_val=44),
    ["DIAS SEM VENDA POR ANO — a curva de ramp-up.",
     "",
     "25 em 2020 e 1 em 2025: dia sem venda é característica de operação",
     "nova, não de sazonalidade."] + DOC_CROSS,
    P4, "Dia sem venda é fenômeno de ramp-up: 25 em 2020, 1 em 2025",
    (806, 516, 442, 176), ("dim_data", "ano"), ["55a073aa849c3353cc23"])

# ── previsão e recomendação (Q6-Q7) ─────────────────────────────────────────
add("HTML — Série da Bússola",
    serie("fct_previsao_bussola", "ano_mes",
          [("[Unidades Realizadas]", AZUL),
           ("[Previsão — Média Móvel 3m]", LARANJA)], 96),
    ["A SÉRIE DA BÚSSOLA DE BORDO 702, em SVG.",
     "",
     "A linha laranja só existe nos três meses de teste — é ali que a previsão",
     "descola do realizado. Os 75 meses cabem sem rolagem, que era o defeito",
     "do gráfico nativo aqui: a previsão ficava fora da janela visível."]
    + DOC_BLOCO,
    P5, "A série da Bússola: alta constante e um dez/2025 fora da curva",
    (32, 96, 528, 288), None, ["f283a342495bf78b805d"])

add("HTML — Faixa da Previsão",
    faixa([
        ("Realizado", 'FORMAT([Realizado no Trimestre], "#,##0") & " un"',
         s("jan a mar de 2026"), AZUL, None),
        ("Previsto (MM3)", 'FORMAT([Previsão — Média Móvel 3m], "#,##0") & " un"',
         s("o baseline do enunciado"), TEXTO, None),
        ("Erro", 'FORMAT([Erro da Previsão], "0.0%")',
         s("o baseline subestima"), LARANJA, None),
    ], tam=26, coluna=True),
    ["O CONFRONTO DA QUESTÃO 6: 207 realizadas contra 116 previstas."]
    + DOC_BLOCO,
    P5, None, (572, 96, 220, 288), None,
    ["a0b9432e39b9c9b1a01e", "7e1158aa1cbbb2fa5a71", "b8343cef7c8ec1ac16be"])

add("HTML — Linha de Similar",
    ranking("fct_similaridade_produto", "produto", "[Similaridade de Cosseno]",
            "0.0000", 10, AZUL, 150),
    ["RANKING DA QUESTÃO 7.",
     "",
     "Quatro casas decimais de propósito: o 1º ganha do 2º por 0,0003, e",
     "arredondar para duas empataria os três primeiros — que é exatamente o",
     "argumento da resposta."] + DOC_CROSS,
    P5, "Top similares ao Motor de Popa 1949 — clique para filtrar",
    (32, 398, 500, 294), ("fct_similaridade_produto", "produto"),
    ["d14e1875d38241c62ead"])

add("HTML — Linha de Cesta",
    ranking("fct_similaridade_produto", "produto", "[Pedidos em Comum]", "#,##0",
            10, ROXO, 150, larg_val=52),
    ["CO-OCORRÊNCIA NO MESMO PEDIDO — a formulação correta do problema da",
     "Marina, que devolve outro campeão: Tinta Antifouling."] + DOC_CROSS,
    P5, "Co-ocorrência no pedido — a pergunta que a Marina fez",
    (546, 398, 500, 294), ("fct_similaridade_produto", "produto"),
    ["9107e2511f4b3299206a"])


# ═══════════════════════════════════════════════════════════════ gravação ══
def campo_medida(nome: str) -> dict:
    return {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}},
                                  "Property": nome}},
            "queryRef": f"_Medidas.{nome}", "nativeQueryRef": nome}


def campo_coluna(tab: str, col: str) -> dict:
    return {"field": {"Column": {"Expression": {"SourceRef": {"Entity": tab}},
                                 "Property": col}},
            "queryRef": f"{tab}.{col}", "nativeQueryRef": col}


def lit(v: str) -> dict:
    return {"expr": {"Literal": {"Value": v}}}


def cor_json(h: str) -> dict:
    return {"solid": {"color": lit(f"'{h}'")}}


def json_visual(nome_visual: str, medida: str, caixa: tuple,
                titulo: str | None, gran: tuple | None,
                ordenar_por: str | None = None) -> dict:
    x, y, w, h = caixa
    estado = {"content": {"projections": [campo_medida(medida)]}}
    if gran:
        estado["sampling"] = {"projections": [campo_coluna(*gran)]}
    consulta: dict = {"queryState": estado}
    if ordenar_por:
        # Sem isto o visual recebe as linhas na ordem da coluna de `sampling`
        # — alfabética — e o ranking aparece 3, 2, 1, 5, 4 na tela, com os
        # números certos e a sequência errada. A ordem de exibição é do
        # dataset, não do HTML.
        consulta["sortDefinition"] = {"sort": [{
            "field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}},
                                  "Property": ordenar_por}},
            "direction": "Descending"}]}
    v = {
        "visualType": GUID,
        "query": consulta,
        "objects": {
            "contentFormatting": [{"properties": {
                "format": lit("'html'"), "showRawHtml": lit("false"),
                # com `true`, o visual pinta a formatação dele por cima do CSS
                # da medida e o desenho inteiro se perde
                "overrideInlineStyling": lit("false"),
                "fontFamily": lit("'Segoe UI'"), "fontSize": lit("11D"),
                "fontColour": cor_json(TEXTO), "align": lit("'left'"),
                "userSelect": lit("true"),
                "noDataMessage": lit("'Sem dados no filtro atual'"),
            }}],
            "crossFilter": [{"properties": {
                "enabled": lit("true" if gran else "false"),
                "useTransparency": lit("true"),
                "transparencyPercent": lit("55D"),
            }}],
        },
        "visualContainerObjects": {
            "background": [{"properties": {"show": lit("true"),
                                           "color": cor_json(CARTAO)}}],
            "border": [{"properties": {"show": lit("true"),
                                       "color": cor_json(BORDA),
                                       "radius": lit("10D")}}],
            "visualHeader": [{"properties": {"show": lit("false")}}],
        },
    }
    if titulo:
        v["visualContainerObjects"]["title"] = [{"properties": {
            "show": lit("true"), "text": lit(f"'{titulo}'"), "fontSize": lit("10D"),
            "fontColor": cor_json(TEXTO), "bold": lit("true"),
            "alignment": lit("'left'")}}]
    return {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/"
                       "report/definition/visualContainer/2.9.0/schema.json",
            "name": nome_visual,
            "position": {"x": x, "y": y, "z": 100, "height": h, "width": w,
                         "tabOrder": 100},
            "visual": v}



# ══════════════════════════════════════════════════ navegação e filtros ════
# Onde ficam os segmentadores de cada página, depois do deslocamento. Filtro
# no rodapé, abaixo dos gráficos, era o que estava errado: quem usa procura o
# controle antes de ler, não depois.
SLICERS = {
    P1: (948, 58, 300, 76),    # status do pedido
    P3: (948, 58, 300, 68),    # flag de elite
}

# Larguras de cabeçalho que precisam encolher para abrir espaço ao lado.
CABECALHO_ESTREITO = 900

DESLOCAMENTO = 34   # altura da faixa de navegação + respiro
LIMITE_Y = 702      # canvas de 720 menos uma margem


def navegador(pagina: str, largura: int) -> dict:
    """Botões de página. `pageNavigator` monta a lista sozinho — nada de
    manter cinco botões e cinco ações sincronizados à mão."""
    nome = id_curto(f"visual:nav:{pagina}")
    return {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/"
                       "report/definition/visualContainer/2.9.0/schema.json",
            "name": nome,
            "position": {"x": 32, "y": 10, "z": 900, "height": 28,
                         "width": largura, "tabOrder": 1},
            "visual": {
                "visualType": "pageNavigator",
                "objects": {
                    "layout": [{"properties": {"orientation": lit("0D"),
                                               "cellPadding": lit("6D")}}],
                    "shape": [{"properties": {"roundEdge": lit("6D")},
                               "selector": {"id": "default"}}],
                    "fill": [{"properties": {
                        "show": lit("true"), "fillColor": cor_json(CARTAO),
                        "transparency": lit("0D")}, "selector": {"id": "default"}}],
                    "text": [{"properties": {
                        "fontColor": cor_json(SUAVE), "fontSize": lit("9D")},
                        "selector": {"id": "default"}}],
                    "outline": [{"properties": {
                        "show": lit("true"), "lineColor": cor_json(BORDA),
                        "weight": lit("1D")}, "selector": {"id": "default"}}],
                },
                "visualContainerObjects": {
                    "background": [{"properties": {"show": lit("false")}}],
                    "visualHeader": [{"properties": {"show": lit("false")}}],
                },
            }}


def reposicionar() -> None:
    """Abre a faixa de navegação no topo e tira os filtros do rodapé."""
    for pagina in (P1, P2, P3, P4, P5):
        base = PAGES / pagina / "visuals"
        arquivos = sorted(base.glob("*/visual.json"))
        for caminho in arquivos:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
            tipo = dados["visual"].get("visualType")
            pos = dados["position"]

            if tipo == "slicer" and pagina in SLICERS:
                x, y, w, h = SLICERS[pagina]
                pos.update(x=x, y=y, width=w, height=h)
            else:
                pos["y"] += DESLOCAMENTO
                # o cabeçalho encolhe para o segmentador caber ao lado
                if (tipo == "textbox" and pos["y"] < 100
                        and pagina in SLICERS and pos["width"] > CABECALHO_ESTREITO):
                    pos["width"] = CABECALHO_ESTREITO
                # quem passou do rodapé cede a altura, em vez de sair da tela
                if pos["y"] + pos["height"] > LIMITE_Y:
                    pos["height"] = LIMITE_Y - pos["y"]

            caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2)
                               + "\n", encoding="utf-8", newline="\r\n")

        largura = 890 if pagina in SLICERS else 1216
        nav = navegador(pagina, largura)
        os.makedirs(base / nav["name"], exist_ok=True)
        (base / nav["name"] / "visual.json").write_text(
            json.dumps(nav, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\r\n")


def main() -> None:
    with open(TMDL, encoding="utf-8", newline="") as fh:
        texto = fh.read()

    # IDEMPOTENTE: remove os blocos já gravados antes de inserir. Sem isto,
    # rodar duas vezes deixa duas cópias — e a segunda sobrescreve a primeira
    # em silêncio na hora de carregar o modelo.
    for nome in re.findall(r"\tmeasure '(HTML — [^']+)'", texto):
        texto = re.sub(
            r"\t///[^\r\n]*(?:\r\n\t///[^\r\n]*)*\r\n\tmeasure '" + re.escape(nome)
            + r"' =(?:\r\n(?!\t///|\tmeasure |\tcolumn |\tpartition )[^\r\n]*)*\r\n\r\n",
            "", texto)

    blocos = "".join(bloco_tmdl(n, c, d) for n, c, d, *_ in COMPONENTES)
    ancora = "\t/// As 207 unidades efetivamente vendidas"
    assert texto.count(ancora) == 1, "âncora não encontrada"
    with open(TMDL, "w", encoding="utf-8", newline="") as fh:
        fh.write(texto.replace(ancora, blocos + ancora))

    esperados: set[str] = set()
    for nome, _, _, pagina, titulo, caixa, gran, _ in COMPONENTES:
        base = PAGES / pagina / "visuals"
        nv = id_curto(f"visual:html3:{nome}")
        esperados.add(nv)
        os.makedirs(base / nv, exist_ok=True)
        with open(base / nv / "visual.json", "w", encoding="utf-8",
                  newline="\r\n") as fh:
            fh.write(json.dumps(
                json_visual(nv, nome, caixa, titulo, gran, ORDENACAO.get(nome)),
                ensure_ascii=False, indent=2) + "\n")

    # Limpeza determinística, no lugar de uma lista de IDs escrita à mão —
    # que foi de onde vieram três cartões e um HTML órfãos sobrepondo os
    # componentes novos. Textbox e slicer ficam: um é narrativa, o outro é
    # controle, e nenhum dos dois foi substituído por HTML.
    substituidos = {"card", "clusteredBarChart", "clusteredColumnChart",
                    "barChart", "lineChart", "tableEx", "pivotTable",
                    "pageNavigator"}
    removidos = 0
    for caminho in PAGES.glob("*/visuals/*/visual.json"):
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        tipo = dados["visual"].get("visualType")
        orfao_html = tipo == GUID and dados["name"] not in esperados
        if tipo in substituidos or orfao_html:
            shutil.rmtree(caminho.parent)
            removidos += 1
    if removidos:
        print(f"  {removidos} visuais antigos removidos")

    reposicionar()

    filtram = sum(1 for c in COMPONENTES if c[6])
    print(f"{len(COMPONENTES)} componentes HTML gravados "
          f"({filtram} com cross-filter, {len(COMPONENTES) - filtram} em bloco)")


if __name__ == "__main__":
    main()
