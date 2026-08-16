#!/usr/bin/env python3
"""
Desafio Lighthouse 2026 — Questão 6: Previsão de demanda da "Bússola de Bordo 702".

Constrói o dataset unificado a partir dos 4 CSVs, treina um baseline de média
móvel de 3 meses com corte em 31/12/2025 e prevê o 1º trimestre de 2026.

    python3 q6_previsao_demanda.py --csv-dir ./1-lh_nautical_csv

PREMISSAS OBRIGATÓRIAS
----------------------
  · Treino: dados até 31/12/2025
  · Teste: 1º trimestre de 2026
  · Base mensal
  · Produto: "Bússola de Bordo 702"
  · Baseline: média móvel dos últimos 3 meses, considerando apenas dados
    anteriores à data prevista
  · Métrica: MAE
  · Datasets: products, product_variants, orders, order_items

DUAS AMBIGUIDADES DO ENUNCIADO, E COMO SÃO RESOLVIDAS
-----------------------------------------------------
1) "Bússola de Bordo 702" existe DUAS VEZES em products.csv, com product_id
   74 e 240 (marcas e categorias diferentes, mesma descrição). O enunciado
   nomeia o produto pelo NOME, e a implementação natural — filtrar
   `products.name == 'Bússola de Bordo 702'` — captura os dois. Escolher um
   exigiria um critério que o enunciado não fornece. Adotamos a soma dos dois,
   e o script imprime os três cenários para que a escolha fique auditável.

2) "considerando apenas dados anteriores à data prevista" admite três
   leituras. Adotamos a ESTÁTICA — treina uma vez na janela out/nov/dez-2025 e
   aplica a mesma previsão aos três meses do horizonte. Justificativa completa
   no relatório impresso ao fim da execução.

Autor: Breno Teodomiro · Desafio Técnico Lighthouse 2026 (Indicium)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PRODUTO_ALVO = "Bússola de Bordo 702"

FIM_TREINO = pd.Period("2025-12", freq="M")
INICIO_TESTE = pd.Period("2026-01", freq="M")
FIM_TESTE = pd.Period("2026-03", freq="M")
JANELA_MM = 3


# ==========================================================================
# §1  DATASET UNIFICADO
# ==========================================================================


def construir_dataset(csv_dir: Path) -> pd.DataFrame:
    """Junta os 4 CSVs no grão de LINHA DE ITEM.

    O grão é escolhido de propósito: uma linha por item vendido é o nível mais
    detalhado que ainda responde à pergunta, e agregar a partir dele é trivial.
    Guardar o dataset já agregado por mês economizaria memória e destruiria a
    possibilidade de qualquer recorte posterior.

    A cadeia de chaves é obrigatória e não tem atalho:

        order_items.product_variant_id -> product_variants.id
        product_variants.product_id    -> products.id

    `order_items` NÃO TEM product_id. Quem tentar juntar itens direto em
    produtos não encontra chave.
    """
    produtos = pd.read_csv(csv_dir / "products.csv")
    variantes = pd.read_csv(csv_dir / "product_variants.csv")
    pedidos = pd.read_csv(csv_dir / "orders.csv")
    itens = pd.read_csv(csv_dir / "order_items.csv")

    df = (
        itens.merge(
            variantes[["id", "product_id"]],
            left_on="product_variant_id",
            right_on="id",
            how="inner",
            suffixes=("", "_variante"),
        )
        .merge(
            produtos[["id", "name", "brand_id", "category_id"]],
            left_on="product_id",
            right_on="id",
            how="inner",
            suffixes=("", "_produto"),
        )
        .merge(
            pedidos[["id", "customer_id", "status", "channel", "created_at"]],
            left_on="order_id",
            right_on="id",
            how="inner",
            suffixes=("", "_pedido"),
        )
    )

    # `created_at` do PEDIDO, não `paid_at` do pagamento: a data em que a
    # demanda se manifestou é a data do pedido. Usar a data de pagamento
    # embutiria informação posterior ao evento que se quer prever.
    df["data_pedido"] = pd.to_datetime(df["created_at"])
    df["mes"] = df["data_pedido"].dt.to_period("M")

    return df[
        [
            "order_id",
            "product_variant_id",
            "product_id",
            "name",
            "brand_id",
            "category_id",
            "customer_id",
            "status",
            "channel",
            "quantity",
            "unit_price",
            "line_total",
            "data_pedido",
            "mes",
        ]
    ].rename(columns={"name": "produto", "quantity": "quantidade"})


# ==========================================================================
# §2  SÉRIE MENSAL
# ==========================================================================


def serie_mensal(df: pd.DataFrame, ids: list[int], inicio, fim) -> pd.Series:
    """Unidades vendidas por mês, com índice mensal DENSO.

    O `reindex` é a linha mais importante desta função. Sem ele, um mês sem
    nenhuma venda simplesmente não aparece na série — e "os últimos 3 meses"
    passaria a significar "as últimas 3 linhas existentes", que podem estar
    espalhadas por seis meses do calendário. A média móvel sairia errada sem
    dar nenhum sinal de que algo está errado.
    """
    recorte = df[df["product_id"].isin(ids)]
    serie = recorte.groupby("mes")["quantidade"].sum()
    indice = pd.period_range(inicio, fim, freq="M")
    return serie.reindex(indice, fill_value=0).astype("float64")


def prever_media_movel(treino: pd.Series, n_meses: int, janela: int) -> pd.Series:
    """Baseline: média das últimas `janela` observações do TREINO.

    Esquema ESTÁTICO — a mesma previsão vale para todo o horizonte. As três
    razões:

    1. Realimentar o real de janeiro faria janeiro virar treino, contradizendo
       o split que o próprio enunciado declara.
    2. A Q6.2 pede a previsão "utilizando seu modelo TREINADO": treina uma vez,
       aplica ao horizonte.
    3. A janela out/nov/dez-2025 é estritamente anterior a cada data prevista,
       que é o que a trava de leakage do enunciado exige.

    E a razão de negócio, que vale mais que as três: a compra do trimestre é
    fechada em dezembro. O comprador não pode esperar o número real de janeiro
    para decidir quanto pedir ao fornecedor.
    """
    media = treino.iloc[-janela:].mean()
    horizonte = pd.period_range(INICIO_TESTE, periods=n_meses, freq="M")
    return pd.Series(media, index=horizonte, name="previsao")


def mae(real: pd.Series, previsto: pd.Series) -> float:
    """Erro Absoluto Médio. Escrito explicitamente — são duas operações."""
    return float(np.abs(real.to_numpy() - previsto.to_numpy()).mean())


# ==========================================================================
# §3  EXECUÇÃO
# ==========================================================================


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Previsão de demanda da Bússola de Bordo 702 (baseline MM3)."
    )
    parser.add_argument("--csv-dir", type=Path, required=True, help="diretório com os .csv")
    parser.add_argument(
        "--cenario",
        choices=("ambos", "74", "240"),
        default="ambos",
        help="quais product_id considerar (o produto tem dois homônimos)",
    )
    parser.add_argument("--parquet", type=Path, help="salva o dataset unificado em Parquet")
    args = parser.parse_args(argv)

    if not args.csv_dir.is_dir():
        print(f"erro: {args.csv_dir} não é um diretório", file=sys.stderr)
        return 1

    print("=" * 70)
    print(" Q6 — Previsão de demanda · Bússola de Bordo 702")
    print("=" * 70)

    # ---- 1. dataset unificado ------------------------------------------
    df = construir_dataset(args.csv_dir)
    print(f"\n[1] Dataset unificado: {len(df):,} linhas de item, "
          f"{df['mes'].min()} a {df['mes'].max()}".replace(",", "."))

    if args.parquet:
        args.parquet.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(args.parquet, index=False)
        print(f"    salvo em {args.parquet}")

    # ---- 2. o produto alvo, e a ambiguidade dos dois ids ----------------
    alvo = df[df["produto"] == PRODUTO_ALVO]
    ids_encontrados = sorted(alvo["product_id"].unique().tolist())

    print(f"\n[2] '{PRODUTO_ALVO}' encontrado com product_id: {ids_encontrados}")
    if len(ids_encontrados) > 1:
        print("    ATENÇÃO: o nome corresponde a mais de um produto no cadastro.")
        for pid in ids_encontrados:
            linha = alvo[alvo["product_id"] == pid].iloc[0]
            print(f"      id {pid}: brand_id={linha['brand_id']}, "
                  f"category_id={linha['category_id']}")

    ids_cenario = ids_encontrados if args.cenario == "ambos" else [int(args.cenario)]
    print(f"    Cenário adotado: {args.cenario}  ->  ids {ids_cenario}")

    # ---- 3. corte de treino, ANTES de qualquer estatística ---------------
    # O corte é físico e acontece aqui, na construção da série, e não num
    # filtro aplicado depois. Nenhuma linha de 2026 participa de nenhum
    # cálculo do modelo.
    inicio_serie = df["mes"].min()
    treino = serie_mensal(df, ids_cenario, inicio_serie, FIM_TREINO)
    real_teste = serie_mensal(df, ids_cenario, INICIO_TESTE, FIM_TESTE)

    print(f"\n[3] Treino: {treino.index.min()} a {treino.index.max()} "
          f"({len(treino)} meses, {treino.sum():.0f} unidades)")
    print(f"    Teste : {real_teste.index.min()} a {real_teste.index.max()} "
          f"({len(real_teste)} meses, {real_teste.sum():.0f} unidades)")

    print(f"\n    Últimos {JANELA_MM} meses do treino (a janela da média móvel):")
    for periodo, valor in treino.iloc[-JANELA_MM:].items():
        print(f"      {periodo}  {valor:6.0f} un.")

    # ---- 4. previsão -----------------------------------------------------
    previsao = prever_media_movel(treino, len(real_teste), JANELA_MM)
    media_movel = treino.iloc[-JANELA_MM:].mean()

    print(f"\n[4] Média móvel de {JANELA_MM} meses = {media_movel:.4f} un./mês")
    print("\n    Mês       Previsto      Real     Erro abs.")
    print("    " + "-" * 44)
    for periodo in real_teste.index:
        p, r = previsao[periodo], real_teste[periodo]
        print(f"    {periodo}   {p:8.2f}  {r:8.0f}     {abs(r - p):8.2f}")
    print("    " + "-" * 44)
    print(f"    SOMA      {previsao.sum():8.2f}  {real_teste.sum():8.0f}")

    # ---- 5. MAE ----------------------------------------------------------
    erro = mae(real_teste, previsao)
    print(f"\n[5] MAE = {erro:.4f} unidades/mês")

    # ---- 6. a resposta da Q6.2 -------------------------------------------
    # O enunciado pede "a SOMA TOTAL da previsão, arredondada para inteiro":
    # arredonda-se a SOMA, não cada mês. A diferença é real — arredondar
    # cada mês daria 39*3 = 117.
    soma_previsao = int(round(previsao.sum()))
    soma_por_mes = int(round(previsao.iloc[0])) * len(previsao)

    print("\n" + "=" * 70)
    print(f" Q6.2 — SOMA DA PREVISÃO PARA O 1º TRIMESTRE DE 2026: {soma_previsao}")
    print("=" * 70)
    print(f"    soma exata = {previsao.sum():.4f}  ->  arredondada = {soma_previsao}")
    print(f"    (arredondar cada mês antes de somar daria {soma_por_mes} — o")
    print("     enunciado pede a soma arredondada, não a soma dos arredondados)")

    # ---- 7. o baseline é adequado? a evidência ---------------------------
    print("\n" + "=" * 70)
    print(" Q6.5.a — O baseline é adequado? Comparação contra alternativas")
    print("=" * 70)

    # Seasonal naive: repete o mesmo trimestre do ano anterior. É o baseline
    # correto para série com sazonalidade, e serve de régua para o MM3.
    jan_mar_2025 = serie_mensal(df, ids_cenario, pd.Period("2025-01"), pd.Period("2025-03"))
    sazonal = pd.Series(jan_mar_2025.to_numpy(), index=real_teste.index)

    # Naive simples: repete o último mês observado.
    ingenuo = pd.Series(treino.iloc[-1], index=real_teste.index)

    modelos = {
        f"Média móvel {JANELA_MM}m (o pedido)": previsao,
        "Seasonal naive (repete Q1/2025)": sazonal,
        "Naive (repete dez/2025)": ingenuo,
    }
    print(f"\n    {'Modelo':<36} {'Soma':>8} {'MAE':>10}")
    print("    " + "-" * 56)
    for nome, serie in modelos.items():
        print(f"    {nome:<36} {serie.sum():>8.0f} {mae(real_teste, serie):>10.2f}")

    melhor = min(modelos, key=lambda k: mae(real_teste, modelos[k]))
    print(f"\n    Menor MAE: {melhor}")
    if not melhor.startswith("Média móvel"):
        print("    >> O baseline pedido PERDE para simplesmente copiar o ano")
        print("       anterior. A sazonalidade domina o sinal desta série.")

    # ---- 8. POR QUE o MM3 subestima -------------------------------------
    # Vale desmontar aqui a explicação intuitiva e ERRADA — "usou meses de
    # baixa para prever meses de pico". Os números abaixo mostram que a janela
    # out-dez é, na média histórica, MAIOR que jan-mar. A causa é outra.
    print("\n" + "=" * 70)
    print(f" Por que o MM3 subestima em {100 * (1 - previsao.sum() / real_teste.sum()):.0f}%")
    print("=" * 70)

    tabela = treino.to_frame("un")
    tabela["ano"] = [p.year for p in tabela.index]
    tabela["mes_num"] = [p.month for p in tabela.index]
    pivo = tabela.pivot_table(index="ano", columns="mes_num", values="un", fill_value=0)
    print("\n    Unidades por mês (linhas = ano de treino):")
    print()
    print(pivo.astype(int).to_string())

    perfil_mes = tabela.groupby("mes_num")["un"].mean()
    media_jfm = perfil_mes.loc[[1, 2, 3]].mean()
    media_ond = perfil_mes.loc[[10, 11, 12]].mean()

    print("\n    (a) NÃO é 'baixa prevendo pico'. A janela usada é ALTA:")
    print(f"        média histórica out-nov-dez = {media_ond:.1f} un./mês")
    print(f"        média histórica jan-fev-mar = {media_jfm:.1f} un./mês")
    print(f"        a baixa da série é o meio do ano "
          f"(jul = {perfil_mes.loc[7]:.1f} un./mês, o mínimo)")

    # (b) tendência: o motivo principal.
    por_ano = tabela.groupby("ano")["un"].sum()
    q1_por_ano = tabela[tabela["mes_num"].isin([1, 2, 3])].groupby("ano")["un"].sum()
    print("\n    (b) A CAUSA PRINCIPAL É A TENDÊNCIA. A série cresce, e uma")
    print("        média é um número plano — ela não extrapola crescimento.")
    print(f"        Total por ano: {', '.join(f'{a}={v:.0f}' for a, v in por_ano.items())}")
    crescimento = 100 * (por_ano.iloc[-1] / por_ano.iloc[0] - 1)
    print(f"        Crescimento de {por_ano.index[0]} a {por_ano.index[-1]}: "
          f"+{crescimento:.0f}%")
    print(f"        Só o 1º trimestre: "
          f"{', '.join(f'{a}={v:.0f}' for a, v in q1_por_ano.items())}"
          f", e 2026 veio {real_teste.sum():.0f}")

    # (c) o dezembro anômalo dentro de uma janela curta.
    dezembros = tabela[tabela["mes_num"] == 12]["un"]
    dez_anteriores = dezembros.iloc[:-1].mean()
    dez_2025 = dezembros.iloc[-1]
    impacto = (dez_anteriores - dez_2025) / JANELA_MM
    print("\n    (c) AGRAVANTE: dez/2025 é um ponto fora da curva, e a janela")
    print("        de 3 meses dá a ele 1/3 do peso.")
    print(f"        dezembros anteriores: "
          f"{', '.join(f'{v:.0f}' for v in dezembros.iloc[:-1])}  "
          f"(média {dez_anteriores:.1f})")
    print(f"        dez/2025 = {dez_2025:.0f} — menos da metade do usual")
    print(f"        sozinho, ele derruba a previsão em {impacto:.1f} un./mês "
          f"({impacto * len(previsao):.0f} un. no trimestre)")

    # ---- 9. os três cenários de id, para deixar a escolha auditável ------
    print("\n" + "=" * 70)
    print(" Sensibilidade — o resultado depende de qual product_id se adota")
    print("=" * 70)
    print(f"\n    {'Cenário':<22} {'MM3':>8} {'Previsão Q1':>12} {'Real Q1':>9} {'MAE':>8}")
    print("    " + "-" * 62)
    for rotulo, ids in [
        ("só id 74", [74]),
        ("só id 240", [240]),
        ("ambos (adotado)", ids_encontrados),
    ]:
        t = serie_mensal(df, ids, inicio_serie, FIM_TREINO)
        r = serie_mensal(df, ids, INICIO_TESTE, FIM_TESTE)
        p = prever_media_movel(t, len(r), JANELA_MM)
        print(f"    {rotulo:<22} {t.iloc[-JANELA_MM:].mean():>8.2f} "
              f"{int(round(p.sum())):>12} {r.sum():>9.0f} {mae(r, p):>8.2f}")

    print("\n" + "=" * 70)
    print(" Fim. Interpretação (Q6.3 e Q6.5) em RESPOSTA.md.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
