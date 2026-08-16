# Questão 4 — Análise de clientes de elite

**Entregável:** `q4_clientes_elite.sql` (Q4.1) · este documento (Q4.2)

```bash
psql -d lh_nautical -f q4_clientes_elite.sql
```

---

## Resultado

### Os 10 clientes fiéis

| # | `customer_id` | Faturamento total | Frequência | **Ticket médio** | Categorias |
|---:|---:|---:|---:|---:|---:|
| 1 | **22** | R$ 1.087.838,44 | 26 | **R$ 41.839,94** | 14 |
| 2 | 1477 | R$ 916.262,58 | 22 | R$ 41.648,30 | 14 |
| 3 | 929 | R$ 1.082.775,89 | 26 | R$ 41.645,23 | 14 |
| 4 | 1116 | R$ 655.737,20 | 16 | R$ 40.983,58 | 14 |
| 5 | 1691 | R$ 815.471,30 | 20 | R$ 40.773,57 | 14 |
| 6 | 774 | R$ 726.127,99 | 18 | R$ 40.340,44 | 14 |
| 7 | 1470 | R$ 1.040.553,09 | 26 | R$ 40.021,27 | 14 |
| 8 | 1599 | R$ 997.616,46 | 25 | R$ 39.904,66 | 14 |
| 9 | 965 | R$ 677.297,78 | 17 | R$ 39.841,05 | 14 |
| 10 | 1722 | R$ 1.146.455,22 | 29 | R$ 39.532,94 | 14 |

### Categoria que o grupo mais consome

> **Hélices** (`category_id` 8), com **492 itens** — `SUM(quantity)`.

| # | Categoria | Itens | Linhas de item | Clientes do top 10 |
|---:|---|---:|---:|---:|
| 1 | **Hélices** | **492** | 88 | 10 |
| 2 | Coletes Salva-Vidas | 393 | 61 | 10 |
| 3 | Eletrônica Náutica | 392 | 65 | 10 |
| 4 | Âncoras | 387 | 66 | 10 |
| 5 | Iluminação | 333 | 58 | 10 |

As 14 categorias aparecem, e **todas as 14 foram compradas pelos 10 clientes** — consequência direta de todos eles terem diversidade 14.

---

## Q4.2 — Explicação

### 1. Como cheguei nas categorias mais vendidas: o mapeamento da cadeia de chaves

`orders` sabe *quanto* cada pedido custou, mas não *o que* foi vendido. Chegar em categoria exige quatro saltos:

```
orders.customer_id
  └─ orders.id ──────────────── order_items.order_id
       └─ order_items.product_variant_id ── product_variants.id
            └─ product_variants.product_id ── products.id
                 └─ products.category_id ─── categories.id
```

**O salto que costuma ser pulado é o segundo: `order_items` não tem `product_id`.** Ela referencia a *variante*, não o produto. Quem tenta juntar `order_items` direto em `products` não encontra chave, e a saída improvisada — casar por nome, ou assumir que `product_variant_id` é `product_id` — produz um número que parece razoável e está errado. `product_variants` é obrigatória no caminho porque é ela que carrega o `product_id`.

`categories` só entra no fim, para trocar o `id` pelo nome. A agregação já está fechada antes disso.

### 2. A lógica do filtro de diversidade mínima

```sql
categorias_por_cliente AS (
    SELECT o.customer_id, count(DISTINCT p.category_id) AS diversidade_categorias
    FROM raw.orders o
    JOIN raw.order_items      oi ON oi.order_id = o.id
    JOIN raw.product_variants pv ON pv.id       = oi.product_variant_id
    JOIN raw.products         p  ON p.id        = pv.product_id
    GROUP BY o.customer_id
)
...
WHERE cc.diversidade_categorias >= 13   -- ANTES do ORDER BY / LIMIT
ORDER BY pc.ticket_medio DESC, pc.customer_id ASC
LIMIT 10
```

Dois pontos:

**`COUNT(DISTINCT category_id)` é imune ao fan-out.** Esta CTE *precisa* fazer join — é o único caminho até a categoria — e o join multiplica linhas. Mas contar valores *distintos* não se importa com quantas vezes cada valor apareceu, então o resultado é correto apesar da multiplicação. É por isso que a diversidade pode ser calculada no grão de item, enquanto o faturamento não pode.

**O filtro vem antes do `LIMIT`, e a ordem importa.** Filtrar depois devolveria "os que sobraram do top 10 geral", que é outra pergunta e daria menos de 10 clientes. O `WHERE` roda sobre o universo inteiro; o `LIMIT` corta o ranking já filtrado.

**Desempate:** `ORDER BY ticket_medio DESC, customer_id ASC`. Não houve empate real nesta base, mas sem o segundo critério o resultado seria não-determinístico se houvesse — e um ranking que muda de execução para execução é um ranking que não se pode auditar.

> ⚠️ **Crítica ao critério (o achado mais relevante desta questão).** O filtro de diversidade **não filtra praticamente ninguém**:
>
> | Categorias distintas | Clientes | % |
> |---:|---:|---:|
> | 11 | 2 | 0,10% |
> | 12 | 27 | 1,35% |
> | 13 | 200 | 10,00% |
> | **14** | **1.771** | **88,55%** |
>
> **Só existem 14 categorias na loja**, e **1.971 de 2.000 clientes (98,5%) compraram de 13 ou mais.** O critério que a Diretoria imaginou como marca de sofisticação — "navega por diversas categorias" — é satisfeito por quase toda a base.
>
> Na prática, **o ranking é ordenado exclusivamente pelo ticket médio**: os 10 selecionados teriam sido os mesmos sem o filtro. A definição de "cliente fiel" do enunciado tem dois critérios, mas apenas um deles opera.

