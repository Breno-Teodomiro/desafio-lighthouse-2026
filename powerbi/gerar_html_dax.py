#!/usr/bin/env python3
"""
Gera as medidas DAX que devolvem HTML para o visual "HTML Content (lite)".

    python3 powerbi/gerar_html_dax.py

POR QUE UM GERADOR, E NÃO DAX ESCRITO À MÃO
-------------------------------------------
Em DAX, aspa dupla dentro de string se escapa dobrando (""). Um HTML com
dezenas de atributos vira um campo minado onde um `"` a mais quebra a medida
inteira, e o erro que o Desktop mostra não aponta a coluna. Aqui o escape é
feito uma vez, na função `s()`, e o resto é template.

DUAS FORMAS DE MEDIDA, E A DIFERENÇA IMPORTA
--------------------------------------------
· BLOCO — uma medida devolve o componente inteiro (a faixa de KPIs). O visual
  recebe UMA linha, e o dataset de uma linha só tem um ponto de seleção: o
  componente todo. Não há o que clicar, e está certo assim — uma faixa de KPIs
  não é para filtrar.

· LINHA — a medida devolve UMA linha da lista, e a coluna que dá a
  granularidade entra no papel `sampling` do visual. Aí o visual monta uma
  entrada por item, cada uma com seu próprio selectionId, e o clique
  CROSS-FILTRA a página como um gráfico nativo.

  A regra está no fonte do visual (`src/view-model.ts`):

      const hasGranularity = columns.some((c) => c.roles?.sampling);
      const hasCrossFiltering = hasGranularity && settings.crossFilter.enabled;

  Sem campo em `sampling`, a opção de cross-filter nem aparece no painel.

O TOP N SEM FILTRO DE VISUAL
----------------------------
A medida de linha devolve BLANK() fora do top N. O Power BI descarta a linha
cujas medidas são todas vazias, então a lista se limita sozinha — sem depender
de `filterConfig`, que não tem uma única ocorrência nos projetos PBIR de
referência desta máquina.

Autor: Breno Teodomiro · Desafio Técnico Lighthouse 2026 (Indicium)
"""

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
A = chr(34)       # aspa dupla literal, para montar os atributos HTML


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
    linhas += ["\t\tdisplayFolder: 0 HTML",
               f"\t\tlineageTag: {guid('med:' + nome)}", ""]
    return "\r\n".join(linhas) + "\r\n"


# ═════════════════════════════════════════════════ faixa de KPIs (BLOCO) ════
CAIXA = (f"flex:1;min-width:0;background:#12203366;border:1px solid {BORDA};"
         "border-radius:14px;padding:14px 16px;")
ROTULO = ("font-size:10px;letter-spacing:.10em;text-transform:uppercase;"
          f"color:{SUAVE};font-weight:600;white-space:nowrap;")
NOTA = f"font-size:11px;color:{FRACO};margin-top:8px;white-space:nowrap;"


def num(cor: str) -> str:
    return (f"font-size:30px;line-height:1.1;font-weight:200;color:{cor};"
            "margin-top:10px;white-space:nowrap;")


