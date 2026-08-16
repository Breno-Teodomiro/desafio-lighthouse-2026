-- ============================================================================
-- Desafio Lighthouse 2026 — Questão 4: Clientes de elite
-- ============================================================================
--
-- PREMISSAS OBRIGATÓRIAS, e como cada uma vira código aqui:
--
--   Faturamento Total  = SUM(orders.total) por cliente
--   Frequência         = contagem de transações (IDs de venda) por cliente
--   Ticket Médio       = Faturamento Total / Frequência
--   Diversidade        = COUNT(DISTINCT category_id) comprados pelo cliente
--   Filtro de Elite    = somente clientes com >= 13 categorias distintas
--   Desempate          = customer_id crescente
--
-- A CADEIA DE CHAVES (a parte que decide se o número está certo):
--
--   orders.customer_id
--     -> orders.id = order_items.order_id
--       -> order_items.product_variant_id = product_variants.id
--         -> product_variants.product_id = products.id
--           -> products.category_id = categories.id
--
--   `order_items` NÃO TEM product_id. A variante é obrigatória no caminho —
--   pular esse salto é o erro mais comum nesta questão.
--
-- O RISCO CENTRAL: FAN-OUT.
--
--   `orders.total` é do grão PEDIDO. `order_items` é do grão ITEM. Somar
--   `total` depois de juntar com `order_items` repete o valor do pedido uma
--   vez por item e infla o faturamento em ~3x (são 147.320 itens para 48.998
--   pedidos). Por isso faturamento e frequência saem de uma CTE que NÃO faz
--   nenhum join.
--
--   O mesmo vale, pior ainda, para `payments`: 6.999 pedidos têm 2 pagamentos.
--   Não há um único JOIN com payments neste arquivo.
--
-- Como rodar:
--     psql -d lh_nautical -f q4_clientes_elite.sql
--
-- Autor: Breno Teodomiro · Desafio Técnico Lighthouse 2026 (Indicium)
-- ============================================================================

\echo ''
\echo '=============================================================='
\echo ' Q4.1 (a) — Ticket médio e diversidade por cliente'
\echo '=============================================================='

-- ----------------------------------------------------------------------------
-- CTE 1 — pedidos_por_cliente
--   Grão: um cliente por linha. NENHUM JOIN. É esta ausência de join que
--   garante que `total` seja somado uma vez por pedido, e não uma vez por item.
-- ----------------------------------------------------------------------------
WITH pedidos_por_cliente AS (
    SELECT
        customer_id,
        sum(total)                  AS faturamento_total,
        count(*)                    AS frequencia,
        sum(total) / count(*)       AS ticket_medio
    FROM raw.orders
    GROUP BY customer_id
),

-- ----------------------------------------------------------------------------
-- CTE 2 — categorias_por_cliente
--   Grão: um cliente por linha. Aqui o join é obrigatório (é o único caminho
--   até category_id), mas o resultado é COUNT(DISTINCT ...) — uma contagem de
--   valores distintos é imune ao fan-out por construção.
-- ----------------------------------------------------------------------------
categorias_por_cliente AS (
    SELECT
        o.customer_id,
        count(DISTINCT p.category_id) AS diversidade_categorias
    FROM raw.orders            o
    JOIN raw.order_items       oi ON oi.order_id           = o.id
    JOIN raw.product_variants  pv ON pv.id                 = oi.product_variant_id
    JOIN raw.products          p  ON p.id                  = pv.product_id
    GROUP BY o.customer_id
)

-- ----------------------------------------------------------------------------
-- Junção 1:1 — os dois lados estão no mesmo grão (cliente), então este join
-- não pode multiplicar linha nenhuma.
--
-- LEFT JOIN de propósito: cliente que fez pedido sem item apareceria com
-- diversidade NULL em vez de sumir da análise. Não é o caso nesta base, mas
-- desaparecer em silêncio é o tipo de coisa que não se descobre depois.
-- ----------------------------------------------------------------------------
SELECT
    pc.customer_id,
    round(pc.faturamento_total, 2)              AS faturamento_total,
    pc.frequencia,
    round(pc.ticket_medio, 2)                   AS ticket_medio,
    coalesce(cc.diversidade_categorias, 0)      AS diversidade_categorias
