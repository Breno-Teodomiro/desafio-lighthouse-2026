#!/usr/bin/env python3
"""
Desafio Lighthouse 2026 — Questão 3: carga dos 24 CSVs no PostgreSQL.

Carrega todos os arquivos CSV de um diretório nas tabelas criadas pelo
`schema.sql` da Questão 2, em uma única transação, sem transformar nenhum valor.

    python3 q3_carregar_csvs.py --csv-dir ./1-lh_nautical_csv --schema raw
    python3 q3_carregar_csvs.py --csv-dir ./1-lh_nautical_csv --dry-run

Conexão por variáveis de ambiente do PostgreSQL (PGHOST, PGPORT, PGDATABASE,
PGUSER, PGPASSWORD) ou por --dsn.

PREMISSA CENTRAL DA QUESTÃO
---------------------------
"Não faça tratamentos como: Remoção de nulos ou correção de caracteres
especiais."

A resposta deste script a essa premissa é `COPY ... FROM STDIN` alimentado com
os BYTES do arquivo, em blocos. O Python aqui nunca decodifica, interpreta nem
reserializa um único valor: os bytes saem do disco e entram no parser do
servidor. Isso elimina, por construção, três classes de alteração silenciosa
que uma carga linha-a-linha introduziria:

  · round-trip por float — `2398.41` lido como float64 e reescrito pode virar
    `2398.4100000000001`; aqui o texto `2398.41` chega intacto ao NUMERIC;
  · reinterpretação de encoding — nenhum `str.encode`/`decode` de valor
    acontece, então acento não tem por onde se corromper;
  · "limpeza" acidental — os tokens `?`, `??`, `-`, `n/a`, `TBD`, `asdf`,
    `Sem Nome` que existem na fonte entram no banco exatamente como estão,
    porque não há um ponto no código onde alguém pudesse decidir o contrário.

A alternativa (`executemany` ou `execute_values`) exigiria escrever à mão a
regra de vazio-vs-NULL para cada campo — ou seja, exigiria tratar o dado
justamente onde o enunciado proíbe.

VAZIO vs NULL
-------------
`WITH (FORMAT csv, NULL '')` converte campo NÃO-aspado vazio em NULL e preserva
campo aspado vazio (`""`) como string vazia. Verificado nesta base: **não existe
um único caractere `"` em nenhum dos 24 arquivos**. Logo a fonte não consegue
representar "string vazia" como algo distinto de "ausente", e o mapeamento não
descarta informação — é bijetivo no domínio que existe. Sem essa verificação a
escolha seria arbitrária; com ela, é demonstrável.

Autor: Breno Teodomiro · Desafio Técnico Lighthouse 2026 (Indicium)
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

try:
    import psycopg
except ImportError:  # pragma: no cover
    print(
        "erro: psycopg 3 não encontrado.  Instale com:  pip install 'psycopg[binary]'\n"
        "      (a Questão 3 permite explicitamente bibliotecas externas)",
        file=sys.stderr,
    )
    raise SystemExit(1) from None


BLOCO = 1 << 20  # 1 MiB por leitura — o COPY é um fluxo, não um buffer único

# As 24 tabelas da camada raw, nominalmente. O TRUNCATE só toca nesta lista.
# A instância PostgreSQL é compartilhada com outros projetos: nada aqui pode
# ser genérico o bastante para alcançar um objeto que não seja nosso.
TABELAS_RAW = (
    "addresses",
    "attributes",
    "brands",
    "categories",
    "customers",
    "employees",
    "fiscal_invoices",
    "goods_receipt_items",
    "goods_receipts",
    "locations",
    "order_items",
    "orders",
    "payments",
    "product_suppliers",
    "product_variants",
    "products",
    "purchase_order_items",
    "purchase_orders",
    "return_items",
    "returns",
    "stock_levels",
    "stock_movements",
    "suppliers",
    "variant_attribute_values",
)

BANCO_ESPERADO = "lh_nautical"

# Tabelas cuja soma responde à Questão 3.2.
TABELAS_VALIDACAO = ("customers", "orders", "order_items", "payments")
TOTAL_ESPERADO_Q32 = 251_864


# ==========================================================================
# §1  LEITURA DO CSV — apenas metadados; os dados nunca passam pelo Python
# ==========================================================================


def ler_cabecalho(caminho: Path) -> list[str]:
    """Lê somente a primeira linha e devolve os nomes das colunas.

    `utf-8-sig` descarta o BOM caso exista: sem isso a primeira coluna se
    chamaria `\\ufeffid` e o COPY falharia com "column does not exist".
    """
    with open(caminho, encoding="utf-8-sig", newline="") as fh:
        return [c.strip() for c in next(csv.reader(fh))]


def contar_linhas_por_bytes(caminho: Path) -> int:
    """Conta registros contando bytes `\\n`, sem usar o parser de CSV.

    O ponto é a INDEPENDÊNCIA: a contagem que valida a carga não pode vir do
    mesmo caminho de código que executou a carga, senão valida a si mesma.
    Aqui não há `csv.reader` — só bytes.

    Válido porque nenhum dos 24 arquivos contém aspas (verificado), portanto
    nenhum campo pode conter uma quebra de linha embutida. Vale para LF e para
    CRLF: em ambos o separador de registro termina em `\\n`.
    """
    total = 0
    ultimo = b""
    with open(caminho, "rb") as fh:
        while bloco := fh.read(BLOCO):
            total += bloco.count(b"\n")
            ultimo = bloco[-1:]
    if ultimo and ultimo != b"\n":
        total += 1  # arquivo sem quebra de linha final
    return max(total - 1, 0)  # desconta o cabeçalho


def detectar_terminador(caminho: Path) -> str:
    """CRLF, LF ou misto — verificação de pré-voo, registrada no relatório.

    `COPY ... FORMAT csv` aceita os dois terminadores nativamente, então isso
    não altera a carga. Está aqui porque "o COPY aguenta" é uma afirmação que
    merece evidência, e porque um arquivo MISTO seria sinal de corrupção na
    extração e deve parar a carga em vez de passar despercebido.
    """
    with open(caminho, "rb") as fh:
        bloco = fh.read(65536)
    n_crlf = bloco.count(b"\r\n")
    n_lf = bloco.count(b"\n") - n_crlf
    if n_crlf and n_lf:
        return "misto"
    return "CRLF" if n_crlf else "LF"


# ==========================================================================
# §2  ORDEM DE CARGA — grafo de dependências lido do próprio banco
# ==========================================================================


def ordem_topologica(conn: psycopg.Connection, schema: str, tabelas: list[str]) -> list[str]:
    """Ordena as tabelas de forma que todo pai seja carregado antes do filho.

    A ordem é lida do `information_schema`, não hardcodada: se o schema mudar,
    a ordem se ajusta sozinha. Auto-referências (`categories.parent_category_id`)
    são ignoradas — uma tabela não pode esperar por si mesma.

    Rigorosamente falando isto é redundante: as FKs são DEFERRABLE e a
    transação roda com SET CONSTRAINTS ALL DEFERRED, então qualquer ordem
    funcionaria. É cinto e suspensório — e mantém o log de carga legível,
    porque os pais aparecem antes dos filhos.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT
                   filho.relname  AS filho,
                   pai.relname    AS pai
              FROM pg_constraint c
              JOIN pg_class      filho ON filho.oid = c.conrelid
              JOIN pg_class      pai   ON pai.oid   = c.confrelid
              JOIN pg_namespace  n     ON n.oid     = filho.relnamespace
             WHERE c.contype = 'f'
               AND n.nspname = %s
            """,
            (schema,),
        )
        arestas = [(f, p) for f, p in cur.fetchall() if f != p]

    conjunto = set(tabelas)
    dependencias: dict[str, set[str]] = defaultdict(set)
    dependentes: dict[str, set[str]] = defaultdict(set)
    for filho, pai in arestas:
        if filho in conjunto and pai in conjunto:
            dependencias[filho].add(pai)
            dependentes[pai].add(filho)

    # Kahn, com desempate alfabético para que a ordem seja determinística.
    prontos = deque(sorted(t for t in tabelas if not dependencias[t]))
    ordem: list[str] = []
    while prontos:
        atual = prontos.popleft()
        ordem.append(atual)
        novos = []
        for filho in sorted(dependentes[atual]):
            dependencias[filho].discard(atual)
            if not dependencias[filho]:
                novos.append(filho)
        for t in sorted(novos):
            prontos.append(t)

    if len(ordem) < len(tabelas):
        # Ciclo entre tabelas. Com constraints diferidas isso não impede a
        # carga, então seguimos em ordem alfabética em vez de abortar.
        restantes = sorted(conjunto - set(ordem))
        print(
            f"aviso: ciclo de FKs envolvendo {', '.join(restantes)}; "
            f"seguindo em ordem alfabética (constraints são DEFERRABLE)",
            file=sys.stderr,
        )
        ordem += restantes
    return ordem


# ==========================================================================
# §3  CARGA
# ==========================================================================


def copiar(
    cur: psycopg.Cursor, caminho: Path, schema: str, tabela: str, colunas: list[str]
) -> int:
    """Executa o COPY de um arquivo, transmitindo bytes crus.

    As colunas são nomeadas explicitamente a partir do cabeçalho do CSV: a
    carga passa a depender do NOME da coluna e não da posição dela na tabela.
    Se o CSV ganhar uma coluna nova amanhã, isso falha com mensagem clara em
    vez de deslocar valores silenciosamente de uma coluna para a vizinha.
    """
    lista = ", ".join(f'"{c}"' for c in colunas)
    sql = (
        f'COPY "{schema}"."{tabela}" ({lista}) FROM STDIN '
        f"WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8')"
    )
    with open(caminho, "rb") as fh, cur.copy(sql) as cp:
        while bloco := fh.read(BLOCO):
            cp.write(bloco)
    return cur.rowcount


def escalar(cur: psycopg.Cursor, sql: str, *params: object) -> Any:
    """Executa uma consulta que devolve um único valor e o retorna.

    Existe para que a ausência de linha vire erro explícito em vez de
    `TypeError: 'NoneType' object is not subscriptable` a três quadros de
    distância — o que importa aqui, onde uma dessas consultas é a guarda que
    decide se é seguro escrever no banco.
    """
    cur.execute(sql, params or None)
    linha = cur.fetchone()
    if linha is None:
        raise RuntimeError(f"consulta não devolveu linha alguma: {sql}")
    return linha[0]


def conferir_colunas(
    cur: psycopg.Cursor, schema: str, tabela: str, colunas_csv: list[str]
) -> None:
    """Aborta antes de escrever qualquer byte se o CSV não casar com a tabela."""
    cur.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_schema = %s AND table_name = %s
        """,
        (schema, tabela),
    )
    no_banco = {r[0] for r in cur.fetchall()}
    if not no_banco:
        raise RuntimeError(f'{tabela}: tabela "{schema}"."{tabela}" não existe — rode a Q2 antes')

    faltando = [c for c in colunas_csv if c not in no_banco]
    if faltando:
        raise RuntimeError(
            f"{tabela}: colunas presentes no CSV e ausentes na tabela: {', '.join(faltando)}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Carrega os CSVs da LH Nautical no PostgreSQL, sem tratar os dados.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Conexão: variáveis PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD, ou --dsn.\n"
            "Exemplo:\n"
            "  python3 q3_carregar_csvs.py --csv-dir ./1-lh_nautical_csv --relatorio carga.md\n"
        ),
    )
    parser.add_argument("--csv-dir", type=Path, required=True, help="diretório com os .csv")
    parser.add_argument("--schema", default="raw", help="schema de destino (padrão: raw)")
    parser.add_argument("--dsn", default=None, help="string de conexão; padrão = variáveis PG*")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="confere cabeçalhos e conta linhas sem escrever nada no banco",
    )
    parser.add_argument(
        "--sem-truncate",
        action="store_true",
        help="não limpa as tabelas antes (padrão é TRUNCATE nominal, para idempotência)",
    )
    parser.add_argument("--relatorio", type=Path, help="grava um relatório .md da carga")
    args = parser.parse_args(argv)

    if not args.csv_dir.is_dir():
        print(f"erro: {args.csv_dir} não é um diretório", file=sys.stderr)
        return 1

    # ---- inventário e pré-voo, tudo antes de abrir transação ---------------
    arquivos: dict[str, Path] = {}
    for tabela in TABELAS_RAW:
        caminho = args.csv_dir / f"{tabela}.csv"
        if not caminho.is_file():
            print(f"erro: arquivo ausente: {caminho}", file=sys.stderr)
            return 1
        arquivos[tabela] = caminho

    extras = sorted(p.stem for p in args.csv_dir.glob("*.csv") if p.stem not in arquivos)
    if extras:
        print(
            f"aviso: {len(extras)} CSV(s) fora da lista da camada raw, ignorados: "
            f"{', '.join(extras)}",
            file=sys.stderr,
        )

    print(f"Pré-voo em {len(arquivos)} arquivos...", file=sys.stderr)
    cabecalhos: dict[str, list[str]] = {}
    linhas_csv: dict[str, int] = {}
    terminadores: dict[str, str] = {}
    for tabela, caminho in arquivos.items():
        cabecalhos[tabela] = ler_cabecalho(caminho)
        linhas_csv[tabela] = contar_linhas_por_bytes(caminho)
        terminadores[tabela] = detectar_terminador(caminho)
        if terminadores[tabela] == "misto":
            print(
                f"erro: {caminho.name} tem terminadores de linha MISTOS (CRLF e LF no "
                f"mesmo arquivo). Isso indica extração corrompida; a carga foi abortada.",
                file=sys.stderr,
            )
            return 1

    total_csv = sum(linhas_csv.values())
    print(
        f"  {len(arquivos)} arquivos · {total_csv:,} linhas de dados".replace(",", "."),
        file=sys.stderr,
    )

    if args.dry_run:
        print("\n--dry-run: nada foi escrito. Inventário:\n", file=sys.stderr)
        for tabela in TABELAS_RAW:
            print(
                f"  {tabela:<26} {linhas_csv[tabela]:>7,} linhas · "
                f"{len(cabecalhos[tabela]):>2} colunas · {terminadores[tabela]}".replace(",", "."),
                file=sys.stderr,
            )
        return 0

    dsn = args.dsn or ""
    inicio = time.monotonic()
    carregadas: dict[str, int] = {}

    with psycopg.connect(dsn, autocommit=False) as conn:
        # ---- guarda de banco compartilhado --------------------------------
        # A instância é compartilhada com outros projetos do usuário. Um
        # TRUNCATE no banco errado seria irreversível, então o alvo é
        # conferido antes de qualquer comando de escrita.
        with conn.cursor() as cur:
            banco = escalar(cur, "SELECT current_database()")
        if banco != BANCO_ESPERADO:
            print(
                f"ABORTADO: conectado em '{banco}', esperado '{BANCO_ESPERADO}'.\n"
                f"          Esta instância PostgreSQL é compartilhada com outros "
                f"projetos.",
                file=sys.stderr,
            )
            return 2
        print(f"Conectado em {banco} (schema {args.schema}).", file=sys.stderr)

        with conn.cursor() as cur:
            # ISO/YMD é o formato dos arquivos; fixar aqui remove a dependência
            # do `datestyle` que estiver configurado no servidor.
            cur.execute("SET datestyle = 'ISO, YMD'")
            cur.execute("SET client_encoding = 'UTF8'")
            # Todas as 37 FKs passam a ser validadas de uma vez no COMMIT.
            cur.execute("SET CONSTRAINTS ALL DEFERRED")

            for tabela in TABELAS_RAW:
                conferir_colunas(cur, args.schema, tabela, cabecalhos[tabela])

            ordem = ordem_topologica(conn, args.schema, list(TABELAS_RAW))

            if not args.sem_truncate:
                # Lista NOMINAL, nunca CASCADE sem enumeração: o CASCADE aqui
                # alcança apenas tabelas que já estão todas na lista, e serve
                # para que a ordem do TRUNCATE não precise ser topológica.
                alvos = ", ".join(f'"{args.schema}"."{t}"' for t in TABELAS_RAW)
                print(f"TRUNCATE em {len(TABELAS_RAW)} tabelas de {args.schema}...",
                      file=sys.stderr)
                cur.execute(f"TRUNCATE {alvos} RESTART IDENTITY CASCADE")

            print("\nCarregando:", file=sys.stderr)
            for tabela in ordem:
                t0 = time.monotonic()
                n = copiar(cur, arquivos[tabela], args.schema, tabela, cabecalhos[tabela])
                carregadas[tabela] = n
                dt = time.monotonic() - t0
                marca = "ok" if n == linhas_csv[tabela] else "DIVERGE"
                print(
                    f"  {tabela:<26} {n:>7,} linhas · {dt:5.2f}s · {marca}".replace(",", "."),
                    file=sys.stderr,
                )

            # ---- verificação ANTES do COMMIT ------------------------------
            divergentes = [
                (t, linhas_csv[t], carregadas[t])
                for t in TABELAS_RAW
                if carregadas[t] != linhas_csv[t]
            ]
            if divergentes:
                detalhe = "; ".join(
                    f"{t}: CSV {esperado}, banco {obtido}" for t, esperado, obtido in divergentes
                )
                raise RuntimeError(f"contagem divergente, ROLLBACK — {detalhe}")

            # Terceira contagem, agora feita pelo próprio servidor: fecha o
            # circuito CSV (bytes) -> COPY (rowcount) -> SELECT (banco).
            for tabela in TABELAS_VALIDACAO:
                n = escalar(cur, f'SELECT count(*) FROM "{args.schema}"."{tabela}"')
                if n != linhas_csv[tabela]:
                    raise RuntimeError(
                        f"{tabela}: SELECT count(*) devolveu {n}, "
                        f"esperado {linhas_csv[tabela]} — ROLLBACK"
                    )

        # O COMMIT é o momento em que o PostgreSQL valida as 37 FKs de uma vez.
        conn.commit()
        print("\nCOMMIT. As 37 chaves estrangeiras foram validadas.", file=sys.stderr)

        # ANALYZE fora da transação de carga: atualiza as estatísticas do
        # planejador, sem o que as consultas das Q1/Q4/Q5 rodariam sobre
        # estimativas de tabela vazia.
        conn.autocommit = True
        with conn.cursor() as cur:
            for tabela in TABELAS_RAW:
                cur.execute(f'ANALYZE "{args.schema}"."{tabela}"')
        print("ANALYZE concluído.", file=sys.stderr)

    duracao = time.monotonic() - inicio
    total = sum(carregadas.values())
    soma_q32 = sum(carregadas[t] for t in TABELAS_VALIDACAO)

    print(
        f"\n{'=' * 62}\n"
        f"{total:,} linhas em {len(TABELAS_RAW)} tabelas · {duracao:.1f}s\n".replace(",", ".")
        + f"{'=' * 62}\n"
        f"Questão 3.2 — customers + orders + order_items + payments:\n",
        file=sys.stderr,
    )
    for tabela in TABELAS_VALIDACAO:
        print(f"  {tabela:<14} {carregadas[tabela]:>8,}".replace(",", "."), file=sys.stderr)
    print(f"  {'TOTAL':<14} {soma_q32:>8,}".replace(",", "."), file=sys.stderr)
    if soma_q32 != TOTAL_ESPERADO_Q32:
        print(
            f"\nATENÇÃO: esperado {TOTAL_ESPERADO_Q32:,}".replace(",", "."),
            file=sys.stderr,
        )

    if args.relatorio:
        args.relatorio.parent.mkdir(parents=True, exist_ok=True)
        args.relatorio.write_text(
            render_relatorio(linhas_csv, carregadas, terminadores, cabecalhos, duracao),
            encoding="utf-8",
        )
        print(f"\nrelatório: {args.relatorio}", file=sys.stderr)

    return 0


