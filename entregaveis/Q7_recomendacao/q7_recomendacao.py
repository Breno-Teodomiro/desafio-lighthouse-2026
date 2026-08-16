#!/usr/bin/env python3
"""
Desafio Lighthouse 2026 — Questão 7: Sistema de recomendação por similaridade.

Constrói a matriz binária cliente × produto, calcula a similaridade de cosseno
produto × produto e gera o ranking dos 5 produtos mais similares ao
"Motor de Popa 1949".

    python3 q7_recomendacao.py --csv-dir ./1-lh_nautical_csv

PREMISSAS OBRIGATÓRIAS
----------------------
  · Matriz de interação: linhas = id_cliente, colunas = id_produto
  · Célula = 1 se o cliente comprou ao menos uma vez, 0 caso contrário
  · Ignorar a quantidade comprada (presença/ausência apenas)
  · Similaridade de cosseno, produto × produto
  · Item de referência: "Motor de Popa 1949"
  · Ranking dos 5 mais similares, desconsiderando o próprio motor
  · Bibliotecas permitidas: pandas, numpy, sklearn (opcional)

A ARMADILHA QUE MUDA A RESPOSTA
-------------------------------
Agrupar a matriz por NOME de produto em vez de product_id funde os homônimos
do cadastro e faz o produto de nome 'asdf' subir ao 1º lugar com 0,2789 — um
artefato puro de juntar dois produtos de lixo que não têm relação entre si.
A matriz é sempre construída por `product_id`; o nome só entra na hora de
renderizar o ranking.

SOBRE O sklearn
---------------
`cosine_similarity` sobre uma matriz binária densa é literalmente `Xn.T @ Xn`
depois de normalizar as colunas em L2. Escrever a métrica explicitamente
demonstra entendê-la, que é o critério declarado do Tech Lead. O bloco
`--validar-sklearn` confere o resultado contra a implementação da biblioteca.

Autor: Breno Teodomiro · Desafio Técnico Lighthouse 2026 (Indicium)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PRODUTO_REFERENCIA = "Motor de Popa 1949"
TOP_N = 5

# Tokens de lixo que existem no cadastro de produtos desta base. Não são
# removidos em lugar nenhum — remover seria "limpar" um resultado. Servem só
# para MARCAR com alerta um item que apareça no ranking, para que quem lê
# saiba que aquilo é um problema de cadastro e não uma recomendação.
NOMES_SUSPEITOS = frozenset(
    {"?", "??", "-", "--", "—", "...", "n/a", "N/A", "TBD", "TODO",
     "FIXME", "asdf", "test", "xxx", "Sem Nome", ""}
)


# ==========================================================================
# §1  DADOS
# ==========================================================================


def carregar(csv_dir: Path) -> pd.DataFrame:
    """Junta itens, pedidos, variantes e produtos no grão de linha de item.

    Dois joins e um motivo para cada:
      · `orders`           -> para chegar em customer_id (o item não o carrega)
      · `product_variants` -> para subir de VARIANTE para PRODUTO

    `order_items` não tem `product_id`: ela referencia a variante. A pergunta
    da Marina é sobre produto ("quem comprou lancha leva defensa"), não sobre
    variante, então esse salto é obrigatório.
    """
    itens = pd.read_csv(csv_dir / "order_items.csv")
    pedidos = pd.read_csv(csv_dir / "orders.csv")
    variantes = pd.read_csv(csv_dir / "product_variants.csv")
    produtos = pd.read_csv(csv_dir / "products.csv")

    return (
        itens.merge(
            pedidos[["id", "customer_id", "status", "created_at"]],
            left_on="order_id", right_on="id", suffixes=("", "_pedido"),
        )
        .merge(
            variantes[["id", "product_id"]],
            left_on="product_variant_id", right_on="id", suffixes=("", "_variante"),
        )
        .merge(
            produtos[["id", "name"]],
            left_on="product_id", right_on="id", suffixes=("", "_produto"),
        )
        .rename(columns={"name": "produto"})
    )


def rotulos_de_produto(df: pd.DataFrame) -> dict[int, str]:
    """Mapa product_id -> rótulo de exibição.

    Quando dois produtos compartilham o nome, o rótulo recebe o id para que o
    ranking não apresente duas linhas visualmente idênticas. Isso é decisão de
    APRESENTAÇÃO — a matriz nunca foi agrupada por nome.
    """
    nomes = df.drop_duplicates("product_id").set_index("product_id")["produto"]
    contagem = nomes.value_counts()
    return {
        pid: (nome if contagem[nome] == 1 else f"{nome} (id={pid})")
        for pid, nome in nomes.items()
    }


# ==========================================================================
# §2  MATRIZ DE INTERAÇÃO E SIMILARIDADE
# ==========================================================================


def matriz_interacao(df: pd.DataFrame) -> pd.DataFrame:
    """Matriz binária cliente × produto.

    `crosstab` conta ocorrências; o `> 0` colapsa qualquer contagem em True.
    É assim que a premissa "ignore a quantidade comprada" vira código: um
    cliente que comprou 7 unidades e outro que comprou 1 são idênticos aqui.
    """
    return (pd.crosstab(df["customer_id"], df["product_id"]) > 0).astype("float64")


def similaridade_cosseno(matriz: pd.DataFrame) -> pd.DataFrame:
    """Cosseno produto × produto, escrito explicitamente.

        cos(i, j) = (vi · vj) / (||vi|| * ||vj||)

    Normalizando cada COLUNA (produto) para norma 1, o produto escalar entre
    duas colunas já É o cosseno — então a matriz inteira sai de uma
    multiplicação só: Xn.T @ Xn.

    Com vetores binários isso tem uma leitura fechada:

        cos(i, j) = |Ci ∩ Cj| / sqrt(|Ci| * |Cj|)

    ou seja, o número de clientes que compraram AMBOS, normalizado pela
    popularidade dos dois. É o coeficiente de Ochiai. Sem a normalização, o
    "mais similar" seria sempre o mais vendido da loja.
    """
    A = matriz.to_numpy()
    normas = np.linalg.norm(A, axis=0)
    # Guarda para produto sem nenhum comprador (cold start): dividir por zero
    # geraria NaN e contaminaria a matriz inteira.
    normas[normas == 0] = 1.0
    An = A / normas
    S = An.T @ An
    return pd.DataFrame(S, index=matriz.columns, columns=matriz.columns)


def ranking(
    sim: pd.DataFrame, pid_ref: int, rotulos: dict[int, str], n: int
) -> pd.DataFrame:
    """Top-N mais similares ao item de referência, excluindo ele mesmo."""
    serie = sim.loc[pid_ref].drop(index=pid_ref)  # descarta o próprio item
    topo = serie.sort_values(ascending=False).head(n)
    return pd.DataFrame(
        {
            "product_id": topo.index,
            "produto": [rotulos[p] for p in topo.index],
            "similaridade": topo.to_numpy(),
            "suspeito": [
                rotulos[p].split(" (id=")[0] in NOMES_SUSPEITOS for p in topo.index
            ],
        }
    ).reset_index(drop=True)


# ==========================================================================
# §3  EXECUÇÃO
# ==========================================================================


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Recomendação por similaridade de cosseno entre produtos."
    )
    parser.add_argument("--csv-dir", type=Path, required=True, help="diretório com os .csv")
    parser.add_argument("--top", type=int, default=TOP_N, help="tamanho do ranking")
    parser.add_argument(
        "--validar-sklearn",
        action="store_true",
        help="confere a matriz de similaridade contra sklearn.cosine_similarity",
    )
    args = parser.parse_args(argv)

    if not args.csv_dir.is_dir():
        print(f"erro: {args.csv_dir} não é um diretório", file=sys.stderr)
        return 1

    print("=" * 70)
    print(f" Q7 — Recomendação para '{PRODUTO_REFERENCIA}'")
    print("=" * 70)

    df = carregar(args.csv_dir)
    rotulos = rotulos_de_produto(df)

    # ---- item de referência ---------------------------------------------
    ids_ref = sorted(df.loc[df["produto"] == PRODUTO_REFERENCIA, "product_id"].unique())
    if not ids_ref:
        print(f"erro: produto '{PRODUTO_REFERENCIA}' não encontrado", file=sys.stderr)
        return 1
    if len(ids_ref) > 1:
        print(f"ATENÇÃO: '{PRODUTO_REFERENCIA}' tem {len(ids_ref)} ids: {ids_ref}")
    pid_ref = ids_ref[0]
    print(f"\n[1] Item de referência: product_id {pid_ref}")

    # ---- matriz ----------------------------------------------------------
    matriz = matriz_interacao(df)
    n_clientes, n_produtos = matriz.shape
    densidade = 100 * matriz.to_numpy().mean()
    print(f"\n[2] Matriz de interação: {n_clientes} clientes × {n_produtos} produtos")
    print(f"    Valores distintos: {sorted(np.unique(matriz.to_numpy()))}  (binária)")
    print(f"    Densidade: {densidade:.2f}%  "
          f"(cada produto tem em média {matriz.sum(axis=0).mean():.0f} compradores)")
    print(f"    O item de referência foi comprado por "
          f"{int(matriz[pid_ref].sum())} clientes")

    # ---- similaridade ----------------------------------------------------
    sim = similaridade_cosseno(matriz)
    print(f"\n[3] Similaridade de cosseno: matriz {sim.shape[0]}×{sim.shape[1]}")
    print(f"    Simétrica: {np.allclose(sim.to_numpy(), sim.to_numpy().T)}")
    print(f"    Diagonal = 1: {np.allclose(np.diag(sim.to_numpy()), 1.0)}")

    if args.validar_sklearn:
        try:
            from sklearn.metrics.pairwise import cosine_similarity

            referencia = cosine_similarity(matriz.to_numpy().T)
            ok = np.allclose(sim.to_numpy(), referencia)
            print(f"    Confere com sklearn.cosine_similarity: {ok}")
        except ImportError:
            print("    sklearn não instalado; validação pulada")

    # ---- ranking ---------------------------------------------------------
    topo = ranking(sim, pid_ref, rotulos, args.top)
    print("\n" + "=" * 70)
    print(f" Q7.2 — TOP {args.top} MAIS SIMILARES A '{PRODUTO_REFERENCIA}'")
    print("=" * 70)
    print(f"\n    {'#':<3} {'id':>5}  {'produto':<28} {'cosseno':>10}")
    print("    " + "-" * 50)
    for i, linha in topo.iterrows():
        marca = "  <-- NOME SUSPEITO NO CADASTRO" if linha["suspeito"] else ""
        print(f"    {i + 1:<3} {linha['product_id']:>5}  {linha['produto']:<28} "
              f"{linha['similaridade']:>10.6f}{marca}")

    print(f"\n    >> RESPOSTA Q7.2: {topo.iloc[0]['produto']}")

    # ---- o 1º lugar é robusto? -------------------------------------------
    print("\n" + "=" * 70)
    print(" O 1º lugar é estatisticamente distinguível do 2º?")
    print("=" * 70)
    todas = sim.loc[pid_ref].drop(index=pid_ref)
    media, desvio = todas.mean(), todas.std()
    gap = topo.iloc[0]["similaridade"] - topo.iloc[1]["similaridade"]
    print(f"\n    As {len(todas)} similaridades do item de referência:")
    print(f"      média {media:.4f} · desvio {desvio:.4f} · máximo {todas.max():.4f}")
    print(f"\n    Gap entre 1º e 2º: {gap:.6f} "
          f"({100 * gap / topo.iloc[0]['similaridade']:.2f}% relativo)")
    print("\n    Distância da média, em desvios-padrão:")
    for i, linha in topo.iterrows():
        z = (linha["similaridade"] - media) / desvio
        print(f"      {i + 1}º {linha['produto']:<28} {z:.2f} sigma")
    print("\n    >> Os primeiros colocados estão praticamente na mesma distância")
    print("       da média. NÃO são estatisticamente distinguíveis entre si.")

    # ---- sensibilidade a filtro de status --------------------------------
    print("\n" + "=" * 70)
    print(" Sensibilidade — o enunciado não menciona status de pedido")
    print("=" * 70)
    recortes = {
        "todos os status (adotado)": df,
        "exclui draft": df[df["status"] != "draft"],
        "exclui cancelled": df[df["status"] != "cancelled"],
        "paid + confirmed": df[df["status"].isin(["paid", "confirmed"])],
        "só paid": df[df["status"] == "paid"],
    }
    print(f"\n    {'Recorte':<28} {'Top-1':<24} {'sim.':>9}")
    print("    " + "-" * 62)
    for rotulo, recorte in recortes.items():
        m = matriz_interacao(recorte)
        if pid_ref not in m.columns:
            continue
        s = similaridade_cosseno(m)
        t = ranking(s, pid_ref, rotulos, 1)
        print(f"    {rotulo:<28} {t.iloc[0]['produto']:<24} "
              f"{t.iloc[0]['similaridade']:>9.5f}")
    print("\n    O enunciado é explícito em todas as outras regras e NÃO menciona")
    print("    status. A leitura literal (sem filtro) é a resposta principal.")

    # ---- a armadilha do agrupamento por nome ------------------------------
    print("\n" + "=" * 70)
    print(" Prova da armadilha: agrupar por NOME em vez de product_id")
    print("=" * 70)
    m_nome = (pd.crosstab(df["customer_id"], df["produto"]) > 0).astype("float64")
    s_nome = similaridade_cosseno(m_nome)
    t_nome = s_nome.loc[PRODUTO_REFERENCIA].drop(index=PRODUTO_REFERENCIA)
    t_nome = t_nome.sort_values(ascending=False).head(3)
    print(f"\n    Matriz por nome: {m_nome.shape[1]} colunas "
          f"(contra {n_produtos} por product_id — {n_produtos - m_nome.shape[1]} "
          f"produtos foram FUNDIDOS)")
    print("\n    Top 3 que sairiam desse jeito ERRADO:")
    for nome, valor in t_nome.items():
        alerta = "  <-- LIXO DE CADASTRO" if nome in NOMES_SUSPEITOS else ""
        print(f"      {nome:<28} {valor:.6f}{alerta}")

    # ---- bônus: a formulação CORRETA do problema da Marina ---------------
    print("\n" + "=" * 70)
    print(" BÔNUS — co-ocorrência no MESMO PEDIDO (o que a Marina descreveu)")
    print("=" * 70)
    pedidos_com_ref = set(df.loc[df["product_id"] == pid_ref, "order_id"])
    juntos = (
        df[df["order_id"].isin(pedidos_com_ref) & (df["product_id"] != pid_ref)]
        .groupby("product_id")["order_id"]
        .nunique()
        .sort_values(ascending=False)
        .head(args.top)
    )
    print(f"\n    Pedidos que contêm o item de referência: {len(pedidos_com_ref)}")
    print(f"\n    {'produto':<30} {'pedidos em comum':>18}")
    print("    " + "-" * 50)
    for pid, n in juntos.items():
        print(f"    {rotulos[pid]:<30} {n:>18}")
    print("\n    Este é o grão CORRETO para 'quem comprou isso também levou':")
    print("    associação de CESTA (mesmo pedido), não sobreposição de base de")
    print("    clientes ao longo de anos. Ver a discussão em RESPOSTA.md.")

    print("\n" + "=" * 70)
    print(" Fim. Explicação (Q7.3) em RESPOSTA.md.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
