#!/usr/bin/env python3
"""
Gera o projeto Power BI (PBIP + TMDL) da LH Nautical a partir dos Parquets.

    python3 powerbi/gerar_pbip.py

POR QUE UM GERADOR, E NÃO UM .pbix CLICADO
------------------------------------------
O modelo tem 14 tabelas e ~18 medidas. Construir isso na interface e depois
mantê-lo sincronizado com a camada gold é trabalho manual repetido a cada
mudança de schema — e é onde entram os erros que ninguém percebe, do tipo
"a coluna mudou de nome e a medida continuou apontando para a antiga".

Aqui as colunas do TMDL são derivadas do SCHEMA REAL dos Parquets. Se o gold
mudar, o modelo muda junto. E o projeto inteiro fica em texto, versionado no
git, revisável em diff — que é a razão de o formato PBIP existir.

Os `lineageTag` são GUIDs derivados de hash do nome do objeto, não aleatórios:
assim regerar o projeto não produz um diff gigante de identificadores.

Autor: Breno Teodomiro · Desafio Técnico Lighthouse 2026 (Indicium)
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PARQUET = RAIZ / "dados" / "gold"
SAIDA = RAIZ / "powerbi"

NOME_MODELO = "sm_lh_nautical"
NOME_RELATORIO = "rel_lh_nautical"
NOME_PBIP = "lh_nautical"


def caminho_windows(caminho: Path) -> str:
    """Converte um caminho do WSL para a forma que o Windows entende.

    O gerador roda no WSL e enxerga `/mnt/c/PROJETOS/...`; o Power BI Desktop
    roda no Windows e precisa de `C:\\PROJETOS\\...`. Gravar o caminho do WSL no
    parâmetro produziria um projeto que abre e falha na atualização, com uma
    mensagem que não aponta para a causa.
    """
    texto = str(caminho)
    if texto.startswith("/mnt/") and len(texto) > 6 and texto[6] == "/":
        letra = texto[5].upper()
        return f"{letra}:" + texto[6:].replace("/", "\\")
    return texto.replace("/", "\\") if "\\" not in texto else texto


def guid(semente: str) -> str:
    """GUID determinístico a partir de um nome. Ver nota no cabeçalho."""
    h = hashlib.sha1(f"lh_nautical::{semente}".encode()).hexdigest()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def id_curto(semente: str) -> str:
    """Identificador de 20 hex — formato que o PBIR usa para páginas/visuais."""
    return hashlib.sha1(f"lh_nautical::{semente}".encode()).hexdigest()[:20]


# ==========================================================================
# §1  MAPEAMENTO DE TIPOS
# ==========================================================================

def tipo_tmdl(dtype: str) -> tuple[str, str, str]:
    """(dataType TMDL, summarizeBy, formatString) para um dtype do pandas."""
    d = str(dtype)
    if d.startswith("datetime"):
        return "dateTime", "none", "yyyy-mm-dd"
    if d.startswith(("int", "uint")):
        return "int64", "sum", "#,##0"
    if d.startswith("float"):
        return "double", "sum", "#,##0.00"
    if d.startswith("bool"):
        return "boolean", "none", ""
    return "string", "none", ""


# Colunas que NÃO devem ser somadas apesar de numéricas: são chaves ou
# identificadores. Somar um product_id não significa nada, e deixar o Power BI
# sugerir isso na lista de campos é convite a erro.
CHAVES = {
    "order_id", "order_item_id", "customer_id", "product_id",
    "product_variant_id", "location_id", "payment_id", "return_id",
    "return_item_id", "category_id", "num_dia_semana", "num_mes",
    "num_trimestre", "ano", "posicao",
}

# Colunas ocultas no relatório: existem para relacionamento ou ordenação.
OCULTAS = {
    "order_id", "order_item_id", "payment_id", "return_id", "return_item_id",
    "product_variant_id", "num_dia_semana", "num_mes", "num_trimestre",
}

DESCRICOES_TABELA = {
    "dim_data": (
        "Dimensão de datas densa, cobrindo todos os dias entre o primeiro e o\n"
        "último pedido.\n"
        "\n"
        "`eh_futuro` é a coluna que permite sombrear a área posterior a hoje nos\n"
        "visuais: 8,7% dos pedidos têm data futura, e apresentá-los como\n"
        "realizados é a armadilha nº 2 do diagnóstico da Questão 1."
    ),
    "dim_cliente": (
        "Um cliente por linha, com as métricas da Questão 4 pré-calculadas.\n"
        "\n"
        "`flag_elite` marca os 10 clientes fiéis. Ele vem do SQL, não de DAX:\n"
        "a regra de desempate (ticket médio desc, customer_id asc) já está\n"
        "resolvida na camada gold, e reimplementá-la em DAX seria a segunda\n"
        "implementação da mesma regra."
    ),
    "dim_produto": (
        "Um produto por linha (500). `produto` é o nome de exibição: recebe o id\n"
        "quando há homônimo, e vira '[sem nome]' quando o cadastro traz lixo.\n"
        "\n"
        "`flag_nome_suspeito` preserva a evidência do problema de cadastro em vez\n"
        "de escondê-la — o item continua no modelo e continua visível."
    ),
    "dim_status_pedido": (
        "A dimensão que resolve toda a ambiguidade de status do projeto.\n"
        "\n"
        "14,7% do GMV são pedidos `cancelled` ou `draft`, que nunca viraram\n"
        "receita. Em vez de enterrar essa decisão num WHERE, ela vira o atributo\n"
        "`eh_receita_efetivada` e o leitor decide no slicer."
    ),
    "fct_pedido": (
        "Grão: PEDIDO (48.998). Única origem de ticket médio e contagem de\n"
        "pedidos.\n"
        "\n"
        "Existe separada de fct_item_pedido porque `total` é do grão pedido: se\n"
        "morasse no fato de itens, o valor se repetiria por item e qualquer soma\n"
        "inflaria 3,67x."
    ),
    "fct_item_pedido": (
        "Grão: LINHA DE ITEM (147.320). Mix de produto, categoria e margem.\n"
        "\n"
        "NÃO contém `orders.total`, de propósito — se contivesse, alguém somaria.\n"
        "O desconto do pedido chega aqui já rateado por participação da linha, e\n"
        "a soma do rateio reproduz orders.discount_amount ao centavo."
    ),
    "fct_pagamento": (
        "ISOLADO DO MODELO, sem nenhum relacionamento. É deliberado.\n"
        "\n"
        "`payments` faz fan-out 2:1 — 6.999 pedidos têm dois pagamentos. Se\n"
        "estivesse relacionado, um filtro de método de pagamento inflaria o\n"
        "faturamento em 9,3%. Serve para responder perguntas SOBRE pagamento\n"
        "(mix de método, parcelamento) e nada mais.\n"
        "\n"
        "A ausência do relacionamento está documentada aqui para que ninguém a\n"
        "'conserte' depois."
    ),
    "fct_venda_diaria_pos": (
        "Grão: DIA de loja física, denso — 2.557 linhas, incluindo os 78 dias em\n"
        "que a loja abriu e não vendeu nada.\n"
        "\n"
        "É a densidade que torna a Questão 5 possível: sem os dias de valor zero,\n"
        "a média por dia da semana passa a ser média condicionada a ter havido\n"
        "venda, que é outra pergunta e aponta outro dia."
    ),
    "fct_previsao_bussola": (
        "Série mensal da Bússola de Bordo 702 (Questão 6), em formato longo:\n"
        "realizado e três modelos na mesma coluna `unidades`, discriminados por\n"
        "`serie`. Formato longo para que um único visual de linhas compare todos."
    ),
    "fct_similaridade_produto": (
        "As 499 similaridades de cosseno do 'Motor de Popa 1949' (Questão 7).\n"
        "\n"
        "`desvios_da_media` é a coluna que sustenta a conclusão honesta: os três\n"
        "primeiros estão a 2,40 / 2,39 / 2,38 sigma, ou seja, estatisticamente\n"
        "indistinguíveis. `pedidos_em_comum` traz a co-ocorrência de cesta, que é\n"
        "a formulação correta do problema."
    ),
}


# ==========================================================================
# §2  MEDIDAS DAX
# ==========================================================================

MEDIDAS: list[tuple[str, str, str, str, str]] = [
    # (nome, expressão DAX, formatString, pasta, descrição)
    (
        "Nº Pedidos",
        "COUNTROWS(fct_pedido)",
        "#,##0",
        "1 Vendas",
        "Contagem de transações. Sai de fct_pedido, nunca do fato de itens.",
    ),
    (
        "Receita Bruta",
        "SUM(fct_pedido[total])",
        "R$ #,##0",
        "1 Vendas",
        "GMV: soma de orders.total, TODOS os status. É o número da leitura\n"
        "literal do enunciado — inclui pedidos cancelados e rascunhos.",
    ),
    (
        "Receita Efetivada",
        "CALCULATE([Receita Bruta], dim_status_pedido[eh_receita_efetivada] = TRUE())",
        "R$ #,##0",
        "1 Vendas",
        "Só `paid` e `confirmed`. A diferença para a Receita Bruta é de\n"
        "R$ 207,1 milhões (14,7%) — pedidos que nunca viraram receita.",
    ),
    (
        "Ticket Médio",
        "DIVIDE([Receita Bruta], [Nº Pedidos])",
        "R$ #,##0.00",
        "1 Vendas",
        "Receita dividida por número de PEDIDOS. Como as duas parcelas saem de\n"
        "fct_pedido, é imune ao fan-out de itens e de pagamentos.",
    ),
    (
        "Taxa de Cancelamento",
        "DIVIDE(\n"
        "    CALCULATE([Nº Pedidos], dim_status_pedido[status] = \"cancelled\"),\n"
        "    CALCULATE([Nº Pedidos], ALL(dim_status_pedido))\n"
        ")",
        "0.0%",
        "1 Vendas",
        "ALL(dim_status_pedido) no denominador para que a taxa continue correta\n"
        "mesmo com o slicer de status aplicado.",
    ),
    (
        "Receita de Itens",
        "SUM(fct_item_pedido[valor_linha])",
        "R$ #,##0",
        "2 Margem",
        "Soma de line_total. Difere da Receita Bruta porque não desconta o\n"
        "desconto do pedido — é a base sobre a qual a margem é calculada.",
    ),
    (
        "Margem Bruta R$",
        "SUM(fct_item_pedido[margem_bruta])",
        "R$ #,##0",
        "2 Margem",
        "valor_linha − (quantidade × custo), antes do desconto do pedido.",
    ),
    (
        "Margem Líquida R$",
        "SUM(fct_item_pedido[margem_liquida])",
        "R$ #,##0",
        "2 Margem",
        "Margem bruta menos o desconto do pedido rateado pela participação da\n"
        "linha. O rateio reproduz orders.discount_amount ao centavo.",
    ),
    (
        "% Margem Bruta",
        "DIVIDE([Margem Bruta R$], [Receita de Itens])",
        "0.00%",
        "2 Margem",
        "Referência do dataset: 42,58%.",
    ),
    (
        "% Margem Líquida",
        "DIVIDE([Margem Líquida R$], [Receita de Itens])",
        "0.00%",
        "2 Margem",
        "Referência do dataset: 40,44%.",
    ),
    (
        "Itens Vendidos",
        "SUM(fct_item_pedido[quantidade])",
        "#,##0",
        "2 Margem",
        "Unidades. É a medida da Questão 4 — Hélices lidera com 492 itens entre\n"
        "os 10 clientes de elite.",
    ),
    (
        "Média de Venda por Dia POS",
        "DIVIDE(\n"
        "    SUM(fct_venda_diaria_pos[valor_venda]),\n"
        "    COUNTROWS(fct_venda_diaria_pos)\n"
        ")",
        "R$ #,##0",
        "3 Sazonalidade",
        "A MEDIDA DA QUESTÃO 5. O denominador é a contagem de linhas do fato\n"
        "denso, ou seja, TODOS os dias do calendário — inclusive os 78 em que a\n"
        "loja abriu e não vendeu nada.\n"
        "\n"
        "Comparar com 'Média por Dia (só dias com venda)' é o argumento inteiro\n"
        "da questão.",
    ),
    (
        "Média por Dia (só dias com venda)",
        "DIVIDE(\n"
        "    SUM(fct_venda_diaria_pos[valor_venda]),\n"
        "    CALCULATE(\n"
        "        COUNTROWS(fct_venda_diaria_pos),\n"
        "        fct_venda_diaria_pos[dia_sem_venda] = FALSE()\n"
        "    )\n"
        ")",
        "R$ #,##0",
        "3 Sazonalidade",
        "O ERRO DO ESTAGIÁRIO, reproduzido de propósito para a comparação lado a\n"
        "lado. Divide só pelos dias em que houve venda — que é o que um GROUP BY\n"
        "direto na tabela de vendas produz.\n"
        "\n"
        "Aponta Segunda-feira como pior dia. A medida correta aponta\n"
        "Quinta-feira.",
    ),
    (
        "Dias sem Venda",
        "CALCULATE(\n"
        "    COUNTROWS(fct_venda_diaria_pos),\n"
        "    fct_venda_diaria_pos[dia_sem_venda] = TRUE()\n"
        ")",
        "#,##0",
        "3 Sazonalidade",
        "78 no período. Concentrados nos anos iniciais: 25 em 2020, 1 em 2025 —\n"
        "é fenômeno de operação em ramp-up, não característica atual.",
    ),
    (
        "Inflação da Média (erro do estagiário)",
        "DIVIDE(\n"
        "    [Média por Dia (só dias com venda)] - [Média de Venda por Dia POS],\n"
        "    [Média de Venda por Dia POS]\n"
        ")",
        "0.00%",
        "3 Sazonalidade",
        "O tamanho do erro por dia da semana. Não é uniforme: +5,78% na quinta\n"
        "contra +1,96% na segunda. É essa desigualdade que inverte o ranking.",
    ),
    (
        "Clientes",
        "DISTINCTCOUNT(fct_pedido[customer_id])",
        "#,##0",
        "4 Clientes",
        "",
    ),
    (
        "Diversidade de Categorias",
        "DISTINCTCOUNT(dim_produto[category_id])",
        "#,##0",
        "4 Clientes",
        "Categorias distintas no contexto atual. Só existem 14 na loja — e\n"
        "1.971 de 2.000 clientes compraram de 13 ou mais, o que é a razão de o\n"
        "filtro de elite da Questão 4 não discriminar praticamente ninguém.",
    ),
    (
        "Taxa de Devolução",
        "DIVIDE(SUM(fct_devolucao[quantidade]), [Itens Vendidos])",
        "0.00%",
        "5 Pós-venda",
        "Unidades devolvidas sobre unidades vendidas.",
    ),
    (
        "Valor em Estoque",
        "SUM(fct_estoque_atual[valor_em_estoque])",
        "R$ #,##0",
        "5 Pós-venda",
        "Quantidade em mãos avaliada ao custo.",
    ),
]


# ==========================================================================
# §3  RELACIONAMENTOS
# ==========================================================================

RELACIONAMENTOS = [
    ("dim_data", "data", "fct_pedido", "data"),
    ("dim_data", "data", "fct_item_pedido", "data"),
    ("dim_data", "data", "fct_venda_diaria_pos", "data"),
    ("dim_data", "data", "fct_devolucao", "data"),
    ("dim_cliente", "customer_id", "fct_pedido", "customer_id"),
    ("dim_cliente", "customer_id", "fct_item_pedido", "customer_id"),
    ("dim_produto", "product_id", "fct_item_pedido", "product_id"),
    ("dim_produto", "product_id", "fct_devolucao", "product_id"),
    ("dim_produto", "product_id", "fct_estoque_atual", "product_id"),
    ("dim_local", "location_id", "fct_pedido", "location_id"),
    ("dim_local", "location_id", "fct_item_pedido", "location_id"),
    ("dim_local", "location_id", "fct_estoque_atual", "location_id"),
    ("dim_canal", "canal", "fct_pedido", "canal"),
    ("dim_canal", "canal", "fct_item_pedido", "canal"),
    ("dim_status_pedido", "status", "fct_pedido", "status"),
    ("dim_status_pedido", "status", "fct_item_pedido", "status"),
]


# ==========================================================================
# §4  GERAÇÃO DO SEMANTIC MODEL
# ==========================================================================

def escrever_tmdl(caminho: Path, texto: str) -> None:
    """Grava um .tmdl com quebra de linha CRLF.

    É o que o Power BI Desktop escreve, e é o formato dos projetos PBIP que
    já abrem nesta máquina. O parser provavelmente aceita LF, mas num artefato
    que não dá para testar localmente, divergir do que comprovadamente funciona
    é trocar risco por nada.
    """
    caminho.write_text(texto, encoding="utf-8", newline="\r\n")


def bloco_doc(texto: str, nivel: int = 0) -> list[str]:
    """Converte texto em comentário de documentação TMDL (///).

    ATENÇÃO — duas regras que o parser do TMDL impõe e que não perdoam:

    1. `///` é a DESCRIÇÃO de um objeto, não um comentário livre. O bloco tem
       de vir colado à declaração que ele descreve. Uma linha em branco entre
       os dois faz o parser abortar com "Unexpected line type: Empty!".
    2. Não existe comentário solto no TMDL. Nota que não descreve um objeto
       não vai no arquivo — vai no MODELO.md ou aqui no gerador.

    A linha vazia sai como `/// ` COM espaço final, que é o que o Desktop
    escreve.
    """
    if not texto:
        return []
    tab = "\t" * nivel
    return [f"{tab}/// {linha}" for linha in texto.split("\n")]


def gerar_tabela_tmdl(nome: str, df: pd.DataFrame) -> str:
    linhas: list[str] = []
    linhas += bloco_doc(DESCRICOES_TABELA.get(nome, ""))
    linhas.append(f"table {nome}")
    linhas.append(f"\tlineageTag: {guid('table:' + nome)}")
    # NÃO emitimos `dataCategory: Time` nem `isKey` em dim_data. São a forma
    # declarativa de "marcar como tabela de datas", mas são os dois únicos
    # construtos que não aparecem em nenhum projeto PBIP que comprovadamente
    # abre nesta máquina — ou seja, os únicos que eu não consigo verificar.
    # Nenhuma das 19 medidas usa time intelligence, então o modelo funciona
    # igual sem eles. Marcar a tabela é um clique no Desktop
    # (dim_data -> botão direito -> Marcar como tabela de data), e está
    # anotado no ENTREGA.md como passo opcional.
    linhas.append("")

    for coluna in df.columns:
        dt, summ, fmt = tipo_tmdl(df[coluna].dtype)
        if coluna in CHAVES:
            summ = "none"

        linhas.append(f"\tcolumn {coluna}")
        linhas.append(f"\t\tdataType: {dt}")
        if coluna in OCULTAS:
            linhas.append("\t\tisHidden")
        if fmt:
            linhas.append(f"\t\tformatString: {fmt}")
        linhas.append(f"\t\tlineageTag: {guid(f'col:{nome}.{coluna}')}")
        linhas.append(f"\t\tsummarizeBy: {summ}")
        linhas.append(f"\t\tsourceColumn: {coluna}")
        if nome == "dim_data" and coluna == "mes":
            linhas.append("\t\tsortByColumn: num_mes")
        if nome == "dim_data" and coluna == "dia_semana":
            linhas.append("\t\tsortByColumn: num_dia_semana")
        linhas.append("")
        if dt == "dateTime":
            linhas.append("\t\tannotation UnderlyingDateTimeDataType = Date")
            linhas.append("")

    # Partição: Import de Parquet. Ver a nota no README sobre por que não é
    # conexão viva ao PostgreSQL.
    linhas.append(f"\tpartition {nome} = m")
    linhas.append("\t\tmode: import")
    linhas.append("\t\tsource =")
    linhas.append("\t\t\t\tlet")
    linhas.append(
        f'\t\t\t\t\tArquivo = File.Contents(#"PastaDados" & "\\{nome}.parquet"),'
    )
    linhas.append("\t\t\t\t\tTabela = Parquet.Document(Arquivo)")
    linhas.append("\t\t\t\tin")
    linhas.append("\t\t\t\t\tTabela")
    linhas.append("")
    linhas.append("\tannotation PBI_ResultType = Table")
    linhas.append("")
    return "\n".join(linhas)


def gerar_medidas_tmdl() -> str:
    linhas: list[str] = []
    linhas += bloco_doc(
        "Todas as medidas do modelo, agrupadas por displayFolder.\n"
        "\n"
        "Ficam numa tabela própria para que a lista de campos mostre dimensões e\n"
        "medidas separadas, em vez de medidas espalhadas por seis fatos.\n"
        "\n"
        "REGRA DESTE MODELO: medida que envolve grão ou fan-out explica na\n"
        "descrição de qual fato ela sai e por quê. Ticket médio sai sempre de\n"
        "fct_pedido; margem sai sempre de fct_item_pedido."
    )
    linhas.append("table _Medidas")
    linhas.append(f"\tlineageTag: {guid('table:_Medidas')}")
    linhas.append("")

    for nome, dax, fmt, pasta, doc in MEDIDAS:
        linhas += bloco_doc(doc, nivel=1)
        corpo = dax.strip()
        if "\n" in corpo:
            linhas.append(f"\tmeasure '{nome}' =")
            for ln in corpo.split("\n"):
                linhas.append(f"\t\t\t{ln}")
        else:
            linhas.append(f"\tmeasure '{nome}' = {corpo}")
        linhas.append(f"\t\tformatString: {fmt}")
        linhas.append(f"\t\tdisplayFolder: {pasta}")
        linhas.append(f"\t\tlineageTag: {guid('measure:' + nome)}")
        linhas.append("")

    # Coluna técnica: uma tabela TMDL precisa de ao menos uma coluna e uma
    # partição. Fica oculta.
    linhas.append("\tcolumn Coluna")
    linhas.append("\t\tdataType: string")
    linhas.append("\t\tisHidden")
    linhas.append(f"\t\tlineageTag: {guid('col:_Medidas.Coluna')}")
    linhas.append("\t\tsummarizeBy: none")
    linhas.append("\t\tsourceColumn: Coluna")
    linhas.append("")
    linhas.append("\tpartition _Medidas = m")
    linhas.append("\t\tmode: import")
    linhas.append("\t\tsource =")
    linhas.append("\t\t\t\tlet")
    linhas.append('\t\t\t\t\tFonte = #table(type table [Coluna = text], {})')
    linhas.append("\t\t\t\tin")
    linhas.append("\t\t\t\t\tFonte")
    linhas.append("")
    return "\n".join(linhas)


def gerar_semantic_model(tabelas: dict[str, pd.DataFrame], destino: Path) -> None:
    sm = destino / f"{NOME_MODELO}.SemanticModel"
    definicao = sm / "definition"
    (definicao / "tables").mkdir(parents=True, exist_ok=True)

    (sm / ".platform").write_text(
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/"
                           "gitIntegration/platformProperties/2.0.0/schema.json",
                "metadata": {"type": "SemanticModel", "displayName": NOME_MODELO},
                "config": {"version": "2.0", "logicalId": guid("semanticmodel")},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    (sm / "definition.pbism").write_text(
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/"
                           "semanticModel/definitionProperties/1.0.0/schema.json",
                "version": "4.2",
                "settings": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    escrever_tmdl(definicao / "database.tmdl", "database\n\tcompatibilityLevel: 1702\n")

    # Parâmetro de pasta: quem abrir o projeto em outra máquina troca UM valor
    # em vez de reescrever 14 consultas.
    escrever_tmdl(
        definicao / "expressions.tmdl",
        "/// Pasta onde estão os Parquets da camada gold.\n"
        "/// \n"
        "/// É um parâmetro para que abrir o projeto em outra máquina seja trocar\n"
        "/// UM valor, e não reescrever a origem de 14 tabelas.\n"
        f'expression PastaDados = "{caminho_windows(RAIZ / "dados" / "gold")}" '
        'meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
        f"\tlineageTag: {guid('expr:PastaDados')}\n"
        "\n"
        "\tannotation PBI_ResultType = Text\n",
    )

    ordem = list(tabelas.keys()) + ["_Medidas"]
    modelo = [
        "model Model",
        "\tculture: pt-BR",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tdiscourageImplicitMeasures",
        "\tsourceQueryCulture: pt-BR",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        f"annotation PBI_QueryOrder = {json.dumps(ordem + ['PastaDados'])}",
        "",
        "annotation __PBI_TimeIntelligenceEnabled = 0",
        "",
        'annotation PBI_ProTooling = ["DevMode"]',
        "",
    ]
    modelo += [f"ref table {t}" for t in ordem]
    # Sem `ref expression`: o expressions.tmdl é descoberto automaticamente,
    # e nenhum projeto PBIP funcional desta máquina declara a referência.
    # O parâmetro continua listado em PBI_QueryOrder, que é onde ele aparece
    # nos projetos que abrem.
    modelo += [""]
    escrever_tmdl(definicao / "model.tmdl", "\n".join(modelo))

    for nome, df in tabelas.items():
        escrever_tmdl(definicao / "tables" / f"{nome}.tmdl", gerar_tabela_tmdl(nome, df))
    escrever_tmdl(definicao / "tables" / "_Medidas.tmdl", gerar_medidas_tmdl())

    # Sem cabeçalho de comentário: o TMDL não tem comentário livre, e um bloco
    # `///` aqui seria interpretado como descrição do primeiro `relationship`.
    # A documentação do modelo (por que fct_pagamento fica de fora, por que os
    # dois fatos de venda não se relacionam) está em powerbi/MODELO.md.
    rel: list[str] = []
    for dim, col_dim, fato, col_fato in RELACIONAMENTOS:
        rel.append(f"relationship {dim}_{fato}_{col_fato}")
        rel.append(f"\tfromColumn: {fato}.{col_fato}")
        rel.append(f"\ttoColumn: {dim}.{col_dim}")
        rel.append("")
    escrever_tmdl(definicao / "relationships.tmdl", "\n".join(rel))

    print(f"  SemanticModel: {len(tabelas) + 1} tabelas · {len(MEDIDAS)} medidas · "
          f"{len(RELACIONAMENTOS)} relacionamentos")


if __name__ == "__main__":
    from gerar_pbip_relatorio import gerar_relatorio  # noqa: E402

    print(f"Lendo Parquets de {PARQUET}/")
    arquivos = sorted(PARQUET.glob("*.parquet"))
    if not arquivos:
        raise SystemExit(f"erro: nenhum .parquet em {PARQUET}")

    tabelas = {}
    for caminho in arquivos:
        nome = caminho.stem
        if nome == "dataset_unificado":
            continue  # insumo da Q6, não é tabela do modelo
        tabelas[nome] = pd.read_parquet(caminho)
        print(f"  {nome:<28} {len(tabelas[nome]):>7,} linhas · "
              f"{len(tabelas[nome].columns):>2} colunas".replace(",", "."))

    for pasta in (SAIDA / f"{NOME_MODELO}.SemanticModel",
                  SAIDA / f"{NOME_RELATORIO}.Report"):
        if pasta.exists():
            shutil.rmtree(pasta)

    print()
    gerar_semantic_model(tabelas, SAIDA)
    gerar_relatorio(SAIDA, NOME_MODELO, NOME_RELATORIO, guid, id_curto)

    (SAIDA / f"{NOME_PBIP}.pbip").write_text(
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/"
                           "pbipProperties/1.0.0/schema.json",
                "version": "1.0",
                "artifacts": [{"report": {"path": f"{NOME_RELATORIO}.Report"}}],
                "settings": {"enableAutoRecovery": True},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nOK  {SAIDA / (NOME_PBIP + '.pbip')}")
    print("    Abra este arquivo no Power BI Desktop (Preview de projetos PBIP ligado).")
