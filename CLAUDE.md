# LH Nautical — Desafio Lighthouse 2026

Sempre se comunicar em **português brasileiro (pt-BR)**. Código, comentários, docstrings, commits e documentação também.

## ▶ Retomando?

Leia `RETOMAR-AQUI.md` — tem o estado e o próximo passo. Não releia os CSVs: os números já validados estão em `docs/MAPA_QUESTOES.md`.

## O projeto

Resposta ao **Desafio Técnico Lighthouse 2026** (Indicium, trilha Dados e IA). São **7 questões** sobre 24 CSVs de uma varejista náutica fictícia + **1 dashboard obrigatório**.

- **Prazo: 17/08/2026 08h.** Tentativa única, sem autosave, sem edição após enviar.
- Nota de corte 7,0. O Tech Lead fictício valoriza **organização e explicação acima de código complexo**.
- Enunciado: `Desafio_Lighthouse.md` · Questões: `Formulario_de_Questoes.md` · Regras: o PDF do edital.

## Perfil do usuário

Breno Teodomiro. Trabalha com engenharia de dados, BI e Power BI (mantém PBIP/TMDL em 5 projetos). Prefere pt-BR, entregas profissionais e documentadas. Quer commit + push a cada etapa importante.

## Onde os dados vivem

| Camada | Local | Regra |
|---|---|---|
| CSVs originais | `1-lh_nautical_csv/` (24 arquivos, 433.424 linhas, 36 MB) | Nunca modificar. Não versionar. |
| `raw` | schema PostgreSQL | Carga **sem nenhum tratamento**. É daqui que saem Q1, Q4, Q5. |
| `silver` | schema PostgreSQL | Limpo e tipado. Apoio + Q6/Q7. |
| `gold` | schema PostgreSQL + `dados/gold/*.parquet` | Star schema. Alimenta o Power BI. |

Conexão: PostgreSQL local no WSL. Credenciais em `.env` (nunca commitar).

## Fatos verificados (não recalcular)

Perfilamento completo em `docs/QUALIDADE_DADOS.md` e `docs/DICIONARIO_DADOS.md`.

- `orders`: **48.998** linhas · `total` min 32,62 / max 127.262,02 / **média 28.704,992077** · `created_at` de `2020-01-01 01:19:28` a `2026-12-31 23:43:09`.
- Soma customers+orders+order_items+payments = **251.864** (resposta da Q3.2).
- Integridade referencial **perfeita**: 37/37 FKs sem órfãos. Aritmética fecha ao centavo em ~260k conferências.
- `status` de orders: paid 34.365 / confirmed 7.335 / cancelled 4.847 / draft 2.451.
- `channel`: ecommerce 34.342 / pos 14.656.
- Só existem **14 categorias**. 1.971 de 2.000 clientes compraram de ≥13 delas.
- Q5: pior dia = **Quinta-feira** (R$ 157.154,32) com calendário completo; vira Segunda-feira se ignorar os 78 dias sem venda.

## Estrutura

```
entregaveis/Q1..Q7/   ⭐ o que vai para a plataforma (rodável isoladamente)
src/lh_nautical/      pipeline (engenharia, não é entregável)
sql/{raw,silver,gold,testes}
powerbi/              PBIP + TMDL + tema + DAX
docs/                 PRD, SPEC, MAPA_QUESTOES, ADRs, dicionário, qualidade
```

## Decisões de arquitetura (não reverter sem motivo)

Detalhe em `docs/adr/`.

1. **PostgreSQL local no WSL** é o banco canônico. Q2/Q3 exigem PostgreSQL explicitamente. Supabase só publica o gold no fim.
2. **Sem DuckDB e sem dbt.** As questões pedem SQL puro e Python puro como arquivos avaliáveis.
3. **Power BI via PBIP/TMDL** gerado aqui; o `.pbix` usa Import de Parquet, nunca conexão ao banco.
4. **Postura "literal + nota de senioridade"**: responder exatamente o que a premissa manda e, abaixo, o bloco *Leitura de engenharia* com o cenário corrigido.
5. **Cada questão é autocontida** — um arquivo, roda sozinho, sem importar o pipeline. Duplicação aqui é proposital.

## ⛔ Armadilhas

- **Q2 proíbe pandas/polars/dask.** Só stdlib. Violar = questão desconsiderada. Há gate por AST em `make check`.
- **`payments` faz fan-out 2:1** (6.999 pedidos têm 2 pagamentos). Nunca calcular faturamento com JOIN em payments.
- **`order_items` não tem `product_id`.** A cadeia é `order_items.product_variant_id → product_variants.product_id → products.category_id`.
- **"Bússola de Bordo 702" (Q6) tem dois product_id: 74 e 240.** A resposta muda: 116 (ambos) / 76 (só 74) / 40 (só 240).
- **Q7 muda com filtro de status**: sem filtro → *Motor de Popa 5331*; com `paid` → *Vela Mestra 1913*. O 1º lugar ganha por 0,0003. Enunciado é omisso → usar literal sem filtro.
- **Colunas que DEVEM ser TEXT** (zeros à esquerda ou estouram int64): `customers.tax_id`, `suppliers.tax_id` (tem `FR-10771657`), `product_variants.barcode_ean`, `fiscal_invoices.series` (`'001'`), `fiscal_invoices.nfe_access_key` (44 dígitos), `addresses.postal_code`, `employees.cpf`, telefones.
- **`stock_levels.reorder_point` é 100% vazia** — inferência de tipo precisa de fallback.
- **7 dos 24 CSVs são CRLF**: fiscal_invoices, order_items, orders, payments, return_items, returns, stock_movements.
- **`stock_movements.quantity` é negativa em 103.577 de 115.312 linhas** (convenção de sinal). Não rejeitar negativos.
- **Datas vão até 2027-02-13**, não 2026. 8,7% dos pedidos são futuros em relação a hoje.
- Nulos aparecem como string vazia **e** como lixo textual: `?`, `??`, `-`, `--`, `—`, `...`, `n/a`, `N/A`, `TBD`, `TODO`, `FIXME`, `asdf`, `test`, `xxx`, `Sem Nome`.

## Comandos

```bash
make setup      # uv sync + verifica Postgres
make db         # cria schemas e roda schema.sql
make pipeline   # carrega raw -> silver -> gold
make questoes   # roda as 7 questões e confere os números
make check      # ruff + mypy + pytest + gate de conformidade
```

## Estado atual — 15/08

Onda 0 (fundação) em andamento. Ver `RETOMAR-AQUI.md`.
