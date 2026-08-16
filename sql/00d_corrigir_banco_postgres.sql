-- ============================================================================
-- LH Nautical — CORREÇÃO: desfaz o que a etapa B fez no banco errado
-- ============================================================================
--
-- ▶ ONDE EXECUTAR: conectado ao banco "postgres", como superusuário.
--
-- CONTEXTO
-- O diagnóstico 00c confirmou que, no banco "postgres":
--   • existem os schemas raw, silver e gold, dono lh_app, TODOS VAZIOS
--     (0 objetos) — foram criados por engano;
--   • o schema public perdeu a permissão USAGE do papel PUBLIC. A ACL ficou
--     apenas "pg_database_owner=UC/pg_database_owner", faltando a entrada
--     "=U/pg_database_owner" que é padrão de fábrica no PostgreSQL 15+.
--
-- Este script desfaz as duas coisas e não toca em mais nada.
-- É idempotente: rodar duas vezes não causa efeito adicional.
-- ============================================================================

-- Trava 1: nunca rodar isto no banco do projeto, onde os schemas são legítimos.
DO $$
BEGIN
    IF current_database() = 'lh_nautical' THEN
        RAISE EXCEPTION
            'ABORTADO: em lh_nautical os schemas raw/silver/gold são legítimos.';
    END IF;
END $$;

-- Trava 2: recusa remover schema que tenha qualquer objeto dentro.
DO $$
DECLARE
    s     text;
    n_obj bigint;
BEGIN
    FOREACH s IN ARRAY ARRAY['raw', 'silver', 'gold'] LOOP
        SELECT count(*) INTO n_obj
        FROM pg_class c
        JOIN pg_namespace ns ON ns.oid = c.relnamespace
        WHERE ns.nspname = s;

        IF n_obj > 0 THEN
            RAISE EXCEPTION
                'ABORTADO: o schema "%" contém % objeto(s) no banco "%". '
                'Investigue antes de remover.', s, n_obj, current_database();
        END IF;
    END LOOP;
END $$;

-- 1) Remove os três schemas vazios criados por engano.
--    RESTRICT (padrão) faz falhar se houver conteúdo — nada some em silêncio.
DROP SCHEMA IF EXISTS raw    RESTRICT;
DROP SCHEMA IF EXISTS silver RESTRICT;
DROP SCHEMA IF EXISTS gold   RESTRICT;

-- 2) Restaura a permissão de fábrica do schema public.
--    No PostgreSQL 15+ o padrão concede USAGE (e não CREATE) ao PUBLIC.
GRANT USAGE ON SCHEMA public TO PUBLIC;

-- ============================================================================
-- CONFERÊNCIA
-- ============================================================================
SELECT current_database() AS banco,
       (SELECT count(*) FROM pg_namespace
         WHERE nspname IN ('raw', 'silver', 'gold'))            AS schemas_restantes,
       (SELECT array_to_string(nspacl, ' | ') FROM pg_namespace
         WHERE nspname = 'public')                              AS acl_public;
-- Esperado:
--   schemas_restantes = 0
--   acl_public contém DUAS entradas:
--     pg_database_owner=UC/pg_database_owner | =U/pg_database_owner
--   A segunda ("=U/") é o USAGE do PUBLIC restaurado.
