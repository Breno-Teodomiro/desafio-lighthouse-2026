# ADR-007 — Repositório público e política de versionamento

**Data:** 15/08/2026 · **Status:** aceito

## Contexto

O repositório `git@github.com:Breno-Teodomiro/desafio-lighthouse-2026.git` existia vazio. O usuário optou por mantê-lo **público, como peça de portfólio**. A janela de correção do desafio vai de 17/08 a 28/08/2026.

## Decisão

- Repositório **público desde o primeiro commit**.
- **Commit + push ao fim de cada onda**, com mensagem em pt-BR no padrão Conventional Commits e `Co-Authored-By: Claude Opus 5`.
- **Os 24 CSVs não são versionados.** `1-lh_nautical_csv/` entra no `.gitignore`.
- Nenhuma credencial no repositório. `.env` ignorado, `.env.example` versionado.
- Tag `v1.0-entrega` no commit exato do que foi submetido.

## Justificativa

O histórico por onda conta a história do projeto — um avaliador que abra o repositório vê a progressão de fundação → carga → análise → BI, o que sustenta a alegação de organização melhor do que qualquer README.

Os CSVs ficam de fora por serem material fornecido pela Indicium: 36 MB de dados que não são meus para redistribuir, e que inchariam o clone sem agregar nada. O `README.md` explica como reconstituir a pasta.

**Risco assumido:** com o repositório público antes de 28/08, outro candidato poderia encontrar as respostas. O usuário foi informado e optou pelo valor de portfólio. A alternativa registrada era privado até 28/08 e público depois.

## Consequências

- Todo commit é imediatamente visível. Nenhum dado sensível ou credencial pode entrar, nem temporariamente.
- O `.gitignore` precisa cobrir os CSVs desde o primeiro commit, antes de qualquer `git add -A`.
- Sem `gh` CLI na máquina: operações de GitHub são feitas por `git` sobre SSH, já autenticado.
