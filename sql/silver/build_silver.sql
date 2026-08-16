-- ============================================================================
-- LH Nautical — camada SILVER
-- ============================================================================
--
-- PAPEL DESTA CAMADA
--   `raw` espelha a fonte, lixo incluído, porque é a evidência do que o ERP
--   entregou. `gold` é modelado para consumo. `silver` é onde as decisões de
--   limpeza acontecem — UMA VEZ, de forma declarada e auditável.
--
--   Se uma regra de negócio precisa ser aplicada, ela mora aqui. Espalhá-la
--   por consultas de dashboard é como duas pessoas chegarem a dois números.
--
-- O QUE ESTA CAMADA CORRIGE (e por quê)
--   1. Tokens de lixo textual viram NULL — com FLAG preservando a evidência.
--      `raw` guarda 'asdf' porque a Q3 proíbe tratar; aqui ele vira NULL e
--      ganha `flag_nome_suspeito = true`, para que o problema continue
--      visível em vez de sumir.
--   2. `stock_levels.reorder_point` (100% vazia em raw, tipada como TEXT)
--      vira INTEGER nullable — o tipo que ela teria se tivesse dado.
--   3. Capitalização de categoria normalizada ('SEGURANÇA' -> 'Segurança').
--   4. Nada mais. Em especial: NENHUMA linha é descartada, nenhum status é
--      filtrado, nenhum outlier é removido. Essas são decisões de análise,
--      não de limpeza, e pertencem ao dashboard como slicer.
--
-- Como rodar:  psql -d lh_nautical -v ON_ERROR_STOP=1 -f sql/silver/build_silver.sql
-- ============================================================================

\echo '>> SILVER: iniciando'

BEGIN;

-- Guarda de banco compartilhado: esta instância roda outros projetos.
DO $$
BEGIN
    IF current_database() <> 'lh_nautical' THEN
        RAISE EXCEPTION 'ABORTADO: banco % nao e lh_nautical', current_database();
    END IF;
END $$;

CREATE SCHEMA IF NOT EXISTS silver;

-- ----------------------------------------------------------------------------
-- Função auxiliar: normaliza texto-lixo para NULL.
-- Centralizada para que a lista de tokens exista em UM lugar só.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION silver.limpar_texto(v text)
RETURNS text
LANGUAGE sql IMMUTABLE
AS $$
    SELECT CASE
        WHEN v IS NULL THEN NULL
        WHEN btrim(v) = '' THEN NULL
        WHEN lower(btrim(v)) IN (
            '?', '??', '-', '--', '—', '...', 'n/a', 'na', 'tbd', 'todo',
            'fixme', 'asdf', 'test', 'xxx', 'sem nome', 'null', 'none'
        ) THEN NULL
        ELSE btrim(v)
    END
$$;

COMMENT ON FUNCTION silver.limpar_texto(text) IS
    'Converte tokens de lixo textual em NULL. A lista vive aqui e em nenhum '
    'outro lugar, para que "o que conta como lixo" seja uma decisão única.';


-- ============================================================================
-- DIMENSÕES DE APOIO
-- ============================================================================

DROP TABLE IF EXISTS silver.categorias CASCADE;
CREATE TABLE silver.categorias AS
SELECT
    id                                   AS category_id,
    -- 'SEGURANÇA' vem em caixa alta na fonte, destoando das outras 13.
    -- initcap() sozinho estragaria 'Coletes Salva-Vidas', então só a
    -- linha problemática é normalizada.
    CASE WHEN name = upper(name) AND length(name) > 3
         THEN initcap(name) ELSE name END AS categoria,
    (name = upper(name) AND length(name) > 3) AS flag_capitalizacao_corrigida,
    parent_category_id,
    is_active
FROM raw.categories;

ALTER TABLE silver.categorias ADD PRIMARY KEY (category_id);


