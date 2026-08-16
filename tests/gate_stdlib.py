#!/usr/bin/env python3
"""
Gate de conformidade da Questão 2 — prova que o script usa SOMENTE a stdlib.

A premissa da Q2 é eliminatória:

    "Utilize somente bibliotecas padrão do Python 3 e python puro. Soluções
     que utilizarem bibliotecas como pandas, dask, polars serão desconsideradas."

Ler o arquivo e procurar a string "pandas" não é verificação suficiente: não
alcança `import numpy as np`, nem `__import__("polars")`, nem um import
escondido dentro de uma função. Este gate percorre a **árvore sintática** do
arquivo, coleta todo import em qualquer profundidade e confere cada módulo raiz
contra `sys.stdlib_module_names` — a lista que o próprio interpretador mantém.

    python3 tests/gate_stdlib.py entregaveis/Q2_schema/q2_gerar_schema.py

Sai com código 0 se conforme, 1 se encontrar qualquer módulo externo.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# Chamadas que carregam um módulo por nome, driblando o nó Import da AST.
CHAMADAS_DINAMICAS = {"__import__", "import_module", "load_module", "exec", "eval"}


def modulos_importados(arvore: ast.AST) -> list[tuple[str, int, str]]:
    """Coleta (modulo_raiz, linha, texto) de todo import, em qualquer nível.

    `ast.walk` desce a árvore inteira, então import dentro de função, de classe,
    de `try` ou de `if` é encontrado igual — que é justamente onde alguém
    esconderia um import proibido, de propósito ou por descuido.
    """
    achados: list[tuple[str, int, str]] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                raiz = alias.name.split(".")[0]
                achados.append((raiz, no.lineno, f"import {alias.name}"))
        elif isinstance(no, ast.ImportFrom):
            # `from . import x` tem module=None e level>0: import relativo,
            # ou seja, código do próprio projeto e não biblioteca externa.
            if no.level and not no.module:
                continue
            raiz = (no.module or "").split(".")[0]
            if raiz:
                nomes = ", ".join(a.name for a in no.names)
                achados.append((raiz, no.lineno, f"from {no.module} import {nomes}"))
    return achados


def chamadas_dinamicas(arvore: ast.AST) -> list[tuple[int, str]]:
    """Detecta carregamento dinâmico de módulo, que a checagem de import não vê."""
    achados: list[tuple[int, str]] = []
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        alvo = no.func
        nome = ""
        if isinstance(alvo, ast.Name):
            nome = alvo.id
        elif isinstance(alvo, ast.Attribute):
            nome = alvo.attr
        if nome in CHAMADAS_DINAMICAS:
            achados.append((no.lineno, nome))
    return achados


def verificar(caminho: Path) -> int:
    codigo = caminho.read_text(encoding="utf-8")
    try:
        arvore = ast.parse(codigo, filename=str(caminho))
    except SyntaxError as erro:
        print(f"REPROVADO  {caminho}: erro de sintaxe na linha {erro.lineno}", file=sys.stderr)
        return 1

    stdlib = sys.stdlib_module_names
    importados = modulos_importados(arvore)
    externos = [(m, ln, txt) for m, ln, txt in importados if m not in stdlib]
    dinamicas = chamadas_dinamicas(arvore)

    print(f"Gate stdlib — {caminho}")
    print(f"  Python {sys.version.split()[0]} · {len(importados)} imports encontrados")

    distintos = sorted({m for m, _, _ in importados})
    print(f"  Módulos: {', '.join(distintos)}")

    falhou = False

    if externos:
        falhou = True
        print("\n  REPROVADO — módulos fora da biblioteca padrão:", file=sys.stderr)
        for modulo, linha, texto in externos:
            print(f"    linha {linha}: {texto}   (módulo '{modulo}' é externo)", file=sys.stderr)

    if dinamicas:
        falhou = True
        print("\n  REPROVADO — carregamento dinâmico de módulo:", file=sys.stderr)
        for linha, nome in dinamicas:
            print(f"    linha {linha}: chamada a {nome}()", file=sys.stderr)

    if falhou:
        print("\n  A Questão 2 seria DESCONSIDERADA com este código.", file=sys.stderr)
        return 1

    print("  APROVADO — apenas biblioteca padrão, sem carregamento dinâmico.")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(f"uso: {argv[0]} <arquivo.py> [arquivo.py ...]", file=sys.stderr)
        return 2

    codigo = 0
    for arg in argv[1:]:
        caminho = Path(arg)
        if not caminho.is_file():
            print(f"erro: {caminho} não existe", file=sys.stderr)
            codigo = 2
            continue
        codigo = max(codigo, verificar(caminho))
    return codigo


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
