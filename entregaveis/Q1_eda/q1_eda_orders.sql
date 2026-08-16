-- ============================================================================
-- Desafio Lighthouse 2026 — Questão 1: Análise Exploratória de `orders`
-- ============================================================================
--
-- PREMISSAS OBRIGATÓRIAS DA QUESTÃO, e como este arquivo as respeita:
--
--   "Utilize apenas a tabela orders"
--       -> Não há um único JOIN neste arquivo. Nem no diagnóstico.
--
--   "Não faça limpeza nem tratamento dos dados"
--       -> Não há WHERE que descarte linha, não há filtro de status, não há
--          COALESCE, não há CAST corretivo, não há remoção de outlier.
--          As 48.998 linhas entram em todas as agregações.
--
--   "Apenas observe, agregue e descreva"
--       -> Só SELECT com funções de agregação.
--
--   "O código deve ser enviado em SQL"
--       -> PostgreSQL 18.
--
-- Como rodar:
--     psql -d lh_nautical -f q1_eda_orders.sql
--
-- Autor: Breno Teodomiro · Desafio Técnico Lighthouse 2026 (Indicium)
-- ============================================================================

\echo ''
\echo '=============================================================='
\echo ' Q1.1 — VISÃO GERAL E ANÁLISE NUMÉRICA DE orders'
\echo '=============================================================='

-- ----------------------------------------------------------------------------
-- CONSULTA PRINCIPAL — responde a Parte 1 e a Parte 2 de uma vez.
--
-- Uma varredura só da tabela produz as cinco estatísticas pedidas. Separar em
-- cinco consultas leria a mesma tabela cinco vezes e, pior, abriria espaço
-- para que uma delas divergisse das outras por um filtro esquecido.
-- ----------------------------------------------------------------------------
SELECT
    -- Parte 1 — visão geral
    count(*)                      AS qtd_total_linhas,
    min(created_at)               AS data_minima,
    max(created_at)               AS data_maxima,

    -- Parte 2 — a coluna `total`
    min(total)                    AS total_minimo,
    max(total)                    AS total_maximo,
    round(avg(total), 2)          AS total_medio
FROM raw.orders;


\echo ''
\echo '-- versão formatada em pt-BR (mesmos números, leitura humana) ---------'

SELECT
    to_char(count(*), 'FM999G999')                       AS qtd_total_linhas,
    to_char(min(created_at), 'DD/MM/YYYY HH24:MI:SS')    AS data_minima,
    to_char(max(created_at), 'DD/MM/YYYY HH24:MI:SS')    AS data_maxima,
    'R$ ' || to_char(min(total), 'FM999G999G990D00')     AS total_minimo,
    'R$ ' || to_char(max(total), 'FM999G999G990D00')     AS total_maximo,
    'R$ ' || to_char(avg(total), 'FM999G999G990D00')     AS total_medio
FROM raw.orders;
-- Depende de lc_numeric para o separador; os números crus estão acima.


-- ############################################################################
-- ############################################################################
--
--   APÊNDICE — DIAGNÓSTICO
--
--   As seis consultas a seguir não são pedidas pela Parte 1 nem pela Parte 2.
--   Elas existem para que a Parte 3 (interpretação) seja um argumento com
--   evidência numerada, e não uma opinião. Todas continuam obedecendo às
--   premissas: só `orders`, sem JOIN, sem filtro que descarte linha.
--
-- ############################################################################
-- ############################################################################

\echo ''
\echo '=============================================================='
\echo ' DIAGNÓSTICO 1 — Nulos em TODAS as 13 colunas'
\echo '=============================================================='
-- Pergunta: "há valores nulos?" — a resposta precisa cobrir a tabela inteira,
-- não a coluna que por acaso olhamos.

SELECT
    count(*) - count(id)              AS nulos_id,
    count(*) - count(order_number)    AS nulos_order_number,
    count(*) - count(channel)         AS nulos_channel,
    count(*) - count(customer_id)     AS nulos_customer_id,
    count(*) - count(salesperson_id)  AS nulos_salesperson_id,
    count(*) - count(location_id)     AS nulos_location_id,
    count(*) - count(status)          AS nulos_status,
    count(*) - count(subtotal)        AS nulos_subtotal,
    count(*) - count(discount_amount) AS nulos_discount_amount,
    count(*) - count(total)           AS nulos_total,
    count(*) - count(placed_at)       AS nulos_placed_at,
    count(*) - count(created_at)      AS nulos_created_at,
    count(*) - count(updated_at)      AS nulos_updated_at
FROM raw.orders;


\echo ''
\echo '=============================================================='
\echo ' DIAGNÓSTICO 2 — O nulo de salesperson_id é estrutural?'
\echo '=============================================================='
-- Se 100% dos nulos estiverem em um único canal, não é falha de coleta: é a
-- ausência legítima de vendedor em venda sem atendente. A diferença importa,
-- porque preencher isso com COALESCE seria inventar dado.

SELECT
    channel,
    count(*)                                                AS pedidos,
    count(*) - count(salesperson_id)                        AS sem_vendedor,
    round(100.0 * (count(*) - count(salesperson_id)) / count(*), 1) AS pct_sem_vendedor
FROM raw.orders
GROUP BY channel
ORDER BY channel;


\echo ''
\echo '=============================================================='
\echo ' DIAGNÓSTICO 3 — Mix de status: a média mistura o que?'
\echo '=============================================================='
-- A média de `total` soma quatro estágios do ciclo de vida do pedido.
-- `cancelled` e `draft` nunca viraram receita, mas entram na média.

SELECT
    status,
    count(*)                                          AS pedidos,
    round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct_pedidos,
    round(sum(total), 2)                              AS soma_total,
    round(100.0 * sum(total) / sum(sum(total)) OVER (), 2) AS pct_valor,
    round(avg(total), 2)                              AS ticket_medio
