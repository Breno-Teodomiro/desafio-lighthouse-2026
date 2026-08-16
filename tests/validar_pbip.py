#!/usr/bin/env python3
"""
Valida o projeto PBIP antes de abrir no Power BI Desktop.

    python3 tests/validar_pbip.py

POR QUE ISTO EXISTE
-------------------
O projeto é gerado por script e não há Power BI Desktop nesta máquina para
abri-lo. Sem uma verificação, o primeiro sinal de que uma coluna foi
referenciada com o nome errado seria o Desktop reclamando na frente de quem
for corrigir a prova — tarde demais.

O que dá para checar sem o Power BI, e é checado aqui:

  1. Todo JSON do relatório faz parse.
  2. Toda tabela referenciada por um visual existe no modelo.
  3. Toda COLUNA referenciada por um visual existe naquela tabela.
  4. Toda MEDIDA referenciada por um visual existe em _Medidas.
  5. Toda coluna citada em uma expressão DAX existe.
  6. Todo lado de todo relacionamento aponta para coluna existente.
  7. Toda tabela do TMDL tem partição, e o Parquet correspondente existe.
  8. As páginas listadas em pages.json existem no disco.
  9. Todo tipo físico do Parquet é importável, e bate com o `dataType` do TMDL.
 10. Todo relacionamento tem lado-1 único e sem órfãos NOS DADOS.

As regras 9 e 10 nasceram da terceira tentativa de abrir o projeto: ele abriu,
mas a atualização morreu em `Argumento 'dataType' não pode ser nulo` e todos os
visuais exibiram "(Em branco)". A causa eram tipos Arrow que o conector do
Power BI não mapeia — `large_string` e `null` — invisíveis para qualquer
checagem que só lesse o TMDL.

O que NÃO dá para checar: se o TMDL abre. Isso exige o Desktop.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
PBI = RAIZ / "powerbi"
MODELO = PBI / "sm_lh_nautical.SemanticModel" / "definition"
RELATORIO = PBI / "rel_lh_nautical.Report" / "definition"
PARQUET = RAIZ / "dados" / "gold"


def ler_modelo() -> tuple[dict[str, set[str]], set[str], dict[str, str]]:
    """Devolve (colunas por tabela, medidas, expressão DAX por medida)."""
    tabelas: dict[str, set[str]] = {}
    medidas: set[str] = set()
    dax: dict[str, str] = {}

    for arquivo in sorted((MODELO / "tables").glob("*.tmdl")):
        # Normaliza CRLF: os .tmdl são gravados com quebra do Windows, e sem
        # isto todo grupo capturado terminaria com um '\r' pendurado.
        texto = arquivo.read_text(encoding="utf-8").replace("\r\n", "\n")
        nome_tabela = None
        for linha in texto.split("\n"):
            m = re.match(r"^table\s+(.+)$", linha)
            if m:
                nome_tabela = m.group(1).strip().strip("'")
                tabelas[nome_tabela] = set()
                continue
            m = re.match(r"^\tcolumn\s+(.+)$", linha)
            if m and nome_tabela:
                tabelas[nome_tabela].add(m.group(1).strip().strip("'"))
                continue
            m = re.match(r"^\tmeasure\s+'([^']+)'", linha) or re.match(
                r"^\tmeasure\s+([^\s=]+)\s*=", linha
            )
            if m:
                medidas.add(m.group(1))

        # Expressões DAX, para checar as colunas citadas nelas.
        for m in re.finditer(r"^\tmeasure\s+'([^']+)'\s*=(.*?)(?=^\t\t\w+:|\Z)",
                             texto, re.S | re.M):
            dax[m.group(1)] = m.group(2)

    return tabelas, medidas, dax


# Vocabulário TMDL comprovado: só o que aparece em projetos PBIP que ABREM
# no Power BI Desktop desta máquina. `dataCategory` e `isKey` foram removidos
# do gerador justamente por não estarem nesta lista — eram os únicos
# construtos sem referência funcional, e não dava para testá-los aqui.
KEYWORDS_CONHECIDOS = frozenset({
    "annotation", "column", "culture", "dataType", "database", "displayFolder",
    "expression", "formatString", "hierarchy", "isHidden", "level", "lineageTag",
    "measure", "mode", "model", "partition", "ref", "relationship",
    "sortByColumn", "source", "sourceColumn", "summarizeBy", "table",
    "compatibilityLevel", "defaultPowerBIDataSourceVersion",
    "discourageImplicitMeasures", "sourceQueryCulture", "dataAccessOptions",
    "legacyRedirects", "returnErrorValuesAsNull", "fromColumn", "toColumn",
})

RE_KEYWORD = re.compile(r"^\t*([a-zA-Z][a-zA-Z0-9_]*)\b")


def validar_sintaxe_tmdl(erros: list[str], avisos: list[str]) -> None:
    """Regras estruturais do TMDL que dá para checar sem o Power BI.

    A regra 1 é a que derrubou a primeira tentativa de abrir o projeto:
    `///` é a DESCRIÇÃO de um objeto, não um comentário livre, e uma linha em
    branco entre o bloco e a declaração faz o parser abortar com
    "Unexpected line type: Empty!".
    """
    arquivos = sorted(MODELO.glob("*.tmdl")) + sorted((MODELO / "tables").glob("*.tmdl"))
    for arquivo in arquivos:
        bruto = arquivo.read_bytes()
        texto = bruto.decode("utf-8")
        linhas = texto.split("\r\n") if b"\r\n" in bruto else texto.split("\n")
        rotulo = arquivo.relative_to(MODELO)

        # Regra 1 — bloco /// tem de vir COLADO à declaração que descreve.
        em_doc = False
        for i, linha in enumerate(linhas, start=1):
            despido = linha.lstrip("\t")
            if despido.startswith("///"):
                em_doc = True
                continue
            if em_doc and not despido.strip():
                erros.append(
                    f"{rotulo}: linha {i} — linha em branco logo após bloco '///'. "
                    f"O parser aborta com 'Unexpected line type: Empty!'"
                )
            em_doc = False

        # Regra 2 — não existe comentário livre no TMDL.
        for i, linha in enumerate(linhas, start=1):
            despido = linha.lstrip("\t")
            if despido.startswith("//") and not despido.startswith("///"):
                erros.append(f"{rotulo}: linha {i} — comentário '//' não existe em TMDL")

        # Regra 3 — só keywords com referência funcional comprovada.
        for i, linha in enumerate(linhas, start=1):
            despido = linha.lstrip("\t")
            if not despido or despido.startswith("///") or linha.startswith("\t\t\t"):
                continue
            m = RE_KEYWORD.match(linha)
            if m and m.group(1) not in KEYWORDS_CONHECIDOS:
                avisos.append(
                    f"{rotulo}: linha {i} — keyword '{m.group(1)}' sem referência "
                    f"em projeto PBIP funcional conhecido"
                )

        # Regra 4 — CRLF, que é o que o Desktop escreve.
        if b"\r\n" not in bruto and len(linhas) > 1:
            avisos.append(f"{rotulo}: quebra de linha LF; o Desktop grava CRLF")

    # Regra 5 — o parâmetro de pasta precisa de caminho WINDOWS.
    expressoes = MODELO / "expressions.tmdl"
    if expressoes.is_file():
        texto = expressoes.read_text(encoding="utf-8")
        if "/mnt/" in texto:
            erros.append(
                "expressions.tmdl: o parâmetro traz caminho do WSL (/mnt/...). "
                "O Power BI roda no Windows e precisa de 'C:\\...'"
            )


# Tipos de visual e combinações papel→tipo-de-campo levantados dos projetos
# PBIP que ABREM no Power BI Desktop desta máquina. Não é a lista do que o
# Power BI suporta — é a lista do que está comprovado aqui.
#
# A regra que mais pega erro é a do papel `Y`: ele recebe MEDIDA, nunca coluna
# crua. Um gráfico com coluna em Y é o tipo de coisa que o Desktop rejeita
# depois de já ter carregado o modelo.
# GUID do "HTML Content (lite)" — a edição CERTIFICADA, que é a aceita em
# Publicar na web. Conferido no pbiviz.json da branch `certification` do
# repositório do autor: as duas edições compartilham o mesmo GUID.
HTML_CONTENT = "htmlContent443BE3AD55E043BF878BED274D3A6865"

VISUAIS_COMPROVADOS = frozenset({
    "actionButton", "advancedSlicerVisual", "barChart", "card",
    "clusteredBarChart", "clusteredColumnChart", "image", "lineChart",
    "pageNavigator", "pivotTable", "shape", "slicer", "tableEx", "textbox",
})

PAPEIS_COMPROVADOS: dict[tuple[str, str], set[str]] = {
    ("card", "Values"): {"Measure"},
    ("slicer", "Values"): {"Column"},
    ("tableEx", "Values"): {"Column", "Measure"},
    ("barChart", "Category"): {"Column"},
    ("barChart", "Y"): {"Measure"},
    ("clusteredBarChart", "Category"): {"Column"},
    ("clusteredBarChart", "Y"): {"Measure"},
    ("clusteredColumnChart", "Category"): {"Column"},
    ("clusteredColumnChart", "Series"): {"Column"},
    ("clusteredColumnChart", "Y"): {"Measure"},
    ("lineChart", "Category"): {"Column"},
    ("lineChart", "Y"): {"Measure"},
    # HTML Content (lite), certificado. O papel se chama `content` e o
    # displayName na UI é "Values" — quem procura por "Values" no JSON não
    # acha nada. Conferido no capabilities.json do visual.
    (HTML_CONTENT, "content"): {"Measure", "Column"},
    # `sampling` é a granularidade: é ele que faz o visual criar um
    # selectionId POR LINHA e, com isso, cross-filtrar a página. Sem campo
    # aqui, `hasGranularity` é falso e a opção de cross-filter nem aparece
    # no painel de formatação. Conferido em src/view-model.ts do visual.
    (HTML_CONTENT, "sampling"): {"Column"},
    # `tooltips` carrega a medida de ordenação. Ela precisa estar no visual
    # para o sortDefinition valer — o Power BI descarta sort por campo
    # ausente e devolve as linhas na ordem alfabética da coluna.
    (HTML_CONTENT, "tooltips"): {"Measure"},
}


def validar_report_json(erros: list[str]) -> None:
    """Campos que o Desktop exige no report.json."""
    caminho = RELATORIO / "report.json"
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    tema = dados.get("themeCollection", {}).get("customTheme")
    if tema is not None:
        faltando = [c for c in ("name", "type", "reportVersionAtImport") if c not in tema]
        for campo in faltando:
            erros.append(
                f"report.json: /themeCollection/customTheme sem '{campo}' — "
                f"o Desktop recusa o arquivo"
            )


# Altura que cada componente HTML precisa, medida no CSS que a medida emite:
# título 30 + respiro 16 + n linhas. Linha simples 25px, linha dupla 42px
# (duas barras empilhadas mais dois valores). Cartão de KPI: 124px, ou 132
# quando tem barra de proporção.
#
# Componente menor que isso ganha barra de rolagem dentro do visual — o
# Desktop não avisa, e a última linha da lista simplesmente some.
ALTURA_HTML = {
    # Calibrado pelas caixas da página 1, que o Breno ajustou à mão no Desktop
    # e aprovou: 2 linhas em 85px, 4 em 140, 5 em 185. Dá 30px de título mais
    # 27 por linha simples; a linha dupla, com duas barras e dois valores,
    # ocupa 42.
    "HTML — Faixa de KPIs": 137, "HTML — Faixa de Margem": 137,
    "HTML — Faixa de Clientes": 137, "HTML — Faixa de Sazonalidade": 137,
    # a faixa da previsão usa número de 26px, não 30: 28 de padding + 13 do
    # rótulo + 10 + 30 + 8 + 14 = 103
    "HTML — Faixa da Previsão": 103,
    "HTML — Linha de Canal": 84,             # 2 linhas
    "HTML — Linha de Status": 138,           # 4
    "HTML — Linha de Categoria": 165,        # 5
    "HTML — Linha de Categoria Dupla": 324,  # 7 duplas
    "HTML — Linha de Produto": 273,          # 9
    "HTML — Linha de Cliente": 246,          # 8
    "HTML — Linha de Categoria Itens": 246,  # 8
    "HTML — Linha de Cliente Dupla": 198,    # 4 duplas
    "HTML — Linha de Dia": 324,              # 7 duplas
    "HTML — Linha de Dia Vazio": 219,        # 7
    # as séries somam 20 da legenda e 16 do eixo ao desenho
    "HTML — Série de Receita": 176, "HTML — Série de Margem": 66,
    "HTML — Série da Bússola": 136, "HTML — Série de Dias Vazios": 136,
    "HTML — Linha de Similar": 195, "HTML — Linha de Cesta": 195,
}


def validar_visuais(erros: list[str], avisos: list[str]) -> None:
    """Tipo de visual e combinação papel→tipo-de-campo, contra o comprovado."""
    # Visual do AppSource: o código não vive no projeto, é resolvido na
    # abertura. O GUID precisa estar em `publicCustomVisuals` do report.json —
    # sem isso o visual renderiza EM BRANCO, sem erro nenhum, que é a falha
    # silenciosa mais comum ao copiar um visual entre relatórios.
    declarados = set(
        json.loads((RELATORIO / "report.json").read_text(encoding="utf-8"))
        .get("publicCustomVisuals", [])
    )

    usados_custom: set[str] = set()
    for caminho in sorted(RELATORIO.rglob("visual.json")):
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        v = dados.get("visual", {})
        tipo = v.get("visualType", "?")
        rotulo = caminho.parent.name

        if tipo not in VISUAIS_COMPROVADOS:
            if tipo in declarados:
                usados_custom.add(tipo)
            else:
                erros.append(
                    f"{rotulo}: visualType '{tipo}' não é nativo comprovado nem "
                    f"está em publicCustomVisuals — renderiza em branco, sem erro"
                )

        if "tabOrder" not in dados.get("position", {}):
            avisos.append(f"{rotulo}: position sem 'tabOrder'")

        # --- 20. componente HTML menor que o conteúdo -----------------------
        if tipo == HTML_CONTENT:
            projs = (v.get("query", {}).get("queryState", {})
                     .get("content", {}).get("projections", []))
            if projs:
                med = projs[0].get("field", {}).get("Measure", {}).get("Property")
                minimo = ALTURA_HTML.get(med)
                altura = dados.get("position", {}).get("height", 0)
                # margem de 20%: a altura de linha real do visual é menor
                # que a estimativa, e o layout final foi calibrado na tela
                if minimo and altura < minimo * 0.8:
                    erros.append(
                        f"{rotulo}: '{med}' tem {altura}px contra {minimo} de "
                        f"conteúdo — some mais de uma linha"
                    )
                elif minimo and altura < minimo:
                    avisos.append(
                        f"{rotulo}: '{med}' tem {altura}px e a estimativa pede "
                        f"{minimo}; confira se a última linha aparece"
                    )

        # --- 16. cross-filter do HTML Content coerente com a granularidade --
        # O visual só cross-filtra se houver campo em `sampling` — é dali que
        # sai um selectionId por linha. Ligar `enabled` sem `sampling` não faz
        # nada e passa despercebido; e ter `sampling` com `enabled` desligado
        # joga fora a interatividade de graça. Foi o erro da primeira versão.
        if tipo == HTML_CONTENT:
            tem_sampling = "sampling" in v.get("query", {}).get("queryState", {})
            ligado = any(
                item.get("properties", {}).get("enabled", {})
                .get("expr", {}).get("Literal", {}).get("Value") == "true"
                for item in (v.get("objects") or {}).get("crossFilter", [])
            )
            if ligado and not tem_sampling:
                erros.append(
                    f"{rotulo}: crossFilter ligado sem campo em 'sampling' — "
                    f"não filtra nada, o visual vira um ponto de seleção só"
                )
            if tem_sampling and not ligado:
                avisos.append(
                    f"{rotulo}: tem 'sampling' mas crossFilter desligado — "
                    f"a interatividade está disponível e não foi usada"
                )

        # Título que não cabe na largura do visual. O Power BI trunca com "…"
        # e a conclusão morre justamente no fim da frase, que é onde ela está
        # — este projeto escreve título como conclusão, não como rótulo.
        for grupo in (v.get("visualContainerObjects") or {}).get("title", []):
            props = grupo.get("properties", {})
            texto = props.get("text", {}).get("expr", {}).get("Literal", {}).get("Value", "")
            texto = texto.strip("'")
            if not texto:
                continue
            corpo = props.get("fontSize", {}).get("expr", {}).get("Literal", {}).get("Value", "10D")
            pt = float(str(corpo).rstrip("D"))
            largura = dados.get("position", {}).get("width", 0)
            # Segoe UI Semibold: ~0.66 do corpo por caractere, 26px de padding
            cabem = int((largura - 26) / (pt * 0.66))
            if len(texto) > cabem:
                erros.append(
                    f"{rotulo}: título de {len(texto)} caracteres em {largura}px "
                    f"({pt:.0f}pt cabe ~{cabem}) — vai truncar: {texto[:40]}…"
                )

        for papel, cfg in v.get("query", {}).get("queryState", {}).items():
            projecoes = cfg.get("projections", [])

            # 'active' só é comprovado onde o papel tem UMA projeção — ali ele
            # marca o campo em foco. Num `tableEx`, cujo papel Values carrega
            # todas as colunas, ele faz o visual tratar o conjunto como
            # hierarquia e exibir só a projeção ativa: a tabela veio com uma
            # coluna e nenhuma linha. Zero ocorrências em 84 projeções de
            # `tableEx` nos projetos de referência.
            if len(projecoes) > 1 and any("active" in p for p in projecoes):
                erros.append(
                    f"{rotulo}: '{tipo}' tem 'active' em '{papel}', que carrega "
                    f"{len(projecoes)} projeções — só é comprovado com uma"
                )

            esperado = PAPEIS_COMPROVADOS.get((tipo, papel))
            if esperado is None:
                avisos.append(
                    f"{rotulo}: papel '{papel}' em '{tipo}' sem referência conhecida"
                )
                continue
            for proj in cfg.get("projections", []):
                campo = proj.get("field", {})
                especie = "Measure" if "Measure" in campo else (
                    "Column" if "Column" in campo else "outro"
                )
                if especie not in esperado:
                    erros.append(
                        f"{rotulo}: '{tipo}' recebe {especie} no papel '{papel}', "
                        f"mas o comprovado é {'/'.join(sorted(esperado))} "
                        f"({proj.get('queryRef', '?')})"
                    )


# Tipo físico do Parquet -> `dataType` que o TMDL tem de declarar. O que não
# está aqui, o conector `Parquet.Document` não sabe importar: ele devolve um
# tipo nulo e o Desktop aborta a atualização inteira, sem dizer qual coluna.
TIPO_PARQUET_PARA_TMDL = {
    "int8": "int64", "int16": "int64", "int32": "int64", "int64": "int64",
    "float": "double", "double": "double",
    "string": "string", "bool": "boolean",
}


def _tmdl_esperado(tipo: str) -> str | None:
    if tipo.startswith(("timestamp", "date")):
        return "dateTime"
    if tipo.startswith("decimal"):
        return "double"
    return TIPO_PARQUET_PARA_TMDL.get(tipo)


def validar_parquets(tabelas_tmdl: dict[str, list[tuple[str, str]]],
                     erros: list[str], avisos: list[str]) -> None:
    """Regras 9 e 10 — checam os DADOS, não só a definição do modelo."""
    try:
        import pyarrow.compute as pc
        import pyarrow.parquet as pq
    except ImportError:
        avisos.append("pyarrow ausente: regras 9 e 10 (Parquet) não rodaram")
        return

    # --- 9. tipo físico importável e coerente com o TMDL ------------------
    for tabela, colunas in tabelas_tmdl.items():
        caminho = PARQUET / f"{tabela}.parquet"
        if not caminho.is_file():
            continue
        schema = {c.name: str(c.type) for c in pq.read_schema(caminho)}
        for origem, tipo_tmdl in colunas:
            if origem not in schema:
                continue  # já coberto pela regra 3
            esperado = _tmdl_esperado(schema[origem])
            if esperado is None:
                erros.append(
                    f"{tabela}.{origem}: tipo Parquet '{schema[origem]}' não é "
                    f"importável pelo Power BI (grave via gold.parquet_compat)"
                )
            elif esperado != tipo_tmdl:
                erros.append(
                    f"{tabela}.{origem}: Parquet é '{schema[origem]}', que chega "
                    f"como '{esperado}', mas o TMDL declara '{tipo_tmdl}'"
                )

    # --- 10. cardinalidade e integridade nos dados ------------------------
    rel_texto = (MODELO / "relationships.tmdl").read_text(encoding="utf-8").replace("\r\n", "\n")
    # `Any` porque o pyarrow é importado dentro da função (a validação degrada
    # para aviso quando ele não está instalado) e não tem stubs para o mypy.
    cache: dict[str, Any] = {}

    def coluna(tabela: str, nome: str) -> Any:
        caminho = PARQUET / f"{tabela}.parquet"
        if not caminho.is_file():
            return None
        if tabela not in cache:
            cache[tabela] = pq.read_table(caminho)
        tabela_pa = cache[tabela]
        return tabela_pa.column(nome) if nome in tabela_pa.column_names else None

    for m in re.finditer(r"^relationship\s+(\S+)\n\tfromColumn:\s+(\S+)\n\ttoColumn:\s+(\S+)",
                         rel_texto, re.M):
        nome_rel, ref_n, ref_um = m.group(1), m.group(2), m.group(3)
        tab_n, _, col_n = ref_n.partition(".")
        tab_um, _, col_um = ref_um.partition(".")
        lado_um, lado_n = coluna(tab_um, col_um), coluna(tab_n, col_n)
        if lado_um is None or lado_n is None:
            continue

        if pc.count_distinct(lado_um).as_py() != lado_um.length():
            erros.append(f"relação {nome_rel}: '{ref_um}' não é único — "
                         f"o Desktop recusa a cardinalidade muitos-para-um")
        if lado_um.null_count:
            erros.append(f"relação {nome_rel}: '{ref_um}' tem "
                         f"{lado_um.null_count} nulos no lado 1")

        # Órfão não impede a relação: o Power BI os agrupa num membro "Em
        # branco" da dimensão, e eles somem de todo visual filtrado por ela.
        # Falha silenciosa — por isso é erro aqui, e não aviso.
        conhecidos = set(lado_um.to_pylist())
        orfaos = sum(1 for v in lado_n.to_pylist() if v is not None and v not in conhecidos)
        orfaos = int(orfaos)
        if orfaos:
            erros.append(f"relação {nome_rel}: {orfaos} valores de '{ref_n}' "
                         f"não existem em '{ref_um}' (virariam linha em branco)")


def ler_colunas_de_origem() -> dict[str, list[tuple[str, str]]]:
    """Devolve {tabela: [(sourceColumn, dataType), ...]} — só colunas de fonte."""
    saida: dict[str, list[tuple[str, str]]] = {}
    for arquivo in sorted((MODELO / "tables").glob("*.tmdl")):
        texto = arquivo.read_text(encoding="utf-8").replace("\r\n", "\n")
        colunas = []
        for _, corpo in re.findall(r"\n\tcolumn ([^\n]+)\n((?:\t\t[^\n]*\n)+)", texto):
            if "type: calculated" in corpo:
                continue  # coluna DAX não tem contrapartida no Parquet
            tipo = re.search(r"dataType: (\S+)", corpo)
            origem = re.search(r"sourceColumn: (\S+)", corpo)
            if tipo and origem:
                colunas.append((origem.group(1), tipo.group(1)))
        saida[arquivo.stem] = colunas
    return saida


def main() -> int:
    if not MODELO.exists():
        print(f"erro: {MODELO} não existe — rode powerbi/gerar_pbip.py", file=sys.stderr)
        return 1

    erros: list[str] = []
    avisos: list[str] = []

    validar_sintaxe_tmdl(erros, avisos)
    validar_report_json(erros)
    validar_visuais(erros, avisos)
    validar_parquets(ler_colunas_de_origem(), erros, avisos)

    tabelas, medidas, dax = ler_modelo()
    print(f"Modelo: {len(tabelas)} tabelas, {len(medidas)} medidas")

    # --- 18. número decimal indo cru para CSS ou SVG ----------------------
    # O modelo é pt-BR: FORMAT(52.74, "0.0") devolve "52,7". Em CSS,
    # `width:52,7%` é inválido e o navegador descarta a regra — a barra vai a
    # 100% e TODAS ficam iguais. Em SVG, `points="3,96,50"` vira três números
    # soltos e a linha vira um emaranhado. Todo número que entra em markup
    # tem de passar por SUBSTITUTE(...,",",".").
    for arquivo in sorted((MODELO / "tables").glob("*.tmdl")):
        texto_tab = arquivo.read_text(encoding="utf-8").replace("\r\n", "\n")
        for m in re.finditer(r"^\tmeasure\s+'([^']+)'\s*=(.*?)(?=^\t\tdisplayFolder:|\Z)",
                             texto_tab, re.S | re.M):
            nome_med, corpo_med = m.group(1), m.group(2)
            if "<div" not in corpo_med and "<svg" not in corpo_med:
                continue
            # Só interessa o FORMAT concatenado logo DEPOIS de uma string
            # que termina em `width:` ou `points=` — aí o número entra na
            # propriedade. Um FORMAT que vira rótulo de texto pode ter
            # vírgula à vontade; é assim que se escreve número em pt-BR.
            for _ in re.finditer(r'(?:width:|points=)"\s*\n\s*&\s*FORMAT\(',
                                 corpo_med):
                    erros.append(
                        f"{arquivo.name}: '{nome_med}' — FORMAT indo cru para CSS/SVG. "
                        f"Em pt-BR o decimal é vírgula e a regra fica inválida; "
                        f"use SUBSTITUTE(FORMAT(...), \",\", \".\")"
                    )

    # --- 17. indentação do bloco de expressão -----------------------------
    # A PRIMEIRA linha de uma expressão define a indentação base do bloco. Se
    # ela vier mais recuada que as seguintes, o parser TMDL recusa o arquivo
    # inteiro com "Invalid indentation" e o Desktop nem abre o projeto —
    # apontando o número da linha errada, a que está "fora", não a culpada.
    for arquivo in sorted((MODELO / "tables").glob("*.tmdl")):
        linhas = arquivo.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
        for i, linha in enumerate(linhas):
            if not re.match(r"^\t(?:measure|column) .* =\s*$", linha):
                continue
            corpo = []
            for seguinte in linhas[i + 1:]:
                if not seguinte.startswith("\t\t\t") or not seguinte.strip():
                    break
                corpo.append(seguinte)
            if len(corpo) < 2:
                continue
            def recuo(texto: str) -> int:
                return len(texto) - len(texto.lstrip("\t "))
            primeira = recuo(corpo[0])
            menor = min(recuo(c) for c in corpo[1:])
            if primeira > menor:
                nome_obj = linha.strip().split(" ", 1)[1].rstrip(" =").strip("'")
                erros.append(
                    f"{arquivo.name}: '{nome_obj}' — a 1ª linha da expressão "
                    f"tem recuo {primeira} e as seguintes {menor}; o parser "
                    f"TMDL recusa o arquivo com 'Invalid indentation'"
                )

    # --- 15. nome declarado duas vezes ------------------------------------
    # Um gerador que insere sem remover o bloco anterior duplica a medida, e
    # nada reclama: o TMDL carrega, a segunda definição sobrescreve a primeira
    # em silêncio. Só aparece quando as duas divergem — aí o modelo usa uma e
    # o autor lê a outra.
    for arquivo in sorted((MODELO / "tables").glob("*.tmdl")):
        texto_tab = arquivo.read_text(encoding="utf-8").replace("\r\n", "\n")
        for especie in ("measure", "column"):
            nomes = re.findall(rf"^\t{especie} (?:'([^']+)'|(\S+))", texto_tab, re.M)
            achatados = [a or b for a, b in nomes]
            for nome in sorted({n for n in achatados if achatados.count(n) > 1}):
                erros.append(
                    f"{arquivo.name}: {especie} '{nome}' declarada "
                    f"{achatados.count(nome)}x — a última sobrescreve as outras"
                )

    # --- 13. fim de linha consistente -------------------------------------
    # Um bloco gravado em LF dentro de um arquivo CRLF faz o parser TMDL ver
    # uma linha vazia onde não há, e ele aborta com "Unexpected line type".
    # Custou uma rodada: o erro reportado aponta o TMDL, não a gravação.
    for arquivo in sorted(MODELO.rglob("*.tmdl")):
        cruas = arquivo.read_bytes().split(b"\n")[:-1]
        soltas = sum(1 for crua in cruas if not crua.endswith(b"\r"))
        if soltas and len(cruas) - soltas:
            erros.append(
                f"{arquivo.name}: {soltas} de {len(cruas)} linhas em LF num "
                f"arquivo CRLF — normalize antes de salvar"
            )

    # --- 7. partição e Parquet correspondente -----------------------------
    for arquivo in sorted((MODELO / "tables").glob("*.tmdl")):
        texto = arquivo.read_text(encoding="utf-8")
        if "\tpartition " not in texto:
            erros.append(f"{arquivo.name}: sem partição")
        nome = arquivo.stem
        if nome != "_Medidas" and not (PARQUET / f"{nome}.parquet").is_file():
            erros.append(f"{nome}: Parquet ausente em {PARQUET}")

    # --- 6. relacionamentos ------------------------------------------------
    rel_texto = (MODELO / "relationships.tmdl").read_text(encoding="utf-8").replace("\r\n", "\n")
    n_rel = 0
    for m in re.finditer(r"^relationship\s+(\S+)\n\tfromColumn:\s+(\S+)\n\ttoColumn:\s+(\S+)",
                         rel_texto, re.M):
        n_rel += 1
        for lado, ref in (("from", m.group(2)), ("to", m.group(3))):
            tab, _, col = ref.partition(".")
            if tab not in tabelas:
                erros.append(f"relação {m.group(1)}: tabela '{tab}' ({lado}) não existe")
            elif col not in tabelas[tab]:
                erros.append(f"relação {m.group(1)}: coluna '{ref}' ({lado}) não existe")
    print(f"Relacionamentos: {n_rel}")

    # --- 5. colunas citadas em DAX ----------------------------------------
    for nome_medida, expressao in dax.items():
        for tab, col in re.findall(r"\b(\w+)\[([^\]]+)\]", expressao):
            if tab not in tabelas:
                erros.append(f"medida '{nome_medida}': tabela '{tab}' não existe")
            elif col not in tabelas[tab]:
                erros.append(f"medida '{nome_medida}': coluna '{tab}[{col}]' não existe")
        # Referências a outras medidas: [Nome da Medida]. As que começam com
        # `@` são colunas de tabela virtual criadas por ADDCOLUMNS e só
        # existem dentro da própria expressão — não são medidas do modelo.
        for ref in re.findall(r"(?<![\w\]])\[([^\]]+)\]", expressao):
            if ref.startswith("@"):
                continue
            if ref not in medidas and not any(
                f"{t}[{ref}]" in expressao for t in tabelas
            ):
                avisos.append(f"medida '{nome_medida}': referência '[{ref}]' "
                              f"não é medida conhecida")

    # --- 1 a 4. relatório --------------------------------------------------
    n_paginas = n_visuais = n_refs = 0
    for caminho in sorted(RELATORIO.rglob("*.json")):
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except json.JSONDecodeError as erro_json:
            erros.append(f"{caminho.relative_to(PBI)}: JSON inválido — {erro_json}")
            continue

        if caminho.name == "page.json":
            n_paginas += 1
        if caminho.name != "visual.json":
            continue
        n_visuais += 1

        def visitar(no: object, caminho: Path = caminho) -> None:
            nonlocal n_refs
            if isinstance(no, dict):
                for chave in ("Column", "Measure"):
                    if chave in no and isinstance(no[chave], dict):
                        alvo = no[chave]
                        entidade = (
                            alvo.get("Expression", {}).get("SourceRef", {}).get("Entity")
                        )
                        prop = alvo.get("Property")
                        if entidade and prop:
                            n_refs += 1
                            rotulo = f"{caminho.parent.name}: {entidade}.{prop}"
                            if chave == "Measure":
                                if prop not in medidas:
                                    erros.append(f"{rotulo} — medida inexistente")
                            elif entidade not in tabelas:
                                erros.append(f"{rotulo} — tabela inexistente")
                            elif prop not in tabelas[entidade]:
                                erros.append(f"{rotulo} — coluna inexistente")
                for valor in no.values():
                    visitar(valor)
            elif isinstance(no, list):
                for item in no:
                    visitar(item)

        visitar(dados)

    # --- 19. layout: sobreposição e canvas ---------------------------------
    # Visual sobreposto some por baixo do vizinho, e visual além do canvas
    # simplesmente não aparece. Nenhum dos dois dá erro no Desktop — foi
    # assim que títulos foram parar em cima de gráficos e que caixas
    # redimensionadas comeram os textos de rodapé.
    CANVAS_L, CANVAS_A = 1280, 720
    for pagina in sorted((RELATORIO / "pages").glob("*/")):
        caixas = []
        for caminho in sorted(pagina.glob("visuals/*/visual.json")):
            dados = json.loads(caminho.read_text(encoding="utf-8"))
            pos = dados.get("position", {})
            caixas.append((caminho.parent.name,
                           dados["visual"].get("visualType", "?"), pos))
        for nome_v, tipo_v, pos in caixas:
            if (pos["x"] + pos["width"] > CANVAS_L
                    or pos["y"] + pos["height"] > CANVAS_A):
                erros.append(
                    f"{nome_v} ({tipo_v}): passa do canvas {CANVAS_L}x{CANVAS_A} — "
                    f"termina em {pos['x'] + pos['width']},{pos['y'] + pos['height']}"
                )
        for i in range(len(caixas)):
            for j in range(i + 1, len(caixas)):
                a, b = caixas[i][2], caixas[j][2]
                if (a["x"] + a["width"] <= b["x"] or b["x"] + b["width"] <= a["x"]
                        or a["y"] + a["height"] <= b["y"]
                        or b["y"] + b["height"] <= a["y"]):
                    continue
                erros.append(
                    f"{caixas[i][0]} ({caixas[i][1]}) sobrepõe "
                    f"{caixas[j][0]} ({caixas[j][1]}) na página "
                    f"{pagina.name[:8]}"
                )

    # --- 8. páginas declaradas existem ------------------------------------
    pages_json = json.loads((RELATORIO / "pages" / "pages.json").read_text(encoding="utf-8"))
    for pid in pages_json["pageOrder"]:
        if not (RELATORIO / "pages" / pid / "page.json").is_file():
            erros.append(f"pages.json declara página '{pid}', que não existe no disco")
    if pages_json["activePageName"] not in pages_json["pageOrder"]:
        erros.append("activePageName não está em pageOrder")

    print(f"Relatório: {n_paginas} páginas, {n_visuais} visuais, "
          f"{n_refs} referências a campos")

    if avisos:
        print(f"\n{len(avisos)} aviso(s):")
        for aviso in avisos:
            print(f"  ~ {aviso}")

    if erros:
        print(f"\nREPROVADO — {len(erros)} erro(s):", file=sys.stderr)
        for erro in erros:
            print(f"  ✗ {erro}", file=sys.stderr)
        return 1

    print("\nAPROVADO — toda referência do relatório existe no modelo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
