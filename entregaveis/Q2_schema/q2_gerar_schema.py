#!/usr/bin/env python3
"""
Desafio Lighthouse 2026 — Questão 2: geração do schema PostgreSQL a partir dos CSVs.

Lê todos os arquivos CSV de um diretório, perfila cada coluna em uma única
passada e emite um arquivo `schema.sql` com um CREATE TABLE por arquivo,
tipos inferidos da evidência encontrada nos dados, chaves primárias e chaves
estrangeiras.

    python3 q2_gerar_schema.py --entrada ./1-lh_nautical_csv --saida schema.sql

PREMISSA ELIMINATÓRIA DA QUESTÃO
--------------------------------
"Utilize somente bibliotecas padrão do Python 3 e python puro. Soluções que
utilizarem bibliotecas como pandas, dask, polars serão desconsideradas."

Os imports abaixo são a lista completa e todos pertencem à biblioteca padrão.
Não há nenhum import dentro de função ou bloco condicional neste arquivo — o
que está no topo é tudo o que o script usa.

DUAS DECISÕES QUE MERECEM DESTAQUE
----------------------------------
1) "Vazio" é somente a string vazia. Tokens como `?`, `n/a`, `TBD` e `asdf`
   aparecem na fonte, mas NÃO são tratados como nulo aqui: tratá-los seria
   limpeza de dados, e a etapa de carga (Q3) exige explicitamente carregar sem
   tratamento. A consequência é desejável — um token de lixo "envenena" a
   coluna e a empurra para texto, que é o tipo honesto para aquele conteúdo.
   Verificado nesta base: nenhuma coluna numérica é envenenada, o lixo textual
   só aparece em colunas que já são texto por natureza.

2) NOT NULL só nas colunas de chave primária. Nulabilidade inferida de uma
   única extração é uma restrição falsa: a coluna que veio 100% preenchida
   hoje pode vir com nulo no extrato da semana que vem, e o schema quebraria na
   ingestão. O perfil de preenchimento vai para o relatório (--relatorio), onde
   é informação útil; dentro do DDL, seria uma armadilha.

Autor: Breno Teodomiro · Desafio Técnico Lighthouse 2026 (Indicium)
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ==========================================================================
# §1  CONSTANTES
# ==========================================================================

# Colunas que são CÓDIGO, não medida. A anulação aqui é SEMÂNTICA: mesmo que
# o conteúdo seja 100% numérico, ninguém soma um CPF nem calcula a média de um
# CEP. Guardar como número perde zeros à esquerda e sugere uma aritmética que
# não existe.
#
# Esta lista é necessária além da detecção automática de zero à esquerda
# (regra 2 da cascata) porque `employees.cpf` e `suppliers.phone` não têm zero
# à esquerda em nenhuma linha desta extração — escapariam da regra estrutural
# e virariam BIGINT por acidente da amostra.
FORCE_TEXT_NAMES = frozenset(
    {
        "tax_id",
        "cpf",
        "cnpj",
        "phone",
        "postal_code",
        "barcode_ean",
        "series",
        "nfe_access_key",
        "nfe_number",
        "ncm_code",
        "state_registration",
        "sku",
        "supplier_sku",
    }
)

# Chaves estrangeiras que a convenção de nomes não alcança, porque o nome da
# coluna descreve o PAPEL e não a tabela de destino.
FK_OVERRIDES = {
    ("orders", "salesperson_id"): ("employees", "id"),
    ("purchase_orders", "buyer_id"): ("employees", "id"),
    ("return_items", "exchange_variant_id"): ("product_variants", "id"),
}

# Coluna polimórfica: aponta ora para `orders`, ora para `returns`, conforme o
# valor de `reference_table` na mesma linha. Não existe FK declarável para isso
# em SQL padrão — declarar uma seria simplesmente errado.
FK_IGNORAR = frozenset({("stock_movements", "reference_id")})

# Sufixos de coluna que terminam em `_id` mas não são referência a tabela.
NAO_SAO_FK = frozenset({"tax_id"})

VARCHAR_BUCKETS = (8, 16, 32, 64, 128, 255)

# Palavras reservadas do PostgreSQL presentes nos cabeçalhos desta base.
# Não são usadas para escapar nada — todo identificador sai entre aspas duplas
# de qualquer forma. Estão aqui para documentar por que isso é obrigatório.
RESERVADAS_PRESENTES = (
    "number, value, action, series, total, status, method, currency, "
    "notes, reason, role, name"
)

RE_INTEIRO = re.compile(r"^-?\d+$")
RE_DECIMAL = re.compile(r"^-?\d+\.\d+$")
RE_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(\.\d+)?$")
BOOLEANOS = frozenset({"TRUE", "FALSE", "true", "false", "True", "False"})

MAX_INT4 = 2_147_483_647


# ==========================================================================
# §2  PERFILAMENTO
# ==========================================================================


@dataclass
class PerfilColuna:
    """Estatísticas de uma coluna, acumuladas em streaming.

    Nenhum atributo guarda a lista de valores: `stock_movements` tem 115 mil
    linhas por 11 colunas, e materializar isso seria trocar um problema
    resolvido por um problema de memória. Tudo aqui é O(1) por coluna.
    """

    nome: str
    posicao: int

    n_total: int = 0
    n_vazio: int = 0
    len_max: int = 0

    tem_zero_a_esquerda: bool = False

    # Começam em True e são derrubados pela primeira violação. Uma coluna
    # 100% vazia termina com todos em True — por isso a regra 0 da cascata
    # trata esse caso antes de qualquer outra coisa.
    so_inteiro: bool = True
    so_decimal: bool = True
    so_booleano: bool = True
    so_data: bool = True
    so_timestamp: bool = True

    escala_max: int = 0  # casas decimais
    digitos_inteiros_max: int = 0  # dígitos antes do ponto
    maior_abs: int = 0  # maior valor absoluto inteiro visto

    amostras: list[str] = field(default_factory=list)

    @property
    def n_preenchido(self) -> int:
        return self.n_total - self.n_vazio

    @property
    def pct_preenchido(self) -> float:
        return 100.0 * self.n_preenchido / self.n_total if self.n_total else 0.0

    def observar(self, valor: str) -> None:
        """Incorpora um valor ao perfil. Chamado uma vez por célula do CSV."""
        self.n_total += 1

        # "Vazio" é a string vazia e nada mais — ver nota 1 do cabeçalho.
        if valor == "":
            self.n_vazio += 1
            return

        if len(valor) > self.len_max:
            self.len_max = len(valor)
        if len(self.amostras) < 5:
            self.amostras.append(valor)

        # Zero à esquerda: '0812356442423' e 812356442423 são coisas
        # diferentes. O segundo caractere precisa não ser '.' para não
        # confundir com o decimal legítimo '0.75'.
        if len(valor) > 1 and valor[0] == "0" and valor[1] != ".":
            self.tem_zero_a_esquerda = True

        if self.so_booleano and valor not in BOOLEANOS:
            self.so_booleano = False
        if self.so_data and not RE_DATA.match(valor):
            self.so_data = False
        if self.so_timestamp and not RE_TIMESTAMP.match(valor):
            self.so_timestamp = False

        if self.so_inteiro:
            if RE_INTEIRO.match(valor):
                corpo = valor.lstrip("-")
                if len(corpo) > self.digitos_inteiros_max:
                    self.digitos_inteiros_max = len(corpo)
                # Comparação em str evita converter para int gigante só para
                # descobrir que a coluna é uma chave de NF-e de 44 dígitos.
                if len(corpo) <= 18:
                    absoluto = int(corpo)
                    if absoluto > self.maior_abs:
                        self.maior_abs = absoluto
            else:
                self.so_inteiro = False

        if self.so_decimal:
            if RE_INTEIRO.match(valor) or RE_DECIMAL.match(valor):
                inteiro, _, fracao = valor.lstrip("-").partition(".")
                if len(inteiro) > self.digitos_inteiros_max:
                    self.digitos_inteiros_max = len(inteiro)
                if len(fracao) > self.escala_max:
                    self.escala_max = len(fracao)
            else:
                self.so_decimal = False


@dataclass
class PerfilTabela:
    """Resultado do perfilamento de um arquivo CSV inteiro."""

    tabela: str
    arquivo: str
    n_linhas: int
    colunas: OrderedDict[str, PerfilColuna]
    terminador: str
    combos_pk: int | None = None  # combinações distintas da PK composta candidata
    colunas_pk_candidatas: list[str] = field(default_factory=list)


def detectar_terminador(caminho: Path) -> str:
    """Descobre se o arquivo usa CRLF, LF ou uma mistura dos dois.

    Sete dos 24 arquivos desta base são CRLF. O módulo `csv` lida com ambos de
    forma transparente quando o arquivo é aberto com `newline=""`, então isso
    não muda a inferência — entra no relatório como evidência de que o formato
    foi verificado, e não presumido.
    """
    with open(caminho, "rb") as fh:
        bloco = fh.read(65536)
    n_crlf = bloco.count(b"\r\n")
    n_lf = bloco.count(b"\n") - n_crlf
    if n_crlf and n_lf:
        return "misto"
    if n_crlf:
        return "CRLF"
    return "LF"


def perfilar_arquivo(caminho: Path) -> PerfilTabela:
    """Perfila um CSV em uma única passada, sem carregar o arquivo na memória."""
    tabela = caminho.stem
    terminador = detectar_terminador(caminho)

    # utf-8-sig descarta o BOM se ele existir; sem isso a primeira coluna se
    # chamaria "﻿id" e nenhuma FK casaria.
    # newline="" é exigência do módulo csv: é ele, e não o Python, que decide
    # onde termina um registro — o que importa para campos com quebra de linha.
    with open(caminho, encoding="utf-8-sig", newline="") as fh:
        leitor = csv.reader(fh)
        try:
            cabecalho = next(leitor)
        except StopIteration:
            raise ValueError(f"{caminho.name}: arquivo vazio, sem cabeçalho") from None

        colunas: OrderedDict[str, PerfilColuna] = OrderedDict()
        for i, nome in enumerate(cabecalho):
            limpo = nome.strip()
            if limpo in colunas:
                raise ValueError(f"{caminho.name}: coluna duplicada no cabeçalho: {limpo!r}")
            colunas[limpo] = PerfilColuna(nome=limpo, posicao=i)

        nomes = list(colunas.keys())
        perfis = list(colunas.values())

        # Candidatas a PK composta: só faz sentido nas tabelas sem `id`.
        # São as colunas `*_id` iniciais — o padrão de tabela associativa.
        candidatas: list[int] = []
        if "id" not in colunas:
            for i, nome in enumerate(nomes):
                if nome.endswith("_id"):
                    candidatas.append(i)
                else:
                    break
        vistos: set[tuple[str, ...]] = set()

        n_linhas = 0
        for linha in leitor:
            # Linha em branco no fim do arquivo não é registro.
            if not linha or (len(linha) == 1 and linha[0] == ""):
                continue
            n_linhas += 1

            if len(linha) != len(perfis):
                raise ValueError(
                    f"{caminho.name}, linha {n_linhas + 1}: "
                    f"{len(linha)} campos, esperados {len(perfis)}"
                )
            for perfil, valor in zip(perfis, linha, strict=True):
                perfil.observar(valor)

            if candidatas:
                vistos.add(tuple(linha[i] for i in candidatas))

    return PerfilTabela(
        tabela=tabela,
        arquivo=caminho.name,
        n_linhas=n_linhas,
        colunas=colunas,
        terminador=terminador,
        combos_pk=len(vistos) if candidatas else None,
        colunas_pk_candidatas=[nomes[i] for i in candidatas],
    )


# ==========================================================================
# §3  INFERÊNCIA DE TIPO — a ordem das regras É o algoritmo
# ==========================================================================


def _bucket_varchar(len_max: int) -> str:
    """Menor VARCHAR que comporta o maior valor visto; acima de 255, TEXT.

    No PostgreSQL não existe ganho de performance de VARCHAR(n) sobre TEXT — o
    armazenamento é o mesmo. O valor de VARCHAR(n) é documentar a expectativa
    e barrar drift silencioso na ingestão. Quem discordar usa --varchar texto.
    """
    for bucket in VARCHAR_BUCKETS:
        if len_max <= bucket:
            return f"VARCHAR({bucket})"
    return "TEXT"


def inferir_tipo(perfil: PerfilColuna, modo_varchar: str) -> tuple[str, str]:
    """Devolve (tipo_sql, justificativa) para uma coluna.

    A justificativa vai como comentário na mesma linha do DDL: é ela que
    transforma o schema.sql de artefato gerado em documento auditável.
    """
    n_ok = perfil.n_preenchido

    def texto(len_max: int) -> str:
        return "TEXT" if modo_varchar == "texto" else _bucket_varchar(len_max)

    # --- Regra 0: sem evidência nenhuma ------------------------------------
    # Não há um único valor para inferir. Chutar um tipo aqui seria inventar
    # informação; TEXT é o único tipo que não descarta nenhum extrato futuro.
    if n_ok == 0:
        return "TEXT", f"coluna 100% vazia na fonte ({perfil.n_total} linhas); tipo indeterminável"

    # --- Regra 1: anulação SEMÂNTICA ---------------------------------------
    if perfil.nome in FORCE_TEXT_NAMES:
        return (
            texto(perfil.len_max),
            f"código de negócio, não medida (len max {perfil.len_max}); "
            f"aritmética não se aplica",
        )

    # --- Regra 2: anulação ESTRUTURAL --------------------------------------
    if perfil.tem_zero_a_esquerda:
        exemplo = next((a for a in perfil.amostras if a.startswith("0")), perfil.amostras[0])
        return (
            texto(perfil.len_max),
            f"zero à esquerda (ex.: {exemplo!r}); converter perderia o dígito",
        )

    # --- Regras 3 a 5: tipos temporais e lógico ----------------------------
    if perfil.so_booleano:
        return "BOOLEAN", f"{n_ok} valores, todos em {{TRUE, FALSE}}"

    if perfil.so_data:
        return "DATE", f"{n_ok} valores, todos YYYY-MM-DD sem componente de hora"

    if perfil.so_timestamp:
        return "TIMESTAMP", f"{n_ok} valores, todos YYYY-MM-DD HH:MM:SS"

    # --- Regra 6: inteiro ---------------------------------------------------
    if perfil.so_inteiro:
        if perfil.digitos_inteiros_max > 18:
            return (
                "TEXT",
                f"{perfil.digitos_inteiros_max} dígitos estouram BIGINT; "
                f"é identificador, não número",
            )
        if perfil.maior_abs <= MAX_INT4:
            return "INTEGER", f"{n_ok} valores inteiros, máximo {perfil.maior_abs}"
        return "BIGINT", f"{n_ok} valores inteiros, máximo {perfil.maior_abs} — excede int4"

    # --- Regra 7: decimal ---------------------------------------------------
    if perfil.so_decimal:
        escala = perfil.escala_max
        # Folga de 2 na parte inteira: a extração de hoje não é o teto do
        # domínio, e ampliar precisão de NUMERIC depois exige reescrever a
        # tabela inteira.
        precisao = perfil.digitos_inteiros_max + escala + 2
        return (
            f"NUMERIC({precisao},{escala})",
            f"{n_ok} valores decimais; até {perfil.digitos_inteiros_max} dígitos "
            f"inteiros e {escala} decimais (+2 de folga)",
        )

    # --- Regra 8: texto -----------------------------------------------------
    return texto(perfil.len_max), f"{n_ok} valores textuais; len max {perfil.len_max}"


# ==========================================================================
# §4  CHAVES
# ==========================================================================


def singularizar(tabela: str) -> str:
    """`categories` -> `category`, `addresses` -> `address`, `orders` -> `order`."""
    if tabela.endswith("ies"):
        return tabela[:-3] + "y"
    if tabela.endswith(("sses", "shes", "ches", "xes", "zes")):
        return tabela[:-2]
    if tabela.endswith("s"):
        return tabela[:-1]
    return tabela


def inferir_pk(perfil: PerfilTabela) -> tuple[list[str], str]:
    """Devolve (colunas_da_pk, justificativa). Lista vazia = sem PK declarável."""
    if "id" in perfil.colunas:
        return ["id"], "coluna surrogate `id`"

    cols = perfil.colunas_pk_candidatas
    if not cols:
        return [], "nenhuma coluna candidata a chave"

    # Não basta a convenção sugerir: a unicidade foi contada durante o
    # perfilamento e só vira PK se a contagem bater exatamente.
    if perfil.combos_pk == perfil.n_linhas:
        return (
            cols,
            f"PK composta inferida e VALIDADA: {perfil.n_linhas} linhas, "
            f"{perfil.combos_pk} combinações distintas",
        )
    return (
        [],
        f"PK composta NÃO declarada: ({', '.join(cols)}) tem {perfil.combos_pk} "
        f"combinações para {perfil.n_linhas} linhas — não é única",
    )


def inferir_fks(perfis: dict[str, PerfilTabela]) -> list[tuple[str, str, str, str, str]]:
    """Descobre as FKs por convenção de nome, com anulações explícitas.

    Devolve tuplas (tabela, coluna, tabela_destino, coluna_destino, origem),
    onde `origem` diz se veio da convenção ou de uma anulação — informação que
    vai como comentário no DDL.
    """
    # Índice: forma singular -> nome real da tabela.
    por_singular = {singularizar(t): t for t in perfis}

    fks: list[tuple[str, str, str, str, str]] = []
    for tabela in sorted(perfis):
        perfil = perfis[tabela]

        for coluna in perfil.colunas:
            if not coluna.endswith("_id") or coluna in NAO_SAO_FK:
                continue
            if (tabela, coluna) in FK_IGNORAR:
                continue

            # Anulação explícita tem prioridade sobre a convenção.
            alvo = FK_OVERRIDES.get((tabela, coluna))
            if alvo:
                fks.append((tabela, coluna, alvo[0], alvo[1], "anulação explícita"))
                continue

            # Nota: pertencer à PK composta NÃO impede ser FK. Em
            # `stock_levels`, `product_variant_id` é metade da chave primária e
            # ao mesmo tempo aponta para `product_variants`.
            radical = coluna[: -len("_id")]
            partes = radical.split("_")

            # Sufixo MAIS LONGO primeiro. Sem isso, `purchase_order_item_id`
            # casaria com `order_items` em vez de `purchase_order_items`, e
            # `product_variant_id` casaria com uma tabela `variants` inexistente.
            destino = None
            for i in range(len(partes)):
                candidato = "_".join(partes[i:])
                if candidato in por_singular:
                    destino = por_singular[candidato]
                    break

            if destino is None:
                continue

            col_destino = "id" if "id" in perfis[destino].colunas else None
            if col_destino is None:
                continue

            fks.append((tabela, coluna, destino, col_destino, "convenção de nome"))

    return fks


# ==========================================================================
# §5  RENDERIZAÇÃO DO DDL
# ==========================================================================


def q(identificador: str) -> str:
    """Todo identificador sai entre aspas duplas.

    Não é preciosismo: esta base tem colunas chamadas `number`, `value`,
    `action`, `series`, `total`, `status`, `method`, `currency`, `notes`,
    `reason`, `role` e `name`. Sem aspas, várias dessas quebram o parser ou
    mudam de significado dependendo da versão do servidor.
    """
    return '"' + identificador.replace('"', '""') + '"'


def render_cabecalho(
    entrada: Path, perfis: dict[str, PerfilTabela], schema: str, args: argparse.Namespace
) -> list[str]:
    total_linhas = sum(p.n_linhas for p in perfis.values())
    total_colunas = sum(len(p.colunas) for p in perfis.values())
    # `.astimezone()` sem argumento resolve para o fuso local. Evita depender de
    # `datetime.UTC`, que só existe a partir do Python 3.11 — este script precisa
    # rodar em qualquer Python 3 que o avaliador tiver à mão.
    agora = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")

    return [
        "-- " + "=" * 74,
        "-- LH Nautical — schema da camada `raw` (PostgreSQL)",
        "-- " + "=" * 74,
        "--",
        "-- GERADO AUTOMATICAMENTE por q2_gerar_schema.py (Questão 2).",
        "-- Não editar à mão: rode o script novamente.",
        "--",
        f"-- Fonte     : {entrada}",
        f"-- Gerado em : {agora}",
        f"-- Escopo    : {len(perfis)} tabelas · {total_colunas} colunas · "
        f"{total_linhas:,} linhas perfiladas".replace(",", "."),
        f"-- Opções    : --schema {schema} --varchar {args.varchar}"
        f"{' --sem-fk' if args.sem_fk else ''}{' --indices' if args.indices else ''}",
        "--",
        "-- CONVENÇÕES",
        "--",
        "--  · Todo identificador sai entre aspas duplas. A base tem colunas",
        f"--    chamadas {RESERVADAS_PRESENTES};",
        "--    sem aspas, parte delas colide com palavra reservada.",
        "--",
        "--  · O tipo de cada coluna foi inferido dos dados, e a evidência que",
        "--    motivou a escolha está no comentário da própria linha.",
        "--",
        "--  · NOT NULL aparece somente nas colunas de chave primária.",
        "--    Nulabilidade inferida de uma única extração é restrição falsa:",
        "--    a coluna cheia hoje pode vir com nulo no extrato de amanhã, e o",
        "--    schema quebraria na ingestão. O perfil de preenchimento está no",
        "--    relatório (--relatorio), onde é informação e não armadilha.",
        "--",
        "--  · As chaves estrangeiras saem em bloco no fim do arquivo, depois",
        "--    de todos os CREATE TABLE, e são DEFERRABLE INITIALLY IMMEDIATE.",
        "--    Assim o carregador da Q3 pode abrir a transação com",
        "--    SET CONSTRAINTS ALL DEFERRED, carregar os 24 arquivos em",
        "--    qualquer ordem e deixar o PostgreSQL validar tudo no COMMIT.",
        "--",
        "-- " + "=" * 74,
        "",
        "BEGIN;",
        "",
        f"CREATE SCHEMA IF NOT EXISTS {q(schema)};",
        f"SET search_path TO {q(schema)};",
        "",
    ]


def render_create_table(
    perfil: PerfilTabela,
    schema: str,
    pk_cols: list[str],
    pk_nota: str,
    args: argparse.Namespace,
) -> list[str]:
    linhas: list[str] = [
        "-- " + "-" * 74,
        f"-- {perfil.tabela}  ({perfil.arquivo})",
        f"--   {perfil.n_linhas:,} linhas · {len(perfil.colunas)} colunas · "
        f"terminador {perfil.terminador}".replace(",", "."),
        f"--   {pk_nota}",
        "-- " + "-" * 74,
        f"DROP TABLE IF EXISTS {q(schema)}.{q(perfil.tabela)} CASCADE;",
        f"CREATE TABLE {q(schema)}.{q(perfil.tabela)} (",
    ]

    corpo: list[tuple[str, str]] = []  # (sql, comentário)
    for nome, coluna in perfil.colunas.items():
        tipo, justificativa = inferir_tipo(coluna, args.varchar)
        restricao = " NOT NULL" if nome in pk_cols else ""
        corpo.append((f"    {q(nome)} {tipo}{restricao}", justificativa))

    if pk_cols:
        cols = ", ".join(q(c) for c in pk_cols)
        corpo.append((f"    CONSTRAINT {q('pk_' + perfil.tabela)} PRIMARY KEY ({cols})", ""))

    # Alinha os comentários numa coluna só — o arquivo é para ser lido.
    largura = max(len(sql) for sql, _ in corpo)
    largura = min(largura, 60)
    for i, (sql, comentario) in enumerate(corpo):
        virgula = "," if i < len(corpo) - 1 else ""
        texto = sql + virgula
        if comentario:
            linhas.append(f"{texto:<{largura + 2}}  -- {comentario}")
        else:
            linhas.append(texto)

    linhas.append(");")
    linhas.append("")
    return linhas


def render_fks(fks: list[tuple[str, str, str, str, str]], schema: str) -> list[str]:
    linhas = [
        "-- " + "=" * 74,
        f"-- §2  CHAVES ESTRANGEIRAS  ({len(fks)} constraints)",
        "-- " + "=" * 74,
        "--",
        "-- Aplicadas depois de todos os CREATE TABLE e declaradas DEFERRABLE,",
        "-- de modo que a ordem de carga dos CSVs deixa de importar: dentro de",
        "-- uma transação com SET CONSTRAINTS ALL DEFERRED, a validação inteira",
        "-- acontece no COMMIT.",
        "--",
        "-- ON DELETE NO ACTION é deliberado. Esta é a camada `raw`: ela espelha",
        "-- a fonte, e apagar em cascata aqui esconderia um problema de origem",
        "-- em vez de expô-lo.",
        "--",
    ]
    for tabela, coluna, destino, col_destino, origem in fks:
        nome = f"fk_{tabela}_{coluna}"
        linhas.append(f"-- {origem}")
        referencia = f"{q(schema)}.{q(destino)} ({q(col_destino)})"
        linhas.append(
            f"ALTER TABLE {q(schema)}.{q(tabela)} ADD CONSTRAINT {q(nome)}\n"
            f"    FOREIGN KEY ({q(coluna)}) REFERENCES {referencia}\n"
            f"    DEFERRABLE INITIALLY IMMEDIATE;"
        )
    linhas.append("")
    return linhas


def render_indices(fks: list[tuple[str, str, str, str, str]], schema: str) -> list[str]:
    linhas = [
        "-- " + "=" * 74,
        "-- §3  ÍNDICES DE APOIO",
        "-- " + "=" * 74,
        "--",
        "-- O PostgreSQL cria índice automaticamente para PRIMARY KEY, mas não",
        "-- para o lado que REFERENCIA. Sem estes, todo JOIN pelo lado filho e",
        "-- toda checagem de FK em UPDATE/DELETE do pai viram varredura completa.",
        "--",
    ]
    for tabela, coluna, _destino, _col, _origem in fks:
        nome = f"ix_{tabela}_{coluna}"
        linhas.append(
            f"CREATE INDEX IF NOT EXISTS {q(nome)} ON {q(schema)}.{q(tabela)} ({q(coluna)});"
        )
    linhas.append("")
    return linhas


# ==========================================================================
# §6  RELATÓRIO DE PERFILAMENTO (opcional)
# ==========================================================================


def render_relatorio(
    perfis: dict[str, PerfilTabela],
    fks: list[tuple[str, str, str, str, str]],
    args: argparse.Namespace,
) -> str:
    total = sum(p.n_linhas for p in perfis.values())
    out = [
        "# Relatório de perfilamento — camada raw",
        "",
        f"Gerado por `q2_gerar_schema.py` em {datetime.now().strftime('%Y-%m-%d %H:%M')}.",
        "",
        f"**{len(perfis)} tabelas · {total:,} linhas · {len(fks)} chaves estrangeiras**".replace(
            ",", "."
        ),
        "",
        "## Visão geral",
        "",
        "| Tabela | Linhas | Colunas | Terminador | Chave primária |",
        "|---|---:|---:|---|---|",
    ]
    for tabela in sorted(perfis):
        p = perfis[tabela]
        pk_cols, _ = inferir_pk(p)
        pk = ", ".join(f"`{c}`" for c in pk_cols) if pk_cols else "—"
        out.append(
            f"| `{tabela}` | {p.n_linhas:,} | {len(p.colunas)} | {p.terminador} | {pk} |".replace(
                ",", "."
            )
        )

    out += [
        "",
        "## Colunas",
        "",
        "`% preenchido` é informativo: **não** vira NOT NULL no DDL. Ver a nota",
        "no cabeçalho do `schema.sql`.",
        "",
    ]
    for tabela in sorted(perfis):
        p = perfis[tabela]
        out += [
            f"### `{tabela}`",
            "",
            "| Coluna | Tipo inferido | % preenchido | len max | Evidência |",
            "|---|---|---:|---:|---|",
        ]
        for nome, col in p.colunas.items():
            tipo, just = inferir_tipo(col, args.varchar)
            out.append(
                f"| `{nome}` | `{tipo}` | {col.pct_preenchido:.1f}% | "
                f"{col.len_max} | {just} |"
            )
        out.append("")

    out += ["## Chaves estrangeiras", "", "| Origem | Coluna | Destino | Como foi descoberta |",
            "|---|---|---|---|"]
    for tabela, coluna, destino, col_destino, origem in fks:
        out.append(f"| `{tabela}` | `{coluna}` | `{destino}.{col_destino}` | {origem} |")
    out.append("")

    ignoradas = sorted(FK_IGNORAR)
    if ignoradas:
        out += [
            "### Não declaradas de propósito",
            "",
        ]
        for tabela, coluna in ignoradas:
            out.append(
                f"- `{tabela}.{coluna}` — coluna polimórfica: o alvo depende do "
                f"valor de outra coluna na mesma linha. Não há FK declarável para "
                f"isso em SQL padrão."
            )
        out.append("")

    return "\n".join(out)


# ==========================================================================
# §7  CLI
# ==========================================================================


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gera schema.sql (PostgreSQL) a partir de um diretório de CSVs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplo:\n"
            "  python3 q2_gerar_schema.py --entrada ./1-lh_nautical_csv "
            "--saida schema.sql --relatorio perfil.md\n"
        ),
    )
    parser.add_argument(
        "--entrada", type=Path, required=True, help="diretório com os arquivos .csv"
    )
    parser.add_argument(
        "--saida", type=Path, default=Path("schema.sql"), help="arquivo .sql de saída"
    )
    parser.add_argument("--schema", default="raw", help="schema PostgreSQL de destino")
    parser.add_argument(
        "--varchar",
        choices=("bucket", "texto"),
        default="bucket",
        help="bucket: VARCHAR(n) dimensionado; texto: TEXT em tudo que for textual",
    )
    parser.add_argument("--sem-fk", action="store_true", help="não emitir chaves estrangeiras")
    parser.add_argument("--indices", action="store_true", help="emitir índices nas colunas de FK")
    parser.add_argument("--relatorio", type=Path, help="grava um relatório .md do perfilamento")
    args = parser.parse_args(argv)

    if not args.entrada.is_dir():
        print(f"erro: {args.entrada} não é um diretório", file=sys.stderr)
        return 1

    arquivos = sorted(args.entrada.glob("*.csv"))
    if not arquivos:
        print(f"erro: nenhum .csv encontrado em {args.entrada}", file=sys.stderr)
        return 1

    print(f"Perfilando {len(arquivos)} arquivos em {args.entrada}...", file=sys.stderr)
    perfis: dict[str, PerfilTabela] = {}
    for caminho in arquivos:
        perfil = perfilar_arquivo(caminho)
        perfis[perfil.tabela] = perfil
        print(
            f"  {perfil.tabela:<26} {perfil.n_linhas:>7,} linhas · "
            f"{len(perfil.colunas):>2} colunas · {perfil.terminador}".replace(",", "."),
            file=sys.stderr,
        )

    pks: dict[str, list[str]] = {}
    notas_pk: dict[str, str] = {}
    for tabela, perfil in perfis.items():
        cols, nota = inferir_pk(perfil)
        pks[tabela] = cols
        notas_pk[tabela] = nota

    fks = [] if args.sem_fk else inferir_fks(perfis)

    linhas = render_cabecalho(args.entrada, perfis, args.schema, args)
    linhas += ["-- " + "=" * 74, "-- §1  TABELAS", "-- " + "=" * 74, ""]
    for tabela in sorted(perfis):
        linhas += render_create_table(
            perfis[tabela], args.schema, pks[tabela], notas_pk[tabela], args
        )
    if fks:
        linhas += render_fks(fks, args.schema)
    if args.indices and fks:
        linhas += render_indices(fks, args.schema)
    linhas += ["COMMIT;", ""]

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text("\n".join(linhas), encoding="utf-8")

    sem_pk = [t for t, c in pks.items() if not c]
    print(
        f"\nOK  {args.saida}"
        f"\n    {len(perfis)} tabelas · {len(fks)} chaves estrangeiras"
        f"\n    {len(perfis) - len(sem_pk)} tabelas com PK declarada"
        + (f" · sem PK: {', '.join(sem_pk)}" if sem_pk else ""),
        file=sys.stderr,
    )

    if args.relatorio:
        args.relatorio.parent.mkdir(parents=True, exist_ok=True)
        args.relatorio.write_text(render_relatorio(perfis, fks, args), encoding="utf-8")
        print(f"    relatório: {args.relatorio}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