DROP TABLE IF EXISTS silver.produtos CASCADE;
CREATE TABLE silver.produtos AS
WITH nomes AS (
    SELECT id, name, brand_id, category_id, is_active,
           count(*) OVER (PARTITION BY name) AS homonimos
    FROM raw.products
)
SELECT
    n.id                                          AS product_id,
    n.name                                        AS nome_bruto,
    silver.limpar_texto(n.name)                   AS nome,
    -- Rótulo de exibição: desambigua homônimos e nunca devolve NULL, para
    -- que um visual não apresente linha em branco.
    CASE
        WHEN silver.limpar_texto(n.name) IS NULL
            THEN '[sem nome] (id=' || n.id || ')'
        WHEN n.homonimos > 1
            THEN n.name || ' (id=' || n.id || ')'
        ELSE n.name
    END                                           AS nome_exibicao,
    (silver.limpar_texto(n.name) IS NULL)         AS flag_nome_suspeito,
    (n.homonimos > 1)                             AS flag_homonimo,
    n.brand_id,
    n.category_id,
    n.is_active
FROM nomes n;

ALTER TABLE silver.produtos ADD PRIMARY KEY (product_id);


DROP TABLE IF EXISTS silver.variantes CASCADE;
CREATE TABLE silver.variantes AS
SELECT
    id                AS product_variant_id,
    product_id,
    sku,
    sale_price,
    cost_price,
    weight_kg,
    is_active
FROM raw.product_variants;

ALTER TABLE silver.variantes ADD PRIMARY KEY (product_variant_id);


DROP TABLE IF EXISTS silver.clientes CASCADE;
CREATE TABLE silver.clientes AS
SELECT
    id                                            AS customer_id,
    person_type,
    silver.limpar_texto(legal_name)               AS razao_social,
    coalesce(silver.limpar_texto(legal_name),
             '[sem nome] (id=' || id || ')')      AS nome_exibicao,
    (silver.limpar_texto(legal_name) IS NULL)     AS flag_nome_suspeito,
    silver.limpar_texto(trade_name)               AS nome_fantasia,
    tax_id,
    silver.limpar_texto(email)                    AS email,
    is_active,
    created_at
FROM raw.customers;

ALTER TABLE silver.clientes ADD PRIMARY KEY (customer_id);


DROP TABLE IF EXISTS silver.locais CASCADE;
CREATE TABLE silver.locais AS
SELECT
    id                             AS location_id,
    name                           AS local,
    location_type                  AS tipo_local,
    city                           AS cidade,
    state                          AS uf,
    is_active
FROM raw.locations;

ALTER TABLE silver.locais ADD PRIMARY KEY (location_id);


-- ============================================================================
-- FATOS
-- ============================================================================

DROP TABLE IF EXISTS silver.pedidos CASCADE;
CREATE TABLE silver.pedidos AS
SELECT
    id                              AS order_id,
    order_number,
    channel                         AS canal,
    customer_id,
    salesperson_id,
    location_id,
    status,
    subtotal,
    discount_amount                 AS desconto,
    total,
    created_at                      AS data_pedido,
    created_at::date                AS data,
    -- Reconhecimento de receita: a decisão fica DECLARADA aqui e vira um
    -- atributo, em vez de um WHERE escondido em cada consulta.
    (status IN ('paid', 'confirmed'))          AS eh_receita_efetivada,
    (status = 'paid')                          AS eh_pago,
    (created_at > now())                       AS eh_futuro
FROM raw.orders;

ALTER TABLE silver.pedidos ADD PRIMARY KEY (order_id);
CREATE INDEX ix_silver_pedidos_cliente ON silver.pedidos (customer_id);
CREATE INDEX ix_silver_pedidos_data    ON silver.pedidos (data);


