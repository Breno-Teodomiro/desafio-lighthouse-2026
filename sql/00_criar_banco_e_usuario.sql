-- ============================================================================
-- LH Nautical — provisionamento inicial do banco
-- ============================================================================
-- Execute UMA VEZ, conectado como superusuário (postgres), no pgAdmin ou psql.
--
-- ⚠️  ESTA INSTÂNCIA É COMPARTILHADA COM OUTROS PROJETOS.
--     Este script apenas CRIA objetos novos. Ele não altera, não remove e não
--     concede acesso a nenhum banco preexistente.
--
-- ANTES DE EXECUTAR: troque 'TROQUE_ESTA_SENHA' por uma senha de sua escolha
-- e informe a mesma senha ao configurar o arquivo .env do projeto.
-- ============================================================================

-- 1) Papel exclusivo deste projeto.
--    Sem SUPERUSER, sem CREATEDB, sem CREATEROLE: ele não alcança seus
--    outros bancos nem consegue criar novos.
CREATE ROLE lh_app WITH LOGIN PASSWORD 'TROQUE_ESTA_SENHA'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;

COMMENT ON ROLE lh_app IS
    'Aplicação do Desafio Lighthouse 2026. Acesso restrito ao banco lh_nautical.';

-- 2) Banco exclusivo deste projeto, com lh_app como dono.
CREATE DATABASE lh_nautical
    WITH OWNER = lh_app
         ENCODING = 'UTF8'
         TEMPLATE = template0
         LC_COLLATE = 'pt-BR'
         LC_CTYPE = 'pt-BR';

COMMENT ON DATABASE lh_nautical IS
    'Desafio Lighthouse 2026 (Indicium) — dados da LH Nautical. Criado em 15/08/2026.';

-- 3) Impede que qualquer usuário logado se conecte por padrão.
--    Só lh_app (dono) e superusuários entram.
REVOKE CONNECT ON DATABASE lh_nautical FROM PUBLIC;
GRANT  CONNECT ON DATABASE lh_nautical TO lh_app;

-- ============================================================================
-- A PARTIR DAQUI: conecte-se AO BANCO lh_nautical (\c lh_nautical) antes de
-- executar. No pgAdmin, abra uma nova query window sobre lh_nautical.
-- ============================================================================

-- 4) Os três schemas da arquitetura medalhão.
CREATE SCHEMA IF NOT EXISTS raw    AUTHORIZATION lh_app;
CREATE SCHEMA IF NOT EXISTS silver AUTHORIZATION lh_app;
CREATE SCHEMA IF NOT EXISTS gold   AUTHORIZATION lh_app;

COMMENT ON SCHEMA raw    IS 'Carga bruta dos 24 CSVs, sem tratamento (questões 1 a 5).';
COMMENT ON SCHEMA silver IS 'Dados limpos e tipados.';
COMMENT ON SCHEMA gold   IS 'Modelo dimensional que alimenta o Power BI.';

-- 5) Tira o schema public do caminho — não usamos.
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- 6) search_path padrão do papel neste banco.
ALTER ROLE lh_app IN DATABASE lh_nautical SET search_path TO raw, silver, gold, public;

-- ============================================================================
-- CONFERÊNCIA — rode e verifique a saída
-- ============================================================================
SELECT current_database()                                   AS banco_atual,
       (SELECT count(*) FROM pg_roles WHERE rolname = 'lh_app')      AS papel_criado,
       (SELECT count(*) FROM information_schema.schemata
         WHERE schema_name IN ('raw', 'silver', 'gold'))             AS schemas_criados;
-- Esperado: banco_atual = lh_nautical | papel_criado = 1 | schemas_criados = 3