FROM raw.orders
GROUP BY status
ORDER BY soma_total DESC;


\echo ''
\echo '=============================================================='
\echo ' DIAGNÓSTICO 4 — Outliers em total: cerca de Tukey'
\echo '=============================================================='
-- A amplitude (32,62 a 127.262,02) parece alarmante isolada. A pergunta certa
-- não é "existe valor extremo?", e sim "a distribuição tem cauda pesada?".
-- Média ≈ mediana responde isso melhor que a amplitude.

WITH quartis AS (
    SELECT
        -- percentile_cont devolve double precision; o cast para numeric é
        -- necessário porque round(double, int) não existe no PostgreSQL,
        -- e mantém a aritmética da cerca em precisão exata.
        percentile_cont(0.25) WITHIN GROUP (ORDER BY total)::numeric AS q1,
        percentile_cont(0.50) WITHIN GROUP (ORDER BY total)::numeric AS mediana,
        percentile_cont(0.75) WITHIN GROUP (ORDER BY total)::numeric AS q3,
        avg(total)                                                   AS media,
        stddev_samp(total)                                           AS desvio
    FROM raw.orders
)
SELECT
    round(q1, 2)                                   AS q1,
    round(mediana, 2)                              AS mediana,
    round(q3, 2)                                   AS q3,
    round(media, 2)                                AS media,
    round(desvio, 2)                               AS desvio_padrao,
    round(media / mediana, 3)                      AS razao_media_mediana,
    round(q3 + 1.5 * (q3 - q1), 2)                 AS cerca_superior,
    (SELECT count(*) FROM raw.orders o, quartis q
      WHERE o.total > q.q3 + 1.5 * (q.q3 - q.q1))  AS acima_da_cerca,
    round(100.0 * (SELECT sum(o.total) FROM raw.orders o, quartis q
                    WHERE o.total > q.q3 + 1.5 * (q.q3 - q.q1))
                / (SELECT sum(total) FROM raw.orders), 2) AS pct_receita_acima_da_cerca,
    (SELECT count(*) FROM raw.orders WHERE total <= 0) AS total_zero_ou_negativo
FROM quartis;
-- Nota: o produto cartesiano com `quartis` é seguro — a CTE tem exatamente
-- uma linha. Continua sendo leitura só de `orders`.


\echo ''
\echo '=============================================================='
\echo ' DIAGNÓSTICO 5 — Recorte temporal: quanto do dado é futuro?'
\echo '=============================================================='
-- `created_at` vai até 31/12/2026. Pedido com data futura não é erro de
-- digitação neste dataset: é volume relevante, e qualquer análise de
-- tendência que o inclua está lendo um ano parcial como se fosse fechado.

SELECT
    date_part('year', created_at)::int  AS ano,
    count(*)                            AS pedidos,
    round(sum(total), 2)                AS soma_total,
    min(created_at)                     AS primeiro,
    max(created_at)                     AS ultimo
FROM raw.orders
GROUP BY 1
ORDER BY 1;

\echo ''
\echo '-- ... e o quanto disso é posterior a hoje --------------------------'

-- A data de referência sai na própria saída porque o número depende dela:
-- "8,7% do dado é futuro" só significa alguma coisa acompanhado do dia em
-- que a conta foi feita. Rodar este arquivo em dezembro devolve outro
-- percentual, e isso é a resposta correta, não uma inconsistência.
SELECT
    now()::date                                                    AS data_de_referencia,
    count(*) FILTER (WHERE created_at > now())                     AS pedidos_futuros,
    count(*)                                                       AS pedidos_total,
    round(100.0 * count(*) FILTER (WHERE created_at > now()) / count(*), 2) AS pct_futuro,
    max(created_at)                                                AS data_mais_distante
FROM raw.orders;


\echo ''
\echo '=============================================================='
\echo ' DIAGNÓSTICO 6 — Os três carimbos de tempo carregam informação?'
\echo '=============================================================='
-- Se placed_at = created_at = updated_at em todas as linhas, não existe linha
-- do tempo do pedido: é impossível medir lead time, tempo até pagamento ou
-- qualquer intervalo entre eventos. Isso não é sujeira — é ausência de sinal,
-- e limita o que a tabela consegue responder.

SELECT
    count(*)                                                        AS pedidos,
    count(*) FILTER (WHERE placed_at = created_at)                  AS placed_igual_created,
    count(*) FILTER (WHERE created_at = updated_at)                 AS created_igual_updated,
    count(*) FILTER (WHERE placed_at = created_at
                       AND created_at = updated_at)                 AS os_tres_iguais
FROM raw.orders;


\echo ''
\echo '=============================================================='
\echo ' DIAGNÓSTICO 7 — A aritmética da própria tabela fecha?'
\echo '=============================================================='
-- subtotal - discount_amount = total deveria valer em toda linha. É a
-- verificação de consistência interna mais barata que existe, e não depende
-- de nenhuma outra tabela.

SELECT
    count(*)                                                          AS pedidos,
    count(*) FILTER (WHERE subtotal - discount_amount = total)        AS aritmetica_fecha,
    count(*) FILTER (WHERE subtotal - discount_amount <> total)       AS aritmetica_quebra,
    count(*) FILTER (WHERE discount_amount = 0)                       AS sem_desconto,
    count(DISTINCT id)                                                AS ids_distintos,
    count(DISTINCT order_number)                                      AS order_numbers_distintos
FROM raw.orders;

\echo ''
\echo '=============================================================='
\echo ' Fim. Interpretação (Q1.3) em RESPOSTA.md.'
\echo '=============================================================='
