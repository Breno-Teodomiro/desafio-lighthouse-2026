-- ============================================================================
-- LH Nautical — camada GOLD (star schema para o Power BI)
-- ============================================================================
--
-- MODELO: estrela, com dois fatos de grãos diferentes e um fato isolado.
--
--   dim_data ──┐
--   dim_cliente┤
--   dim_produto┼── fct_item_pedido   (147.320 · grão: linha de item)
--   dim_local  ┤
--   dim_canal  ┤
--   dim_status ┴── fct_pedido        ( 48.998 · grão: pedido)
--
--                  fct_pagamento     ( 53.546 · ISOLADO, sem relação com itens)
--
-- POR QUE DOIS FATOS DE VENDA
--   `orders.total` é do grão PEDIDO. Se ele morasse em `fct_item_pedido`, o
--   valor se repetiria por item e qualquer soma inflaria 3,67x. Ticket médio e
--   contagem de pedidos saem SEMPRE de `fct_pedido`; mix de produto, categoria
--   e margem saem de `fct_item_pedido`. Separar os grãos é o que impede o
--   erro, e nenhuma medida DAX precisa "tomar cuidado".
--
-- POR QUE fct_pagamento FICA ISOLADO
--   `payments` faz fan-out 2:1 — 6.999 pedidos têm dois pagamentos. Se ele
--   fosse relacionado ao modelo, um filtro de método de pagamento inflaria o
--   faturamento em 9,3%. Ele existe para responder perguntas SOBRE pagamento
--   (mix de método, parcelamento) e nada mais. A ausência do relacionamento é
--   deliberada e está documentada aqui para que ninguém a "conserte" depois.
--
-- Como rodar:  psql -d lh_nautical -v ON_ERROR_STOP=1 -f sql/gold/build_gold.sql
-- ============================================================================

\echo '>> GOLD: iniciando'

BEGIN;

DO $$
BEGIN
    IF current_database() <> 'lh_nautical' THEN
        RAISE EXCEPTION 'ABORTADO: banco % nao e lh_nautical', current_database();
    END IF;
END $$;

CREATE SCHEMA IF NOT EXISTS gold;

-- A Q5 criou gold.dim_calendario e gold.vw_venda_diaria_pos. A dimensão de
-- data do modelo é mais ampla (cobre TODOS os pedidos, não só POS), então
-- vive separada. A view da Q5 depende da dim_calendario e é recriada no fim.
DROP VIEW  IF EXISTS gold.vw_venda_diaria_pos CASCADE;


-- ============================================================================
-- §1  DIMENSÕES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- dim_data — cobre todo o período de TODOS os fatos datados, denso.
--
-- O limite não sai só de `silver.pedidos`: a devolução acontece DEPOIS do
-- pedido que a originou, e 27 delas caem em janeiro de 2027, além do último
-- pedido (2026-12-31). Um calendário fechado em pedidos deixaria essas 27
-- linhas órfãs — no Power BI elas cairiam num membro "Em branco" da dimensão
-- e sumiriam de qualquer visual filtrado por data, sem erro nenhum.
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.dim_data CASCADE;
CREATE TABLE gold.dim_data AS
WITH limites AS (
    SELECT
        least(   (SELECT min(data) FROM silver.pedidos),
                 (SELECT min(data) FROM silver.devolucoes)) AS ini,
        greatest((SELECT max(data) FROM silver.pedidos),
                 (SELECT max(data) FROM silver.devolucoes)) AS fim
)
SELECT
    d::date                                AS data,
    extract(isodow FROM d)::int            AS num_dia_semana,
    CASE extract(isodow FROM d)
        WHEN 1 THEN 'Segunda-feira' WHEN 2 THEN 'Terça-feira'
        WHEN 3 THEN 'Quarta-feira'  WHEN 4 THEN 'Quinta-feira'
        WHEN 5 THEN 'Sexta-feira'   WHEN 6 THEN 'Sábado'
        WHEN 7 THEN 'Domingo'
    END                                    AS dia_semana,
    extract(year FROM d)::int              AS ano,
    extract(month FROM d)::int             AS num_mes,
    CASE extract(month FROM d)
        WHEN  1 THEN 'Janeiro' WHEN  2 THEN 'Fevereiro' WHEN  3 THEN 'Março'
        WHEN  4 THEN 'Abril'   WHEN  5 THEN 'Maio'      WHEN  6 THEN 'Junho'
        WHEN  7 THEN 'Julho'   WHEN  8 THEN 'Agosto'    WHEN  9 THEN 'Setembro'
        WHEN 10 THEN 'Outubro' WHEN 11 THEN 'Novembro'  WHEN 12 THEN 'Dezembro'
    END                                    AS mes,
    to_char(d, 'YYYY-MM')                  AS ano_mes,
    extract(quarter FROM d)::int           AS num_trimestre,
    'T' || extract(quarter FROM d)::text   AS trimestre,
    (extract(isodow FROM d) >= 6)          AS eh_fim_de_semana,
    -- 8,7% dos pedidos têm data posterior a hoje. Esta flag é o que permite
    -- ao dashboard sombrear a área futura em vez de apresentá-la como
    -- realizada — a armadilha nº 2 do diagnóstico da Q1.
    (d::date > current_date)               AS eh_futuro
