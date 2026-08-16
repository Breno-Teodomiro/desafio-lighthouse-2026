#!/usr/bin/env python3
"""
Verificação adversarial das 7 respostas — por caminho INDEPENDENTE.

    python3 tests/verificar_respostas.py

A ideia é simples e é a única que vale: recalcular cada resposta usando a
tecnologia OPOSTA à do entregável.

  · Q1, Q4 e Q5 foram respondidas em SQL, lendo o banco.
    Aqui são recalculadas em Python, lendo os CSVs originais.

  · Q6 e Q7 foram respondidas em Python (pandas/numpy), lendo os CSVs.
    Aqui são recalculadas em SQL, lendo o banco.

  · Q2 e Q3 são verificadas contra o estado real do banco.

Se as duas rotas concordam, o número sobreviveu a: uma carga de CSV para
PostgreSQL, uma inferência de tipo, dois motores de agregação diferentes e
duas implementações escritas em momentos distintos. Se divergem, uma das
duas está errada — e é muito melhor descobrir isso aqui.

A prova é de TENTATIVA ÚNICA. Este arquivo é a última linha de defesa.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import psycopg

RAIZ = Path(__file__).resolve().parent.parent
CSV_DIR = RAIZ / "1-lh_nautical_csv"

resultados: list[tuple[str, str, str, str, bool]] = []


def conferir(questao: str, item: str, esperado: object, obtido: object) -> None:
    ok = str(esperado) == str(obtido)
    resultados.append((questao, item, str(esperado), str(obtido), ok))


def ler_csv(nome: str) -> list[dict[str, str]]:
    with open(CSV_DIR / f"{nome}.csv", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# ==========================================================================
#  Q1 — em Python, direto dos CSVs (o entregável é SQL)
# ==========================================================================

def verificar_q1() -> None:
    pedidos = ler_csv("orders")
    totais = [Decimal(p["total"]) for p in pedidos]
    datas = [p["created_at"] for p in pedidos]

    conferir("Q1", "linhas", 48998, len(pedidos))
    conferir("Q1", "created_at min", "2020-01-01 01:19:28", min(datas))
    conferir("Q1", "created_at max", "2026-12-31 23:43:09", max(datas))
    conferir("Q1", "total min", "32.62", min(totais))
    conferir("Q1", "total max", "127262.02", max(totais))

    # `sum(x, Decimal(0))` e não `sum(x)`: sem a semente, o acumulador começa
    # no int 0 e a divisão poderia cair em float, perdendo exatidão justo na
    # conta que é a resposta da questão.
    media = sum(totais, Decimal(0)) / len(totais)
    conferir("Q1.2", "total médio (2 casas)", "28704.99",
             media.quantize(Decimal("0.01")))

    # A aritmética interna, conferida item a item.
    fecha = sum(
        1 for p in pedidos
        if Decimal(p["subtotal"]) - Decimal(p["discount_amount"]) == Decimal(p["total"])
    )
    conferir("Q1", "subtotal-desconto=total", 48998, fecha)


# ==========================================================================
#  Q2 / Q3 — contra o estado real do banco
# ==========================================================================

def verificar_q2_q3(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='raw'"
        )
        conferir("Q2", "tabelas em raw", 24, cur.fetchone()[0])  # type: ignore[index]

        cur.execute(
            "SELECT count(*) FROM information_schema.table_constraints "
            "WHERE table_schema='raw' AND constraint_type='FOREIGN KEY'"
        )
        conferir("Q2", "chaves estrangeiras", 37, cur.fetchone()[0])  # type: ignore[index]

        # Os tipos das colunas-armadilha, conferidos um a um.
        armadilhas = {
            ("customers", "tax_id"): "character varying",
            ("fiscal_invoices", "series"): "character varying",
            ("fiscal_invoices", "nfe_access_key"): "character varying",
            ("employees", "cpf"): "character varying",
            ("stock_levels", "reorder_point"): "text",
            ("stock_movements", "quantity"): "numeric",
            ("order_items", "quantity"): "integer",
            ("purchase_orders", "expected_delivery_at"): "date",
        }
        for (tabela, col), esperado in armadilhas.items():
            cur.execute(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_schema='raw' AND table_name=%s AND column_name=%s",
                (tabela, col),
            )
            linha = cur.fetchone()
            conferir("Q2", f"tipo {tabela}.{col}", esperado,
                     linha[0] if linha else "AUSENTE")

        # Q3.2 — contagem no banco contra contagem dos CSVs.
        total = 0
        for tabela in ("customers", "orders", "order_items", "payments"):
            cur.execute(f'SELECT count(*) FROM raw."{tabela}"')
            no_banco = cur.fetchone()[0]  # type: ignore[index]
            no_csv = len(ler_csv(tabela))
            conferir("Q3", f"{tabela} (banco vs CSV)", no_csv, no_banco)
            total += no_banco
        conferir("Q3.2", "SOMA das 4 tabelas", 251864, total)

        # Fidelidade: o lixo textual continua no banco, sem tratamento.
        cur.execute(
            "SELECT count(*) FROM raw.customers WHERE legal_name IN ('TBD','Sem Nome')"
        )
        conferir("Q3", "lixo textual preservado", 2, cur.fetchone()[0])  # type: ignore[index]
        cur.execute("SELECT count(*) FROM raw.customers WHERE tax_id LIKE '0%'")
        n_zeros = cur.fetchone()[0]  # type: ignore[index]
        conferir("Q3", "zeros à esquerda preservados", True, n_zeros > 0)


# ==========================================================================
#  Q4 — em Python, direto dos CSVs (o entregável é SQL)
# ==========================================================================

def verificar_q4() -> None:
    pedidos = ler_csv("orders")
    itens = ler_csv("order_items")
    variantes = {v["id"]: v["product_id"] for v in ler_csv("product_variants")}
    produtos = {p["id"]: p["category_id"] for p in ler_csv("products")}
    categorias = {c["id"]: c["name"] for c in ler_csv("categories")}

    # Faturamento e frequência SEM nenhum join — é o que evita o fan-out.
    fat: dict[str, Decimal] = defaultdict(Decimal)
    freq: dict[str, int] = defaultdict(int)
    cliente_do_pedido: dict[str, str] = {}
    for p in pedidos:
        fat[p["customer_id"]] += Decimal(p["total"])
        freq[p["customer_id"]] += 1
        cliente_do_pedido[p["id"]] = p["customer_id"]

    # Diversidade: percorre itens, sobe até a categoria.
    cats_por_cliente: dict[str, set[str]] = defaultdict(set)
    for it in itens:
        cliente = cliente_do_pedido.get(it["order_id"])
        if cliente is None:
            continue
        cat = produtos.get(variantes.get(it["product_variant_id"], ""), "")
        if cat:
            cats_por_cliente[cliente].add(cat)

    elegiveis = [
        (fat[c] / freq[c], int(c))
        for c in fat
        if len(cats_por_cliente.get(c, set())) >= 13
    ]
    # Desempate: ticket desc, customer_id asc.
    elegiveis.sort(key=lambda t: (-t[0], t[1]))
    top10 = [str(cid) for _, cid in elegiveis[:10]]

    conferir("Q4", "quantidade no top 10", 10, len(top10))
    conferir("Q4", "líder do ranking", "22", top10[0])
    conferir("Q4", "ticket do líder", "41839.94",
             (elegiveis[0][0]).quantize(Decimal("0.01")))
    conferir("Q4", "top 10 completo",
             "22,1477,929,1116,1691,774,1470,1599,965,1722", ",".join(top10))
    conferir("Q4", "clientes com >= 13 categorias", 1971,
             sum(1 for c in cats_por_cliente if len(cats_por_cliente[c]) >= 13))

    # Categoria com maior SUM(quantity) no grupo dos 10.
    grupo = set(top10)
    qtd_por_cat: dict[str, int] = defaultdict(int)
    for it in itens:
        if cliente_do_pedido.get(it["order_id"]) in grupo:
            cat = produtos.get(variantes.get(it["product_variant_id"], ""), "")
            if cat:
                qtd_por_cat[cat] += int(it["quantity"])
    lider = max(qtd_por_cat.items(), key=lambda kv: kv[1])
    conferir("Q4", "categoria líder", "Hélices", categorias[lider[0]])
    conferir("Q4", "itens da categoria líder", 492, lider[1])


# ==========================================================================
#  Q5 — em Python, direto dos CSVs (o entregável é SQL)
# ==========================================================================

def verificar_q5() -> None:
    from datetime import date, timedelta

    pedidos = [p for p in ler_csv("orders") if p["channel"] == "pos"]
    por_dia: dict[date, Decimal] = defaultdict(Decimal)
    for p in pedidos:
        d = date.fromisoformat(p["created_at"][:10])
        por_dia[d] += Decimal(p["total"])

    inicio, fim = min(por_dia), max(por_dia)
    dias = (fim - inicio).days + 1
    conferir("Q5", "dias no calendário", 2557, dias)

    nomes = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
             "Sexta-feira", "Sábado", "Domingo"]
    soma: dict[int, Decimal] = defaultdict(Decimal)
    n_cal: dict[int, int] = defaultdict(int)
    n_com: dict[int, int] = defaultdict(int)

    d = inicio
    vazios = 0
    while d <= fim:
        dow = d.weekday()  # 0 = segunda
        valor = por_dia.get(d, Decimal(0))
        soma[dow] += valor
        n_cal[dow] += 1
        if d in por_dia:
            n_com[dow] += 1
        else:
            vazios += 1
        d += timedelta(days=1)

    conferir("Q5", "dias sem venda", 78, vazios)

    com_cal = {i: soma[i] / n_cal[i] for i in range(7)}
    sem_cal = {i: soma[i] / n_com[i] for i in range(7)}
    pior_com = min(com_cal, key=lambda i: com_cal[i])
    pior_sem = min(sem_cal, key=lambda i: sem_cal[i])

    conferir("Q5", "pior dia COM calendário", "Quinta-feira", nomes[pior_com])
    conferir("Q5", "média do pior dia", "157154.32",
             com_cal[pior_com].quantize(Decimal("0.01")))
    conferir("Q5", "pior dia SEM calendário", "Segunda-feira", nomes[pior_sem])
    conferir("Q5", "média sem calendário", "161335.26",
             sem_cal[pior_sem].quantize(Decimal("0.01")))
    conferir("Q5", "dias vazios na quinta", 20, n_cal[3] - n_com[3])


# ==========================================================================
#  Q6 — em SQL, no banco (o entregável é pandas)
# ==========================================================================

def verificar_q6(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM raw.products WHERE name = 'Bússola de Bordo 702' ORDER BY id"
        )
        ids = [r[0] for r in cur.fetchall()]
        conferir("Q6", "product_id do produto alvo", "[74, 240]", str(ids))

        # Vendas mensais da janela de treino, em SQL puro.
        cur.execute(
            """
            SELECT to_char(o.created_at, 'YYYY-MM') AS mes, sum(oi.quantity)
              FROM raw.order_items      oi
              JOIN raw.product_variants pv ON pv.id = oi.product_variant_id
              JOIN raw.orders           o  ON o.id  = oi.order_id
             WHERE pv.product_id = ANY(%s)
               AND o.created_at >= '2025-10-01' AND o.created_at < '2026-01-01'
             GROUP BY 1 ORDER BY 1
            """,
            (ids,),
        )
        janela = cur.fetchall()
        conferir("Q6", "janela out/nov/dez-2025", "[34, 60, 22]",
                 str([int(v) for _, v in janela]))

        mm3 = sum(int(v) for _, v in janela) / 3
        conferir("Q6.2", "soma da previsão Q1/2026", 116, round(mm3 * 3))

        cur.execute(
            """
            SELECT sum(oi.quantity)
              FROM raw.order_items      oi
              JOIN raw.product_variants pv ON pv.id = oi.product_variant_id
              JOIN raw.orders           o  ON o.id  = oi.order_id
             WHERE pv.product_id = ANY(%s)
               AND o.created_at >= '2026-01-01' AND o.created_at < '2026-04-01'
            """,
            (ids,),
        )
        real = int(cur.fetchone()[0])  # type: ignore[index]
        conferir("Q6", "real do Q1/2026", 207, real)


# ==========================================================================
#  Q7 — em SQL, no banco (o entregável é numpy)
# ==========================================================================

def verificar_q7(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        # Cosseno binário = |Ci ∩ Cj| / sqrt(|Ci| * |Cj|), calculado em SQL.
        # É a mesma métrica por uma implementação completamente diferente da
        # multiplicação de matrizes do numpy.
        cur.execute(
            """
            WITH cliente_produto AS (
                SELECT DISTINCT o.customer_id, pv.product_id
                  FROM raw.order_items      oi
                  JOIN raw.product_variants pv ON pv.id = oi.product_variant_id
                  JOIN raw.orders           o  ON o.id  = oi.order_id
            ),
            referencia AS (
                SELECT id FROM raw.products WHERE name = 'Motor de Popa 1949'
            ),
            compradores_ref AS (
                SELECT customer_id FROM cliente_produto
                 WHERE product_id = (SELECT id FROM referencia)
            ),
            popularidade AS (
                SELECT product_id, count(*)::numeric AS n
                  FROM cliente_produto GROUP BY product_id
            ),
            intersecao AS (
                SELECT cp.product_id, count(*)::numeric AS comuns
                  FROM cliente_produto cp
                  JOIN compradores_ref cr ON cr.customer_id = cp.customer_id
                 WHERE cp.product_id <> (SELECT id FROM referencia)
                 GROUP BY cp.product_id
            )
            SELECT p.name,
                   round(i.comuns / sqrt(pop.n * (SELECT n FROM popularidade
                                                   WHERE product_id =
                                                     (SELECT id FROM referencia))), 6)
                     AS cosseno
              FROM intersecao   i
              JOIN popularidade pop ON pop.product_id = i.product_id
              JOIN raw.products p   ON p.id           = i.product_id
             ORDER BY cosseno DESC, p.id
             LIMIT 3
            """
        )
        topo = cur.fetchall()
        conferir("Q7.2", "produto mais similar", "Motor de Popa 5331", topo[0][0])
        conferir("Q7", "cosseno do 1º lugar", "0.256553", str(topo[0][1]))
        conferir("Q7", "2º lugar", "Cabo Náutico 2105", topo[1][0])
        conferir("Q7", "3º lugar", "Vela Mestra 1913", topo[2][0])


# ==========================================================================

def main() -> int:
    if not CSV_DIR.is_dir():
        print(f"erro: {CSV_DIR} não existe", file=sys.stderr)
        return 1

    print("=" * 78)
    print(" VERIFICAÇÃO ADVERSARIAL — cada resposta por caminho independente")
    print("=" * 78)
    print("\nQ1, Q4, Q5: entregues em SQL  ->  recalculadas aqui em Python, dos CSVs")
    print("Q6, Q7:     entregues em Python -> recalculadas aqui em SQL, do banco")
    print("Q2, Q3:     conferidas contra o estado real do banco\n")

    with psycopg.connect("") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database()")
            banco = cur.fetchone()[0]  # type: ignore[index]
        if banco != "lh_nautical":
            print(f"ABORTADO: conectado em '{banco}'", file=sys.stderr)
            return 2

        verificar_q1()
        verificar_q2_q3(conn)
        verificar_q4()
        verificar_q5()
        verificar_q6(conn)
        verificar_q7(conn)

    largura = max(len(i) for _, i, _, _, _ in resultados)
    questao_atual = None
    for questao, item, esperado, obtido, ok in resultados:
        if questao != questao_atual:
            print(f"\n  {questao}")
            questao_atual = questao
        marca = "ok  " if ok else "FALHA"
        detalhe = "" if ok else f"   (esperado {esperado}, obtido {obtido})"
        valor = obtido if ok else ""
        print(f"    {marca} {item:<{largura}}  {valor}{detalhe}")

    falhas = [r for r in resultados if not r[4]]
    print("\n" + "=" * 78)
    if falhas:
        print(f" REPROVADO — {len(falhas)} de {len(resultados)} conferências falharam")
        print("=" * 78)
        return 1
    print(f" APROVADO — {len(resultados)} conferências, todas por caminho independente")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
