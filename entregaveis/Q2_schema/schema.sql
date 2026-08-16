-- ==========================================================================
-- LH Nautical — schema da camada `raw` (PostgreSQL)
-- ==========================================================================
--
-- GERADO AUTOMATICAMENTE por q2_gerar_schema.py (Questão 2).
-- Não editar à mão: rode o script novamente.
--
-- Fonte     : 1-lh_nautical_csv
-- Gerado em : 2026-08-15 23:44:03 -0300
-- Escopo    : 24 tabelas · 212 colunas · 433.424 linhas perfiladas
-- Opções    : --schema raw --varchar bucket --indices
--
-- CONVENÇÕES
--
--  · Todo identificador sai entre aspas duplas. A base tem colunas
--    chamadas number, value, action, series, total, status, method, currency, notes, reason, role, name;
--    sem aspas, parte delas colide com palavra reservada.
--
--  · O tipo de cada coluna foi inferido dos dados, e a evidência que
--    motivou a escolha está no comentário da própria linha.
--
--  · NOT NULL aparece somente nas colunas de chave primária.
--    Nulabilidade inferida de uma única extração é restrição falsa:
--    a coluna cheia hoje pode vir com nulo no extrato de amanhã, e o
--    schema quebraria na ingestão. O perfil de preenchimento está no
--    relatório (--relatorio), onde é informação e não armadilha.
--
--  · As chaves estrangeiras saem em bloco no fim do arquivo, depois
--    de todos os CREATE TABLE, e são DEFERRABLE INITIALLY IMMEDIATE.
--    Assim o carregador da Q3 pode abrir a transação com
--    SET CONSTRAINTS ALL DEFERRED, carregar os 24 arquivos em
--    qualquer ordem e deixar o PostgreSQL validar tudo no COMMIT.
--
-- ==========================================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS "raw";
SET search_path TO "raw";

-- ==========================================================================
-- §1  TABELAS
-- ==========================================================================

