---
name: ambiente-maquina-breno
description: O que está e o que não está disponível na máquina WSL do Breno para projetos de dados
metadata: 
  node_type: memory
  type: reference
  originSessionId: 6b5a842b-ad32-4804-ad5b-7c30614dea9c
  modified: 2026-08-16T01:13:24.792Z
---

Levantado em 15/08/2026 (WSL2 Ubuntu, Windows host).

**Disponível:** `uv` 0.10.10 (gerenciador padrão da casa), Python 3.12.3 do sistema, node 22 / npm 10 (então MCP via `npx` funciona), git com SSH já autenticado no GitHub como `Breno-Teodomiro`, cliente `psql` 16, ruff, mypy, pytest. Em Python: pandas 3.0.2, numpy 2.4.4, plotly 6.7.0, streamlit 1.57, statsmodels, scipy, lightgbm, pyarrow, sqlalchemy.

**Ausente:** `gh` CLI, `duckdb`, `dbt`, `quarto`, `jq`, `sqlite3` CLI. Em Python faltam scikit-learn, matplotlib, seaborn, polars, jupyter — todos instaláveis via `uv add`.

**Docker está indisponível** — o binário do Windows aparece no PATH mas a integração WSL do Docker Desktop está desligada. Não planejar nada que dependa de container.

**PostgreSQL:** o host Windows tem o **PG 18 rodando** e escutando em `0.0.0.0:5432`, mas o WSL está em modo NAT (`172.22.x.x`, gateway `172.22.192.1`) e o firewall do Windows bloqueia a conexão. Para usá-lo seria preciso regra de firewall em PowerShell admin e possivelmente ajuste de `pg_hba.conf`. A decisão em 15/08 foi instalar o PostgreSQL nativo no WSL via `apt`.

**Atenção:** `git config user.email` global está com typo — `insidhts.jobs.ia@gmail.com` em vez de `insights.jobs.ia@gmail.com`. Corrigido no escopo do repositório do Lighthouse, mas o global segue errado e vai afetar outros projetos.

**Ativos reutilizáveis:** `~/.claude/MODELO-CLAUDE-MD.md` (doutrina de CLAUDE.md com teto de 10k tokens), 16 skills em `~/.claude/skills-estacionadas/` (parked de propósito, custam ~1,7k tokens/sessão se globais), 20 skills de Power BI em `/mnt/c/PROJETOS/POWERBI_DATAVIZ_WORLD_CHAMPS_BCN_2026/.claude/skills/`, e o projeto `SCORECARD_ANS_ELINSA` como melhor template de estrutura (agents + skills + dbt + uv).