DROP TABLE IF EXISTS silver.itens_pedido CASCADE;
CREATE TABLE silver.itens_pedido AS
-- O rateio do desconto do pedido pelos itens é a definição de margem do
-- projeto. Ele acontece AQUI, uma vez, e não em cada medida do dashboard.
WITH rateio AS (
    SELECT
        oi.id                       AS order_item_id,
        oi.order_id,
        oi.product_variant_id,
        oi.quantity                 AS quantidade,
        oi.unit_price               AS preco_unitario,
        oi.line_total               AS valor_linha,
        o.desconto,
        -- Participação da linha no pedido. NULLIF protege contra pedido de
        -- valor zero, que geraria divisão por zero.
        oi.line_total / nullif(sum(oi.line_total) OVER (PARTITION BY oi.order_id), 0)
                                    AS participacao
    FROM raw.order_items oi
    JOIN silver.pedidos  o ON o.order_id = oi.order_id
),
arredondado AS (
    SELECT
        r.*,
        round(coalesce(r.desconto * r.participacao, 0), 2) AS rateado_bruto
    FROM rateio r
),
com_residuo AS (
    SELECT
        a.*,
        -- Arredondar cada linha para 2 casas faz a soma do pedido não fechar
        -- exatamente com o desconto original — resíduo de até poucos centavos.
        -- Ele é absorvido INTEIRO na maior linha do pedido, de modo que
        -- SUM(desconto_rateado) reproduza orders.discount_amount ao centavo.
        -- Distribuir o resíduo seria pior: criaria centavos em várias linhas
        -- e a conciliação deixaria de ser exata em qualquer recorte parcial.
        a.desconto - sum(a.rateado_bruto) OVER (PARTITION BY a.order_id)
                                                           AS residuo_do_pedido,
        row_number() OVER (PARTITION BY a.order_id
                           ORDER BY a.valor_linha DESC, a.order_item_id)
                                                           AS posto_na_linha
    FROM arredondado a
)
SELECT
    c.order_item_id,
    c.order_id,
    c.product_variant_id,
    v.product_id,
    c.quantidade,
    c.preco_unitario,
    c.valor_linha,
    -- numeric em todo o caminho: float acumularia erro e a validação
    -- "a soma do rateio bate com o desconto do pedido" falharia por centavos.
    (c.rateado_bruto
     + CASE WHEN c.posto_na_linha = 1 THEN coalesce(c.residuo_do_pedido, 0)
            ELSE 0 END)                                    AS desconto_rateado,
    round(c.quantidade * v.cost_price, 2)                  AS custo,
    round(c.valor_linha - c.quantidade * v.cost_price, 2)  AS margem_bruta,
    round(c.valor_linha - c.quantidade * v.cost_price, 2)
      - (c.rateado_bruto
         + CASE WHEN c.posto_na_linha = 1 THEN coalesce(c.residuo_do_pedido, 0)
                ELSE 0 END)                                AS margem_liquida
FROM com_residuo      c
JOIN silver.variantes v ON v.product_variant_id = c.product_variant_id;

ALTER TABLE silver.itens_pedido ADD PRIMARY KEY (order_item_id);
CREATE INDEX ix_silver_itens_pedido  ON silver.itens_pedido (order_id);
CREATE INDEX ix_silver_itens_produto ON silver.itens_pedido (product_id);


DROP TABLE IF EXISTS silver.pagamentos CASCADE;
CREATE TABLE silver.pagamentos AS
-- ISOLADA de propósito. `payments` faz fan-out 2:1 (6.999 pedidos têm dois
-- pagamentos). Esta tabela NUNCA deve ser relacionada a itens de pedido.
SELECT
    id            AS payment_id,
    order_id,
    method        AS metodo,
    installments  AS parcelas,
    amount        AS valor,
    status,
    paid_at       AS data_pagamento
FROM raw.payments;

ALTER TABLE silver.pagamentos ADD PRIMARY KEY (payment_id);