### 3. Como garanti que a contagem de itens refletisse apenas os Top 10

A lista dos 10 é materializada em uma CTE (`top10_fieis`) e usada como **tabela dirigente** do join:

```sql
FROM top10_fieis          t
JOIN raw.orders           o  ON o.customer_id = t.customer_id
JOIN raw.order_items      oi ON oi.order_id   = o.id
JOIN raw.product_variants pv ON pv.id         = oi.product_variant_id
JOIN raw.products         p  ON p.id          = pv.product_id
```

O `INNER JOIN` a partir de `top10_fieis` é o que restringe o universo. A alternativa — recalcular o critério de diversidade dentro da consulta de itens — traria de volta os **1.971 clientes** que passam no filtro e inflaria a contagem em quase 200×.

A consulta seguinte no arquivo é uma **asserção explícita**: conta os clientes do grupo e imprime `OK` se forem exatamente 10. É barata e transforma uma suposição em verificação.

---

## Os quatro erros que destroem o número

Este é o coração da questão, e os três primeiros estão **medidos** no apêndice do arquivo SQL — não são hipóteses.

| Erro | Faturamento resultante | Desvio |
|---|---:|---:|
| ✅ **Correto** — `SUM(total)` sem join | **R$ 1.406.487.201,80** | — |
| ❌ `SUM(total)` após join em `payments` | R$ 1.536.966.390,29 | **+R$ 130,5 mi (+9,3%)** |
| ❌ `SUM(total)` após join em `order_items` | R$ 5.162.685.388,47 | **+267% (3,67×)** |

**1. Somar `total` depois de juntar `order_items`.** `orders.total` é do grão *pedido*; `order_items` é do grão *item*. O join repete o valor do pedido uma vez por item — 147.320 itens para 48.998 pedidos — e o faturamento infla 3,67×. É por isso que `pedidos_por_cliente` **não faz nenhum join**: a ausência do join é o mecanismo de proteção, não um descuido.

**2. Qualquer `JOIN` com `payments`.** Pior porque é mais sutil: 6.999 pedidos têm 2 pagamentos, então o fan-out é parcial. O erro é de +9,3% — grande o bastante para mudar decisões, pequeno o bastante para ninguém desconfiar. Não há um único join com `payments` neste arquivo.

**3. `COUNT(*)` como frequência dentro da CTE que já fez join.** Contaria *itens*, não *transações*. O ticket médio despencaria e o ranking inteiro mudaria.

**4. Aplicar o filtro de diversidade depois do `LIMIT`.** Devolveria menos de 10 clientes, e os errados.

---

## Leitura de engenharia

1. **O critério de "cliente fiel" precisa ser redesenhado, e a evidência está acima.** Com 98,5% da base passando no filtro de diversidade, o segundo critério é decorativo. Sugestões concretas: usar **cobertura relativa** (percentil de diversidade em vez de valor absoluto), ou trocar diversidade por **recência + frequência + valor (RFM)**, ou medir diversidade em nível de *produto* em vez de categoria — há 500 produtos contra 14 categorias, então o sinal existe, só não está sendo lido no grão certo.

2. **"Ticket médio alto" e "cliente valioso" não são a mesma coisa, e o ranking mostra isso.** O cliente 1116 tem o 4º maior ticket médio e faturamento total de R$ 655 mil; o cliente 1722 tem o 10º ticket e **R$ 1,15 milhão** — 75% a mais. Ordenar por ticket médio premia quem compra caro e raro em cima de quem compra muito. Se o objetivo declarado é *"replicar o comportamento em outros segmentos"*, o comportamento de 1722 provavelmente interessa mais.

3. **O resultado da letra (c) é quase uma tautologia, e vale dizer isso.** Todos os 10 clientes compraram das 14 categorias, então a categoria vencedora é decidida por diferenças pequenas de quantidade: Hélices tem 492 itens contra 393 do segundo — margem confortável, mas do 2º ao 4º lugar (393, 392, 387) a diferença é ruído. Com 10 clientes e 88 linhas de item na categoria líder, **a amostra é pequena demais para sustentar uma decisão de sortimento**. O número está certo; a inferência de negócio que ele suporta é fraca.

4. **Achado colateral de qualidade:** a categoria 13 se chama `SEGURANÇA`, em caixa alta, enquanto todas as outras 13 usam capitalização normal (`Hélices`, `Coletes Salva-Vidas`). É inconsistência de cadastro na fonte. Não afeta esta resposta — a agregação é por `category_id` — mas apareceria como rótulo destoante em qualquer visual, e é o tipo de coisa que a camada `silver` deve normalizar.

5. **Sobre não filtrar status.** O enunciado define faturamento como *"soma da coluna total por cliente"*, sem qualificar. A leitura literal soma tudo, e é o que está aqui. Vale registrar que **14,7% do GMV são pedidos `cancelled` ou `draft`** (medido na Q1): um "faturamento" que inclui pedidos cancelados não é faturamento em nenhuma definição contábil. Em um projeto real, esta seria a primeira pergunta ao solicitante — e o dashboard resolve isso com um *slicer* de status em vez de uma decisão enterrada num `WHERE`.