FROM limites, generate_series(limites.ini, limites.fim, interval '1 day') AS d;

ALTER TABLE gold.dim_data ADD PRIMARY KEY (data);


-- ----------------------------------------------------------------------------
-- dim_cliente — com a marca dos 10 clientes de elite da Q4.
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.dim_cliente CASCADE;
CREATE TABLE gold.dim_cliente AS
WITH metricas AS (
    SELECT customer_id,
           sum(total)            AS faturamento,
           count(*)              AS frequencia,
           sum(total)/count(*)   AS ticket_medio
    FROM silver.pedidos
    GROUP BY customer_id
),
diversidade AS (
    SELECT p.customer_id, count(DISTINCT pr.category_id) AS categorias
    FROM silver.pedidos      p
    JOIN silver.itens_pedido i  ON i.order_id   = p.order_id
    JOIN silver.produtos     pr ON pr.product_id = i.product_id
    GROUP BY p.customer_id
),
elite AS (
    SELECT m.customer_id
    FROM metricas    m
    JOIN diversidade d ON d.customer_id = m.customer_id
    WHERE d.categorias >= 13
    ORDER BY m.ticket_medio DESC, m.customer_id ASC
    LIMIT 10
)
SELECT
    c.customer_id,
    c.nome_exibicao                            AS cliente,
    c.person_type                              AS tipo_pessoa,
    c.flag_nome_suspeito,
    round(m.faturamento, 2)                    AS faturamento_total,
    m.frequencia,
    round(m.ticket_medio, 2)                   AS ticket_medio,
    coalesce(d.categorias, 0)                  AS diversidade_categorias,
    (e.customer_id IS NOT NULL)                AS flag_elite
FROM silver.clientes  c
LEFT JOIN metricas    m ON m.customer_id = c.customer_id
LEFT JOIN diversidade d ON d.customer_id = c.customer_id
LEFT JOIN elite       e ON e.customer_id = c.customer_id;

ALTER TABLE gold.dim_cliente ADD PRIMARY KEY (customer_id);


-- ----------------------------------------------------------------------------
-- dim_produto
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.dim_produto CASCADE;
CREATE TABLE gold.dim_produto AS
SELECT
    p.product_id,
    p.nome_exibicao          AS produto,
    p.flag_nome_suspeito,
    p.flag_homonimo,
    c.category_id,
    c.categoria,
    c.flag_capitalizacao_corrigida,
    b.name                   AS marca,
    p.is_active              AS ativo
FROM silver.produtos    p
LEFT JOIN silver.categorias c ON c.category_id = p.category_id
LEFT JOIN raw.brands        b ON b.id          = p.brand_id;

ALTER TABLE gold.dim_produto ADD PRIMARY KEY (product_id);


-- ----------------------------------------------------------------------------
-- dim_local / dim_canal / dim_status_pedido
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.dim_local CASCADE;
CREATE TABLE gold.dim_local AS
SELECT location_id, local, tipo_local, cidade, uf FROM silver.locais;
ALTER TABLE gold.dim_local ADD PRIMARY KEY (location_id);


DROP TABLE IF EXISTS gold.dim_canal CASCADE;
CREATE TABLE gold.dim_canal AS
SELECT DISTINCT
    canal,
    CASE canal WHEN 'pos'       THEN 'Loja física'
               WHEN 'ecommerce' THEN 'E-commerce'
               ELSE initcap(canal) END AS canal_exibicao
FROM silver.pedidos;
ALTER TABLE gold.dim_canal ADD PRIMARY KEY (canal);


