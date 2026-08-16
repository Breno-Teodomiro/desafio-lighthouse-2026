-- ============================================================================
-- LH Nautical — ETAPA A: papel e banco  (nível de servidor)
-- ============================================================================
--
-- ▶ ONDE EXECUTAR: conectado ao banco "postgres", como superusuário.
--   No pgAdmin: clique com o botão direito no banco "postgres" > Query Tool.
--
-- ⚠️  ESTA INSTÂNCIA É COMPARTILHADA COM OUTROS PROJETOS.
--     Este script apenas CRIA objetos novos. Não altera, não remove e não
--     concede acesso a nenhum banco preexistente.
--
-- ▶ DEPOIS DESTE, execute 00b_criar_schemas.sql CONECTADO AO lh_nautical.
--   (Os schemas vivem dentro do banco, por isso são um arquivo separado —
--    rodar aquela parte na conexão errada cria os schemas no banco errado.)
--
-- ANTES DE EXECUTAR: troque 'TROQUE_ESTA_SENHA' pela senha de sua escolha.
-- A mesma senha vai no arquivo .env do projeto.
-- ============================================================================

-- 1) Papel exclusivo deste projeto.
--    Sem SUPERUSER, sem CREATEDB, sem CREATEROLE: não alcança seus outros
--    bancos nem consegue criar novos.
CREATE ROLE lh_app WITH LOGIN PASSWORD 'TROQUE_ESTA_SENHA'
    NOSUPERUSER NOCREATEDB NOCREATEROLE;

COMMENT ON ROLE lh_app IS
    'Aplicação do Desafio Lighthouse 2026. Acesso restrito ao banco lh_nautical.';

-- 2) Banco exclusivo deste projeto, com lh_app como dono.
CREATE DATABASE lh_nautical
    WITH OWNER = lh_app
         ENCODING = 'UTF8'
         TEMPLATE = template0;

COMMENT ON DATABASE lh_nautical IS
    'Desafio Lighthouse 2026 (Indicium) — dados da LH Nautical. Criado em 15/08/2026.';

-- 3) Só o dono e superusuários se conectam a este banco.
REVOKE CONNECT ON DATABASE lh_nautical FROM PUBLIC;
GRANT  CONNECT ON DATABASE lh_nautical TO lh_app;

-- 4) search_path padrão do papel, válido apenas dentro de lh_nautical.
ALTER ROLE lh_app IN DATABASE lh_nautical SET search_path TO raw, silver, gold, public;

-- ============================================================================
-- CONFERÊNCIA
-- ============================================================================
SELECT (SELECT count(*) FROM pg_roles    WHERE rolname = 'lh_app')      AS papel_criado,
       (SELECT count(*) FROM pg_database WHERE datname = 'lh_nautical') AS banco_criado;
-- Esperado: papel_criado = 1 | banco_criado = 1
--
-- ▶ PRÓXIMO: abrir Query Tool sobre o banco lh_nautical e rodar 00b_criar_schemas.sql
