# ADR-003 — Power BI via PBIP/TMDL, com Import de Parquet

**Data:** 15/08/2026 · **Status:** aceito

## Contexto

O material complementar exige dashboard, e a exigência é nomeada: *"O que deve ser entregue: Dashboard (Power BI, Looker Studio, Tableau, etc.)"*. Notebook, PDF e documento aparecem apenas em "O que também pode ser entregue" — são complementos, não substitutos.

O desenvolvimento acontece no WSL, mas o Power BI Desktop só roda no Windows e não é automatizável de fora. O usuário tem o Desktop instalado e já mantém projetos em formato PBIP em cinco repositórios.

## Decisão

Gerar o projeto Power BI inteiro **em formato texto** a partir do WSL: modelo semântico em **TMDL**, tema em **JSON**, dados da camada `gold` exportados em **Parquet**. O usuário abre o `.pbip` no Desktop, atualiza e salva o `.pbix`.

O `.pbix` usa **Import mode lendo os Parquet**, nunca conexão viva ao PostgreSQL.

## Justificativa

PBIP é texto versionável, então o dashboard entra no git como código e não como binário opaco — e o trabalho manual do usuário cai de uma montagem completa (~4h) para abrir, conferir e salvar (~40min).

A escolha de Import sobre Parquet, em vez de conexão ao banco, é sobre o avaliador: ele precisa abrir o arquivo e ver os dados, sem credencial, sem VPN, sem PostgreSQL instalado. Um `.pbix` apontando para `localhost:5432` chega quebrado do outro lado.

Um dashboard HTML autocontido foi considerado e **rebaixado a complemento**: é mais bonito e 100% automatizável, mas não é "ferramenta de BI" no sentido que o enunciado nomeia, e o risco de o corretor considerar a exigência não atendida não compensa.

## Consequências

- Dependência de uma ação manual do usuário na Onda 5.
- Se o PBIP não abrir corretamente, o fallback é entregar os Parquet da `gold` + medidas DAX + guia de montagem, e usar o dashboard HTML como material complementar.
- O tema JSON e as medidas DAX ficam versionados separadamente, reutilizáveis em outros projetos.
