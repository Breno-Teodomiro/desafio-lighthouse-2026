# ADR-005 — Cada questão é um artefato autocontido

**Data:** 15/08/2026 · **Status:** aceito

## Contexto

O formulário pede upload de arquivos soltos: *"Faça o upload de seu código Python"*, *"Faça o upload de seu schema.sql"*. O corretor recebe um `.py` ou um `.sql` isolado, fora de qualquer repositório, e precisa conseguir lê-lo e possivelmente executá-lo.

Um pipeline bem fatorado empurraria a lógica comum para `src/lh_nautical/` e deixaria cada questão como um script fino de três linhas importando o pacote — o que é correto em engenharia e **péssimo** aqui: o arquivo enviado ficaria incompreensível sozinho.

## Decisão

Cada questão vive em um **único arquivo autossuficiente** dentro de `entregaveis/QN_*/`, executável isoladamente, sem importar nada de `src/`. A duplicação de trechos entre questões é aceita deliberadamente.

O pipeline em `src/lh_nautical/` existe em paralelo e serve o dashboard, não as questões.

## Justificativa

O artefato avaliado é o arquivo, não o repositório. Otimizar para DRY aqui otimizaria para o leitor errado.

A Q2 reforça a decisão por um segundo motivo: ela **proíbe bibliotecas externas**. Um script que importasse o pacote do projeto violaria a premissa por construção, ainda que o pacote só usasse stdlib.

## Consequências

- Constantes como o caminho dos CSVs e a lista de tabelas se repetem entre scripts. Cada um recebe `--csv-dir` por linha de comando, com default sensato.
- Uma correção de lógica compartilhada precisa ser aplicada em mais de um arquivo. Mitigado por `make questoes`, que executa todos e confere os números contra `docs/MAPA_QUESTOES.md`.
- Cada arquivo abre com um cabeçalho declarando questão, premissas atendidas e como executar.
