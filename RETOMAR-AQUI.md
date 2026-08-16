# ▶ Retomar aqui

**Atualizado:** 16/08/2026 · **Prazo final: 17/08/2026 08h**

> **Para uma sessão nova do Claude (sem histórico da conversa anterior):**
> leia este arquivo inteiro, depois `CLAUDE.md`, depois `docs/MAPA_QUESTOES.md`.
> Isso é suficiente para continuar sem reler os 36 MB de CSV. Não refaça o
> perfilamento — ele já está catalogado em `docs/` e em
> `entregaveis/Q2_schema/perfil.md`.

---

## O que é este projeto

Resposta ao **Desafio Técnico Lighthouse 2026** da Indicium (trilha Dados e IA): **7 questões** sobre 24 CSVs de uma varejista náutica fictícia (LH Nautical), mais **um dashboard obrigatório** em ferramenta de BI.

Prova de **tentativa única**, sem autosave, sem edição após enviar. Nota de corte 7,0.

As questões estão em `Formulario_de_Questoes.md` e o contexto em `Desafio_Lighthouse.md` — **ambos fora do git de propósito** (repositório é público e a correção vai até 28/08). Estão no disco, na raiz do projeto.

---

## Estado: Ondas 0 e 1 ✅ concluídas

### Onda 0 — fundação ✅

Estrutura de pastas · `CLAUDE.md` · `docs/MAPA_QUESTOES.md` · `docs/SPEC.md` · `docs/PLANO_ONDAS.md` · 7 ADRs · README · `Makefile` · `pyproject.toml` · 3 agentes em `.claude/agents/`.

### Onda 1 — questões 2 e 3 ✅

| Entregável | Situação |
|---|---|
| `entregaveis/Q2_schema/q2_gerar_schema.py` | ✅ stdlib pura, gate AST aprovado |
| `entregaveis/Q2_schema/schema.sql` | ✅ 24 tabelas · 212 colunas · 37 FKs · 24 PKs |
| `entregaveis/Q2_schema/perfil.md` | ✅ relatório de perfilamento |
| `entregaveis/Q2_schema/RESPOSTA.md` | ✅ |
| `entregaveis/Q3_carga/q3_carregar_csvs.py` | ✅ COPY em streaming de bytes |
| `entregaveis/Q3_carga/relatorio_carga.md` | ✅ conferência das 24 tabelas |
| `entregaveis/Q3_carga/RESPOSTA.md` | ✅ |
| `tests/gate_stdlib.py` | ✅ gate por AST da premissa eliminatória |

**Banco carregado e verificado.** 433.424 linhas em `lh_nautical.raw`, 24 tabelas, transação única, 17 s. Rodado 3× — idempotente. As **37 FKs validaram no `COMMIT`** (prova de zero órfãos).

`ruff` e `mypy` limpos nos entregáveis.

---

## ✅ Infraestrutura resolvida — não relitigar

A rede espelhada do WSL **subiu** após o `wsl --shutdown`: `eth0` agora é `192.168.0.128` (antes NAT `172.22.x.x`) e `pg_isready -h localhost -p 5432` responde. **Python no WSL conecta direto no PostgreSQL do Windows.** O plano B do `psql.exe` ficou desnecessário.

O `.venv` existe e tem tudo (`psycopg 3.3.4`, pandas, numpy, sklearn, pyarrow). Ele fica em `/mnt/c/...`, então `uv sync` do zero demora vários minutos — mas já está feito, não refazer sem motivo.

O `Makefile` agora faz `include .env`, então `make db` e `make carga` funcionam sem exportar variável à mão.

---

## Próximo passo: Onda 2 — Questão 1 (EDA)

Design em `docs/SPEC.md`. Resumo:

`entregaveis/Q1_eda/q1_eda_orders.sql` — uma consulta principal com as 5 estatísticas, seguida de apêndice `-- DIAGNÓSTICO` com 6 consultas curtas (nulos por coluna, nulos por canal, mix de status, cerca de Tukey, datas futuras, colapso de carimbos). **Todas só em `orders`** — nenhum JOIN, nenhum filtro de status, nenhum WHERE que descarte linha.

Os números da Q1 **já foram conferidos no banco carregado**:

```
linhas    48.998
created_at   2020-01-01 01:19:28  →  2026-12-31 23:43:09
total        min 32,62 · max 127.262,02 · média 28704.992077227642
```