def cartao(rotulo: str, valor: str, nota: str, cor: str = TEXTO,
           barra: str | None = None) -> list[str]:
    saida = [
        f'& {s(f"<div style={A}{CAIXA}{A}>")}',
        f'& {s(f"<div style={A}{ROTULO}{A}>{rotulo}</div>")}',
        f'& {s(f"<div style={A}{num(cor)}{A}>")} & {valor} & {s("</div>")}',
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
    return saida


faixa = [
    "VAR _Bruta     = [Receita Bruta]",
    "VAR _Efetivada = [Receita Efetivada]",
    "VAR _Pct       = DIVIDE(_Efetivada, _Bruta)",
    "RETURN",
    f'    {s(f"<div style={A}display:flex;gap:10px;font-family:{FONTE};{A}>")}',
]
faixa += cartao("Receita Bruta", 'FORMAT(_Bruta / 1000000, "R$ #,##0") & " Mi"',
                s("GMV — todos os status"))
faixa += cartao("Receita Efetivada",
                'FORMAT(_Efetivada / 1000000, "R$ #,##0") & " Mi"',
                'FORMAT(_Pct, "0.0%") & " do GMV virou receita"', AZUL,
                barra='FORMAT(_Pct * 100, "0")')
faixa += cartao("Pedidos", 'FORMAT([Nº Pedidos], "#,##0")', s("2020 a 2026"))
faixa += cartao("Ticket Médio", 'FORMAT([Ticket Médio], "R$ #,##0.00")',
                s("a resposta da Questão 1"))
faixa += cartao("Margem Líquida", 'FORMAT([% Margem Líquida], "0.00%")',
                s("já líquida de desconto"), LARANJA)
faixa.append(f'& {s("</div>")}')

DOC_FAIXA = [
    'FAIXA DE KPIs — visual "HTML Content (lite)", forma BLOCO.',
    "",
    "Os cinco indicadores da capa: número em peso 200, rótulo em versalete",
    "espaçado, barra de proporção na receita efetivada e uma linha de contexto",
    "por indicador, que o cartão nativo não comporta.",
    "",
    "RECEBE filtro como qualquer medida — mexer no segmentador de status",
    "reescreve os cinco números e a largura da barra. NÃO EMITE filtro, e é",
    "deliberado: uma faixa de KPIs é para ler, não para clicar.",
    "",
    "CSS INLINE POR OBRIGAÇÃO: o visual roda num iframe com apenas",
    "`allow-scripts`, que bloqueia toda tag <script> externa. Nenhum CDN",
    "carrega ali — nem Tailwind, nem fonte do Google.",
]


# ══════════════════════════════════════════════════ linha de ranking (LINHA) ═
LINHA = ("display:flex;align-items:center;gap:10px;padding:2px 2px;"
         f"font-family:{FONTE};")
POS = f"width:18px;font-size:11px;color:{FRACO};text-align:right;flex:none;"
NOME = (f"width:150px;font-size:12px;color:{TEXTO};overflow:hidden;"
        "text-overflow:ellipsis;white-space:nowrap;flex:none;")
TRI = (f"flex:1;height:8px;background:{TRILHO};border-radius:4px;"
       "overflow:hidden;min-width:30px;")
VAL = f"width:78px;text-align:right;font-size:12px;color:{SUAVE};flex:none;"


def linha_rank(tabela: str, coluna: str, med: str, fmt: str, n: int,
               cor: str) -> list[str]:
    """Uma linha da lista. A coluna vai no papel `sampling` do visual."""
    escopo = f"ALLSELECTED({tabela}[{coluna}])"
    barra = (f"height:8px;border-radius:4px;"
             f"background:linear-gradient(90deg,{cor},{cor}66);width:")
    return [
        f"VAR _V   = {med}",
        f"VAR _Pos = RANKX({escopo}, {med},, DESC)",
        f"VAR _Max = MAXX(TOPN({n}, {escopo}, {med}, DESC), {med})",
        "RETURN",
        # BLANK fora do top N: o Power BI descarta a linha toda vazia, e a
        # lista se limita sem filtro de visual.
        "    IF(",
        f"        _Pos <= {n},",
        f"        {s(f'<div style={A}{LINHA}{A}>')}",
        f"      & {s(f'<div style={A}{POS}{A}>')} & _Pos & {s('</div>')}",
        f"      & {s(f'<div style={A}{NOME}{A}>')}",
        f"      & SELECTEDVALUE({tabela}[{coluna}]) & {s('</div>')}",
        f"      & {s(f'<div style={A}{TRI}{A}><div style={A}{barra}')}",
        "      & FORMAT(DIVIDE(_V, _Max) * 100, \"0.0\")",
        f"      & {s(f'%{A}></div></div>')}",
        f"      & {s(f'<div style={A}{VAL}{A}>')} & FORMAT(_V, {s(fmt)})",
        f"      & {s('</div></div>')}",
        "    )",
    ]


DOC_CROSS = [
    "",
    "FORMA LINHA — devolve UMA linha, e a coluna de granularidade entra no",
    "papel `sampling` do visual. É isso que dá cross-filter: o visual cria um",
    "selectionId por linha, e clicar filtra a página como um gráfico nativo.",
    "Sem campo em `sampling`, a opção de cross-filter nem aparece.",
    "",
    "O top N sai do BLANK: fora do corte a medida devolve vazio e o Power BI",
    "descarta a linha, sem precisar de filtro de visual.",
]

blocos = [
    bloco("HTML — Faixa de KPIs", faixa, DOC_FAIXA),
    bloco(
        "HTML — Linha de Produto",
        linha_rank("dim_produto", "produto", "[% Margem Líquida]", "0.00%", 10, LARANJA),
        ["TOP PRODUTOS POR MARGEM, uma linha por produto.",
         "",
         "A barra é proporcional ao MAIOR DA LISTA, não a 100%: as margens vão",
         "de 37% a 53%, e num eixo de 0 a 100 nada se distinguiria. O valor",
         "absoluto vai no rótulo, então a escala relativa não engana."] + DOC_CROSS,
    ),
    bloco(
        "HTML — Linha de Similar",
        linha_rank("fct_similaridade_produto", "produto",
                   "[Similaridade de Cosseno]", "0.0000", 10, AZUL),
        ["RANKING DA QUESTÃO 7, uma linha por produto.",
         "",
         "Quatro casas decimais de propósito: o 1º ganha do 2º por 0,0003, e",
         "arredondar para duas empataria os três primeiros — que é exatamente",
         "o argumento da resposta."] + DOC_CROSS,
    ),
    bloco(
        "HTML — Linha de Cliente",
        linha_rank("dim_cliente", "cliente", "[Ticket Médio]", "R$ #,##0", 10, ROXO),
        ["TOP CLIENTES POR TICKET MÉDIO, uma linha por cliente.",
         "",
         "É o ranking literal da Questão 4 — ticket médio, sem RFM. Clicar num",
         "cliente filtra a página e mostra o que o ranking premiou nele."] + DOC_CROSS,
    ),
]

with open(TMDL, encoding="utf-8", newline="") as fh:
    texto = fh.read()

# IDEMPOTENTE: remove os blocos já gravados antes de inserir. Sem isto, rodar
# duas vezes deixa duas cópias de cada medida — e o TMDL aceita, porque a
# segunda sobrescreve a primeira em silêncio na hora de carregar.
for _nome in ("HTML — Faixa de KPIs", "HTML — Top Produtos por Margem",
              "HTML — Top Similares Q7", "HTML — Linha de Produto",
              "HTML — Linha de Similar", "HTML — Linha de Cliente",
              "HTML — Linha de Dia"):
    texto = re.sub(
        r"\t///[^\r\n]*(?:\r\n\t///[^\r\n]*)*\r\n\tmeasure '" + re.escape(_nome)
        + r"' =(?:\r\n(?!\t///|\tmeasure |\tcolumn |\tpartition )[^\r\n]*)*\r\n\r\n",
        "", texto)

ancora = "\t/// As 207 unidades efetivamente vendidas"
assert texto.count(ancora) == 1, "âncora não encontrada"
with open(TMDL, "w", encoding="utf-8", newline="") as fh:
    fh.write(texto.replace(ancora, "".join(blocos) + ancora))
print(f"{len(blocos)} medidas HTML gravadas")
