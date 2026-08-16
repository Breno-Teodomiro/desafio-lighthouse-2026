-- ============================================================================
-- Desafio Lighthouse 2026 — Questão 5: Dimensão de calendário
-- ============================================================================
--
-- PERGUNTA DO SR. ALMIR:
--   "Qual é o dia da semana, nas lojas físicas, em que temos a pior média de
--    vendas?" — para decidir se vale a pena fechar a loja nesses dias.
--
-- PREMISSAS OBRIGATÓRIAS:
--   · Período: da menor à maior data de venda presente no arquivo
--   · A loja esteve aberta TODOS os dias, inclusive fins de semana
--   · Apenas lojas físicas (channel = 'pos')
--   · Dia sem registro conta como venda = 0
--   · "Vendas diárias" = soma do valor da venda por dia
--   · A média por dia da semana considera TODOS os dias do calendário
--   · Nome do dia da semana em português
--
-- POR QUE ISTO NÃO É DETALHE:
--   O estagiário agrupou direto na tabela de vendas. Dias em que a loja abriu
--   e não vendeu nada simplesmente não existem em `orders`, então sumiram do
--   denominador. O resultado não é uma média um pouco otimista — é uma média
--   de OUTRA COISA: faturamento médio condicionado a ter havido venda.
--
--   Este arquivo calcula as duas e mostra lado a lado, porque a comparação é
--   a resposta da questão.
--
-- DUAS ARMADILHAS TÉCNICAS EVITADAS AQUI:
--
--   1. `to_char(data, 'TMDay')` NÃO é usado. Ele depende de lc_time do
--      servidor: em instalação padrão devolve 'Monday   ' (inglês, preenchido
--      com espaços até 9 caracteres) e nunca a forma '-feira'. O CASE explícito
--      abaixo é portátil e não depende de configuração de localidade.
--
--   2. `EXTRACT(ISODOW)` em vez de `EXTRACT(DOW)`. ISODOW numera 1=Segunda
--      até 7=Domingo, que já é a ordem da semana brasileira — o ORDER BY sai
--      correto sem nenhum CASE de reordenação. DOW numera 0=Domingo.
--
-- Como rodar:
--     psql -d lh_nautical -f q5_dim_calendario.sql
--
-- Autor: Breno Teodomiro · Desafio Técnico Lighthouse 2026 (Indicium)
-- ============================================================================

\echo ''
\echo '=============================================================='
\echo ' Q5.1 (a) — A DIMENSÃO DE DATAS'
\echo '=============================================================='

-- ----------------------------------------------------------------------------
-- O calendário é materializado como tabela para poder ser reaproveitado pelo
-- restante do arquivo e pelo dashboard. É criado no schema `gold`, nunca em
-- `raw` — `raw` espelha a fonte, e um calendário não veio de nenhum CSV.
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.dim_calendario;

CREATE TABLE gold.dim_calendario AS
WITH limites AS (
    -- O período vem dos DADOS, não de constante digitada: "todas as datas
    -- entre a menor e a maior data de venda presentes no arquivo".
    -- O recorte de canal entra já aqui, porque a pergunta é sobre loja física.
    SELECT min(created_at)::date AS data_inicio,
           max(created_at)::date AS data_fim
    FROM raw.orders
    WHERE channel = 'pos'
)
SELECT
    d::date                                          AS data,
    extract(isodow FROM d)::int                      AS num_dia_semana,   -- 1=Seg .. 7=Dom
    -- Nomes em pt-BR sem depender de lc_time do servidor.
    CASE extract(isodow FROM d)
        WHEN 1 THEN 'Segunda-feira'
        WHEN 2 THEN 'Terça-feira'
        WHEN 3 THEN 'Quarta-feira'
        WHEN 4 THEN 'Quinta-feira'
        WHEN 5 THEN 'Sexta-feira'
        WHEN 6 THEN 'Sábado'
        WHEN 7 THEN 'Domingo'
    END                                              AS nome_dia_semana,
    extract(year  FROM d)::int                       AS ano,
    extract(month FROM d)::int                       AS mes,
    CASE extract(month FROM d)
        WHEN  1 THEN 'Janeiro'   WHEN  2 THEN 'Fevereiro' WHEN  3 THEN 'Março'
        WHEN  4 THEN 'Abril'     WHEN  5 THEN 'Maio'      WHEN  6 THEN 'Junho'
        WHEN  7 THEN 'Julho'     WHEN  8 THEN 'Agosto'    WHEN  9 THEN 'Setembro'
        WHEN 10 THEN 'Outubro'   WHEN 11 THEN 'Novembro'  WHEN 12 THEN 'Dezembro'
    END                                              AS nome_mes,
    extract(quarter FROM d)::int                     AS trimestre,
    extract(day     FROM d)::int                     AS dia_do_mes,
    (extract(isodow FROM d) >= 6)                    AS eh_fim_de_semana
