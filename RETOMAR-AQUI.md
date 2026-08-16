# ▶ Retomar aqui

**Atualizado:** 15/08/2026, noite · **Prazo final: 17/08/2026 08h**

## Onde estamos

**Onda 0 — Fundação** · ✅ concluída, commitada e no GitHub (`e0e7772`)

Entregue: estrutura de pastas · `CLAUDE.md` · `docs/MAPA_QUESTOES.md` (controle central com as 7 respostas pré-validadas) · `docs/SPEC.md` (design de implementação) · 7 ADRs · README · `Makefile` · `pyproject.toml` · 3 agentes em `.claude/agents/` · 4 memórias persistentes.

## ⛔ Bloqueio ativo — o WSL foi reiniciado para ativar rede espelhada

O projeto usa o **PostgreSQL 18 que já roda no Windows**, compartilhado com outros projetos do usuário.

**Diagnóstico feito:** o servidor responde (`listen_addresses = '*'`), mas havia dois bloqueios entre o WSL e ele — o firewall do Windows e o `pg_hba.conf`, que só aceitava `127.0.0.1/32` e `::1/128`.

**Solução escolhida:** rede espelhada. Já foi adicionado `networkingMode=mirrored` em `/mnt/c/Users/admbr/.wslconfig`. Com isso a conexão do WSL chega ao servidor como `127.0.0.1`, que o `pg_hba.conf` já aceita — sem firewall e sem alterar arquivo do PostgreSQL.

### Ao retomar, verifique nesta ordem

```bash
# 1. A rede espelhada está ativa?
pg_isready -h localhost -p 5432        # esperado: accepting connections

# 2. O banco e o usuário do projeto já existem?
#    (o usuário deveria ter rodado sql/00_criar_banco_e_usuario.sql no pgAdmin)
psql -h localhost -U lh_app -d lh_nautical -c "select current_database(), current_user;"

# 3. O .env existe e tem a senha?
test -f .env && echo "ok" || cp .env.example .env   # e pedir a senha ao usuário
```

Se `pg_isready` falhar, a rede espelhada não subiu — conferir se o `wsl --shutdown` foi realmente executado.

## Próximo passo

Abrir a **Onda 1 — Q2 e Q3**, conforme `docs/SPEC.md`:

1. `entregaveis/Q2_schema/q2_gerar_schema.py` — gerador de schema em **stdlib pura** (pandas desclassifica a questão). Cascata de inferência de 9 níveis, PKs compostas inferidas e validadas, FKs `DEFERRABLE` no fim do arquivo.
2. `entregaveis/Q3_carga/q3_carregar_csvs.py` — loader com `COPY ... FROM STDIN` em streaming de bytes, transação única, `TRUNCATE` nominal nas 24 tabelas de `raw`.
3. Validar: **251.864** linhas em customers + orders + order_items + payments.

## 🚫 Nunca esquecer

A instância PostgreSQL é **compartilhada**. Ver as regras invioláveis no `CLAUDE.md`: só o banco `lh_nautical`, sempre com `-d lh_nautical` explícito, nada de `DROP`/`TRUNCATE`/`ALTER` fora dele, e nada de mexer em `postgresql.conf`, `pg_hba.conf` ou papéis globais.

## Não refaça

Números já calculados direto dos CSVs e conferidos — detalhes em `docs/MAPA_QUESTOES.md`.

| Q | Resposta |
|---|---|
| 1.2 | média de `orders.total` = **28.704,992077** |
| 3.2 | **251.864** linhas |
| 4 | líder cliente **22** · categoria **Hélices** (492 itens) |
| 5 | pior dia = **Quinta-feira** (R$ 157.154,32) |
| 6.2 | **116** (ids 74+240) |
| 7.2 | **Motor de Popa 5331** (literal, sem filtro de status) |
