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

O que NÃO dá para checar: se o TMDL abre. Isso exige o Desktop.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

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
        texto = arquivo.read_text(encoding="utf-8")
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


def main() -> int:
    if not MODELO.exists():
        print(f"erro: {MODELO} não existe — rode powerbi/gerar_pbip.py", file=sys.stderr)
        return 1

    erros: list[str] = []
    avisos: list[str] = []

    tabelas, medidas, dax = ler_modelo()
    print(f"Modelo: {len(tabelas)} tabelas, {len(medidas)} medidas")

    # --- 7. partição e Parquet correspondente -----------------------------
    for arquivo in sorted((MODELO / "tables").glob("*.tmdl")):
        texto = arquivo.read_text(encoding="utf-8")
        if "\tpartition " not in texto:
            erros.append(f"{arquivo.name}: sem partição")
        nome = arquivo.stem
        if nome != "_Medidas" and not (PARQUET / f"{nome}.parquet").is_file():
            erros.append(f"{nome}: Parquet ausente em {PARQUET}")

    # --- 6. relacionamentos ------------------------------------------------
    rel_texto = (MODELO / "relationships.tmdl").read_text(encoding="utf-8")
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
        # Referências a outras medidas: [Nome da Medida]
        for ref in re.findall(r"(?<![\w\]])\[([^\]]+)\]", expressao):
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
