# Questão 1 — EDA de `orders`

**Entregável:** `q1_eda_orders.sql` (Q1.1) · este documento (Q1.2 e Q1.3)

```bash
psql -d lh_nautical -f q1_eda_orders.sql
```

---

## Conformidade com as premissas

| Premissa | Como o arquivo atende |
|---|---|
| *"Utilize apenas a tabela orders"* | **Nenhum `JOIN`** no arquivo inteiro — nem nas consultas de diagnóstico |
| *"Não faça limpeza nem tratamento"* | Nenhum `WHERE` que descarte linha, nenhum filtro de `status`, nenhum `COALESCE`, nenhuma remoção de outlier. As 48.998 linhas entram em todas as agregações |
| *"Apenas observe, agregue e descreva"* | Só `SELECT` com funções de agregação |
| *"O código deve ser enviado em SQL"* | PostgreSQL 18 |

---

## Q1.1 — Resultados

```sql
SELECT count(*)             AS qtd_total_linhas,
       min(created_at)      AS data_minima,
       max(created_at)      AS data_maxima,
       min(total)           AS total_minimo,
       max(total)           AS total_maximo,
       round(avg(total), 2) AS total_medio
FROM raw.orders;
```

| Métrica | Valor |
|---|---|
| Quantidade total de linhas | **48.998** |
| `created_at` mínima | **01/01/2020 01:19:28** |
| `created_at` máxima | **31/12/2026 23:43:09** |
| `total` mínimo | **R$ 32,62** |
| `total` máximo | **R$ 127.262,02** |
| `total` médio | **R$ 28.704,99** |

Uma varredura só produz as cinco estatísticas. Separar em cinco consultas leria a mesma tabela cinco vezes e abriria espaço para que uma delas divergisse das outras por um filtro esquecido.

---

## Q1.2 — Valor médio da coluna `total`

> **R$ 28.704,99**

Valor sem arredondamento: `28704.992077227642`.

---

## Q1.3 — Diagnóstico de confiabilidade

> **Tese: `orders` é estruturalmente confiável e semanticamente não pronta. O que falta não é limpeza de sujeira — é política de negócio.**

Cada afirmação abaixo tem uma consulta correspondente no apêndice `-- DIAGNÓSTICO` do arquivo SQL.

### (a) Outliers em `total`: existem estatisticamente, mas não são defeito

| Medida | Valor |
|---|---|
| Q1 · Mediana · Q3 | 13.171,24 · **25.917,84** · 40.941,88 |
| Média | 28.704,99 |
| **Razão média / mediana** | **1,108** |
| Desvio padrão | 19.425,64 |
| Cerca superior de Tukey (Q3 + 1,5·IQR) | 82.597,85 |
| Pedidos acima da cerca | **452 (0,92%)** |
| Receita que esses 452 representam | **2,94%** |
| Pedidos com `total` ≤ 0 | **0** |

A amplitude — de R$ 32,62 a R$ 127.262,02, uma razão de 3.901× — parece alarmante isolada, e é o número que normalmente motiva um "tem outlier, precisa limpar".

Mas a pergunta certa não é *"existe valor extremo?"* e sim *"a distribuição tem cauda pesada?"*. **Média ≈ mediana (razão 1,108)** diz que não: a distribuição é quase simétrica. Os 452 pedidos acima da cerca são 0,92% das linhas e apenas 2,94% da receita — não movem nenhum agregado. E não há um único `total` ≤ 0, que seria o sinal real de erro de captura.

**Veredito: são tickets legítimos de alto valor** — motores, eletrônica náutica — em uma varejista cujo mix vai de cabo a lancha. **Não remover; segmentar.**

> **Observação de faro.** Ticket quase simétrico é *atípico* em varejo, onde se espera distribuição log-normal com cauda longa. Isso é evidência de que a base é sintética, e recomenda cautela ao extrapolar qualquer conclusão de negócio daqui para o mundo real. Não afeta a validade técnica do exercício; afeta o peso das recomendações.

### (b) Qualidade: a tabela em si está limpa

| Verificação | Resultado |
|---|---|
| Nulos nas 13 colunas | **Zero**, exceto `salesperson_id` |
| `salesperson_id` nulo | 24.131 (49,2%) |
| ...e **100% desses nulos estão no canal `ecommerce`** | `pos`: 0 de 14.656 sem vendedor |
| `id` duplicados | 0 (48.998 distintos) |
| `order_number` duplicados | 0 (48.998 distintos) |
| `subtotal − discount_amount = total` | **48.998 de 48.998** |
| Tokens de lixo (`?`, `n/a`, `asdf`) | **nenhum em `orders`** |

O único nulo da tabela é **estrutural, não uma falha de coleta**: venda de e-commerce não tem vendedor atribuído porque não houve atendente. A prova é o Diagnóstico 2 — nenhum pedido `pos` tem `salesperson_id` nulo, e 70,3% dos `ecommerce` têm. Preencher isso com `COALESCE` seria **inventar dado**; o tratamento correto é ler `NULL` aqui como "venda sem vendedor" e nada mais.