FROM pedidos_por_cliente        pc
LEFT JOIN categorias_por_cliente cc ON cc.customer_id = pc.customer_id
ORDER BY pc.ticket_medio DESC, pc.customer_id ASC
LIMIT 20;
-- LIMIT só para a inspeção visual; o ranking oficial é a consulta seguinte.


\echo ''
\echo '=============================================================='
\echo ' Q4.1 (b) — Os 10 clientes FIÉIS'
\echo '   (maior ticket médio, entre os com diversidade >= 13)'
\echo '=============================================================='

WITH pedidos_por_cliente AS (
    SELECT customer_id,
           sum(total)            AS faturamento_total,
           count(*)              AS frequencia,
           sum(total) / count(*) AS ticket_medio
    FROM raw.orders
    GROUP BY customer_id
),
categorias_por_cliente AS (
    SELECT o.customer_id,
           count(DISTINCT p.category_id) AS diversidade_categorias
    FROM raw.orders           o
    JOIN raw.order_items      oi ON oi.order_id = o.id
    JOIN raw.product_variants pv ON pv.id       = oi.product_variant_id
    JOIN raw.products         p  ON p.id        = pv.product_id
    GROUP BY o.customer_id
)
SELECT
    row_number() OVER (ORDER BY pc.ticket_medio DESC, pc.customer_id ASC) AS posicao,
    pc.customer_id,
    round(pc.faturamento_total, 2) AS faturamento_total,
    pc.frequencia,
    round(pc.ticket_medio, 2)      AS ticket_medio,
    cc.diversidade_categorias
FROM pedidos_por_cliente         pc
JOIN categorias_por_cliente      cc ON cc.customer_id = pc.customer_id
-- O filtro de elite é aplicado ANTES do ORDER BY / LIMIT. Aplicá-lo depois
-- devolveria "os que sobraram do top 10 geral", que é outra pergunta.
WHERE cc.diversidade_categorias >= 13
ORDER BY pc.ticket_medio DESC, pc.customer_id ASC
LIMIT 10;


\echo ''
\echo '=============================================================='
\echo ' Q4.1 (c) — Categoria mais consumida PELO GRUPO dos 10'
\echo '=============================================================='

-- A lista dos 10 é materializada uma vez e usada como TABELA DIRIGENTE.
-- A contagem de itens faz INNER JOIN contra ela — nunca refiltra pelo
-- critério de diversidade, o que traria de volta os 1.971 clientes que
-- passam no filtro e destruiria o número.
WITH pedidos_por_cliente AS (
    SELECT customer_id,
           sum(total) / count(*) AS ticket_medio
    FROM raw.orders
    GROUP BY customer_id
),
categorias_por_cliente AS (
    SELECT o.customer_id,
           count(DISTINCT p.category_id) AS diversidade_categorias
    FROM raw.orders           o
    JOIN raw.order_items      oi ON oi.order_id = o.id
    JOIN raw.product_variants pv ON pv.id       = oi.product_variant_id
    JOIN raw.products         p  ON p.id        = pv.product_id
    GROUP BY o.customer_id
),
top10_fieis AS (
    SELECT pc.customer_id
    FROM pedidos_por_cliente    pc
    JOIN categorias_por_cliente cc ON cc.customer_id = pc.customer_id
    WHERE cc.diversidade_categorias >= 13
    ORDER BY pc.ticket_medio DESC, pc.customer_id ASC
    LIMIT 10
),
itens_do_grupo AS (
    SELECT
        p.category_id,
        oi.quantity,
        o.customer_id
    FROM top10_fieis          t
    JOIN raw.orders           o  ON o.customer_id        = t.customer_id
    JOIN raw.order_items      oi ON oi.order_id          = o.id
    JOIN raw.product_variants pv ON pv.id                = oi.product_variant_id
    JOIN raw.products         p  ON p.id                 = pv.product_id
)
SELECT
    c.id                            AS category_id,
    c.name                          AS categoria,
    sum(ig.quantity)                AS total_itens_comprados,
    count(*)                        AS linhas_de_item,
    count(DISTINCT ig.customer_id)  AS clientes_do_top10_que_compraram
