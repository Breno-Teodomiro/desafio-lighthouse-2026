# ▶ Retomar aqui

**Atualizado:** 15/08/2026, noite · **Prazo final: 17/08/2026 08h**

## Onde estamos

**Onda 0 — Fundação** · 🟨 em andamento

Concluído:
- Repositório git inicializado, remoto `git@github.com:Breno-Teodomiro/desafio-lighthouse-2026.git` configurado (estava vazio), e-mail do commit corrigido para `insights.jobs.ia@gmail.com`.
- Estrutura de pastas criada.
- `CLAUDE.md`, `.gitignore`, `pyproject.toml`, `Makefile`.
- `docs/MAPA_QUESTOES.md` — **documento de controle central, com as respostas das 7 questões já pré-validadas nos CSVs.**

## ⛔ Bloqueio ativo

**PostgreSQL ainda não está instalado.** O usuário precisa rodar no prompt:

```
! sudo apt install -y postgresql postgresql-contrib
```

Depois: `sudo service postgresql start` e criar o papel do usuário. Nada da Onda 1 (Q2/Q3) roda antes disso.

## Próximo passo

1. Confirmar o PostgreSQL no ar (`pg_isready`).
2. Terminar a Onda 0: ADRs, PRD, SPEC, agentes em `.claude/agents/`, skills locais, README, memória.
3. Commit + push da Onda 0.
4. Abrir a **Onda 1** — Q2 (gerador de schema em stdlib pura) e Q3 (loader).

## Não refaça

Os números abaixo já foram calculados direto dos CSVs e conferidos. Estão detalhados em `docs/MAPA_QUESTOES.md`.

| Q | Resposta |
|---|---|
| 1.2 | média de `orders.total` = **28.704,992077** |
| 3.2 | **251.864** linhas |
| 4 | líder cliente **22** · categoria **Hélices** (492 itens) |
| 5 | pior dia = **Quinta-feira** (R$ 157.154,32) |
| 6.2 | **116** (ids 74+240) |
| 7.2 | **Motor de Popa 5331** (literal, sem filtro de status) |