-- --------------------------------------------------------------------------
-- addresses  (addresses.csv)
--   3.998 linhas · 12 colunas · terminador LF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."addresses" CASCADE;
CREATE TABLE "raw"."addresses" (
    "id" INTEGER NOT NULL,                          -- 3998 valores inteiros, máximo 3998
    "customer_id" INTEGER,                          -- 3998 valores inteiros, máximo 2000
    "address_type" VARCHAR(16),                     -- 3998 valores textuais; len max 9
    "postal_code" VARCHAR(16),                      -- código de negócio, não medida (len max 9); aritmética não se aplica
    "street" VARCHAR(64),                           -- 3998 valores textuais; len max 35
    "number" INTEGER,                               -- 3998 valores inteiros, máximo 999
    "complement" VARCHAR(8),                        -- 1652 valores textuais; len max 8
    "district" VARCHAR(64),                         -- 3998 valores textuais; len max 33
    "city" VARCHAR(32),                             -- 3998 valores textuais; len max 27
    "state" VARCHAR(8),                             -- 3998 valores textuais; len max 2
    "country" VARCHAR(8),                           -- 3998 valores textuais; len max 2
    "is_primary" BOOLEAN,                           -- 3998 valores, todos em {TRUE, FALSE}
    CONSTRAINT "pk_addresses" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- attributes  (attributes.csv)
--   8 linhas · 3 colunas · terminador LF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."attributes" CASCADE;
CREATE TABLE "raw"."attributes" (
    "id" INTEGER NOT NULL,                           -- 8 valores inteiros, máximo 8
    "name" VARCHAR(16),                              -- 8 valores textuais; len max 10
    "data_type" VARCHAR(8),                          -- 8 valores textuais; len max 7
    CONSTRAINT "pk_attributes" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- brands  (brands.csv)
--   12 linhas · 6 colunas · terminador LF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."brands" CASCADE;
CREATE TABLE "raw"."brands" (
    "id" INTEGER NOT NULL,                       -- 12 valores inteiros, máximo 12
    "name" VARCHAR(16),                          -- 12 valores textuais; len max 14
    "country" VARCHAR(8),                        -- 7 valores textuais; len max 2
    "is_active" BOOLEAN,                         -- 12 valores, todos em {TRUE, FALSE}
    "created_at" TIMESTAMP,                      -- 12 valores, todos YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP,                      -- 12 valores, todos YYYY-MM-DD HH:MM:SS
    CONSTRAINT "pk_brands" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- categories  (categories.csv)
--   14 linhas · 7 colunas · terminador LF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."categories" CASCADE;
CREATE TABLE "raw"."categories" (
    "id" INTEGER NOT NULL,                           -- 14 valores inteiros, máximo 14
    "name" VARCHAR(32),                              -- 14 valores textuais; len max 20
    "slug" VARCHAR(32),                              -- 14 valores textuais; len max 20
    "parent_category_id" INTEGER,                    -- 11 valores inteiros, máximo 3
    "is_active" BOOLEAN,                             -- 14 valores, todos em {TRUE, FALSE}
    "created_at" TIMESTAMP,                          -- 14 valores, todos YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP,                          -- 14 valores, todos YYYY-MM-DD HH:MM:SS
    CONSTRAINT "pk_categories" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- customers  (customers.csv)
--   2.000 linhas · 11 colunas · terminador LF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."customers" CASCADE;
CREATE TABLE "raw"."customers" (
    "id" INTEGER NOT NULL,                          -- 2000 valores inteiros, máximo 2000
    "person_type" VARCHAR(8),                       -- 2000 valores textuais; len max 2
    "legal_name" VARCHAR(32),                       -- 2000 valores textuais; len max 32
    "trade_name" VARCHAR(32),                       -- 555 valores textuais; len max 27
    "tax_id" VARCHAR(16),                           -- código de negócio, não medida (len max 14); aritmética não se aplica
    "state_registration" VARCHAR(16),               -- código de negócio, não medida (len max 10); aritmética não se aplica
    "email" VARCHAR(64),                            -- 1996 valores textuais; len max 49
    "phone" VARCHAR(16),                            -- código de negócio, não medida (len max 14); aritmética não se aplica
    "is_active" BOOLEAN,                            -- 2000 valores, todos em {TRUE, FALSE}
    "created_at" TIMESTAMP,                         -- 2000 valores, todos YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP,                         -- 2000 valores, todos YYYY-MM-DD HH:MM:SS
    CONSTRAINT "pk_customers" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- employees  (employees.csv)
--   15 linhas · 11 colunas · terminador LF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."employees" CASCADE;
CREATE TABLE "raw"."employees" (
    "id" INTEGER NOT NULL,                          -- 15 valores inteiros, máximo 15
    "full_name" VARCHAR(32),                        -- 15 valores textuais; len max 25
    "cpf" VARCHAR(16),                              -- código de negócio, não medida (len max 11); aritmética não se aplica
    "email" VARCHAR(64),                            -- 15 valores textuais; len max 46
    "role" VARCHAR(16),                             -- 15 valores textuais; len max 11
    "primary_location_id" INTEGER,                  -- 15 valores inteiros, máximo 6
    "hire_date" DATE,                               -- 15 valores, todos YYYY-MM-DD sem componente de hora
    "termination_date" DATE,                        -- 2 valores, todos YYYY-MM-DD sem componente de hora
    "is_active" BOOLEAN,                            -- 15 valores, todos em {TRUE, FALSE}
    "created_at" TIMESTAMP,                         -- 15 valores, todos YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP,                         -- 15 valores, todos YYYY-MM-DD HH:MM:SS
    CONSTRAINT "pk_employees" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- fiscal_invoices  (fiscal_invoices.csv)
--   34.365 linhas · 11 colunas · terminador CRLF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."fiscal_invoices" CASCADE;
CREATE TABLE "raw"."fiscal_invoices" (
    "id" INTEGER NOT NULL,                                -- 34365 valores inteiros, máximo 35079
    "order_id" INTEGER,                                   -- 34365 valores inteiros, máximo 50000
    "nfe_number" VARCHAR(16),                             -- código de negócio, não medida (len max 12); aritmética não se aplica
    "nfe_access_key" VARCHAR(64),                         -- código de negócio, não medida (len max 44); aritmética não se aplica
    "series" VARCHAR(8),                                  -- código de negócio, não medida (len max 3); aritmética não se aplica
    "issued_at" TIMESTAMP,                                -- 34365 valores, todos YYYY-MM-DD HH:MM:SS
    "status" VARCHAR(16),                                 -- 34365 valores textuais; len max 10
    "total_amount" NUMERIC(10,2),                         -- 34365 valores decimais; até 6 dígitos inteiros e 2 decimais (+2 de folga)
    "xml_storage_uri" VARCHAR(128),                       -- 34365 valores textuais; len max 69
    "created_at" TIMESTAMP,                               -- 34365 valores, todos YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP,                               -- 34365 valores, todos YYYY-MM-DD HH:MM:SS
    CONSTRAINT "pk_fiscal_invoices" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- goods_receipt_items  (goods_receipt_items.csv)
--   4.733 linhas · 4 colunas · terminador LF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."goods_receipt_items" CASCADE;
CREATE TABLE "raw"."goods_receipt_items" (
    "id" INTEGER NOT NULL,                                    -- 4733 valores inteiros, máximo 4733
    "goods_receipt_id" INTEGER,                               -- 4733 valores inteiros, máximo 1548
    "purchase_order_item_id" INTEGER,                         -- 4733 valores inteiros, máximo 6059
    "quantity_received" NUMERIC(7,3),                         -- 4733 valores decimais; até 2 dígitos inteiros e 3 decimais (+2 de folga)
    CONSTRAINT "pk_goods_receipt_items" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- goods_receipts  (goods_receipts.csv)
--   1.548 linhas · 6 colunas · terminador LF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."goods_receipts" CASCADE;
CREATE TABLE "raw"."goods_receipts" (
    "id" INTEGER NOT NULL,                               -- 1548 valores inteiros, máximo 1548
    "purchase_order_id" INTEGER,                         -- 1548 valores inteiros, máximo 2000
    "received_by_employee_id" INTEGER,                   -- 1548 valores inteiros, máximo 15
    "received_at" TIMESTAMP,                             -- 1548 valores, todos YYYY-MM-DD HH:MM:SS
    "notes" VARCHAR(16),                                 -- 77 valores textuais; len max 15
    "created_at" TIMESTAMP,                              -- 1548 valores, todos YYYY-MM-DD HH:MM:SS
    CONSTRAINT "pk_goods_receipts" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- locations  (locations.csv)
--   6 linhas · 14 colunas · terminador LF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."locations" CASCADE;
CREATE TABLE "raw"."locations" (
    "id" INTEGER NOT NULL,                          -- 6 valores inteiros, máximo 6
    "name" VARCHAR(16),                             -- 6 valores textuais; len max 16
    "location_type" VARCHAR(16),                    -- 6 valores textuais; len max 9
    "postal_code" VARCHAR(16),                      -- código de negócio, não medida (len max 9); aritmética não se aplica
    "street" VARCHAR(32),                           -- 6 valores textuais; len max 24
    "number" INTEGER,                               -- 6 valores inteiros, máximo 381
    "complement" VARCHAR(8),                        -- 3 valores textuais; len max 7
    "district" VARCHAR(32),                         -- 6 valores textuais; len max 27
    "city" VARCHAR(32),                             -- 6 valores textuais; len max 18
    "state" VARCHAR(8),                             -- 6 valores textuais; len max 2
    "country" VARCHAR(8),                           -- 6 valores textuais; len max 2
    "is_active" BOOLEAN,                            -- 6 valores, todos em {TRUE, FALSE}
    "created_at" TIMESTAMP,                         -- 6 valores, todos YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP,                         -- 6 valores, todos YYYY-MM-DD HH:MM:SS
    CONSTRAINT "pk_locations" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- order_items  (order_items.csv)
--   147.320 linhas · 8 colunas · terminador CRLF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."order_items" CASCADE;
CREATE TABLE "raw"."order_items" (
    "id" INTEGER NOT NULL,                            -- 147320 valores inteiros, máximo 150321
    "order_id" INTEGER,                               -- 147320 valores inteiros, máximo 50000
    "product_variant_id" INTEGER,                     -- 147320 valores inteiros, máximo 1009
    "quantity" INTEGER,                               -- 147320 valores inteiros, máximo 10
    "unit_price" NUMERIC(8,2),                        -- 147320 valores decimais; até 4 dígitos inteiros e 2 decimais (+2 de folga)
    "icms_rate" NUMERIC(6,2),                         -- 147320 valores decimais; até 2 dígitos inteiros e 2 decimais (+2 de folga)
    "ipi_rate" NUMERIC(6,2),                          -- 147320 valores decimais; até 2 dígitos inteiros e 2 decimais (+2 de folga)
    "line_total" NUMERIC(9,2),                        -- 147320 valores decimais; até 5 dígitos inteiros e 2 decimais (+2 de folga)
    CONSTRAINT "pk_order_items" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- orders  (orders.csv)
--   48.998 linhas · 13 colunas · terminador CRLF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."orders" CASCADE;
CREATE TABLE "raw"."orders" (
    "id" INTEGER NOT NULL,                       -- 48998 valores inteiros, máximo 50000
    "order_number" VARCHAR(16),                  -- 48998 valores textuais; len max 9
    "channel" VARCHAR(16),                       -- 48998 valores textuais; len max 9
    "customer_id" INTEGER,                       -- 48998 valores inteiros, máximo 2000
    "salesperson_id" INTEGER,                    -- 24867 valores inteiros, máximo 10
    "location_id" INTEGER,                       -- 48998 valores inteiros, máximo 6
    "status" VARCHAR(16),                        -- 48998 valores textuais; len max 9
    "subtotal" NUMERIC(10,2),                    -- 48998 valores decimais; até 6 dígitos inteiros e 2 decimais (+2 de folga)
    "discount_amount" NUMERIC(9,2),              -- 48998 valores decimais; até 5 dígitos inteiros e 2 decimais (+2 de folga)
    "total" NUMERIC(10,2),                       -- 48998 valores decimais; até 6 dígitos inteiros e 2 decimais (+2 de folga)
    "placed_at" TIMESTAMP,                       -- 48998 valores, todos YYYY-MM-DD HH:MM:SS
    "created_at" TIMESTAMP,                      -- 48998 valores, todos YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP,                      -- 48998 valores, todos YYYY-MM-DD HH:MM:SS
    CONSTRAINT "pk_orders" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- payments  (payments.csv)
--   53.546 linhas · 9 colunas · terminador CRLF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."payments" CASCADE;
CREATE TABLE "raw"."payments" (
    "id" INTEGER NOT NULL,                         -- 53546 valores inteiros, máximo 54635
    "order_id" INTEGER,                            -- 53546 valores inteiros, máximo 50000
    "method" VARCHAR(16),                          -- 53546 valores textuais; len max 13
    "installments" INTEGER,                        -- 53546 valores inteiros, máximo 12
    "amount" NUMERIC(10,2),                        -- 53546 valores decimais; até 6 dígitos inteiros e 2 decimais (+2 de folga)
    "status" VARCHAR(8),                           -- 53546 valores textuais; len max 8
    "paid_at" TIMESTAMP,                           -- 41219 valores, todos YYYY-MM-DD HH:MM:SS
    "created_at" TIMESTAMP,                        -- 53546 valores, todos YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP,                        -- 53546 valores, todos YYYY-MM-DD HH:MM:SS
    CONSTRAINT "pk_payments" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- product_suppliers  (product_suppliers.csv)
--   1.520 linhas · 8 colunas · terminador LF
--   PK composta inferida e VALIDADA: 1520 linhas, 1520 combinações distintas
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."product_suppliers" CASCADE;
CREATE TABLE "raw"."product_suppliers" (
    "product_variant_id" INTEGER NOT NULL,                      -- 1520 valores inteiros, máximo 1009
    "supplier_id" INTEGER NOT NULL,                             -- 1520 valores inteiros, máximo 25
    "supplier_sku" VARCHAR(16),                                 -- código de negócio, não medida (len max 13); aritmética não se aplica
    "last_quoted_cost" NUMERIC(8,2),                            -- 1520 valores decimais; até 4 dígitos inteiros e 2 decimais (+2 de folga)
    "lead_time_days" INTEGER,                                   -- 1520 valores inteiros, máximo 45
    "is_preferred" BOOLEAN,                                     -- 1520 valores, todos em {TRUE, FALSE}
    "created_at" TIMESTAMP,                                     -- 1520 valores, todos YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP,                                     -- 1520 valores, todos YYYY-MM-DD HH:MM:SS
    CONSTRAINT "pk_product_suppliers" PRIMARY KEY ("product_variant_id", "supplier_id")
);

-- --------------------------------------------------------------------------
-- product_variants  (product_variants.csv)
--   1.009 linhas · 12 colunas · terminador LF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."product_variants" CASCADE;
CREATE TABLE "raw"."product_variants" (
    "id" INTEGER NOT NULL,                                 -- 1009 valores inteiros, máximo 1009
    "product_id" INTEGER,                                  -- 1009 valores inteiros, máximo 500
    "sku" VARCHAR(16),                                     -- código de negócio, não medida (len max 10); aritmética não se aplica
    "barcode_ean" VARCHAR(16),                             -- código de negócio, não medida (len max 13); aritmética não se aplica
    "sale_price" NUMERIC(8,2),                             -- 1009 valores decimais; até 4 dígitos inteiros e 2 decimais (+2 de folga)
    "cost_price" NUMERIC(8,2),                             -- 1009 valores decimais; até 4 dígitos inteiros e 2 decimais (+2 de folga)
    "weight_kg" NUMERIC(7,3),                              -- 1009 valores decimais; até 2 dígitos inteiros e 3 decimais (+2 de folga)
    "icms_rate" NUMERIC(6,2),                              -- 1009 valores decimais; até 2 dígitos inteiros e 2 decimais (+2 de folga)
    "ipi_rate" NUMERIC(6,2),                               -- 1009 valores decimais; até 2 dígitos inteiros e 2 decimais (+2 de folga)
    "is_active" BOOLEAN,                                   -- 1009 valores, todos em {TRUE, FALSE}
    "created_at" TIMESTAMP,                                -- 1009 valores, todos YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP,                                -- 1009 valores, todos YYYY-MM-DD HH:MM:SS
    CONSTRAINT "pk_product_variants" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- products  (products.csv)
--   500 linhas · 10 colunas · terminador LF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."products" CASCADE;
CREATE TABLE "raw"."products" (
    "id" INTEGER NOT NULL,                         -- 500 valores inteiros, máximo 500
    "name" VARCHAR(32),                            -- 500 valores textuais; len max 23
    "description" VARCHAR(64),                     -- 490 valores textuais; len max 48
    "brand_id" INTEGER,                            -- 500 valores inteiros, máximo 12
    "category_id" INTEGER,                         -- 500 valores inteiros, máximo 14
    "ncm_code" VARCHAR(8),                         -- código de negócio, não medida (len max 8); aritmética não se aplica
    "unit_of_measure" VARCHAR(8),                  -- 500 valores textuais; len max 2
    "is_active" BOOLEAN,                           -- 500 valores, todos em {TRUE, FALSE}
    "created_at" TIMESTAMP,                        -- 500 valores, todos YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP,                        -- 500 valores, todos YYYY-MM-DD HH:MM:SS
    CONSTRAINT "pk_products" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- purchase_order_items  (purchase_order_items.csv)
--   6.059 linhas · 6 colunas · terminador LF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."purchase_order_items" CASCADE;
CREATE TABLE "raw"."purchase_order_items" (
    "id" INTEGER NOT NULL,                                     -- 6059 valores inteiros, máximo 6059
    "purchase_order_id" INTEGER,                               -- 6059 valores inteiros, máximo 2000
    "product_variant_id" INTEGER,                              -- 6059 valores inteiros, máximo 1009
    "quantity_ordered" INTEGER,                                -- 6059 valores inteiros, máximo 50
    "unit_cost" NUMERIC(8,2),                                  -- 6059 valores decimais; até 4 dígitos inteiros e 2 decimais (+2 de folga)
    "line_total" NUMERIC(10,2),                                -- 6059 valores decimais; até 6 dígitos inteiros e 2 decimais (+2 de folga)
    CONSTRAINT "pk_purchase_order_items" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- purchase_orders  (purchase_orders.csv)
--   2.000 linhas · 13 colunas · terminador LF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."purchase_orders" CASCADE;
CREATE TABLE "raw"."purchase_orders" (
    "id" INTEGER NOT NULL,                                -- 2000 valores inteiros, máximo 2000
    "po_number" VARCHAR(16),                              -- 2000 valores textuais; len max 9
    "supplier_id" INTEGER,                                -- 2000 valores inteiros, máximo 25
    "buyer_id" INTEGER,                                   -- 2000 valores inteiros, máximo 13
    "destination_location_id" INTEGER,                    -- 2000 valores inteiros, máximo 6
    "status" VARCHAR(32),                                 -- 2000 valores textuais; len max 18
    "currency" VARCHAR(8),                                -- 2000 valores textuais; len max 3
    "subtotal" NUMERIC(10,2),                             -- 2000 valores decimais; até 6 dígitos inteiros e 2 decimais (+2 de folga)
    "total" NUMERIC(10,2),                                -- 2000 valores decimais; até 6 dígitos inteiros e 2 decimais (+2 de folga)
    "placed_at" TIMESTAMP,                                -- 2000 valores, todos YYYY-MM-DD HH:MM:SS
    "expected_delivery_at" DATE,                          -- 1713 valores, todos YYYY-MM-DD sem componente de hora
    "created_at" TIMESTAMP,                               -- 2000 valores, todos YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP,                               -- 2000 valores, todos YYYY-MM-DD HH:MM:SS
    CONSTRAINT "pk_purchase_orders" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- return_items  (return_items.csv)
--   1.384 linhas · 7 colunas · terminador CRLF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."return_items" CASCADE;
CREATE TABLE "raw"."return_items" (
    "id" INTEGER NOT NULL,                             -- 1384 valores inteiros, máximo 1409
    "return_id" INTEGER,                               -- 1384 valores inteiros, máximo 1000
    "order_item_id" INTEGER,                           -- 1384 valores inteiros, máximo 150286
    "quantity" NUMERIC(7,3),                           -- 1384 valores decimais; até 2 dígitos inteiros e 3 decimais (+2 de folga)
    "action" VARCHAR(8),                               -- 1384 valores textuais; len max 8
    "exchange_variant_id" INTEGER,                     -- 360 valores inteiros, máximo 1007
    "unit_refund_amount" NUMERIC(8,2),                 -- 1384 valores decimais; até 4 dígitos inteiros e 2 decimais (+2 de folga)
    CONSTRAINT "pk_return_items" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- returns  (returns.csv)
--   980 linhas · 10 colunas · terminador CRLF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."returns" CASCADE;
CREATE TABLE "raw"."returns" (
    "id" INTEGER NOT NULL,                        -- 980 valores inteiros, máximo 1000
    "return_number" VARCHAR(16),                  -- 980 valores textuais; len max 9
    "order_id" INTEGER,                           -- 980 valores inteiros, máximo 49988
    "customer_id" INTEGER,                        -- 980 valores inteiros, máximo 1997
    "received_at_location_id" INTEGER,            -- 980 valores inteiros, máximo 6
    "status" VARCHAR(16),                         -- 980 valores textuais; len max 9
    "reason" VARCHAR(64),                         -- 973 valores textuais; len max 33
    "total_refund_amount" NUMERIC(9,2),           -- 980 valores decimais; até 5 dígitos inteiros e 2 decimais (+2 de folga)
    "created_at" TIMESTAMP,                       -- 980 valores, todos YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP,                       -- 980 valores, todos YYYY-MM-DD HH:MM:SS
    CONSTRAINT "pk_returns" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- stock_levels  (stock_levels.csv)
--   6.054 linhas · 5 colunas · terminador LF
--   PK composta inferida e VALIDADA: 6054 linhas, 6054 combinações distintas
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."stock_levels" CASCADE;
CREATE TABLE "raw"."stock_levels" (
    "product_variant_id" INTEGER NOT NULL,                      -- 6054 valores inteiros, máximo 1009
    "location_id" INTEGER NOT NULL,                             -- 6054 valores inteiros, máximo 6
    "quantity_on_hand" NUMERIC(7,3),                            -- 6054 valores decimais; até 2 dígitos inteiros e 3 decimais (+2 de folga)
    "reorder_point" TEXT,                                       -- coluna 100% vazia na fonte (6054 linhas); tipo indeterminável
    "updated_at" TIMESTAMP,                                     -- 6054 valores, todos YYYY-MM-DD HH:MM:SS
    CONSTRAINT "pk_stock_levels" PRIMARY KEY ("product_variant_id", "location_id")
);

-- --------------------------------------------------------------------------
-- stock_movements  (stock_movements.csv)
--   115.312 linhas · 11 colunas · terminador CRLF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."stock_movements" CASCADE;
CREATE TABLE "raw"."stock_movements" (
    "id" INTEGER NOT NULL,                                -- 115312 valores inteiros, máximo 117427
    "product_variant_id" INTEGER,                         -- 115312 valores inteiros, máximo 1009
    "location_id" INTEGER,                                -- 115312 valores inteiros, máximo 6
    "movement_type" VARCHAR(16),                          -- 115312 valores textuais; len max 11
    "quantity" NUMERIC(8,3),                              -- 115312 valores decimais; até 3 dígitos inteiros e 3 decimais (+2 de folga)
    "reference_table" VARCHAR(16),                        -- 109418 valores textuais; len max 14
    "reference_id" INTEGER,                               -- 109418 valores inteiros, máximo 50000
    "employee_id" INTEGER,                                -- 57255 valores inteiros, máximo 15
    "notes" VARCHAR(64),                                  -- 11405 valores textuais; len max 34
    "occurred_at" TIMESTAMP,                              -- 115312 valores, todos YYYY-MM-DD HH:MM:SS
    "created_at" TIMESTAMP,                               -- 115312 valores, todos YYYY-MM-DD HH:MM:SS
    CONSTRAINT "pk_stock_movements" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- suppliers  (suppliers.csv)
--   25 linhas · 12 colunas · terminador LF
--   coluna surrogate `id`
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."suppliers" CASCADE;
CREATE TABLE "raw"."suppliers" (
    "id" INTEGER NOT NULL,                          -- 25 valores inteiros, máximo 25
    "legal_name" VARCHAR(32),                       -- 25 valores textuais; len max 30
    "trade_name" VARCHAR(16),                       -- 13 valores textuais; len max 11
    "country" VARCHAR(8),                           -- 25 valores textuais; len max 2
    "tax_id" VARCHAR(16),                           -- código de negócio, não medida (len max 14); aritmética não se aplica
    "tax_id_type" VARCHAR(8),                       -- 25 valores textuais; len max 4
    "email" VARCHAR(32),                            -- 25 valores textuais; len max 30
    "phone" VARCHAR(16),                            -- código de negócio, não medida (len max 13); aritmética não se aplica
    "contact_name" VARCHAR(32),                     -- 25 valores textuais; len max 27
    "is_active" BOOLEAN,                            -- 25 valores, todos em {TRUE, FALSE}
    "created_at" TIMESTAMP,                         -- 25 valores, todos YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP,                         -- 25 valores, todos YYYY-MM-DD HH:MM:SS
    CONSTRAINT "pk_suppliers" PRIMARY KEY ("id")
);

-- --------------------------------------------------------------------------
-- variant_attribute_values  (variant_attribute_values.csv)
--   2.018 linhas · 3 colunas · terminador LF
--   PK composta inferida e VALIDADA: 2018 linhas, 2018 combinações distintas
-- --------------------------------------------------------------------------
DROP TABLE IF EXISTS "raw"."variant_attribute_values" CASCADE;
CREATE TABLE "raw"."variant_attribute_values" (
    "product_variant_id" INTEGER NOT NULL,                      -- 2018 valores inteiros, máximo 1009
    "attribute_id" INTEGER NOT NULL,                            -- 2018 valores inteiros, máximo 8
    "value" VARCHAR(16),                                        -- 2018 valores textuais; len max 14
    CONSTRAINT "pk_variant_attribute_values" PRIMARY KEY ("product_variant_id", "attribute_id")
);

-- ==========================================================================
-- §2  CHAVES ESTRANGEIRAS  (37 constraints)
-- ==========================================================================
--
-- Aplicadas depois de todos os CREATE TABLE e declaradas DEFERRABLE,
-- de modo que a ordem de carga dos CSVs deixa de importar: dentro de
-- uma transação com SET CONSTRAINTS ALL DEFERRED, a validação inteira
-- acontece no COMMIT.
--
-- ON DELETE NO ACTION é deliberado. Esta é a camada `raw`: ela espelha
-- a fonte, e apagar em cascata aqui esconderia um problema de origem
-- em vez de expô-lo.
--
-- convenção de nome
ALTER TABLE "raw"."addresses" ADD CONSTRAINT "fk_addresses_customer_id"
    FOREIGN KEY ("customer_id") REFERENCES "raw"."customers" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."categories" ADD CONSTRAINT "fk_categories_parent_category_id"
    FOREIGN KEY ("parent_category_id") REFERENCES "raw"."categories" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."employees" ADD CONSTRAINT "fk_employees_primary_location_id"
    FOREIGN KEY ("primary_location_id") REFERENCES "raw"."locations" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."fiscal_invoices" ADD CONSTRAINT "fk_fiscal_invoices_order_id"
    FOREIGN KEY ("order_id") REFERENCES "raw"."orders" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."goods_receipt_items" ADD CONSTRAINT "fk_goods_receipt_items_goods_receipt_id"
    FOREIGN KEY ("goods_receipt_id") REFERENCES "raw"."goods_receipts" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."goods_receipt_items" ADD CONSTRAINT "fk_goods_receipt_items_purchase_order_item_id"
    FOREIGN KEY ("purchase_order_item_id") REFERENCES "raw"."purchase_order_items" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."goods_receipts" ADD CONSTRAINT "fk_goods_receipts_purchase_order_id"
    FOREIGN KEY ("purchase_order_id") REFERENCES "raw"."purchase_orders" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."goods_receipts" ADD CONSTRAINT "fk_goods_receipts_received_by_employee_id"
    FOREIGN KEY ("received_by_employee_id") REFERENCES "raw"."employees" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."order_items" ADD CONSTRAINT "fk_order_items_order_id"
    FOREIGN KEY ("order_id") REFERENCES "raw"."orders" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."order_items" ADD CONSTRAINT "fk_order_items_product_variant_id"
    FOREIGN KEY ("product_variant_id") REFERENCES "raw"."product_variants" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."orders" ADD CONSTRAINT "fk_orders_customer_id"
    FOREIGN KEY ("customer_id") REFERENCES "raw"."customers" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- anulação explícita
ALTER TABLE "raw"."orders" ADD CONSTRAINT "fk_orders_salesperson_id"
    FOREIGN KEY ("salesperson_id") REFERENCES "raw"."employees" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."orders" ADD CONSTRAINT "fk_orders_location_id"
    FOREIGN KEY ("location_id") REFERENCES "raw"."locations" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."payments" ADD CONSTRAINT "fk_payments_order_id"
    FOREIGN KEY ("order_id") REFERENCES "raw"."orders" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."product_suppliers" ADD CONSTRAINT "fk_product_suppliers_product_variant_id"
    FOREIGN KEY ("product_variant_id") REFERENCES "raw"."product_variants" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."product_suppliers" ADD CONSTRAINT "fk_product_suppliers_supplier_id"
    FOREIGN KEY ("supplier_id") REFERENCES "raw"."suppliers" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."product_variants" ADD CONSTRAINT "fk_product_variants_product_id"
    FOREIGN KEY ("product_id") REFERENCES "raw"."products" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."products" ADD CONSTRAINT "fk_products_brand_id"
    FOREIGN KEY ("brand_id") REFERENCES "raw"."brands" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."products" ADD CONSTRAINT "fk_products_category_id"
    FOREIGN KEY ("category_id") REFERENCES "raw"."categories" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."purchase_order_items" ADD CONSTRAINT "fk_purchase_order_items_purchase_order_id"
    FOREIGN KEY ("purchase_order_id") REFERENCES "raw"."purchase_orders" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."purchase_order_items" ADD CONSTRAINT "fk_purchase_order_items_product_variant_id"
    FOREIGN KEY ("product_variant_id") REFERENCES "raw"."product_variants" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."purchase_orders" ADD CONSTRAINT "fk_purchase_orders_supplier_id"
    FOREIGN KEY ("supplier_id") REFERENCES "raw"."suppliers" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- anulação explícita
ALTER TABLE "raw"."purchase_orders" ADD CONSTRAINT "fk_purchase_orders_buyer_id"
    FOREIGN KEY ("buyer_id") REFERENCES "raw"."employees" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."purchase_orders" ADD CONSTRAINT "fk_purchase_orders_destination_location_id"
    FOREIGN KEY ("destination_location_id") REFERENCES "raw"."locations" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."return_items" ADD CONSTRAINT "fk_return_items_return_id"
    FOREIGN KEY ("return_id") REFERENCES "raw"."returns" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."return_items" ADD CONSTRAINT "fk_return_items_order_item_id"
    FOREIGN KEY ("order_item_id") REFERENCES "raw"."order_items" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- anulação explícita
ALTER TABLE "raw"."return_items" ADD CONSTRAINT "fk_return_items_exchange_variant_id"
    FOREIGN KEY ("exchange_variant_id") REFERENCES "raw"."product_variants" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."returns" ADD CONSTRAINT "fk_returns_order_id"
    FOREIGN KEY ("order_id") REFERENCES "raw"."orders" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."returns" ADD CONSTRAINT "fk_returns_customer_id"
    FOREIGN KEY ("customer_id") REFERENCES "raw"."customers" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."returns" ADD CONSTRAINT "fk_returns_received_at_location_id"
    FOREIGN KEY ("received_at_location_id") REFERENCES "raw"."locations" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."stock_levels" ADD CONSTRAINT "fk_stock_levels_product_variant_id"
    FOREIGN KEY ("product_variant_id") REFERENCES "raw"."product_variants" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."stock_levels" ADD CONSTRAINT "fk_stock_levels_location_id"
    FOREIGN KEY ("location_id") REFERENCES "raw"."locations" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."stock_movements" ADD CONSTRAINT "fk_stock_movements_product_variant_id"
    FOREIGN KEY ("product_variant_id") REFERENCES "raw"."product_variants" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."stock_movements" ADD CONSTRAINT "fk_stock_movements_location_id"
    FOREIGN KEY ("location_id") REFERENCES "raw"."locations" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."stock_movements" ADD CONSTRAINT "fk_stock_movements_employee_id"
    FOREIGN KEY ("employee_id") REFERENCES "raw"."employees" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."variant_attribute_values" ADD CONSTRAINT "fk_variant_attribute_values_product_variant_id"
    FOREIGN KEY ("product_variant_id") REFERENCES "raw"."product_variants" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;
-- convenção de nome
ALTER TABLE "raw"."variant_attribute_values" ADD CONSTRAINT "fk_variant_attribute_values_attribute_id"
    FOREIGN KEY ("attribute_id") REFERENCES "raw"."attributes" ("id")
    DEFERRABLE INITIALLY IMMEDIATE;

-- ==========================================================================
-- §3  ÍNDICES DE APOIO
-- ==========================================================================
--
-- O PostgreSQL cria índice automaticamente para PRIMARY KEY, mas não
-- para o lado que REFERENCIA. Sem estes, todo JOIN pelo lado filho e
-- toda checagem de FK em UPDATE/DELETE do pai viram varredura completa.
--
CREATE INDEX IF NOT EXISTS "ix_addresses_customer_id" ON "raw"."addresses" ("customer_id");
CREATE INDEX IF NOT EXISTS "ix_categories_parent_category_id" ON "raw"."categories" ("parent_category_id");
CREATE INDEX IF NOT EXISTS "ix_employees_primary_location_id" ON "raw"."employees" ("primary_location_id");
CREATE INDEX IF NOT EXISTS "ix_fiscal_invoices_order_id" ON "raw"."fiscal_invoices" ("order_id");
CREATE INDEX IF NOT EXISTS "ix_goods_receipt_items_goods_receipt_id" ON "raw"."goods_receipt_items" ("goods_receipt_id");
CREATE INDEX IF NOT EXISTS "ix_goods_receipt_items_purchase_order_item_id" ON "raw"."goods_receipt_items" ("purchase_order_item_id");
CREATE INDEX IF NOT EXISTS "ix_goods_receipts_purchase_order_id" ON "raw"."goods_receipts" ("purchase_order_id");
CREATE INDEX IF NOT EXISTS "ix_goods_receipts_received_by_employee_id" ON "raw"."goods_receipts" ("received_by_employee_id");
CREATE INDEX IF NOT EXISTS "ix_order_items_order_id" ON "raw"."order_items" ("order_id");
CREATE INDEX IF NOT EXISTS "ix_order_items_product_variant_id" ON "raw"."order_items" ("product_variant_id");
CREATE INDEX IF NOT EXISTS "ix_orders_customer_id" ON "raw"."orders" ("customer_id");
CREATE INDEX IF NOT EXISTS "ix_orders_salesperson_id" ON "raw"."orders" ("salesperson_id");
CREATE INDEX IF NOT EXISTS "ix_orders_location_id" ON "raw"."orders" ("location_id");
CREATE INDEX IF NOT EXISTS "ix_payments_order_id" ON "raw"."payments" ("order_id");
CREATE INDEX IF NOT EXISTS "ix_product_suppliers_product_variant_id" ON "raw"."product_suppliers" ("product_variant_id");
CREATE INDEX IF NOT EXISTS "ix_product_suppliers_supplier_id" ON "raw"."product_suppliers" ("supplier_id");
CREATE INDEX IF NOT EXISTS "ix_product_variants_product_id" ON "raw"."product_variants" ("product_id");
CREATE INDEX IF NOT EXISTS "ix_products_brand_id" ON "raw"."products" ("brand_id");
CREATE INDEX IF NOT EXISTS "ix_products_category_id" ON "raw"."products" ("category_id");
CREATE INDEX IF NOT EXISTS "ix_purchase_order_items_purchase_order_id" ON "raw"."purchase_order_items" ("purchase_order_id");
CREATE INDEX IF NOT EXISTS "ix_purchase_order_items_product_variant_id" ON "raw"."purchase_order_items" ("product_variant_id");
CREATE INDEX IF NOT EXISTS "ix_purchase_orders_supplier_id" ON "raw"."purchase_orders" ("supplier_id");
CREATE INDEX IF NOT EXISTS "ix_purchase_orders_buyer_id" ON "raw"."purchase_orders" ("buyer_id");
CREATE INDEX IF NOT EXISTS "ix_purchase_orders_destination_location_id" ON "raw"."purchase_orders" ("destination_location_id");
CREATE INDEX IF NOT EXISTS "ix_return_items_return_id" ON "raw"."return_items" ("return_id");
CREATE INDEX IF NOT EXISTS "ix_return_items_order_item_id" ON "raw"."return_items" ("order_item_id");
CREATE INDEX IF NOT EXISTS "ix_return_items_exchange_variant_id" ON "raw"."return_items" ("exchange_variant_id");
CREATE INDEX IF NOT EXISTS "ix_returns_order_id" ON "raw"."returns" ("order_id");
CREATE INDEX IF NOT EXISTS "ix_returns_customer_id" ON "raw"."returns" ("customer_id");
CREATE INDEX IF NOT EXISTS "ix_returns_received_at_location_id" ON "raw"."returns" ("received_at_location_id");
CREATE INDEX IF NOT EXISTS "ix_stock_levels_product_variant_id" ON "raw"."stock_levels" ("product_variant_id");
CREATE INDEX IF NOT EXISTS "ix_stock_levels_location_id" ON "raw"."stock_levels" ("location_id");
CREATE INDEX IF NOT EXISTS "ix_stock_movements_product_variant_id" ON "raw"."stock_movements" ("product_variant_id");
CREATE INDEX IF NOT EXISTS "ix_stock_movements_location_id" ON "raw"."stock_movements" ("location_id");
CREATE INDEX IF NOT EXISTS "ix_stock_movements_employee_id" ON "raw"."stock_movements" ("employee_id");
CREATE INDEX IF NOT EXISTS "ix_variant_attribute_values_product_variant_id" ON "raw"."variant_attribute_values" ("product_variant_id");
CREATE INDEX IF NOT EXISTS "ix_variant_attribute_values_attribute_id" ON "raw"."variant_attribute_values" ("attribute_id");

COMMIT;
