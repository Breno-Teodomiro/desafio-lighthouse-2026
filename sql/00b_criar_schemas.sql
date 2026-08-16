-- ============================================================================
-- LH Nautical — ETAPA B: schemas do medalhão  (dentro do banco)
-- ============================================================================
--
-- ▶ ONDE EXECUTAR: conectado ao banco "lh_nautical".
--   No pgAdmin: clique com o botão direito em lh_nautical > Query Tool.
--   Rodar isto na conexão errada cria os schemas no banco errado.
--
-- É seguro executar mais de uma vez (idempotente).
-- ============================================================================

-- Trava de segurança: aborta se a conexão não for o banco certo.
DO $$
BEGIN
    IF current_database() <> 'lh_nautical' THEN
        RAISE EXCEPTION
            'ABORTADO: conectado a "%", esperado "lh_nautical". '
            'Abra o Query Tool sobre o banco lh_nautical e execute de novo.',
            current_database();
    END IF;
END $$;

-- Os três schemas da arquitetura medalhão.
CREATE SCHEMA IF NOT EXISTS raw    AUTHORIZATION lh_app;
CREATE SCHEMA IF NOT EXISTS silver AUTHORIZATION lh_app;
CREATE SCHEMA IF NOT EXISTS gold   AUTHORIZATION lh_app;

COMMENT ON SCHEMA raw    IS 'Carga bruta dos 24 CSVs, sem tratamento (questões 1 a 5).';
COMMENT ON SCHEMA silver IS 'Dados limpos e tipados.';
COMMENT ON SCHEMA gold   IS 'Modelo dimensional que alimenta o Power BI.';

-- Garante que lh_app é dono, mesmo que os schemas já existissem.
ALTER SCHEMA raw    OWNER TO lh_app;
ALTER SCHEMA silver OWNER TO lh_app;
ALTER SCHEMA gold   OWNER TO lh_app;

-- ============================================================================
-- CONFERÊNCIA
-- ============================================================================
SELECT current_database() AS banco_atual,
       string_agg(nspname, ', ' ORDER BY nspname) AS schemas_do_projeto,
       count(*) AS total
FROM pg_namespace
WHERE nspname IN ('raw', 'silver', 'gold');
-- Esperado: lh_nautical | gold, raw, silver | 3