Depois: Onda 3 (Q4, Q5) → Onda 4 (Q6, Q7) → Onda 5 (gold + Power BI) → Onda 6 (empacotamento e revisão adversarial).

**Modo de trabalho combinado:** autônomo com checkpoint ao fim de cada onda, commit + push em cada uma.

---

## 🚫 Regras invioláveis

A instância PostgreSQL é **compartilhada com outros projetos do usuário**. Detalhe no `CLAUDE.md`:

- Usar **exclusivamente** o banco `lh_nautical`.
- **Sempre** passar `-d lh_nautical` explícito no `psql`.
- Nada de `DROP` / `TRUNCATE` / `ALTER` fora dele.
- Não tocar em `postgresql.conf`, `pg_hba.conf` nem papéis globais.
- Antes de operação destrutiva, conferir `SELECT current_database()`.
  O loader da Q3 já faz isso e **aborta com código 2** se o banco não for `lh_nautical`.

---

## Não refaça — números já validados

Detalhamento e justificativa em `docs/MAPA_QUESTOES.md`.

| Q | Resposta | Observação |
|---|---|---|
| 1.2 | média de `orders.total` = **28.704,992077** | ✅ reconferido no banco |
| 3.2 | **251.864** linhas | ✅ reconferido no banco |
| 4 | líder cliente **22** · categoria **Hélices** (492 itens) | sem filtro de status (leitura literal) |
| 5 | pior dia = **Quinta-feira** (R$ 157.154,32) | com calendário completo; sem ele vira Segunda |
| 6.2 | **116** | somando os dois `product_id` da Bússola (74 e 240) |
| 7.2 | **Motor de Popa 5331** | literal, sem filtro de status; vence por 0,0003 |

### Armadilhas que mudam resposta
- **"Bússola de Bordo 702" tem dois `product_id`: 74 e 240.** Q6 vale 116 / 76 / 40 conforme a leitura.
- **Q7 troca de resposta com filtro de status.** Sem filtro → *Motor de Popa 5331*; com `paid` → *Vela Mestra 1913*.
- **Q4: o filtro de ≥13 categorias não filtra** — 1.971 de 2.000 clientes (98,5%) passam.
- **Não citar "2027" na Q1** — `orders` termina em 2026-12-31. O 2027 está em outras tabelas, fora do escopo da questão.

### Armadilhas que quebram pipeline
- `payments` faz **fan-out 2:1** — nunca calcular faturamento com JOIN nele.
- `order_items` **não tem `product_id`** — a cadeia passa por `product_variants`.
- Colunas que **devem ser TEXT/VARCHAR**: `tax_id`, `cpf`, `barcode_ean`, `series` (`'001'`), `nfe_access_key` (44 dígitos), `postal_code`, telefones. ✅ já tratado no `schema.sql`.
- `stock_levels.reorder_point` é **100% vazia**. ✅ virou `TEXT` com comentário no DDL.
- **7 dos 24 CSVs são CRLF**: fiscal_invoices, order_items, orders, payments, return_items, returns, stock_movements. ✅ detectados no pré-voo da carga.
- `stock_movements.quantity` é **negativa em 103.577 de 115.312 linhas** (convenção de sinal). ✅ preservado.

### Fatos novos, descobertos na Onda 1
- **Não existe um único caractere `"` em nenhum dos 24 CSVs.** É isso que torna o mapeamento `NULL ''` bijetivo e a contagem de linhas por bytes `\n` válida. Se alguém questionar a carga, esta é a resposta.
- **`purchase_orders.expected_delivery_at` é `DATE`**, não `TIMESTAMP` — junto com `employees.hire_date` e `employees.termination_date`, são as 3 únicas colunas de data pura.
- **`return_items.quantity` é `NUMERIC(7,3)`**, não inteiro: a fonte mistura `5` e `1.000`.

---

## Decisões já tomadas (não relitigar)

Justificativas completas em `docs/adr/`.

1. **PostgreSQL do Windows** via rede espelhada. Sem DuckDB, sem dbt, sem Docker.
2. **Medalhão em 3 schemas**: questões saem de `raw`, dashboard sai de `gold`.
3. **Power BI via PBIP/TMDL** gerado no WSL, com Import de Parquet.
4. **Postura "literal + nota de senioridade"**: responder o que a premissa manda e, abaixo, o bloco *Leitura de engenharia* com o cenário corrigido.
5. **Cada questão é autocontida** — um arquivo, roda sozinho, sem importar `src/`.
6. **Tudo em pt-BR.**
7. **Repositório público**; material da prova fora do git.
