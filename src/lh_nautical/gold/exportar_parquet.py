#!/usr/bin/env python3
"""
Exporta a camada `gold` do PostgreSQL para Parquet, para o Power BI consumir.

    python3 -m lh_nautical.gold.exportar_parquet --saida dados/gold

POR QUE PARQUET, E NÃO CONEXÃO DIRETA AO BANCO
----------------------------------------------
O `.pbix` entregue precisa abrir na máquina de quem corrige, e essa máquina
não tem acesso ao PostgreSQL local deste projeto. Um relatório com conexão
viva ao banco chegaria quebrado — sem dados e sem como atualizar.

Import de Parquet resolve isso: os dados ficam embutidos no arquivo, o
relatório abre em qualquer lugar, e o Parquet ainda preserva os tipos (o CSV
devolveria tudo como texto e exigiria reinferência no Power Query).

Autor: Breno Teodomiro · Desafio Técnico Lighthouse 2026 (Indicium)
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import psycopg

from lh_nautical.gold.parquet_compat import gravar

BANCO_ESPERADO = "lh_nautical"

# Objetos exportados, na ordem em que fazem sentido para quem lê a pasta.
# `dim_calendario` fica de fora de propósito: ela é o artefato da Questão 5 e
# é redundante com `dim_data`, que cobre um período maior. Manter as duas no
# modelo criaria duas fontes de verdade para "quantas quintas-feiras houve".
OBJETOS = (
    "dim_data",
    "dim_cliente",
    "dim_produto",
    "dim_local",
    "dim_canal",
    "dim_status_pedido",
    "fct_pedido",
    "fct_item_pedido",
    "fct_pagamento",
    "fct_venda_diaria_pos",
    "fct_devolucao",
    "fct_estoque_atual",
)


def exportar(conn: psycopg.Connection, objeto: str, saida: Path) -> tuple[int, int]:
    """Lê uma tabela do gold e grava o Parquet. Devolve (linhas, bytes)."""
    # Leitura pelo cursor em vez de `pd.read_sql`: o pandas só suporta
    # oficialmente conexões SQLAlchemy e emite aviso com um driver DBAPI2
    # direto. Construir o DataFrame a partir do cursor evita a dependência
    # e a mensagem, e é o mesmo trabalho.
    with conn.cursor() as cur:
        cur.execute(f'SELECT * FROM gold."{objeto}"')
        colunas = [d.name for d in cur.description or []]
        df = pd.DataFrame(cur.fetchall(), columns=colunas)

    # Dois ajustes de tipo, feitos aqui uma vez em vez de virarem passos
    # manuais no Power Query que alguém esquece de repetir:
    #
    #   · NUMERIC do PostgreSQL chega como Decimal, que o Power BI não lê bem
    #     -> float64;
    #   · DATE chega como datetime.date, que o Parquet grava como objeto
    #     genérico e o Power BI importa como texto -> datetime64.
    for coluna in df.columns:
        if df[coluna].dtype != "object":
            continue
        amostra = df[coluna].dropna()
        if not len(amostra):
            continue
        primeiro = amostra.iloc[0]
        if hasattr(primeiro, "as_tuple"):  # decimal.Decimal
            df[coluna] = df[coluna].astype("float64")
        elif isinstance(primeiro, date):
            df[coluna] = pd.to_datetime(df[coluna])

    # A gravação passa por `parquet_compat.gravar` e não pelo `to_parquet` do
    # pandas: o pandas 3.0 grava texto como `large_string`, tipo que o
    # conector Parquet do Power BI não sabe importar. Ver o módulo.
    caminho = saida / f"{objeto}.parquet"
    return len(df), gravar(df, caminho)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exporta o gold para Parquet.")
    parser.add_argument("--saida", type=Path, default=Path("dados/gold"))
    parser.add_argument("--dsn", default="", help="string de conexão; padrão = variáveis PG*")
    args = parser.parse_args(argv)

    args.saida.mkdir(parents=True, exist_ok=True)

    with psycopg.connect(args.dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database()")
            linha = cur.fetchone()
            banco = linha[0] if linha else None
        if banco != BANCO_ESPERADO:
            print(f"ABORTADO: conectado em '{banco}', esperado '{BANCO_ESPERADO}'",
                  file=sys.stderr)
            return 2

        print(f"Exportando gold de {banco} para {args.saida}/\n")
        print(f"  {'objeto':<24} {'linhas':>9} {'tamanho':>10}")
        print("  " + "-" * 46)
        total_linhas = total_bytes = 0
        for objeto in OBJETOS:
            n, b = exportar(conn, objeto, args.saida)
            total_linhas += n
            total_bytes += b
            print(f"  {objeto:<24} {n:>9,} {b / 1024:>9.0f} KB".replace(",", "."))
        print("  " + "-" * 46)
        print(f"  {'TOTAL':<24} {total_linhas:>9,} "
              f"{total_bytes / 1024 / 1024:>9.1f} MB".replace(",", "."))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