FROM limites,
     -- generate_series é o que materializa os dias que NÃO existem em `orders`.
     -- É a peça inteira da questão: sem ela, não há como um dia sem venda
     -- entrar no denominador.
     generate_series(limites.data_inicio, limites.data_fim, interval '1 day') AS d;

\echo ''
SELECT count(*)                          AS dias_no_calendario,
       min(data)                         AS primeira_data,
       max(data)                         AS ultima_data,
       count(DISTINCT nome_dia_semana)   AS nomes_distintos
FROM gold.dim_calendario;

\echo ''
\echo '-- amostra dos 7 primeiros dias --------------------------------------'
SELECT data, num_dia_semana, nome_dia_semana, eh_fim_de_semana
FROM gold.dim_calendario
ORDER BY data
LIMIT 7;


\echo ''
\echo '=============================================================='
\echo ' Q5.1 (b) — LEFT JOIN calendário x vendas, com zero nos vazios'
\echo '=============================================================='

-- ----------------------------------------------------------------------------
-- Vendas diárias das lojas físicas. O agrupamento é feito ANTES do join,
-- para que o calendário encontre no máximo uma linha por data — um join no
-- grão de pedido multiplicaria os dias do calendário.
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS gold.vw_venda_diaria_pos;

CREATE VIEW gold.vw_venda_diaria_pos AS
WITH vendas_por_dia AS (
    SELECT created_at::date AS data,
           sum(total)       AS valor_venda,
           count(*)         AS qtd_pedidos
    FROM raw.orders
    WHERE channel = 'pos'
    GROUP BY created_at::date
)
SELECT
    c.data,
    c.num_dia_semana,
    c.nome_dia_semana,
    c.ano,
    c.mes,
    -- É AQUI que o dia sem venda vira zero em vez de desaparecer.
    coalesce(v.valor_venda, 0)  AS valor_venda,
    coalesce(v.qtd_pedidos, 0)  AS qtd_pedidos,
    (v.data IS NULL)            AS dia_sem_venda
FROM gold.dim_calendario c
-- LEFT JOIN do CALENDÁRIO para as VENDAS. A direção é o ponto:
-- o calendário é a tabela dirigente e nenhum dia pode sumir.
LEFT JOIN vendas_por_dia v ON v.data = c.data;

\echo ''
SELECT count(*)                                      AS dias_totais,
       count(*) FILTER (WHERE dia_sem_venda)         AS dias_sem_venda,
       count(*) FILTER (WHERE NOT dia_sem_venda)     AS dias_com_venda,
       round(sum(valor_venda), 2)                    AS faturamento_pos_total
FROM gold.vw_venda_diaria_pos;


\echo ''
\echo '=============================================================='
\echo ' Q5.1 (c) — RESPOSTA: média de vendas por dia da semana'
\echo '=============================================================='

SELECT
    num_dia_semana                            AS n,
    nome_dia_semana                           AS dia_da_semana,
    count(*)                                  AS dias_no_periodo,
    count(*) FILTER (WHERE dia_sem_venda)     AS dias_sem_venda,
    round(sum(valor_venda), 2)                AS faturamento_total,
    -- avg() sobre a view já densificada: o denominador é o número de dias do
    -- CALENDÁRIO, porque os dias sem venda estão presentes com valor 0.
    round(avg(valor_venda), 2)                AS media_por_dia
FROM gold.vw_venda_diaria_pos
GROUP BY num_dia_semana, nome_dia_semana
ORDER BY media_por_dia ASC;   -- o pior dia aparece primeiro