A aritmética interna fecha em 100% das linhas, e as duas chaves candidatas são únicas. Estruturalmente, não há o que consertar.

### (c) Os três bloqueadores reais

**1. A média mistura quatro coisas diferentes.**

| Status | Pedidos | % | Soma de `total` | Ticket médio |
|---|---:|---:|---:|---:|
| `paid` | 34.365 | 70,1% | R$ 985.741.294,26 | R$ 28.684,45 |
| `confirmed` | 7.335 | 15,0% | R$ 213.625.785,28 | R$ 29.124,17 |
| `cancelled` | 4.847 | 9,9% | R$ 137.418.441,62 | R$ 28.351,24 |
| `draft` | 2.451 | 5,0% | R$ 69.701.680,64 | R$ 28.438,06 |

Os R$ 28.704,99 somam quatro estágios do ciclo de vida do pedido. **R$ 207,1 milhões (14,7% do GMV) são `cancelled` + `draft` e nunca viraram receita.** O ticket médio realizado é R$ 28.684,45.

A diferença entre os dois números é pequena — 0,07% — e é exatamente por isso que o problema é perigoso: ele não aparece no ticket médio, mas **infla o faturamento total em 14,7%**. Quem responder "qual foi nosso faturamento?" com `SUM(total)` erra em R$ 207 milhões.

**2. O recorte temporal é inválido para série temporal.**

`created_at` vai até **31/12/2026**, e **4.259 pedidos (8,69%) têm data posterior a hoje** (referência: 15/08/2026). A distribuição anual é monotonicamente crescente — 4.466 pedidos em 2020 até 10.268 em 2026 — o que faz 2026 *parecer* o melhor ano da série quando na verdade é um ano ainda não vivido.

Qualquer YoY, tendência ou média móvel que inclua 2026 está lendo dado futuro como se fosse realizado. **Exige data de corte explícita antes de qualquer análise temporal.**

**3. Os carimbos de tempo não carregam informação.**

`placed_at = created_at = updated_at` em **48.998 de 48.998 linhas (100%)**.

Não existe linha do tempo do pedido. É impossível medir lead time, tempo até o pagamento, tempo até a expedição ou qualquer intervalo entre eventos. Isso **não é sujeira** — as colunas estão preenchidas e são válidas. É ausência de sinal, e limita o que a tabela consegue responder: toda pergunta sobre *duração* está fora de alcance.

### (d) Veredito: pronta para análise, ou exige tratamento?

**Não exige tratamento prévio no sentido de limpeza** — não há nulo espúrio para imputar, duplicata para remover, tipo para corrigir nem outlier para descartar. Uma rotina de *data cleaning* rodando aqui não teria o que fazer.

**Exige três definições de negócio antes do primeiro gráfico:**

1. **Quais status contam como venda?** Sem isso, todo número de faturamento é ambíguo em 14,7%.
2. **Qual é a data de corte?** Sem isso, toda série temporal inclui 8,7% de futuro.
3. **Qual é a pergunta?** Se envolver duração, `orders` não responde.

**E exige relacionamento com outras tabelas para quase tudo que interessa.** É o ponto mais importante do diagnóstico: `orders` **não tem grão de produto**. Ela sabe *quanto* cada pedido custou, mas não *o que* foi vendido. Mix de produto, categoria, margem, curva ABC e análise de cesta são todos impossíveis a partir daqui — dependem de `order_items → product_variants → products → categories`, e `order_items` sequer tem `product_id` (a variante é obrigatória no caminho).

> **Resumo em uma frase:** `orders` é confiável como **fonte** e insuficiente como **base analítica** — não por defeito dos dados, mas por escopo da tabela.

---

## Leitura de engenharia

1. **A pergunta do Sr. Almir — "posso confiar nesses dados?" — não tem resposta binária, e devolver "sim" ou "não" seria desserviço.** A resposta útil é: *confie nos números que a tabela mede; não confie em números que ela não mede.* `SUM(total)` é exato; "faturamento" não é `SUM(total)`.

2. **O maior risco desta tabela é ela ser boa demais.** Zero nulo espúrio, zero duplicata, aritmética fechando em 100% — isso convida a pular a etapa de validação e ir direto ao dashboard. Os três bloqueadores (status, data futura, carimbos colapsados) são invisíveis para qualquer checagem automática de qualidade, porque nenhum deles é um defeito de formato. **Passariam ilesos por qualquer *data quality framework* baseado em regras de completude e unicidade.**

3. **Sobre a decisão de não filtrar nada.** A premissa proíbe tratamento, e este arquivo obedece. Vale registrar que, num projeto real, a primeira coisa a fazer seria materializar uma dimensão de status com uma flag `é_receita_efetivada` — não para filtrar em código, mas para que a escolha vire um *slicer* no dashboard e a pergunta "isso inclui cancelados?" tenha resposta visível em vez de enterrada num `WHERE`.

4. **O que eu pediria antes de seguir:** a definição contábil de receita da empresa (reconhece em `confirmed` ou só em `paid`?), a razão de existirem pedidos com data futura (previsão? erro de carga? pedido programado?) e o fuso horário dos carimbos, que a fonte não declara.
