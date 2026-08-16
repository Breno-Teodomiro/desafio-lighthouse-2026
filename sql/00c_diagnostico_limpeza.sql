-- ============================================================================
-- LH Nautical — DIAGNÓSTICO: a etapa B foi executada no banco errado?
-- ============================================================================
--
-- POR QUE ESTE ARQUIVO EXISTE
-- A primeira versão do script de provisionamento juntava, num arquivo só,
-- comandos de nível de servidor (papel, banco) e comandos de dentro do banco
-- (schemas). Executado inteiro com a janela conectada a "postgres", os
-- CREATE SCHEMA e o REVOKE do schema public caem no banco ERRADO.
--
-- ▶ ONDE EXECUTAR: conectado ao banco "postgres" (e repita em qualquer outro
--   banco onde você possa ter executado o script por engano).
--
-- A PARTE 1 é somente leitura. Não altera nada. Rode primeiro.
-- A PARTE 2 está comentada — só descomente o que o diagnóstico indicar.
-- ============================================================================


-- ============================================================================
-- PARTE 1 — DIAGNÓSTICO (somente leitura, seguro)
-- ============================================================================

-- 1.1 Existem schemas do projeto neste banco? (não deveriam, exceto em lh_nautical)
SELECT current_database()                      AS banco_inspecionado,
       n.nspname                               AS schema_indevido,
       pg_get_userbyid(n.nspowner)             AS dono,
       (SELECT count(*) FROM pg_class c
         WHERE c.relnamespace = n.oid)         AS objetos_dentro
FROM pg_namespace n
WHERE n.nspname IN ('raw', 'silver', 'gold')
ORDER BY n.nspname;
-- Em "postgres": o esperado é NENHUMA linha.
-- Se aparecerem linhas com objetos_dentro = 0, são schemas vazios criados por
-- engano e podem ser removidos com segurança na Parte 2.
-- Se objetos_dentro > 0, PARE e investigue antes de remover.


-- 1.2 O schema public deste banco perdeu permissões?
SELECT current_database()                          AS banco_inspecionado,
       nspname                                     AS schema,
       pg_get_userbyid(nspowner)                   AS dono,
       COALESCE(array_to_string(nspacl, E'\n'), '(sem ACL — PUBLIC perdeu tudo)') AS permissoes
FROM pg_namespace
WHERE nspname = 'public';
-- No PostgreSQL 15+, o padrão de fábrica concede USAGE ao PUBLIC:
--   pg_database_owner=UC/pg_database_owner
--   =U/pg_database_owner            <-- esta linha é o USAGE do PUBLIC
-- Se a linha "=U/..." SUMIU, o REVOKE atingiu este banco e outras aplicações
-- podem perder acesso ao schema public. Corrija na Parte 2.


-- 1.3 Panorama: onde os schemas do projeto existem em toda a instância?
--     (roda em qualquer banco; lista só o banco atual — repita se necessário)
SELECT current_database() AS banco,
       count(*) FILTER (WHERE nspname = 'raw')    AS tem_raw,
       count(*) FILTER (WHERE nspname = 'silver') AS tem_silver,
       count(*) FILTER (WHERE nspname = 'gold')   AS tem_gold
FROM pg_namespace
WHERE nspname IN ('raw', 'silver', 'gold');


-- ============================================================================
-- PARTE 2 — CORREÇÃO (descomente APENAS o que o diagnóstico apontou)
-- ============================================================================

-- 2.1 Remover schemas criados por engano NESTE banco.
--     RESTRICT (padrão) faz o comando falhar se houver qualquer objeto dentro,
--     o que é proposital: nada é apagado silenciosamente.
--     NUNCA rode isto conectado ao lh_nautical.
--
-- DO $$
-- BEGIN
--     IF current_database() = 'lh_nautical' THEN
--         RAISE EXCEPTION 'ABORTADO: em lh_nautical estes schemas são legítimos.';
--     END IF;
-- END $$;
--
-- DROP SCHEMA IF EXISTS raw    RESTRICT;
-- DROP SCHEMA IF EXISTS silver RESTRICT;
-- DROP SCHEMA IF EXISTS gold   RESTRICT;


-- 2.2 Restaurar a permissão padrão do schema public (só se 1.2 mostrou perda).
--
-- GRANT USAGE ON SCHEMA public TO PUBLIC;
--
-- Observação: no PostgreSQL 15+ o CREATE em public NÃO é concedido ao PUBLIC
-- por padrão. Só restaure o CREATE se este banco dependia disso antes:
-- GRANT CREATE ON SCHEMA public TO PUBLIC;


-- 2.3 Conferência após a correção — repita a Parte 1.