def render_relatorio(
    linhas_csv: dict[str, int],
    carregadas: dict[str, int],
    terminadores: dict[str, str],
    cabecalhos: dict[str, list[str]],
    duracao: float,
) -> str:
    total_csv = sum(linhas_csv.values())
    total_db = sum(carregadas.values())
    soma_q32 = sum(carregadas[t] for t in TABELAS_VALIDACAO)

    def br(n: int) -> str:
        """Separador de milhar no padrão brasileiro."""
        return f"{n:,}".replace(",", ".")

    out = [
        "# Relatório de carga — camada raw",
        "",
        f"Gerado por `q3_carregar_csvs.py` · {time.strftime('%Y-%m-%d %H:%M')} · "
        f"{duracao:.1f}s.",
        "",
        f"**{br(total_db)} linhas carregadas em {len(TABELAS_RAW)} tabelas.**",
        "",
        "## Conferência por tabela",
        "",
        "A coluna *CSV* vem da contagem de bytes `\\n` no arquivo; a coluna *Banco*",
        "vem do `rowcount` devolvido pelo `COPY`. São dois caminhos independentes —",
        "é isso que torna a conferência uma verificação, e não uma repetição.",
        "",
        "| Tabela | Colunas | Terminador | CSV | Banco | |",
        "|---|---:|---|---:|---:|---|",
    ]
    for tabela in TABELAS_RAW:
        ok = "✅" if carregadas[tabela] == linhas_csv[tabela] else "❌"
        out.append(
            f"| `{tabela}` | {len(cabecalhos[tabela])} | {terminadores[tabela]} | "
            f"{br(linhas_csv[tabela])} | {br(carregadas[tabela])} | {ok} |"
        )
    out += [
        f"| **TOTAL** | | | **{br(total_csv)}** | **{br(total_db)}** | "
        f"{'✅' if total_csv == total_db else '❌'} |",
        "",
        "## Questão 3.2",
        "",
        "| Tabela | Linhas |",
        "|---|---:|",
    ]
    for tabela in TABELAS_VALIDACAO:
        out.append(f"| `{tabela}` | {br(carregadas[tabela])} |")
    out += [
        f"| **TOTAL** | **{br(soma_q32)}** |",
        "",
        f"**Resposta: {br(soma_q32)}**",
        "",
        "## Garantias da carga",
        "",
        "- Transação única: qualquer divergência de contagem levanta exceção "
        "**antes** do `COMMIT` e desfaz tudo.",
        "- `COPY ... FROM STDIN` alimentado com bytes: nenhum valor é decodificado, "
        "interpretado ou reserializado pelo Python.",
        "- `TRUNCATE` nominal nas 24 tabelas da camada `raw`, o que torna a carga "
        "idempotente — rodar duas vezes produz o mesmo estado.",
        "- `SET CONSTRAINTS ALL DEFERRED`: as 37 chaves estrangeiras são validadas "
        "em bloco no `COMMIT`.",
        "- Nenhum tratamento de dado: tokens como `?`, `n/a`, `TBD` e `asdf` estão "
        "no banco exatamente como estão na fonte.",
        "",
    ]
    return "\n".join(out)


if __name__ == "__main__":
    raise SystemExit(main())