DROP TABLE IF EXISTS gold.dim_status_pedido CASCADE;
CREATE TABLE gold.dim_status_pedido AS
-- A dimensão que resolve TODA a ambiguidade de status do projeto.
-- Em vez de enterrar a decisão "o que conta como receita" num WHERE, ela
-- vira atributo e o usuário decide no slicer. É a diferença entre um número
-- que alguém precisa defender e um número que o leitor consegue interrogar.
SELECT * FROM (VALUES
    ('draft',     'Rascunho',   1, false, false),
    ('confirmed', 'Confirmado', 2, true,  false),
    ('paid',      'Pago',       3, true,  true),
    ('cancelled', 'Cancelado',  4, false, false)
) AS t(status, status_exibicao, ordem, eh_receita_efetivada, eh_pago);
ALTER TABLE gold.dim_status_pedido ADD PRIMARY KEY (status);


-- ============================================================================
-- §2  FATOS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- fct_pedido — grão: PEDIDO. Única origem de ticket médio e contagem.
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.fct_pedido CASCADE;
CREATE TABLE gold.fct_pedido AS
SELECT
    order_id,
    data,
    customer_id,
    location_id,
    canal,
    status,
    subtotal,
    desconto,
    total,
    eh_futuro
FROM silver.pedidos;

ALTER TABLE gold.fct_pedido ADD PRIMARY KEY (order_id);
CREATE INDEX ix_gold_pedido_data    ON gold.fct_pedido (data);
CREATE INDEX ix_gold_pedido_cliente ON gold.fct_pedido (customer_id);


-- ----------------------------------------------------------------------------
-- fct_item_pedido — grão: LINHA DE ITEM. Mix, categoria e margem.
--   NÃO contém `orders.total`, de propósito: se contivesse, alguém somaria.
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.fct_item_pedido CASCADE;
CREATE TABLE gold.fct_item_pedido AS
SELECT
    i.order_item_id,
    i.order_id,
    p.data,
    p.customer_id,
    p.location_id,
    p.canal,
    p.status,
    i.product_id,
    i.product_variant_id,
    i.quantidade,
    i.preco_unitario,
    i.valor_linha,
    i.custo,
    i.desconto_rateado,
    i.margem_bruta,
    i.margem_liquida
FROM silver.itens_pedido i
JOIN silver.pedidos      p ON p.order_id = i.order_id;

ALTER TABLE gold.fct_item_pedido ADD PRIMARY KEY (order_item_id);
CREATE INDEX ix_gold_item_data    ON gold.fct_item_pedido (data);
CREATE INDEX ix_gold_item_produto ON gold.fct_item_pedido (product_id);


-- ----------------------------------------------------------------------------
-- fct_pagamento — ISOLADO. Ver a nota no cabeçalho.
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.fct_pagamento CASCADE;
CREATE TABLE gold.fct_pagamento AS
SELECT
    pg.payment_id,
    pg.order_id,
    pg.data_pagamento::date AS data,
    pg.metodo,
    pg.parcelas,
    pg.valor,
    pg.status
FROM silver.pagamentos pg;
ALTER TABLE gold.fct_pagamento ADD PRIMARY KEY (payment_id);


-- ----------------------------------------------------------------------------
-- fct_venda_diaria_pos — a Q5 materializada, DENSA.
--   Uma linha por dia do calendário, inclusive os 78 sem venda.
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.fct_venda_diaria_pos CASCADE;
CREATE TABLE gold.fct_venda_diaria_pos AS
WITH periodo AS (
    SELECT min(data) AS ini, max(data) AS fim
    FROM silver.pedidos WHERE canal = 'pos'
),
calendario AS (
    SELECT d::date AS data
    FROM periodo, generate_series(periodo.ini, periodo.fim, interval '1 day') AS d
),
vendas AS (
    SELECT data, sum(total) AS valor, count(*) AS pedidos
    FROM silver.pedidos WHERE canal = 'pos'
    GROUP BY data
)
SELECT
    c.data,
    coalesce(v.valor, 0)   AS valor_venda,
    coalesce(v.pedidos, 0) AS qtd_pedidos,
    (v.data IS NULL)       AS dia_sem_venda
FROM calendario c
LEFT JOIN vendas v ON v.data = c.data;
ALTER TABLE gold.fct_venda_diaria_pos ADD PRIMARY KEY (data);


-- ----------------------------------------------------------------------------
-- fct_devolucao / fct_estoque_atual
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.fct_devolucao CASCADE;
CREATE TABLE gold.fct_devolucao AS
SELECT
    d.return_item_id,
    d.return_id,
    d.order_id,
    d.customer_id,
    d.data,
    i.product_id,
    d.quantidade,
    d.acao,
    round(d.quantidade * d.valor_unitario_reembolso, 2) AS valor_reembolso,
    d.motivo,
    d.status
