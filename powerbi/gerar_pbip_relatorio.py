#!/usr/bin/env python3
"""
Camada de relatório (PBIR) do projeto Power BI da LH Nautical.

Separado de `gerar_pbip.py` porque são dois artefatos com ciclos de vida
diferentes: o modelo semântico muda quando o gold muda; o relatório muda
quando a narrativa muda.

PRINCÍPIO DE DESIGN DAS PÁGINAS
-------------------------------
Todo título de visual é uma FRASE DE CONCLUSÃO, não um rótulo. "Quinta-feira
é o pior dia — mas por apenas 10%" em vez de "Média por dia da semana".

Um rótulo obriga o leitor a descobrir sozinho o que o gráfico quer dizer, e
metade dos leitores descobre errado. Uma conclusão no título transforma o
visual em evidência de uma afirmação — e deixa o leitor livre para discordar
dela olhando o gráfico, que é o ponto.

Autor: Breno Teodomiro · Desafio Técnico Lighthouse 2026 (Indicium)
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

LARGURA, ALTURA = 1280, 720

# Paleta — azul-marinho (varejo náutico), com laranja como cor de destaque
# reservada para o achado de cada página. Uso parcimonioso é o que faz o
# destaque funcionar.
COR_TEXTO = "#E8EEF4"
COR_SUAVE = "#93A5B8"
COR_PRIMARIA = "#2D9CDB"
COR_DESTAQUE = "#D9772A"
COR_FUNDO = "#0A121E"
COR_CARTAO = "#0E1826"
COR_BORDA = "#1E2E42"


def lit(valor: Any) -> dict:
    """Envelope de literal do formato PBIR."""
    return {"expr": {"Literal": {"Value": valor}}}


def cor(hexa: str) -> dict:
    return {"solid": {"color": lit(f"'{hexa}'")}}


def medida(nome: str) -> dict:
    return {
        "field": {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": "_Medidas"}},
                "Property": nome,
            }
        },
        "queryRef": f"_Medidas.{nome}",
        "nativeQueryRef": nome,
    }


def coluna(tabela: str, campo: str, ativo: bool = False) -> dict:
    d: dict[str, Any] = {
        "field": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": tabela}},
                "Property": campo,
            }
        },
        "queryRef": f"{tabela}.{campo}",
        "nativeQueryRef": campo,
    }
    if ativo:
        d["active"] = True
    return d


def caixa_visual(cor_fundo: str = COR_CARTAO) -> dict:
    """Fundo e borda padrão dos visuais — o 'cartão'."""
    return {
        "background": [{"properties": {"show": lit("true"), "color": cor(cor_fundo)}}],
        "border": [
            {"properties": {"show": lit("true"), "color": cor(COR_BORDA),
                            "radius": lit("10D")}}
        ],
        "visualHeader": [{"properties": {"show": lit("false")}}],
    }


def titulo(texto: str, tamanho: float = 11, cor_texto: str = COR_TEXTO) -> dict:
    return {
        "title": [
            {
                "properties": {
                    "show": lit("true"),
                    "text": lit(f"'{texto}'"),
                    "fontSize": lit(f"{tamanho}D"),
                    "fontColor": cor(cor_texto),
                    "bold": lit("true"),
                    "alignment": lit("'left'"),
                }
            }
        ]
    }


def visual(
    nome: str, tipo: str, x: int, y: int, w: int, h: int,
    query: dict | None = None, objetos: dict | None = None,
    header: dict | None = None, z: int = 100,
) -> dict:
    v: dict[str, Any] = {"visualType": tipo}
    if query:
        v["query"] = {"queryState": query}
    if objetos:
        v["objects"] = objetos
    v["visualContainerObjects"] = {**caixa_visual(), **(header or {})}
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/"
                   "definition/visualContainer/2.9.0/schema.json",
        "name": nome,
        "position": {"x": x, "y": y, "z": z, "height": h, "width": w,
                     "tabOrder": z},
        "visual": v,
    }


def texto_livre(nome: str, x: int, y: int, w: int, h: int,
                paragrafos: list[tuple[str, int, str, bool]], z: int = 100) -> dict:
    """Caixa de texto. `paragrafos` = [(texto, tamanho, cor, negrito)]."""
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/"
                   "definition/visualContainer/2.9.0/schema.json",
        "name": nome,
        "position": {"x": x, "y": y, "z": z, "height": h, "width": w,
                     "tabOrder": z},
        "visual": {
            "visualType": "textbox",
            "objects": {
                "general": [
                    {
                        "properties": {
                            "paragraphs": [
                                {
                                    "textRuns": [
                                        {
                                            "value": t,
                                            "textStyle": {
                                                "fontSize": f"{sz}pt",
                                                "color": c,
                                                "fontWeight": "bold" if b else "normal",
                                                "fontFamily": "Segoe UI",
                                            },
                                        }
                                    ]
                                }
                                for (t, sz, c, b) in paragrafos
                            ]
                        }
                    }
                ]
            },
            "visualContainerObjects": {
                "background": [{"properties": {"show": lit("false")}}],
                "visualHeader": [{"properties": {"show": lit("false")}}],
            },
        },
    }


# Medidas cujo cartão é exibido em MILHÕES. O resto vai sem abreviação.
#
# A unidade precisa ser explícita porque o padrão do cartão é "Auto", e o Auto
# arredonda para a unidade mais próxima: Receita Bruta (1,41 bi) e Receita
# Efetivada (1,20 bi) apareciam AMBAS como "R$ 1 Bi", lado a lado, numa página
# cujo próprio subtítulo diz "R$ 1,41 bi de GMV". Ticket médio virava
# "R$ 28,70 Mil" e 48.998 pedidos viravam "49 Mil".
CARTOES_EM_MILHOES = frozenset({
    "Receita Bruta", "Receita Efetivada", "Receita de Itens",
    "Margem Bruta R$", "Margem Líquida R$", "Valor em Estoque",
})


def cartao(nome: str, nome_medida: str, x: int, y: int, w: int = 200, h: int = 92,
           destaque: bool = False) -> dict:
    unidade = "1000000D" if nome_medida in CARTOES_EM_MILHOES else "1D"
    return visual(
        nome, "card", x, y, w, h,
        query={"Values": {"projections": [medida(nome_medida)]}},
        objetos={
            "labels": [
                {
                    "properties": {
                        "fontSize": lit("24D"),
                        "bold": lit("true"),
                        "color": cor(COR_DESTAQUE if destaque else COR_PRIMARIA),
                        "labelDisplayUnits": lit(unidade),
                    }
                }
            ],
            "categoryLabels": [
                {"properties": {"show": lit("true"), "fontSize": lit("9D"),
                                "color": cor(COR_SUAVE)}}
            ],
        },
    )


# ==========================================================================
#  PÁGINAS
# ==========================================================================

def pagina_sumario(vid: Callable[[str], str]) -> tuple[str, list[dict]]:
    v = [
        texto_livre(
            vid("s-tit"), 32, 24, 900, 78,
            [
                ("LH Nautical — visão executiva", 22, COR_TEXTO, True),
                ("48.998 pedidos · 2020 a 2026 · R$ 1,41 bi de GMV", 11, COR_SUAVE, False),
            ],
        ),
        texto_livre(
            vid("s-alerta"), 32, 104, 1216, 56,
            [
                ("Leia antes: R$ 207,1 milhões (14,7% do GMV) são pedidos "
                 "cancelados ou em rascunho, e 8,7% dos pedidos têm data futura. "
                 "Use os filtros de status e período — os números mudam, e é isso "
                 "que a régua acima quer dizer.", 10, COR_DESTAQUE, False),
            ],
        ),
        cartao(vid("s-c1"), "Receita Bruta", 32, 162, 232),
        cartao(vid("s-c2"), "Receita Efetivada", 278, 162, 232, destaque=True),
        cartao(vid("s-c3"), "Nº Pedidos", 524, 162, 232),
        cartao(vid("s-c4"), "Ticket Médio", 770, 162, 232),
        cartao(vid("s-c5"), "% Margem Líquida", 1016, 162, 232),
        visual(
            vid("s-serie"), "lineChart", 32, 272, 780, 250,
            query={
                "Category": {"projections": [coluna("dim_data", "ano_mes", ativo=True)]},
                "Y": {"projections": [medida("Receita Bruta"),
                                      medida("Receita Efetivada")]},
            },
            header=titulo("A receita cresce todo ano — mas 2026 inclui meses que "
                          "ainda não aconteceram"),
        ),
        visual(
            vid("s-status"), "clusteredBarChart", 826, 272, 422, 250,
            query={
                "Category": {"projections": [
                    coluna("dim_status_pedido", "status_exibicao", ativo=True)]},
                "Y": {"projections": [medida("Receita Bruta")]},
            },
            header=titulo("Um em cada sete reais nunca virou receita"),
        ),
        visual(
            vid("s-canal"), "clusteredColumnChart", 32, 534, 380, 158,
            query={
                "Category": {"projections": [coluna("dim_canal", "canal_exibicao",
                                                    ativo=True)]},
                "Y": {"projections": [medida("Receita Bruta")]},
            },
            header=titulo("E-commerce responde por 70% dos pedidos"),
        ),
        visual(
            vid("s-cat"), "clusteredBarChart", 426, 534, 400, 158,
            query={
                "Category": {"projections": [coluna("dim_produto", "categoria",
                                                    ativo=True)]},
                "Y": {"projections": [medida("Margem Líquida R$")]},
            },
            header=titulo("Margem líquida por categoria"),
        ),
        visual(
            vid("s-slicer"), "slicer", 840, 534, 408, 158,
            query={"Values": {"projections": [
                coluna("dim_status_pedido", "status_exibicao", ativo=True)]}},
            header=titulo("Filtro de status — mude e veja a receita mudar"),
        ),
    ]
    return "Sumário executivo", v


def pagina_margem(vid: Callable[[str], str]) -> tuple[str, list[dict]]:
    v = [
        texto_livre(
            vid("m-tit"), 32, 24, 900, 72,
            [("Vendas e margem", 20, COR_TEXTO, True),
             ("Grão de item — 147.320 linhas. O desconto do pedido chega aqui "
              "rateado pela participação de cada linha.", 10, COR_SUAVE, False)],
        ),
        cartao(vid("m-c1"), "Receita de Itens", 32, 96, 240),
        cartao(vid("m-c2"), "Margem Bruta R$", 286, 96, 240),
        cartao(vid("m-c3"), "% Margem Bruta", 540, 96, 240, destaque=True),
        cartao(vid("m-c4"), "Margem Líquida R$", 794, 96, 240),
        cartao(vid("m-c5"), "% Margem Líquida", 1048, 96, 200),
        visual(
            vid("m-cat"), "clusteredBarChart", 32, 206, 608, 290,
            query={
                "Category": {"projections": [coluna("dim_produto", "categoria",
                                                    ativo=True)]},
                "Y": {"projections": [medida("Receita de Itens"),
                                      medida("Margem Líquida R$")]},
            },
            header=titulo("Receita e margem não seguem a mesma ordem — "
                          "categoria que mais vende não é a que mais dá lucro"),
        ),
        visual(
            vid("m-prod"), "tableEx", 654, 206, 594, 290,
            query={
                # Sem `ativo=True`: em `tableEx`, marcar uma projeção como
                # ativa faz o visual tratar o conjunto como hierarquia e
                # exibir só ela — a tabela veio com uma coluna e nenhuma
                # linha. Nas 84 projeções de `tableEx` dos projetos de
                # referência, `active` não aparece nenhuma vez.
                "Values": {"projections": [
                    coluna("dim_produto", "produto"),
                    coluna("dim_produto", "categoria"),
                    medida("Itens Vendidos"),
                    medida("Receita de Itens"),
                    medida("% Margem Líquida"),
                ]}
            },
            header=titulo("Produtos por margem — o detalhe que o gráfico esconde"),
        ),
        visual(
            vid("m-mes"), "lineChart", 32, 510, 1216, 182,
            query={
                "Category": {"projections": [coluna("dim_data", "ano_mes", ativo=True)]},
                "Y": {"projections": [medida("% Margem Líquida")]},
            },
            header=titulo("A margem percentual é estável no tempo — "
                          "o crescimento vem de volume, não de preço"),
        ),
    ]
    return "Vendas e margem", v


def pagina_clientes(vid: Callable[[str], str]) -> tuple[str, list[dict]]:
    v = [
        texto_livre(
            vid("c-tit"), 32, 24, 1100, 68,
            [("Clientes de elite — Questão 4", 20, COR_TEXTO, True),
             ("Ticket médio alto e compra em muitas categorias. "
              "O ranking usa ticket médio, com desempate por customer_id.",
              10, COR_SUAVE, False)],
        ),
        texto_livre(
            vid("c-critica"), 32, 92, 1216, 54,
            [("O filtro de diversidade não filtra: só existem 14 categorias na "
              "loja, e 1.971 de 2.000 clientes (98,5%) compraram de 13 ou mais. "
              "Na prática, o ranking é ordenado só pelo ticket médio.",
              10, COR_DESTAQUE, False)],
        ),
        cartao(vid("c-c1"), "Clientes", 32, 148, 240),
        cartao(vid("c-c2"), "Ticket Médio", 286, 148, 240),
        cartao(vid("c-c3"), "Nº Pedidos", 540, 148, 240),
        cartao(vid("c-c4"), "Itens Vendidos", 794, 148, 240),
        cartao(vid("c-c5"), "Taxa de Devolução", 1048, 148, 200),
        visual(
            vid("c-top10"), "tableEx", 32, 258, 640, 250,
            query={
                "Values": {"projections": [  # sem `ativo` — ver nota em pagina_margem
                    coluna("dim_cliente", "customer_id"),
                    coluna("dim_cliente", "cliente"),
                    coluna("dim_cliente", "ticket_medio"),
                    coluna("dim_cliente", "frequencia"),
                    coluna("dim_cliente", "faturamento_total"),
                    coluna("dim_cliente", "diversidade_categorias"),
                ]}
            },
            header=titulo("Os 10 fiéis — use o filtro de elite ao lado"),
        ),
        visual(
            vid("c-elite"), "slicer", 686, 258, 260, 116,
            query={"Values": {"projections": [
                coluna("dim_cliente", "flag_elite", ativo=True)]}},
            header=titulo("Só os 10 de elite"),
        ),
        visual(
            vid("c-disp"), "clusteredBarChart", 960, 258, 288, 250,
            query={
                "Category": {"projections": [coluna("dim_cliente", "cliente",
                                                    ativo=True)]},
                "Y": {"projections": [medida("Ticket Médio"),
                                      medida("Receita Bruta")]},
            },
            header=titulo("Ticket alto não é o mesmo que cliente valioso"),
        ),
        visual(
            vid("c-cat"), "clusteredBarChart", 686, 388, 260, 120,
            query={
                "Category": {"projections": [coluna("dim_produto", "categoria",
                                                    ativo=True)]},
                "Y": {"projections": [medida("Itens Vendidos")]},
            },
            header=titulo("Hélices lidera o grupo"),
        ),
        texto_livre(
            vid("c-nota"), 32, 522, 1216, 170,
            [
                ("O que o ranking premia, e o que ele deixa passar", 12, COR_TEXTO, True),
                ("Ordenar por ticket médio premia quem compra caro e raro em cima "
                 "de quem compra muito. O cliente 1116 tem o 4º maior ticket e "
                 "R$ 655 mil de faturamento; o cliente 1722 tem o 10º ticket e "
                 "R$ 1,15 milhão — 75% a mais.", 10, COR_SUAVE, False),
                ("Se o objetivo declarado é replicar o comportamento em outros "
                 "segmentos, o comportamento de 1722 provavelmente interessa mais. "
                 "Um critério de RFM (recência, frequência, valor) discriminaria o "
                 "que o filtro de 13 categorias não discrimina.", 10, COR_SUAVE, False),
            ],
        ),
    ]
    return "Clientes (Q4)", v


def pagina_sazonalidade(vid: Callable[[str], str]) -> tuple[str, list[dict]]:
    v = [
        texto_livre(
            vid("z-tit"), 32, 24, 1100, 68,
            [("Quinta-feira é o pior dia — e o cálculo ingênuo aponta outro",
              20, COR_TEXTO, True),
             ("Lojas físicas · 2.557 dias de calendário · 78 deles sem nenhuma venda",
              10, COR_SUAVE, False)],
        ),
        cartao(vid("z-c1"), "Média de Venda por Dia POS", 32, 92, 300, destaque=True),
        cartao(vid("z-c2"), "Média por Dia (só dias com venda)", 346, 92, 300),
        cartao(vid("z-c3"), "Dias sem Venda", 660, 92, 240),
        cartao(vid("z-c4"), "Inflação da Média (erro do estagiário)", 914, 92, 334),
        visual(
            vid("z-comp"), "clusteredBarChart", 32, 202, 760, 300,
            query={
                "Category": {"projections": [coluna("dim_data", "dia_semana",
                                                    ativo=True)]},
                "Y": {"projections": [
                    medida("Média de Venda por Dia POS"),
                    medida("Média por Dia (só dias com venda)"),
                ]},
            },
            header=titulo("O visual mais importante do painel: as duas médias lado "
                          "a lado. A correta (barra escura) coloca a quinta em "
                          "último; a do estagiário coloca a segunda."),
        ),
        visual(
            vid("z-vazios"), "clusteredColumnChart", 806, 202, 442, 300,
            query={
                "Category": {"projections": [coluna("dim_data", "dia_semana",
                                                    ativo=True)]},
                "Y": {"projections": [medida("Dias sem Venda")]},
            },
            header=titulo("A quinta tem 20 dias vazios contra 7 da segunda — "
                          "é essa desigualdade que inverte o ranking"),
        ),
        texto_livre(
            vid("z-nota"), 32, 516, 760, 176,
            [
                ("Por que o erro é perigoso, e por que a recomendação é não fechar",
                 12, COR_TEXTO, True),
                ("Se o erro fosse uniforme, ele seria inofensivo para o ranking: "
                 "todos os dias inflariam igual e a ordem sobreviveria. Ele não é. "
                 "Remover 20 dias vazios do denominador da quinta sobe a média dela "
                 "em R$ 9.084 (+5,78%) e a tira do último lugar; a segunda, com 7 "
                 "vazios, sobe só R$ 3.094 (+1,96%) e cai para lá.", 10, COR_SUAVE, False),
                ("Mas a diferença entre o pior dia e o melhor é de apenas 10,5%, e "
                 "entre quinta e domingo é de 0,3%. Isso é ruído, não sazonalidade. "
                 "Nenhum dia da semana justifica fechar a loja.", 10, COR_DESTAQUE, False),
            ],
        ),
        visual(
            vid("z-ano"), "clusteredColumnChart", 806, 516, 442, 176,
            query={
                "Category": {"projections": [coluna("dim_data", "ano", ativo=True)]},
                "Y": {"projections": [medida("Dias sem Venda")]},
            },
            header=titulo("Dia sem venda é fenômeno de ramp-up: 25 em 2020, 1 em 2025"),
        ),
    ]
    return "Sazonalidade (Q5)", v


def pagina_modelos(vid: Callable[[str], str]) -> tuple[str, list[dict]]:
    v = [
        texto_livre(
            vid("p-tit"), 32, 24, 1100, 72,
            [("Previsão e recomendação — Questões 6 e 7", 20, COR_TEXTO, True),
             ("Dois modelos baseline, e a evidência de que nenhum dos dois "
              "deveria ir para produção como está.", 10, COR_SUAVE, False)],
        ),
        visual(
            vid("p-serie"), "lineChart", 32, 96, 760, 288,
            query={
                "Category": {"projections": [coluna("fct_previsao_bussola", "ano_mes",
                                                    ativo=True)]},
                # Quatro MEDIDAS em Y, não uma coluna com papel Series: é o
                # padrão multi-série comprovado para lineChart.
                "Y": {"projections": [
                    medida("Unidades Realizadas"),
                    medida("Previsão — Média Móvel 3m"),
                    medida("Previsão — Seasonal Naive"),
                    medida("Previsão — Naive"),
                ]},
            },
            header=titulo("A média móvel prevê 116 unidades e o real foi 207 — "
                          "erra 44% porque uma média é um número plano e a série "
                          "cresce 82% em seis anos"),
        ),
        texto_livre(
            vid("p-nota6"), 806, 96, 442, 288,
            [
                ("Questão 6 — por que o baseline não serve", 12, COR_TEXTO, True),
                ("Não é 'usou meses de baixa para prever meses de pico': out–dez "
                 "vale 39,6 un./mês contra 35,9 de jan–mar. A janela estava do "
                 "lado certo do ciclo.", 10, COR_SUAVE, False),
                ("As causas reais são a tendência (o Q1 saiu de 64 unidades em 2020 "
                 "para 207 em 2026) e dez/2025 ter vendido 22 contra uma média "
                 "histórica de 45,6 — sozinho, esse mês derruba a previsão em 24 "
                 "unidades no trimestre.", 10, COR_SUAVE, False),
                ("O seasonal naive, que só repete o ano anterior, tem MAE de 25,0 "
                 "contra 30,3 da média móvel. O baseline pedido perde para a regra "
                 "mais simples que existe.", 10, COR_DESTAQUE, False),
            ],
        ),
        visual(
            vid("p-sim"), "clusteredBarChart", 32, 398, 500, 294,
            query={
                "Category": {"projections": [coluna("fct_similaridade_produto",
                                                    "produto", ativo=True)]},
                "Y": {"projections": [medida("Similaridade de Cosseno")]},
            },
            header=titulo("Top similares ao Motor de Popa 1949 — o 1º ganha do 2º "
                          "por 0,0003"),
        ),
        visual(
            vid("p-cesta"), "clusteredBarChart", 546, 398, 500, 294,
            query={
                "Category": {"projections": [coluna("fct_similaridade_produto",
                                                    "produto", ativo=True)]},
                "Y": {"projections": [medida("Pedidos em Comum")]},
            },
            header=titulo("Co-ocorrência no mesmo pedido — a pergunta que a Marina "
                          "realmente fez, e a resposta muda"),
        ),
        texto_livre(
            vid("p-nota7"), 1060, 398, 188, 294,
            [
                ("Questão 7", 12, COR_TEXTO, True),
                ("Os três primeiros estão a 2,40 / 2,39 / 2,38 desvios da média. "
                 "São indistinguíveis.", 9, COR_SUAVE, False),
                ("O top-1 é outro motor de popa: a métrica encontra substitutos, "
                 "e cross-sell precisa de complementos.", 9, COR_DESTAQUE, False),
                ("Por cesta, o vizinho mais frequente é Tinta Antifouling — que "
                 "faz sentido de negócio.", 9, COR_SUAVE, False),
            ],
        ),
    ]
    return "Previsão e recomendação (Q6-Q7)", v


PAGINAS = [
    pagina_sumario,
    pagina_margem,
    pagina_clientes,
    pagina_sazonalidade,
    pagina_modelos,
]


# ==========================================================================
#  ESCRITA
# ==========================================================================

def gerar_relatorio(
    saida: Path, nome_modelo: str, nome_relatorio: str,
    guid: Callable[[str], str], id_curto: Callable[[str], str],
) -> None:
    rep = saida / f"{nome_relatorio}.Report"
    definicao = rep / "definition"
    (definicao / "pages").mkdir(parents=True, exist_ok=True)
    (rep / "StaticResources" / "RegisteredResources").mkdir(parents=True, exist_ok=True)

    (rep / ".platform").write_text(
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/"
                           "gitIntegration/platformProperties/2.0.0/schema.json",
                "metadata": {"type": "Report", "displayName": nome_relatorio},
                "config": {"version": "2.0", "logicalId": guid("report")},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    (rep / "definition.pbir").write_text(
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/"
                           "report/definitionProperties/2.0.0/schema.json",
                "version": "4.0",
                "datasetReference": {
                    "byPath": {"path": f"../{nome_modelo}.SemanticModel"}
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    (definicao / "version.json").write_text(
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/"
                           "report/definition/versionMetadata/1.0.0/schema.json",
                "version": "2.0.0",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    tema = {
        "name": "tema_lh_nautical",
        "dataColors": [COR_PRIMARIA, COR_DESTAQUE, "#2E8AA8", "#8FB4C4",
                       "#C46A1F", "#54707F", "#A9C3CE", "#3D5666"],
        "background": COR_FUNDO,
        "foreground": COR_TEXTO,
        "tableAccent": COR_PRIMARIA,
        "textClasses": {
            "title": {"fontFace": "Segoe UI Semibold", "fontSize": 13,
                      "color": COR_TEXTO},
            "label": {"fontFace": "Segoe UI", "fontSize": 9, "color": COR_SUAVE},
        },
        "visualStyles": {
            "*": {
                "*": {
                    "background": [{"show": True, "color": {"solid": {"color": COR_CARTAO}},
                                    "transparency": 0}],
                    "border": [{"show": True, "color": {"solid": {"color": COR_BORDA}},
                                "radius": 6}],
                }
            }
        },
    }
    (rep / "StaticResources" / "RegisteredResources" / "tema_lh_nautical.json").write_text(
        json.dumps(tema, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    (definicao / "report.json").write_text(
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/"
                           "report/definition/report/3.3.0/schema.json",
                "themeCollection": {
                    "customTheme": {
                        "name": "tema_lh_nautical.json",
                        # Campo OBRIGATÓRIO. Sem ele o Desktop recusa o
                        # report.json. As versões são as mesmas dos $schema
                        # usados nos arquivos gerados aqui.
                        "reportVersionAtImport": {
                            "visual": "2.9.0",
                            "report": "3.3.0",
                            "page": "2.1.0",
                        },
                        "type": "RegisteredResources",
                    }
                },
                "resourcePackages": [
                    {
                        "name": "RegisteredResources",
                        "type": "RegisteredResources",
                        "items": [
                            {
                                "name": "tema_lh_nautical.json",
                                "path": "tema_lh_nautical.json",
                                "type": "CustomTheme",
                            }
                        ],
                    }
                ],
                "settings": {"useStylableVisualContainerHeader": True},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    ordem: list[str] = []
    for i, construtor in enumerate(PAGINAS):
        nome_exibicao, visuais = construtor(lambda s, _i=i: id_curto(f"visual{_i}:{s}"))
        pid = id_curto(f"page:{nome_exibicao}")
        ordem.append(pid)

        pasta = definicao / "pages" / pid
        (pasta / "visuals").mkdir(parents=True, exist_ok=True)

        (pasta / "page.json").write_text(
            json.dumps(
                {
                    "$schema": "https://developer.microsoft.com/json-schemas/fabric/"
                               "item/report/definition/page/2.1.0/schema.json",
                    "name": pid,
                    "displayName": nome_exibicao,
                    "displayOption": "FitToPage",
                    "height": ALTURA,
                    "width": LARGURA,
                    "objects": {
                        "background": [
                            {"properties": {"color": cor(COR_FUNDO),
                                            "transparency": lit("0D")}}
                        ]
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        for vis in visuais:
            vpasta = pasta / "visuals" / vis["name"]
            vpasta.mkdir(parents=True, exist_ok=True)
            (vpasta / "visual.json").write_text(
                json.dumps(vis, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        print(f"  Página: {nome_exibicao:<34} {len(visuais):>2} visuais")

    (definicao / "pages" / "pages.json").write_text(
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/"
                           "report/definition/pagesMetadata/1.0.0/schema.json",
                "pageOrder": ordem,
                "activePageName": ordem[0],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
