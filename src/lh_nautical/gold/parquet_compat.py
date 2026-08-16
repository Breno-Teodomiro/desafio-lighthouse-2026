#!/usr/bin/env python3
"""
Grava Parquet no dialeto que o conector `Parquet.Document` do Power BI lê.

POR QUE ESTE MÓDULO EXISTE
--------------------------
O `df.to_parquet()` do pandas escreve um arquivo tecnicamente correto que o
Power BI Desktop **não consegue importar**. Dois tipos físicos do Arrow não
têm equivalente no motor Mashup, e ambos apareciam no nosso `gold`:

  · `large_string` (LargeUtf8) — o pandas 3.0 tornou o dtype `str` nativo do
    Arrow o padrão, e ele grava LargeUtf8 em vez de Utf8. Toda coluna de texto
    do projeto saía assim.

  · `null` — uma coluna 100% vazia não dá ao pyarrow nenhuma evidência de
    tipo, e ele grava o tipo `null`, que não carrega informação nenhuma. É o
    caso de `stock_levels.reorder_point`, vazia nas 24.000 linhas de origem.

Ao encontrar qualquer um dos dois, o Desktop aborta a atualização com
`Argumento 'dataType' não pode ser nulo` — mensagem que não cita a coluna nem
o arquivo, e por isso custa caro de diagnosticar. O relatório abre, as tabelas
ficam vazias e todo visual mostra "(Em branco)".

A correção é fazer o *cast* do schema antes de gravar. É barato (só metadado,
os dados não são reescritos) e mantém o Parquet válido para qualquer outro
leitor.

Autor: Breno Teodomiro · Desafio Técnico Lighthouse 2026 (Indicium)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Colunas inteiramente vazias não têm tipo inferível. Em vez de deixar o
# pyarrow gravar `null`, declaramos o tipo aqui — e ele tem de ser o mesmo
# `dataType` que o TMDL declara para a coluna, senão o Desktop reclama na
# atualização seguinte.
TIPO_DE_COLUNA_VAZIA: dict[str, pa.DataType] = {
    "ponto_de_reposicao": pa.string(),  # gold.fct_estoque_atual — TMDL: string
}

# Substituições de tipo físico. À esquerda o que o pyarrow tende a produzir,
# à direita o equivalente que o Mashup entende.
EQUIVALENTES: tuple[tuple[pa.DataType, pa.DataType], ...] = (
    (pa.large_string(), pa.string()),
    (pa.large_binary(), pa.binary()),
)


def compatibilizar(tabela: pa.Table) -> pa.Table:
    """Devolve a tabela com o schema trocado para tipos que o Power BI lê."""
    campos = []
    for campo in tabela.schema:
        tipo = campo.type
        if pa.types.is_null(tipo):
            tipo = TIPO_DE_COLUNA_VAZIA.get(campo.name, pa.string())
        else:
            for origem, destino in EQUIVALENTES:
                if tipo.equals(origem):
                    tipo = destino
                    break
            # Listas e structs também nascem em variante "large"; o cast
            # recursivo do Arrow resolve os aninhados de uma vez.
            if pa.types.is_large_list(tipo):
                tipo = pa.list_(tipo.value_type)
        campos.append(campo.with_type(tipo))
    return tabela.cast(pa.schema(campos))


def gravar(df: pd.DataFrame, caminho: Path) -> int:
    """Grava o DataFrame em Parquet compatível. Devolve o tamanho em bytes."""
    tabela = compatibilizar(pa.Table.from_pandas(df, preserve_index=False))
    pq.write_table(tabela, caminho, compression="snappy")
    return caminho.stat().st_size


def diagnosticar(caminho: Path) -> list[tuple[str, str]]:
    """Lista as colunas do Parquet cujo tipo o Power BI não consegue importar.

    Usada pelos testes: é a checagem que teria evitado a terceira tentativa
    frustrada de abrir o relatório no Desktop.
    """
    incompativeis = []
    for campo in pq.read_schema(caminho):
        tipo = campo.type
        if (
            pa.types.is_null(tipo)
            or pa.types.is_large_string(tipo)
            or pa.types.is_large_binary(tipo)
            or pa.types.is_large_list(tipo)
        ):
            incompativeis.append((campo.name, str(tipo)))
    return incompativeis