FROM silver.devolucoes        d
LEFT JOIN silver.itens_pedido i ON i.order_item_id = d.order_item_id;
ALTER TABLE gold.fct_devolucao ADD PRIMARY KEY (return_item_id);


DROP TABLE IF EXISTS gold.fct_estoque_atual CASCADE;
CREATE TABLE gold.fct_estoque_atual AS
SELECT
    e.product_variant_id,
    v.product_id,
    e.location_id,
    e.quantidade_em_maos,
    e.ponto_de_reposicao,
    round(e.quantidade_em_maos * v.cost_price, 2) AS valor_em_estoque
FROM silver.estoque   e
JOIN silver.variantes v ON v.product_variant_id = e.product_variant_id;
ALTER TABLE gold.fct_estoque_atual ADD PRIMARY KEY (product_variant_id, location_id);


-- ----------------------------------------------------------------------------
-- Recria a view da Q5 sobre a dimensão de calendário dela.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold.vw_venda_diaria_pos AS
SELECT
    f.data,
    c.num_dia_semana,
    c.dia_semana        AS nome_dia_semana,
    c.ano,
    c.num_mes           AS mes,
    f.valor_venda,
    f.qtd_pedidos,
    f.dia_sem_venda
FROM gold.fct_venda_diaria_pos f
JOIN gold.dim_data             c ON c.data = f.data;


-- ============================================================================
-- §3  VALIDAÇÕES — o gold não existe se alguma falhar
-- ============================================================================

DO $$
DECLARE
    v numeric; n bigint;
BEGIN
    -- Grãos preservados
    SELECT count(*) INTO n FROM gold.fct_pedido;
    IF n <> 48998 THEN RAISE EXCEPTION 'fct_pedido: % linhas', n; END IF;

    SELECT count(*) INTO n FROM gold.fct_item_pedido;
    IF n <> 147320 THEN RAISE EXCEPTION 'fct_item_pedido: % linhas', n; END IF;

    -- GMV conferido contra a Q1
    SELECT sum(total) INTO v FROM gold.fct_pedido;
    IF round(v, 2) <> 1406487201.80 THEN
        RAISE EXCEPTION 'GMV = %, esperado 1406487201.80', v;
    END IF;

    -- Rateio de desconto continua fechando no gold
    SELECT sum(desconto_rateado) INTO v FROM gold.fct_item_pedido;
    IF round(v, 2) <> 30717403.16 THEN
        RAISE EXCEPTION 'Desconto rateado = %, esperado 30717403.16', v;
    END IF;

    -- Os 10 clientes de elite da Q4
    SELECT count(*) INTO n FROM gold.dim_cliente WHERE flag_elite;
    IF n <> 10 THEN RAISE EXCEPTION 'flag_elite marcou % clientes', n; END IF;

    -- O calendário POS da Q5
    SELECT count(*) INTO n FROM gold.fct_venda_diaria_pos;
    IF n <> 2557 THEN RAISE EXCEPTION 'calendario POS: % dias', n; END IF;
    SELECT count(*) INTO n FROM gold.fct_venda_diaria_pos WHERE dia_sem_venda;
    IF n <> 78 THEN RAISE EXCEPTION 'dias sem venda: %', n; END IF;

    RAISE NOTICE 'GOLD: todas as validacoes passaram';
END $$;

COMMIT;

ANALYZE gold.fct_pedido;
ANALYZE gold.fct_item_pedido;
ANALYZE gold.fct_pagamento;

\echo '>> GOLD: concluida'

SELECT relname AS objeto, n_live_tup AS linhas
FROM pg_stat_user_tables
WHERE schemaname = 'gold'
ORDER BY relname;

\echo ''
\echo '-- Referências de margem (o dashboard deve reproduzir) ----------------'
SELECT
    round(sum(valor_linha), 2)     AS receita_bruta_itens,
    round(sum(margem_bruta), 2)    AS margem_bruta,
    round(100.0 * sum(margem_bruta) / sum(valor_linha), 2) AS pct_margem_bruta,
    round(sum(desconto_rateado), 2) AS desconto,
    round(sum(margem_liquida), 2)  AS margem_liquida,
    round(100.0 * sum(margem_liquida) / sum(valor_linha), 2) AS pct_margem_liquida
FROM gold.fct_item_pedido;
