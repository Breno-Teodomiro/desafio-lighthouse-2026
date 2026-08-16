#!/usr/bin/env python3
"""
Materializa em Parquet os resultados das Questões 6 e 7 para o dashboard.

    python3 -m lh_nautical.gold.exportar_modelos --csv-dir ./1-lh_nautical_csv

Gera dois artefatos que o Power BI consome como fatos:

  · fct_previsao_bussola     — série mensal real x prevista da Bússola de
    Bordo 702, com os três modelos comparados (MM3, seasonal naive, naive).
  · fct_similaridade_produto — as similaridades de cosseno do item de
    referência da Q7 contra todos os outros produtos.

A lógica é IMPORTADA dos próprios entregáveis, e não reescrita aqui. Duas
implementações da mesma conta são duas chances de ela divergir — e a
divergência apareceria justamente no dashboard, que é onde ela seria vista
por último.

Autor: Breno Teodomiro · Desafio Técnico Lighthouse 2026 (Indicium)
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]


def _carregar_entregavel(nome: str, caminho: Path) -> ModuleType:
    """Importa um entregável pelo caminho.

    Os entregáveis vivem em `entregaveis/` e são autocontidos de propósito —
    não formam um pacote importável. Carregá-los por caminho é o preço dessa
    decisão, e é preferível a duplicar a lógica aqui.
    """
    spec = importlib.util.spec_from_file_location(nome, caminho)
    if spec is None or spec.loader is None:
        raise ImportError(f"não foi possível carregar {caminho}")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def gerar_previsao(csv_dir: Path) -> pd.DataFrame:
    """Série mensal da Bússola com real e três modelos, em formato longo."""
    q6 = _carregar_entregavel(
        "q6", RAIZ / "entregaveis" / "Q6_previsao" / "q6_previsao_demanda.py"
    )
    df = q6.construir_dataset(csv_dir)
    ids = sorted(df.loc[df["produto"] == q6.PRODUTO_ALVO, "product_id"].unique())

    historico = q6.serie_mensal(df, ids, df["mes"].min(), q6.FIM_TREINO)
    real = q6.serie_mensal(df, ids, q6.INICIO_TESTE, q6.FIM_TESTE)

    mm3 = q6.prever_media_movel(historico, len(real), q6.JANELA_MM)
    sazonal = pd.Series(
        q6.serie_mensal(df, ids, pd.Period("2025-01"), pd.Period("2025-03")).to_numpy(),
        index=real.index,
    )
    ingenuo = pd.Series(historico.iloc[-1], index=real.index)

    linhas = []
    for periodo, valor in historico.items():
        linhas.append(
            {
                "ano_mes": str(periodo),
                "data": periodo.to_timestamp().date(),
                "serie": "Realizado",
                "unidades": float(valor),
                "eh_treino": True,
            }
        )
    for periodo, valor in real.items():
        linhas.append(
            {
                "ano_mes": str(periodo),
                "data": periodo.to_timestamp().date(),
                "serie": "Realizado",
                "unidades": float(valor),
                "eh_treino": False,
            }
        )
    for rotulo, serie in [
        ("Previsto — média móvel 3m", mm3),
        ("Previsto — seasonal naive", sazonal),
        ("Previsto — naive", ingenuo),
    ]:
        for periodo, valor in serie.items():
            linhas.append(
                {
                    "ano_mes": str(periodo),
                    "data": periodo.to_timestamp().date(),
                    "serie": rotulo,
                    "unidades": float(valor),
                    "eh_treino": False,
                }
            )

    return pd.DataFrame(linhas)


def gerar_similaridade(csv_dir: Path) -> pd.DataFrame:
    """Similaridades do item de referência da Q7 contra todos os produtos."""
    q7 = _carregar_entregavel(
        "q7", RAIZ / "entregaveis" / "Q7_recomendacao" / "q7_recomendacao.py"
    )
    df = q7.carregar(csv_dir)
    rotulos = q7.rotulos_de_produto(df)

    pid_ref = sorted(df.loc[df["produto"] == q7.PRODUTO_REFERENCIA, "product_id"].unique())[0]
    matriz = q7.matriz_interacao(df)
    sim = q7.similaridade_cosseno(matriz)

    serie = sim.loc[pid_ref].drop(index=pid_ref).sort_values(ascending=False)
    media, desvio = serie.mean(), serie.std()

    # Co-ocorrência no mesmo pedido — a formulação correta do problema da
    # Marina, que o dashboard mostra lado a lado com a similaridade.
    pedidos_ref = set(df.loc[df["product_id"] == pid_ref, "order_id"])
    cesta = (
        df[df["order_id"].isin(pedidos_ref) & (df["product_id"] != pid_ref)]
        .groupby("product_id")["order_id"]
        .nunique()
    )

    return pd.DataFrame(
        {
            "product_id": serie.index,
            "produto": [rotulos[p] for p in serie.index],
            "similaridade": serie.to_numpy(),
            "desvios_da_media": ((serie - media) / desvio).to_numpy(),
            "posicao": np.arange(1, len(serie) + 1),
            "pedidos_em_comum": [int(cesta.get(p, 0)) for p in serie.index],
            "produto_referencia": q7.PRODUTO_REFERENCIA,
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Materializa Q6 e Q7 em Parquet.")
    parser.add_argument("--csv-dir", type=Path, default=RAIZ / "1-lh_nautical_csv")
    parser.add_argument("--saida", type=Path, default=RAIZ / "dados" / "gold")
    args = parser.parse_args(argv)

    args.saida.mkdir(parents=True, exist_ok=True)

    for nome, gerador in [
        ("fct_previsao_bussola", gerar_previsao),
        ("fct_similaridade_produto", gerar_similaridade),
    ]:
        df = gerador(args.csv_dir)
        for coluna in df.columns:
            if df[coluna].dtype == "object" and len(df) and hasattr(df[coluna].iloc[0], "year"):
                df[coluna] = pd.to_datetime(df[coluna])
        caminho = args.saida / f"{nome}.parquet"
        df.to_parquet(caminho, index=False, compression="snappy")
        print(f"  {nome:<28} {len(df):>6} linhas  ->  {caminho}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