\echo ''
\echo '=============================================================='
\echo ' A COMPARAÇÃO — o cálculo correto x o cálculo do estagiário'
\echo '=============================================================='
-- Esta é a consulta que responde à Q5.2. Ela roda as duas médias lado a lado
-- sobre exatamente os mesmos dados, e mostra que o DIAGNÓSTICO TROCA DE DIA.

SELECT
    num_dia_semana                                        AS n,
    nome_dia_semana                                       AS dia_da_semana,
    count(*)                                              AS dias_calendario,
    count(*) FILTER (WHERE NOT dia_sem_venda)             AS dias_com_venda,
    count(*) FILTER (WHERE dia_sem_venda)                 AS dias_sem_venda,

    -- CORRETO: divide pelo total de dias do calendário.
    round(avg(valor_venda), 2)                            AS media_com_calendario,

    -- ERRO DO ESTAGIÁRIO: divide só pelos dias em que houve venda.
    -- É o que um GROUP BY direto em `orders` produz, porque os dias sem
    -- registro nunca chegam à consulta.
    round(sum(valor_venda)
          / nullif(count(*) FILTER (WHERE NOT dia_sem_venda), 0), 2)
                                                          AS media_sem_calendario,

    round(sum(valor_venda) / nullif(count(*) FILTER (WHERE NOT dia_sem_venda), 0)
          - avg(valor_venda), 2)                          AS inflacao_r$,
    round(100.0 * (sum(valor_venda)
                   / nullif(count(*) FILTER (WHERE NOT dia_sem_venda), 0)
                   / nullif(avg(valor_venda), 0) - 1), 2) AS inflacao_pct
FROM gold.vw_venda_diaria_pos
GROUP BY num_dia_semana, nome_dia_semana
ORDER BY media_com_calendario ASC;


\echo ''
\echo '-- os dois vereditos, lado a lado ------------------------------------'

WITH base AS (
    SELECT nome_dia_semana,
           avg(valor_venda) AS media_correta,
           sum(valor_venda) / nullif(count(*) FILTER (WHERE NOT dia_sem_venda), 0)
                            AS media_estagiario
    FROM gold.vw_venda_diaria_pos
    GROUP BY nome_dia_semana
)
SELECT
    'COM calendário (correto)' AS metodo,
    (SELECT nome_dia_semana FROM base ORDER BY media_correta ASC LIMIT 1)    AS pior_dia,
    (SELECT round(min(media_correta), 2) FROM base)                          AS media_do_pior_dia
UNION ALL
SELECT
    'SEM calendário (estagiário)',
    (SELECT nome_dia_semana FROM base ORDER BY media_estagiario ASC LIMIT 1),
    (SELECT round(min(media_estagiario), 2) FROM base);


\echo ''
\echo '=============================================================='
\echo ' DIAGNÓSTICO — onde estão os 78 dias sem venda?'
\echo '=============================================================='
-- A distribuição desigual dos dias vazios entre os dias da semana é a razão
-- mecânica de o ranking mudar. Se estivessem distribuídos por igual, o erro
-- do estagiário inflaria todos os dias na mesma proporção e o RANKING
-- sobreviveria — só os valores estariam errados. Não é o caso.

SELECT
    num_dia_semana                          AS n,
    nome_dia_semana                         AS dia_da_semana,
    count(*)                                AS dias_no_periodo,
    count(*) FILTER (WHERE dia_sem_venda)   AS dias_sem_venda,
    round(100.0 * count(*) FILTER (WHERE dia_sem_venda) / count(*), 2) AS pct_vazio
FROM gold.vw_venda_diaria_pos
GROUP BY num_dia_semana, nome_dia_semana
ORDER BY dias_sem_venda DESC;

\echo ''
\echo '-- e por ano, para descartar concentração em um período isolado ------'
SELECT ano,
       count(*)                              AS dias,
       count(*) FILTER (WHERE dia_sem_venda) AS dias_sem_venda
FROM gold.vw_venda_diaria_pos
GROUP BY ano
ORDER BY ano;

\echo ''
\echo '=============================================================='
\echo ' Fim. Explicação (Q5.2) em RESPOSTA.md.'
\echo '=============================================================='