DROP TABLE IF EXISTS silver.devolucoes CASCADE;
CREATE TABLE silver.devolucoes AS
SELECT
    ri.id                  AS return_item_id,
    r.id                   AS return_id,
    r.order_id,
    r.customer_id,
    ri.order_item_id,
    ri.quantity            AS quantidade,
    ri.action              AS acao,
    ri.unit_refund_amount  AS valor_unitario_reembolso,
    r.status,
    silver.limpar_texto(r.reason) AS motivo,
    r.created_at::date     AS data
FROM raw.returns      r
JOIN raw.return_items ri ON ri.return_id = r.id;

ALTER TABLE silver.devolucoes ADD PRIMARY KEY (return_item_id);


DROP TABLE IF EXISTS silver.estoque CASCADE;
CREATE TABLE silver.estoque AS
SELECT
    sl.product_variant_id,
    sl.location_id,
    sl.quantity_on_hand::numeric  AS quantidade_em_maos,
    -- Em `raw` esta coluna é TEXT porque veio 100% vazia e não havia
    -- evidência para inferir tipo. Aqui ela recebe o tipo que teria se
    -- tivesse dado — e continua nula.
    nullif(btrim(sl.reorder_point), '')::integer AS ponto_de_reposicao,
    sl.updated_at
FROM raw.stock_levels sl;

ALTER TABLE silver.estoque ADD PRIMARY KEY (product_variant_id, location_id);


-- ============================================================================
-- VALIDAÇÕES — a camada não é considerada construída se alguma falhar
-- ============================================================================

DO $$
DECLARE
    v_pedidos      bigint;
    v_itens        bigint;
    v_desc_pedido  numeric;
    v_desc_rateado numeric;
    v_divergentes  bigint;
BEGIN
    SELECT count(*) INTO v_pedidos FROM silver.pedidos;
    IF v_pedidos <> 48998 THEN
        RAISE EXCEPTION 'silver.pedidos tem % linhas, esperado 48998', v_pedidos;
    END IF;

    SELECT count(*) INTO v_itens FROM silver.itens_pedido;
    IF v_itens <> 147320 THEN
        RAISE EXCEPTION 'silver.itens_pedido tem % linhas, esperado 147320', v_itens;
    END IF;

    -- A validação que dá sentido ao rateio: a soma dos descontos rateados
    -- por pedido tem de reproduzir o desconto do pedido.
    SELECT sum(desconto) INTO v_desc_pedido FROM silver.pedidos;
    SELECT sum(desconto_rateado) INTO v_desc_rateado FROM silver.itens_pedido;

    SELECT count(*) INTO v_divergentes
    FROM (
        SELECT i.order_id,
               sum(i.desconto_rateado) AS rateado,
               max(p.desconto)         AS original
        FROM silver.itens_pedido i
        JOIN silver.pedidos      p ON p.order_id = i.order_id
        GROUP BY i.order_id
        HAVING abs(sum(i.desconto_rateado) - max(p.desconto)) > 0.01
    ) t;

    RAISE NOTICE 'Desconto: pedidos = %, rateado = %, diferenca = %',
                 v_desc_pedido, v_desc_rateado, v_desc_pedido - v_desc_rateado;
    RAISE NOTICE 'Pedidos com rateio divergente acima de 1 centavo: %', v_divergentes;

    -- O resíduo de arredondamento é absorvido na maior linha de cada pedido,
    -- então a conciliação tem de ser EXATA. Divergência aqui é defeito.
    IF v_divergentes > 0 THEN
        RAISE EXCEPTION 'Ha % pedidos cujo rateio de desconto nao fecha ao '
                        'centavo', v_divergentes;
    END IF;

    IF v_desc_pedido <> v_desc_rateado THEN
        RAISE EXCEPTION 'Desconto total nao concilia: pedidos = %, rateado = %',
                        v_desc_pedido, v_desc_rateado;
    END IF;
END $$;

COMMIT;

\echo '>> SILVER: concluida'

SELECT relname AS tabela, n_live_tup AS linhas
FROM pg_stat_user_tables
WHERE schemaname = 'silver'
ORDER BY relname;
