---
name: numeros-validados-lighthouse
description: "Respostas numéricas das 7 questões do Desafio Lighthouse 2026, já calculadas direto dos CSVs — não recalcular"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6b5a842b-ad32-4804-ad5b-7c30614dea9c
  modified: 2026-08-16T01:12:46.122Z
---

Respostas do Desafio Lighthouse 2026 (LH Nautical) pré-calculadas em 15/08/2026 lendo os 24 CSVs com Python stdlib. Detalhamento completo em `docs/MAPA_QUESTOES.md` do projeto.

- **Q1.2** — `AVG(orders.total)` = **28.704,992077**. Tabela tem 48.998 linhas; `created_at` de 2020-01-01 01:19:28 a 2026-12-31 23:43:09; `total` min 32,62 / max 127.262,02.
- **Q3.2** — customers 2.000 + orders 48.998 + order_items 147.320 + payments 53.546 = **251.864**.
- **Q4** — Top 10 por ticket médio liderado pelo `customer_id` **22** (R$ 41.839,94). Categoria campeã do grupo: **Hélices** (id 8), 492 itens.
- **Q5** — Pior dia com calendário completo: **Quinta-feira**, R$ 157.154,32. Sem o calendário o resultado vira Segunda-feira — o diagnóstico troca de dia.
- **Q6.2** — **116** unidades (somando os dois product_id da Bússola). Alternativas: 76 (só id 74), 40 (só id 240). Real do Q1/2026 = 207, então o baseline subestima 44%.
- **Q7.2** — **Motor de Popa 5331** (id 389, cosseno 0,256553) na leitura literal sem filtro de status.

Ver também [[armadilhas-dados-lh-nautical]] e [[postura-literal-mais-senioridade]].