FROM itens_do_grupo ig
JOIN raw.categories c ON c.id = ig.category_id
GROUP BY c.id, c.name
ORDER BY total_itens_comprados DESC;


\echo ''
\echo '=============================================================='
\echo ' ASSERÇÃO — o grupo tem exatamente 10 clientes?'
\echo '=============================================================='
-- Se esta consulta não devolver 10, a resposta da letra (c) está errada e
-- precisa parar aqui. Barato de rodar, e é o tipo de conferência que se
-- lamenta não ter feito.

WITH pedidos_por_cliente AS (
    SELECT customer_id, sum(total) / count(*) AS ticket_medio
    FROM raw.orders GROUP BY customer_id
),
categorias_por_cliente AS (
    SELECT o.customer_id, count(DISTINCT p.category_id) AS diversidade
    FROM raw.orders           o
    JOIN raw.order_items      oi ON oi.order_id = o.id
    JOIN raw.product_variants pv ON pv.id       = oi.product_variant_id
    JOIN raw.products         p  ON p.id        = pv.product_id
    GROUP BY o.customer_id
),
top10_fieis AS (
    SELECT pc.customer_id
    FROM pedidos_por_cliente    pc
    JOIN categorias_por_cliente cc ON cc.customer_id = pc.customer_id
    WHERE cc.diversidade >= 13
    ORDER BY pc.ticket_medio DESC, pc.customer_id ASC
    LIMIT 10
)
SELECT count(*)                                        AS clientes_no_grupo,
       CASE WHEN count(*) = 10 THEN 'OK' ELSE 'FALHOU' END AS asercao
FROM top10_fieis;


-- ############################################################################
--   APÊNDICE — DIAGNÓSTICO DO CRITÉRIO
--   Não é pedido pelo enunciado. Existe porque a Q4.2 pergunta pela lógica
--   do filtro, e a lógica só pode ser avaliada olhando o que ela seleciona.
-- ############################################################################

\echo ''
\echo '=============================================================='
\echo ' DIAGNÓSTICO — o filtro de >= 13 categorias discrimina alguém?'
\echo '=============================================================='

WITH categorias_por_cliente AS (
    SELECT o.customer_id, count(DISTINCT p.category_id) AS diversidade
    FROM raw.orders           o
    JOIN raw.order_items      oi ON oi.order_id = o.id
    JOIN raw.product_variants pv ON pv.id       = oi.product_variant_id
    JOIN raw.products         p  ON p.id        = pv.product_id
    GROUP BY o.customer_id
)
SELECT
    diversidade                                              AS categorias_distintas,
    count(*)                                                 AS clientes,
    round(100.0 * count(*) / sum(count(*)) OVER (), 2)       AS pct,
    sum(count(*)) FILTER (WHERE diversidade >= 13) OVER ()   AS passam_no_filtro
FROM categorias_por_cliente
GROUP BY diversidade
ORDER BY diversidade;

\echo ''
\echo '-- quantas categorias existem no total? ------------------------------'
SELECT count(*) AS categorias_existentes FROM raw.categories;


\echo ''
\echo '=============================================================='
\echo ' DIAGNÓSTICO — a prova do fan-out (por que a CTE 1 não faz join)'
\echo '=============================================================='
-- Mostra lado a lado o faturamento correto e os dois erros clássicos.
-- Não é hipótese: são os números que sairiam.

SELECT
    'correto: SUM(total) sem join'          AS metodo,
    round(sum(total), 2)                    AS faturamento
FROM raw.orders
UNION ALL
SELECT
    'ERRADO: SUM(total) após join em order_items',
    round(sum(o.total), 2)
FROM raw.orders o
JOIN raw.order_items oi ON oi.order_id = o.id
UNION ALL
SELECT
    'ERRADO: SUM(total) após join em payments',
    round(sum(o.total), 2)
FROM raw.orders o
JOIN raw.payments pg ON pg.order_id = o.id;

\echo ''
\echo '=============================================================='
\echo ' Fim. Explicação (Q4.2) em RESPOSTA.md.'
\echo '=============================================================='
