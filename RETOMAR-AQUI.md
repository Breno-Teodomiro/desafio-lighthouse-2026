# ▶ Retomar aqui

**Atualizado:** 15/08/2026, 22h40 · **Prazo final: 17/08/2026 08h**

> **Para uma sessão nova do Claude (sem histórico da conversa anterior):**
> leia este arquivo inteiro, depois `CLAUDE.md`, depois `docs/MAPA_QUESTOES.md`.
> Isso é suficiente para continuar sem reler os 36 MB de CSV. Não refaça o
> perfilamento — ele já está catalogado em `docs/`.

---

## O que é este projeto

Resposta ao **Desafio Técnico Lighthouse 2026** da Indicium (trilha Dados e IA): **7 questões** sobre 24 CSVs de uma varejista náutica fictícia (LH Nautical), mais **um dashboard obrigatório** em ferramenta de BI.

Prova de **tentativa única**, sem autosave, sem edição após enviar. Nota de corte 7,0.

As questões estão em `Formulario_de_Questoes.md` e o contexto em `Desafio_Lighthouse.md` — **ambos fora do git de propósito** (repositório é público e a correção vai até 28/08). Estão no disco, na raiz do projeto.

---

## Estado: Onda 0 ✅ concluída

Commits `e0e7772` e `b78772e`, ambos no GitHub. Nada pendente.

Entregue: estrutura de pastas · `CLAUDE.md` · `docs/MAPA_QUESTOES.md` (controle central, com as 7 respostas já pré-validadas) · `docs/SPEC.md` (design de implementação detalhado de cada questão) · `docs/PLANO_ONDAS.md` (plano completo aprovado) · 7 ADRs · README · `Makefile` · `pyproject.toml` · 3 agentes em `.claude/agents/` · memórias em `docs/memoria/`.

---

## ⛔ Bloqueio ativo — dois passos manuais do usuário

O projeto usa o **PostgreSQL 18 que já roda no Windows**, e essa instância é **compartilhada com outros projetos do usuário**.

**Diagnóstico já feito:** o servidor responde e `listen_addresses = '*'`, mas havia dois bloqueios entre o WSL e ele — o firewall do Windows, e o `pg_hba.conf`, que só aceita `127.0.0.1/32` e `::1/128`.

**Solução adotada:** rede espelhada, que resolve os dois sem privilégio de admin.

### Passo 1 — usuário executa `sql/00_criar_banco_e_usuario.sql` no pgAdmin
Cria o papel `lh_app` (sem SUPERUSER/CREATEDB/CREATEROLE) e o banco `lh_nautical` com os schemas `raw`, `silver`, `gold`. Só cria objetos novos.
Da etapa 4 em diante o script precisa rodar **conectado ao `lh_nautical`**.

### Passo 2 — usuário roda `wsl.exe --shutdown`
Já foi adicionado `networkingMode=mirrored` em `/mnt/c/Users/admbr/.wslconfig`. Falta reiniciar o WSL para valer.

### Ao retomar, verifique nesta ordem
```bash
pg_isready -h localhost -p 5432        # esperado: accepting connections
psql -h localhost -U lh_app -d lh_nautical -c "select current_database(), current_user;"
test -f .env || cp .env.example .env   # e pedir a senha do lh_app ao usuário
```
Se `pg_isready` falhar, a rede espelhada não subiu — confirmar se o `wsl --shutdown` foi executado.

---

## Próximo passo: Onda 1 — questões 2 e 3

Design completo em `docs/SPEC.md`. Resumo:

1. **`entregaveis/Q2_schema/q2_gerar_schema.py`** — gerador de `schema.sql` em **stdlib pura**. Importar pandas/polars/dask **desclassifica a questão**. Cascata de inferência de 9 níveis (protege zeros à esquerda, chave de NF-e de 44 dígitos, coluna 100% vazia), PKs compostas inferidas e validadas nas 3 tabelas sem `id`, FKs `DEFERRABLE` em bloco no fim do arquivo.
2. **`entregaveis/Q3_carga/q3_carregar_csvs.py`** — loader com `COPY ... FROM STDIN` em streaming de bytes (o argumento é fidelidade, não velocidade: o Python nunca reserializa um valor), transação única, `TRUNCATE` nominal só nas 24 tabelas de `raw`.
3. **Validar: 251.864** linhas somando customers + orders + order_items + payments.

Depois: Onda 2 (Q1) → Onda 3 (Q4, Q5) → Onda 4 (Q6, Q7) → Onda 5 (gold + Power BI) → Onda 6 (empacotamento e revisão adversarial).

**Modo de trabalho combinado:** autônomo com checkpoint ao fim de cada onda, commit + push em cada uma.

---

## 🚫 Regras invioláveis

A instância PostgreSQL é **compartilhada com outros projetos do usuário**. Detalhe no `CLAUDE.md`:

- Usar **exclusivamente** o banco `lh_nautical`.
- **Sempre** passar `-d lh_nautical` explícito no `psql`.
- Nada de `DROP` / `TRUNCATE` / `ALTER` fora dele.
- Não tocar em `postgresql.conf`, `pg_hba.conf` nem papéis globais.
- Antes de operação destrutiva, conferir `SELECT current_database()`.

---

## Não refaça — números já validados direto dos CSVs

Detalhamento e justificativa em `docs/MAPA_QUESTOES.md`.

| Q | Resposta | Observação |
|---|---|---|
| 1.2 | média de `orders.total` = **28.704,992077** | 48.998 linhas; `created_at` de 2020-01-01 01:19:28 a 2026-12-31 23:43:09 |
| 3.2 | **251.864** linhas | 2.000 + 48.998 + 147.320 + 53.546 |
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
- Colunas que **devem ser TEXT**: `tax_id`, `cpf`, `barcode_ean`, `series` (`'001'`), `nfe_access_key` (44 dígitos), `postal_code`, telefones.
- `stock_levels.reorder_point` é **100% vazia**.
- **7 dos 24 CSVs são CRLF**: fiscal_invoices, order_items, orders, payments, return_items, returns, stock_movements.
- `stock_movements.quantity` é **negativa em 103.577 de 115.312 linhas** (convenção de sinal).

---

## Decisões já tomadas (não relitigar)

Justificativas completas em `docs/adr/`.

1. **PostgreSQL do Windows** via rede espelhada. Sem DuckDB, sem dbt, sem Docker (integração WSL desligada).
2. **Medalhão em 3 schemas**: questões saem de `raw` (as premissas exigem dado bruto), dashboard sai de `gold`.
3. **Power BI via PBIP/TMDL** gerado no WSL, com Import de Parquet — nunca conexão viva ao banco.
4. **Postura "literal + nota de senioridade"**: responder o que a premissa manda e, abaixo, o bloco *Leitura de engenharia* com o cenário corrigido.
5. **Cada questão é autocontida** — um arquivo, roda sozinho, sem importar `src/`.
6. **Tudo em pt-BR.**
7. **Repositório público**; material da prova fora do git.
